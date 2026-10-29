"""Futures scalper execution loop — SCALPER.md component #7.

24/7 per-candle loop:
    1. MTF analysis         → alignment, chop detection
    2. Scanner consensus    → which strategies agree
    3. CandlePredictor      → P(next bar up)
    4. Optional sentiment   → Fear & Greed / news
    5. SignalFuser          → final (direction, confidence) or stand_aside
    6. RiskEngine gates     → sizing, circuit breakers, daily limits
    7. Futures broker       → open/close position on testnet (dry-run by default)

Dry-run by default: pass armed=True + confirm=HUMAN_CONFIRM_PHRASE to transmit.
Real money is NOT supported here (testnet only, Constitution R-B.4).
"""
from __future__ import annotations

import csv
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from ..config import HUB_ROOT, LiveConfig
from ..data import get_data
from ..live.risk import RiskEngine, RiskLimits, RiskState
from ..paper import HUMAN_CONFIRM_PHRASE
from ..scan import consensus, scan
from .fuse import FusedSignal, SignalFuser, ScannerConsensus
from .mtf import MTFAnalyzer
from .predict import CandlePredictor


# ---------------------------------------------------------------------------
# Risk wiring (pure helpers — testable without market data)
# ---------------------------------------------------------------------------

def risk_gate(limits: RiskLimits, state: dict, equity: float,
              mode: str = "futures_testnet") -> tuple[RiskEngine, bool, str]:
    """RiskEngine whose state is carried across steps in the scalper state dict.

    A fresh engine every step (the old code) can never see a drawdown, a daily loss or a trade count,
    so no breaker could trip. The state dict is updated in place; the caller persists it. A drawdown /
    equity-floor halt is sticky: clear ``risk_halted`` in scalper_state.json to resume.

    Only a REAL account read is evaluated. When the broker is unavailable ``_account`` substitutes a fake
    10,000; breakers on that would persist a sticky halt (or a bogus peak) from numbers that never existed,
    so in that case nothing is evaluated and the state dict is left untouched.
    """
    if mode != "futures_testnet":
        return RiskEngine(limits), True, "simulated equity: breakers not evaluated"
    rs = RiskState(
        peak_equity=float(state.get("equity_peak") or 0.0),
        day=state.get("daily_date") or "",
        day_start_equity=float(state.get("day_start_equity") or 0.0),
        trades_today=int(state.get("trades_today", 0)),
        halted=bool(state.get("risk_halted", False)),
        halt_reason=state.get("risk_halt_reason", ""),
    )
    engine = RiskEngine(limits, rs)
    engine.update_equity(equity)               # rolls the day, tracks the peak
    ok, reason = engine.can_trade(equity)      # (can_trade takes the equity FLOAT, not a dict)
    state.update(equity_peak=rs.peak_equity, daily_date=rs.day, day_start_equity=rs.day_start_equity,
                 trades_today=rs.trades_today, risk_halted=rs.halted, risk_halt_reason=rs.halt_reason)
    return engine, ok, reason


def size_units(risk: RiskEngine, equity: float, price: float, atr: float) -> float:
    """Units for a stop one ATR away. position_size wants the stop as a FRACTION of price; the old
    code passed the ATR in price units, making every size ~price-times too small."""
    if price <= 0:
        return 0.0
    stop_distance = atr if atr > 0 else price * 0.01
    return risk.position_size(equity, price, stop_distance / price)


_MIN_QTY = 0.001


def flatten_order(units: float, price: float, qty_fn=None) -> dict | None:
    """A reduce-only market order that closes the whole position (a risk halt must never freeze an open
    position: RiskEngine says exits are always allowed). None if there is nothing to close."""
    qty = qty_fn(abs(units)) if qty_fn else round(abs(units), 3)
    if qty <= _MIN_QTY:
        return None
    return {"side": "sell" if units > 0 else "buy", "qty": qty, "notional": round(qty * price, 2),
            "reduce_only": True}


def stop_order(units: float, price: float, atr: float) -> dict | None:
    """Protective stop one ATR from ``price`` — the same distance ``size_units`` sized the risk on, so the
    "risk_per_trade" premise holds. None for a flat target."""
    if units == 0:
        return None
    distance = atr if atr > 0 else price * 0.01
    long = units > 0
    return {"side": "sell" if long else "buy", "qty": round(abs(units), 3),
            "stop_price": round(price - distance if long else price + distance, 2)}


# ---------------------------------------------------------------------------
# Scalper decision record
# ---------------------------------------------------------------------------

