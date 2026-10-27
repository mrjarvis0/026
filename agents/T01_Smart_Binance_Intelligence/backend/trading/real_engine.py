"""Real trading engine — places ACTUAL Binance orders.

Locked by default. It operates only when ALL of these hold:
  1. the accuracy gate is unlocked (performance.is_real_trading_unlocked()),
  2. Binance API credentials are configured,
  3. the operator has explicitly enabled real mode, AND
  4. nothing has halted trading (emergency stop / daily-loss circuit breaker).

It mirrors PaperEngine's interface (open_trade / close_trade / check_exits /
open_positions / equity) so the bot can route to it transparently. Every order
is sized by risk, rounded to the market's lot precision, checked against the
exchange min-notional, and persisted to the DB under mode='real'.

Note: if BINANCE_TESTNET=true, collector routes to Binance's testnet, so the
"real" path is first exercised against test funds — a deliberate safety ramp.
"""
from datetime import datetime, timezone

from backend import config
from backend.analysis import risk
from backend.data import collector, database as db
from backend.safety import circuit_breaker
from backend.trading import fees, performance

MODE = "real"


class RealTradingLocked(Exception):
    pass


class RealEngine:
    def __init__(self):
        self.enabled = db.get_state("real_enabled", "false") == "true"

    # ---------- gating ----------
    def ready(self) -> tuple[bool, str]:
        """Whether real trading may operate right now. Never raises."""
        if not performance.is_real_trading_unlocked():
            return False, (f"accuracy gate locked (need >={config.ACCURACY_UNLOCK_THRESHOLD}% "
                           f"over {config.ACCURACY_MIN_TRADES}+ paper trades)")
        if not (config.BINANCE_API_KEY and config.BINANCE_API_SECRET):
            return False, "no Binance API credentials configured"
        if not self.enabled:
            return False, "real mode not enabled by operator"
        return True, "ready"

    def _guard(self) -> None:
        ok, why = self.ready()
        if not ok:
            raise RealTradingLocked(why)

    def enable(self) -> None:
        """Allowed only when the gate is unlocked AND credentials exist."""
        if not performance.is_real_trading_unlocked():
            raise RealTradingLocked("Cannot enable real mode before the accuracy gate unlocks.")
        if not (config.BINANCE_API_KEY and config.BINANCE_API_SECRET):
            raise RealTradingLocked("Cannot enable real mode without Binance API credentials.")
        self.enabled = True
        db.set_state("real_enabled", "true")
        # Snapshot starting capital once, so real ROI is measured against it.
        if not db.get_state("real_start_equity"):
            try:
                bal = collector.get_exchange().fetch_balance()
                db.set_state("real_start_equity",
                             str(float((bal.get("free") or {}).get("USDT", 0.0) or 0.0)))
            except Exception:
                pass

    def disable(self) -> None:
        self.enabled = False
        db.set_state("real_enabled", "false")

    # ---------- account reads ----------
    def open_positions(self) -> list[dict]:
        return db.get_open_trades(mode=MODE)

    def _free_quote(self, symbol: str) -> float:
        quote = symbol.split("/")[1]
        bal = collector.get_exchange().fetch_balance()
        return float((bal.get("free") or {}).get(quote, 0.0) or 0.0)

    def equity(self, mark_prices: dict[str, float]) -> float:
        """Account equity in USDT = free USDT + open positions valued at mark."""
        eq = 0.0
        try:
            bal = collector.get_exchange().fetch_balance()
            eq += float((bal.get("free") or {}).get("USDT", 0.0) or 0.0)
        except Exception:
            pass
        for pos in self.open_positions():
            price = mark_prices.get(pos["symbol"], pos["entry_price"])
            eq += pos["quantity"] * price
        return eq

    # ---------- exchange helpers ----------
    def _round_amount(self, symbol: str, qty: float) -> float:
        try:
            ex = collector.get_exchange()
            ex.load_markets()  # cached by ccxt after the first call
            return float(ex.amount_to_precision(symbol, qty))
        except Exception:
            return round(qty, 6)

    def _min_notional(self, symbol: str) -> float:
        try:
            ex = collector.get_exchange()
            ex.load_markets()
            m = ex.market(symbol)
            return float(((m.get("limits") or {}).get("cost") or {}).get("min") or 0.0)
        except Exception:
            return 0.0

    # ---------- trade actions (mirror PaperEngine) ----------
    def open_trade(self, symbol: str, price: float, reason: str = "",
                   atr: float = 0.0, meta: dict | None = None) -> dict | None:
        self._guard()
        # New entries respect the circuit breaker (emergency stop + daily loss).
        allowed, _ = circuit_breaker.trading_allowed(MODE)
        if not allowed:
            return None
        if price <= 0 or not risk.can_open_position(len(self.open_positions())):
            return None
        if any(p["symbol"] == symbol for p in self.open_positions()):
            return None

        meta = meta or {}
        stop_mult = float(meta.get("stop_mult", 0.0) or 0.0)
        free = self._free_quote(symbol)
        qty = self._round_amount(symbol, risk.position_size(
            free, price, mode=MODE, open_count=len(self.open_positions()),
            atr=atr, stop_mult=stop_mult))
        notional = qty * price
        if qty <= 0 or notional > free or notional < self._min_notional(symbol):
            return None

        order = collector.get_exchange().create_order(symbol, "market", "buy", qty)
        fill_price = float(order.get("average") or order.get("price") or price)
        fill_qty = float(order.get("filled") or qty)
        if fill_qty <= 0:
            return None

        trade = {
            "mode": MODE, "symbol": symbol, "side": "buy",
            "entry_price": fill_price, "quantity": fill_qty,
            "stop_loss": risk.stop_loss_price(fill_price, "buy", atr, stop_mult),
            "take_profit": risk.take_profit_price(fill_price, "buy", atr),
            "entry_reason": reason,
            "entry_factor": meta.get("factor"),
            "entry_regime": meta.get("regime"),
            "entry_adx": meta.get("adx"),
            "opened_at": datetime.now(timezone.utc).isoformat(),
        }
        trade["id"] = db.insert_trade(trade)
        db.record_equity(MODE, free - fill_qty * fill_price, free)
        return trade

    def close_trade(self, position: dict, price: float, reason: str = "") -> dict:
        self._guard()
        qty = position["quantity"]
        order = collector.get_exchange().create_order(position["symbol"], "market", "sell", qty)
        fill_price = float(order.get("average") or order.get("price") or price)
        entry = position["entry_price"]
        # The exchange really charges both legs on the account, so the recorded
        # PnL subtracts the same round-trip fee paper uses (REAL_FEE_PCT) — both
        # modes then report net-of-fee numbers and stay comparable (F2).
        pnl, pnl_pct = fees.round_trip_pnl(entry, fill_price, qty, config.REAL_FEE_PCT)
        db.close_trade(position["id"], fill_price, pnl, pnl_pct, reason)
        return {
            "id": position["id"], "symbol": position["symbol"],
            "pnl": round(pnl, 4), "pnl_pct": round(pnl_pct, 2), "exit_reason": reason,
        }

    def check_exits(self, mark_prices: dict[str, float]) -> list[dict]:
        """Trail profitable stops, then close on stop / target. Exits always allowed."""
        self._guard()
        closed = []
        for pos in self.open_positions():
            price = mark_prices.get(pos["symbol"])
            if not price or price <= 0:   # a bad/zero mark must never trigger an exit
                continue
            new_stop = risk.maybe_trail_stop(pos.get("stop_loss"), price, pos["entry_price"])
            if new_stop is not None:
                pos["stop_loss"] = new_stop
                db.update_trade_stop_loss(pos["id"], new_stop)
            if pos["stop_loss"] and price <= pos["stop_loss"]:
                closed.append(self.close_trade(pos, price, "stop_loss"))
            elif pos["take_profit"] and price >= pos["take_profit"]:
                closed.append(self.close_trade(pos, price, "take_profit"))
        return closed
