"""Background trading bot loop — analyzes the selected symbol and paper-trades."""
import asyncio
from collections import deque
from datetime import datetime, timezone

from backend import config
from backend.analysis import indicators, signals
from backend.data import collector, database as db
from backend.strategy import engine, reflection
from backend.safety import circuit_breaker
from backend.trading.paper_engine import PaperEngine
from backend.trading.real_engine import RealEngine

# Ensure tables exist before any engine/bot reads persisted state at import time.
db.init_db()

# Timeframe -> milliseconds, for detecting a still-forming last candle.
_TF_MS = {
    "1m": 60_000, "3m": 180_000, "5m": 300_000, "15m": 900_000, "30m": 1_800_000,
    "1h": 3_600_000, "2h": 7_200_000, "4h": 14_400_000, "6h": 21_600_000,
    "8h": 28_800_000, "12h": 43_200_000, "1d": 86_400_000,
}


# F4: how many failed cycles in a row before the bot auto-pauses itself, and how
# old a completed cycle may be before the feed counts as stale (seconds).
MAX_CONSECUTIVE_ERRORS = 5
STALE_FEED_SECONDS = 60.0
# T03's consensus may download bars the first time; a slow T03 means "no veto", never a stalled cycle.
T03_TIMEOUT_S = 20.0

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class TradingBot:
    def __init__(self):
        self.symbol = db.get_state("active_symbol", config.DEFAULT_SYMBOL)
        self.timeframe = db.get_state("active_timeframe", config.DEFAULT_TIMEFRAME)
        self.running = db.get_state("bot_running", "false") == "true"
        self.interval = 12  # seconds between analysis cycles
        self.paper = PaperEngine()
        self.real = RealEngine()
        self.active_mode = "paper"   # which engine last handled a cycle
        self.last_signal: dict | None = None
        self.last_price: float | None = None
        self.last_indicators: dict | None = None
        self.last_ticker: dict | None = None
        self.activity: deque = deque(maxlen=120)   # live terminal feed
        self._subscribers: set[asyncio.Queue] = set()
        # F4: liveness telemetry — when the last cycle completed, and how many
        # cycles in a row have raised. N consecutive failures auto-pause the bot
        # (purana/stale feed par trade nahi) instead of trading blind.
        self.last_cycle_ts: str | None = None
        self.consecutive_errors: int = 0

    # ---------- pub/sub for websocket ----------
    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=80)
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        self._subscribers.discard(q)

    async def _broadcast(self, event: dict):
        for q in list(self._subscribers):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass

    def log(self, level: str, message: str):
        entry = {"ts": _now_iso(), "level": level, "message": message}
        self.activity.append(entry)
        return entry

    # ---------- control ----------
    def set_symbol(self, symbol: str, timeframe: str | None = None):
        self.symbol = symbol
        db.set_state("active_symbol", symbol)
        if timeframe:
            self.timeframe = timeframe
            db.set_state("active_timeframe", timeframe)
        self.log("info", f"Instrument switched to {symbol} @ {self.timeframe}")

    def start(self):
        self.running = True
        db.set_state("bot_running", "true")
        self.log("ok", "Engine STARTED — scanning market")

    def stop(self):
        self.running = False
        db.set_state("bot_running", "false")
        self.log("warn", "Engine STOPPED")

    # ---------- F4: liveness ----------
    def feed_fresh(self) -> tuple[bool, float | None]:
        """(fresh, age_seconds). A bot that never completed a cycle has no
        telemetry yet — fresh only when explicitly running is False (idle, not
        stale). A RUNNING bot with an old/no cycle is stale: do not trust its
        last price or signal."""
        if self.last_cycle_ts is None:
            return (not self.running), None
        try:
            age = (datetime.now(timezone.utc)
                   - datetime.fromisoformat(self.last_cycle_ts)).total_seconds()
        except ValueError:
            return False, None
        return age <= STALE_FEED_SECONDS, round(age, 1)

    def _note_cycle_ok(self):
        self.last_cycle_ts = _now_iso()
        self.consecutive_errors = 0

    def _note_cycle_error(self):
        self.consecutive_errors += 1
        if self.consecutive_errors >= MAX_CONSECUTIVE_ERRORS and self.running:
            self.stop()
            self.log("error",
                     f"feed stale ({self.consecutive_errors} failed cycles) — "
                     f"auto-paused, resume manually after checking connectivity")

    # ---------- decision data ----------
    def _closed_bars(self, ohlcv: list) -> list:
        """Drop the still-forming last candle so signals act on CLOSED bars only.

        ccxt returns the in-progress candle as the last element; its OHLC repaint
        until the bar closes. Deciding on it makes entries fire on values that
        revert intrabar. A candle opening at ts covers [ts, ts+tf); it is closed
        once now >= ts+tf.
        """
        if len(ohlcv) < 2:
            return ohlcv
        tf_ms = _TF_MS.get(self.timeframe, 0)
        if not tf_ms:
            return ohlcv
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        last_open = ohlcv[-1][0]
        if now_ms < last_open + tf_ms:      # last candle still forming -> drop it
            return ohlcv[:-1]
        return ohlcv

    # ---------- engine routing ----------
    def _active_engine(self):
        """Real engine only when fully gated-on; otherwise the paper engine."""
        ok, _ = self.real.ready()
        return (self.real, "real") if ok else (self.paper, "paper")

    def _real_daily_base(self, equity_now: float) -> float:
        """Real account size the daily-loss % applies to, snapshot at day start."""
        today = datetime.now(timezone.utc).date().isoformat()
        if db.get_state("real_base_date") != today:
            db.set_state("real_base_date", today)
            db.set_state("real_base_equity", str(equity_now))
        return float(db.get_state("real_base_equity", str(equity_now)))

    async def _decide(self, df, params: dict):
        """T01's signal, then the T03 soft veto on an entry (off the event loop; a slow or
        failing T03 means no veto)."""
        sig = signals.generate_signal(df, params)
        if sig.action != "buy":
            return sig
        try:
            out = await asyncio.wait_for(
                asyncio.to_thread(engine.apply_t03_veto, sig, self.symbol), T03_TIMEOUT_S)
        except Exception:  # includes the timeout
            return sig
        if out.details.get("t03_veto"):
            self.log("info", f"{out.reason}")
        return out

    # ---------- main loop ----------
    async def run_forever(self):
        while True:
            try:
                if self.running:
                    await self._cycle()
                    self._note_cycle_ok()
            except Exception as exc:  # keep the loop alive on transient errors
                self._note_cycle_error()
                self.log("error", f"cycle error: {exc}")
                await self._broadcast({"type": "error", "message": str(exc),
                                       "consecutive_errors": self.consecutive_errors})
            await asyncio.sleep(self.interval)

    async def _cycle(self):
        # Fetch market data (blocking ccxt calls off the event loop)
        ohlcv = await asyncio.to_thread(
            collector.fetch_ohlcv, self.symbol, self.timeframe, 250
        )
        ticker = await asyncio.to_thread(collector.fetch_ticker, self.symbol)
        try:
            order_book = await asyncio.to_thread(
                collector.fetch_order_book, self.symbol, 12
            )
        except Exception:
            order_book = {"bids": [], "asks": []}

        raw = ticker["last"] or (ohlcv[-1][4] if ohlcv else 0.0)
        try:
            price = float(raw)
        except (TypeError, ValueError):
            price = 0.0
        self.last_ticker = ticker

        # A zero/NaN price would make every stop-loss compare True and liquidate
        # the whole book at price 0. Never act on a non-positive price — skip the
        # entire cycle (no exits, no entries) and surface it.
        if not (price > 0):
            self.log("warn", f"skipped cycle: invalid price ({raw!r}) for {self.symbol}")
            await self._broadcast({"type": "error",
                                   "message": f"invalid price for {self.symbol}; cycle skipped"})
            return
        self.last_price = price

        # Route to the real engine only when the gate is unlocked, the operator
        # enabled it, creds exist and nothing is halted — otherwise paper.
        trader, mode = self._active_engine()
        self.active_mode = mode
        mark = {self.symbol: price}

        # Mark EVERY held symbol, not just the active one. Positions are only
        # opened on the active symbol, but the operator can switch symbols while
        # a position stays open. Without its own mark price, check_exits() skips
        # that position (price is None) and its stop-loss / take-profit never
        # fire — a stranded, unmanaged position. Pull a fresh price for each
        # other held symbol so its exits are always evaluated.
        try:
            for pos in await asyncio.to_thread(trader.open_positions):
                sym = pos["symbol"]
                if sym in mark:
                    continue
                try:
                    t = await asyncio.to_thread(collector.fetch_ticker, sym)
                    mp = t.get("last")
                    if mp and float(mp) > 0:
                        mark[sym] = float(mp)
                except Exception as exc:
                    self.log("warn", f"mark price fetch failed for {sym}: {exc}")
        except Exception as exc:
            self.log("warn", f"could not enumerate open positions: {exc}")

        # DB (and, in real mode, network) work runs off the event loop so a slow
        # query/order never stalls the WebSocket broadcasts or the API.
        if mode == "real":
            try:
                eq = await asyncio.to_thread(trader.equity, mark)
                base = self._real_daily_base(eq)
            except Exception as exc:
                self.log("error", f"real equity read failed: {exc}")
                base = None
            allowed, msg = await asyncio.to_thread(circuit_breaker.trading_allowed, "real", base)
        else:
            allowed, msg = await asyncio.to_thread(circuit_breaker.trading_allowed, "paper")

        # Manage existing positions first (stop-loss / take-profit)
        try:
            closed = await asyncio.to_thread(trader.check_exits, mark)
        except Exception as exc:
            self.log("error", f"exit check failed ({mode}): {exc}")
            closed = []
        did_close = bool(closed)   # did any position resolve this cycle?
        for c in closed:
            self.log("trade", f"EXIT {c['symbol']} @ {price:.4f} "
                              f"{c['exit_reason']} PnL {c['pnl']:+.2f}")

        # Analyze on CLOSED bars only (the forming candle repaints).
        bars = self._closed_bars(ohlcv)
        df = indicators.compute_all(bars)
        cur_params = engine.load_params()
        signal = await self._decide(df, cur_params)
        # Latest ATR feeds volatility-adaptive stops/sizing; NaN while warming up.
        atr_v = signals._safe(df.iloc[-1].get("atr"), 0.0) if len(df) else 0.0
        # Non-acting foresight (conservative/standard/aggressive) for the dashboard.
        predictions = engine.predict_scenarios(df)
        self.last_indicators = signal.details.get("indicators", {})
        self.last_signal = {
            "action": signal.action,
            "confidence": round(signal.confidence, 2),
            "reason": signal.reason,
            "price": price,
            "details": signal.details,
        }

        opened = None
        tag = mode.upper()
        try:
            if allowed and signal.action == "buy":
                # Tag the entry with its loss-attribution context so reflection can
                # later say WHY it lost; stop_mult carries any reflection-widened stop.
                meta = {
                    "factor": signal.details.get("dominant_factor"),
                    "regime": signal.details.get("regime"),
                    "adx": signal.details.get("adx"),
                    "stop_mult": cur_params.get("atr_stop_mult", 0.0),
                }
                opened = await asyncio.to_thread(trader.open_trade, self.symbol, price, signal.reason, atr_v, meta)
                if opened:
                    self.log("trade", f"[{tag}] ENTRY BUY {self.symbol} @ {price:.4f} "
                                      f"qty {opened['quantity']:.6f}")
                else:
                    self.log("info", f"[{tag}] BUY signal — skipped (limit/dup/halt/min-notional)")
            elif signal.action == "sell":
                for pos in await asyncio.to_thread(trader.open_positions):
                    if pos["symbol"] == self.symbol:
                        res = await asyncio.to_thread(trader.close_trade, pos, price, "signal_sell")
                        did_close = True
                        self.log("trade", f"[{tag}] EXIT SELL {self.symbol} @ {price:.4f} "
                                          f"PnL {res['pnl']:+.2f}")
            else:
                self.log("scan", f"{self.symbol} {price:.4f} · {signal.reason}")
        except Exception as exc:
            self.log("error", f"order failed ({mode}): {exc}")

        # Learn only when a trade actually resolved this cycle — not every
        # wall-clock tick, which would drive the threshold to its clamp in minutes.
        # self_tune moves the global net_threshold; reflection then diagnoses WHY
        # recent trades lost and corrects the specific cause (different knobs, no
        # collision). Both run off the event loop.
        if did_close:
            await asyncio.to_thread(engine.self_tune)
            corrections = await asyncio.to_thread(reflection.diagnose_and_correct, mode)
            if corrections:
                self.log("info", f"[{tag}] reflection tuned: {', '.join(corrections)}")
        params = engine.load_params()

        await self._broadcast({
            "type": "tick",
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "price": price,
            "ticker": ticker,
            "order_book": order_book,
            "signal": self.last_signal,
            "indicators": self.last_indicators,
            "predictions": predictions,
            "params": params,
            "opened": opened,
            "closed": closed,
            "mode": mode,
            "running": self.running,
            "trading_allowed": allowed,
            "halt_reason": None if allowed else msg,
            "activity": list(self.activity)[-12:],
            "ts": _now_iso(),
        })


bot = TradingBot()