@dataclass
class ScalperDecision:
    symbol: str
    bar_ts: str
    fused: FusedSignal
    price: float
    equity: float
    target_units: float         # what RiskEngine says to hold (signed, futures)
    current_units: float        # what's currently held (signed)
    delta: float                # target − current
    order: dict | None          # filled order dict if placed
    placed: bool = False
    armed: bool = False
    notes: list[str] = field(default_factory=list)

    def summary(self) -> str:
        act = "no order"
        if self.order:
            side = self.order.get("side", "?").upper()
            qty = self.order.get("qty", 0)
            note = " [SENT]" if self.placed else " [dry-run]"
            act = f"{side} {qty}{note}"
        return (
            f"scalper {self.symbol} bar={self.bar_ts} "
            f"dir={self.fused.direction:+d} conf={self.fused.confidence:.0%} "
            f"price={self.price:.2f} equity={self.equity:.2f} "
            f"pos={self.current_units:+g}→{self.target_units:+g} | {act}"
        )


# ---------------------------------------------------------------------------
# Scalper agent
# ---------------------------------------------------------------------------

class FuturesScalper:
    """One-symbol 24/7 futures scalper.  Dry-run by default."""

    def __init__(self, config: dict, agent_dir: Path | None = None) -> None:
        self.config = config
        self.agent_dir = agent_dir or (HUB_ROOT / "agents" / "$009-scalper")
        self.symbol: str = config.get("symbol", config.get("symbols", "BTC/USDT"))
        if isinstance(self.symbol, (list, tuple)):
            self.symbol = self.symbol[0]
        self.market: str = config.get("market", "crypto")
        self.timeframe: str = config.get("timeframe", "5m")
        self.mtf_tfs: list[str] = config.get("mtf_timeframes", ["1m", "5m", "15m", "1h"])
        self.data_start: str = config.get("data", {}).get("start", "2024-01-01")

        sc = config.get("scalper", {}) or {}
        self.leverage: int = int(sc.get("leverage", 5))
        self.risk_per_trade: float = float(sc.get("risk_per_trade_pct", 0.01))
        self.min_oos_accuracy: float = float(sc.get("min_oos_accuracy", 0.52))

        risk_cfg = config.get("risk", {}) or {}
        self.risk_limits = RiskLimits(
            max_leverage=float(risk_cfg.get("max_leverage", self.leverage)),
            risk_per_trade_pct=self.risk_per_trade,
            daily_loss_limit_pct=float(risk_cfg.get("daily_loss_limit_pct", 0.05)),
            max_drawdown_pct=float(risk_cfg.get("max_drawdown_pct", 0.25)),
            equity_floor=float(risk_cfg.get("equity_floor", 0.0)),
            max_trades_per_day=int(risk_cfg.get("max_trades_per_day", 50)),
        )

        fuse_cfg = config.get("fuse", {}) or {}
        self.fuser = SignalFuser(
            weights=fuse_cfg.get("weights"),
            thresholds=fuse_cfg.get("thresholds"),
        )
        self.predictor = CandlePredictor()
        self._predictor_trained = False
        self._broker: Any = None
        self._state_path = self.agent_dir / "scalper_state.json"
        self._trades_path = self.agent_dir / "results" / "scalper_trades.csv"

    # ------------------------------------------------------------------
    # State persistence
    # ------------------------------------------------------------------

    def _load_state(self) -> dict:
        if self._state_path.exists():
            try:
                return json.loads(self._state_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"last_bar": None, "equity_peak": None, "daily_pnl": 0.0,
                "daily_date": None, "trades_today": 0}

    def _save_state(self, state: dict) -> None:
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        self._state_path.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")

    def _record_trade(self, dec: ScalperDecision) -> None:
        self._trades_path.parent.mkdir(parents=True, exist_ok=True)
        is_new = not self._trades_path.exists()
        with self._trades_path.open("a", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            if is_new:
                w.writerow(["utc_time", "bar_ts", "symbol", "direction", "confidence",
                             "price", "equity", "delta_units", "order_side", "placed",
                             "p_up", "mtf_alignment", "scanner_bias", "reason"])
            w.writerow([
                datetime.now(timezone.utc).isoformat(), dec.bar_ts, dec.symbol,
                dec.fused.direction, dec.fused.confidence, dec.price, dec.equity,
                dec.delta,
                dec.order["side"] if dec.order else "",
                dec.placed,
                dec.fused.p_up, dec.fused.mtf_alignment, dec.fused.scanner_direction,
                dec.fused.reason,
            ])

    # ------------------------------------------------------------------
    # Core logic: one step
    # ------------------------------------------------------------------

    def _get_data(self, use_cache: bool = False) -> pd.DataFrame:
        cfg_data = self.config.get("data", {}) or {}
        return get_data(self.market, self.symbol, self.timeframe,
                        cfg_data.get("start", self.data_start), None,
                        use_cache=use_cache)

    def _train_predictor(self, data: pd.DataFrame, mtf_alignment: int) -> None:
        """Train (or retrain) the candle predictor on current data. Idempotent."""
        try:
            acc = self.predictor.fit(data, mtf_alignment=mtf_alignment)
            self._predictor_trained = True
            model_path = self.agent_dir / "results" / "predictor_state.json"
            self.predictor.save(model_path)
        except Exception:
            self._predictor_trained = False

    def _scanner_consensus(self) -> ScannerConsensus:
        """Run all strategy agents on this symbol and return consensus."""
        try:
            _, signals = scan(self.symbol, self.market, self.timeframe,
                              self.data_start, use_cache=True)
            raw = consensus(signals)
            return ScannerConsensus.from_dict(raw)
        except Exception as exc:
            # Degraded mode: scanner unavailable → neutral
            return ScannerConsensus(long=0, short=0, flat=0, err=1,
                                    net=0, bias="NEUTRAL", total=1)

    def _mtf_signal(self):
        """Run MTF analysis. Returns (mtf_signal, alignment, confidence)."""
        try:
            mtf = MTFAnalyzer(self.symbol, self.mtf_tfs, self.data_start,
                              use_cache=True)
            sig = mtf.run()
            return sig, sig.alignment, sig.confidence
        except Exception:
            return None, 0, 0.0  # degraded → chop / stand aside

    def _account(self) -> tuple[float, float, str]:
        """Returns (equity, held_units, mode). Simulates if broker unavailable."""
        try:
            from ..paper import binance_futures_testnet as fut
            if self._broker is None:
                self._broker = fut.connect(leverage=self.leverage)
            equity = fut.get_equity(self._broker)
            units = fut.get_position_units(self._broker, self.symbol)
            return equity, units, "futures_testnet"
        except Exception:
            cfg_bt = self.config.get("backtest", {}) or {}
            sim_equity = float(cfg_bt.get("starting_cash", 10_000))
            return sim_equity, 0.0, "simulated(no keys)"

    def _sync_stop(self, target_units: float, price: float, atr: float, confirm: str | None, notes: list) -> None:
        """After an order went out: drop stale orders and (unless flat) place a fresh protective stop. If the
        stop cannot be placed the position is closed rather than left unprotected."""
        from ..paper import binance_futures_testnet as fut
        try:
            fut.cancel_open_orders(self._broker, self.symbol, confirm)
        except Exception as exc:
            notes.append(f"cancel of old orders failed: {exc}")
        stop = stop_order(target_units, price, atr)
        if stop is None:
            return
        stop["qty"] = fut.round_qty(self._broker, self.symbol, stop["qty"])
        try:
            fut.submit_stop(self._broker, self.symbol, stop["side"], stop["qty"], stop["stop_price"], confirm)
            notes.append(f"protective stop {stop['side']} {stop['qty']} @ {stop['stop_price']}")
        except Exception as exc:
            try:
                fut.close_position(self._broker, self.symbol, confirm)
                outcome = "position flattened"
            except Exception as close_exc:
                outcome = f"FLATTEN ALSO FAILED: {close_exc}"
            notes.append(f"STOP FAILED: {exc}; {outcome}")

    def step(
        self,
        armed: bool = False,
        confirm: str | None = None,
        use_cache: bool = False,
    ) -> ScalperDecision:
        """Execute one scalper step (one closed bar)."""
        state = self._load_state()

        # 1. Fetch data
        data = self._get_data(use_cache=use_cache)
        closed = data.iloc[:-1]
        bar_ts = str(closed.index[-1])
        close_price = float(closed["Close"].iloc[-1])

        notes: list[str] = []

        # Idempotency: never re-act on the same bar
        if armed and state.get("last_bar") and bar_ts <= str(state["last_bar"]):
            notes.append("already acted on this bar; skipping")
            equity, units, _ = self._account()
            fused = FusedSignal(0, 0.0, True, "idempotency skip",
                                raw={"last_bar": state["last_bar"]})
            return ScalperDecision(self.symbol, bar_ts, fused, close_price,
                                   equity, 0.0, units, 0.0, None, False, armed, notes)

        # 2. MTF
        mtf_sig, mtf_alignment, mtf_conf = self._mtf_signal()

        # 3. Train predictor if not yet trained (lazy, once per session)
        if not self._predictor_trained:
            self._train_predictor(closed, mtf_alignment)
            if not self._predictor_trained:
                notes.append("predictor not fitted (not enough data or sklearn missing); using heuristic")

        # 4. Predict
        try:
            pred = self.predictor.predict(closed, mtf_alignment)
            p_up = pred.p_up
            oos_acc = pred.oos_accuracy
        except Exception:
            p_up = 0.5
            oos_acc = 0.0

        # 5. Scanner
        scanner = self._scanner_consensus()

        # 6. Fuse
        fused = self.fuser.fuse(
            scanner, mtf_alignment, mtf_conf, p_up, oos_acc
        )

        # 7. Account state
        equity, current_units, mode = self._account()

        # 8. RiskEngine check — state persists across steps (breakers can actually trip)
        risk, can_trade, block_reason = risk_gate(self.risk_limits, state, equity, mode)
        if mode == "futures_testnet":
            self._save_state(state)
        if not can_trade:
            notes.append(f"RiskEngine BLOCKED: {block_reason}")
            fused = FusedSignal(0, 0.0, True, f"risk: {block_reason}",
                                scanner_direction=fused.scanner_direction,
                                mtf_alignment=fused.mtf_alignment)

        # 9. Compute target position
        target_units = 0.0
        order: dict | None = None
        delta = 0.0
        atr = 0.0

        if not fused.stand_aside and can_trade and fused.direction != 0:
            atr = float((closed["High"] - closed["Low"]).ewm(span=14, adjust=False).mean().iloc[-1])
            target_units = size_units(risk, equity, close_price, atr) * fused.direction
            target_units = max(min(target_units, 1e6), -1e6)  # sanity cap

            delta = target_units - current_units
            min_qty = 0.001
            if abs(delta) > min_qty:
                side = "buy" if delta > 0 else "sell"
                try:
                    from ..paper import binance_futures_testnet as fut
                    qty = fut.round_qty(self._broker, self.symbol, abs(delta)) if self._broker else round(abs(delta), 3)
                except Exception:
                    qty = round(abs(delta), 3)
                order = {"side": side, "qty": qty, "notional": round(qty * close_price, 2)}

        # A risk halt blocks NEW exposure, never the exit: flatten whatever is open (reduce-only).
        flattening = False
        if not can_trade and current_units != 0:
            try:
                from ..paper import binance_futures_testnet as fut
                qty_fn = (lambda q: fut.round_qty(self._broker, self.symbol, q)) if self._broker else None
            except Exception:
                qty_fn = None
            order = flatten_order(current_units, close_price, qty_fn)
            if order is not None:
                flattening, target_units, delta = True, 0.0, -current_units
                notes.append("risk halt: flattening the open position (reduce-only)")

        dec = ScalperDecision(
            symbol=self.symbol, bar_ts=bar_ts, fused=fused,
            price=close_price, equity=equity,
            target_units=round(target_units, 6),
            current_units=round(current_units, 6),
            delta=round(delta, 6),
            order=order, armed=armed, notes=notes,
        )

        if order is None or (fused.stand_aside and not flattening):
            return dec

        if not armed:
            notes.append("dry-run: not sent (use --arm --confirm to transmit to futures testnet)")
            return dec

        # 10. Transmit to futures testnet
        try:
            from ..paper import binance_futures_testnet as fut
            from ..paper import HUMAN_CONFIRM_PHRASE as _TOKEN
            resp = fut.submit_order(
                self._broker,
                __import__("core.paper", fromlist=["PaperOrder"]).PaperOrder(
                    market="crypto", symbol=self.symbol,
                    side=order["side"], qty=order["qty"],
                ),
                confirm_token=confirm,
                reduce_only=bool(order.get("reduce_only")),
            )
            dec.placed = True
            notes.append(f"futures testnet order id={resp.get('id','?')} status={resp.get('status','?')}")
        except Exception as exc:
            notes.append(f"ORDER FAILED: {exc}")
            return dec

        # The order is out: whatever happens to the stop, record the bar so it is never acted on twice.
        try:
            self._sync_stop(0.0 if flattening else target_units, close_price, atr, confirm, notes)
        except Exception as exc:
            notes.append(f"STOP SYNC ERROR: {exc}")

        # Update state
        state["last_bar"] = bar_ts
        state["equity_peak"] = max(equity, float(state.get("equity_peak") or equity))
        state["trades_today"] = int(state.get("trades_today", 0)) + 1
        self._save_state(state)
        self._record_trade(dec)
        return dec
