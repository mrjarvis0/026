"""Paper trading engine — simulated wallet, real market prices, no real money."""
from datetime import datetime, timezone

from backend import config
from backend.analysis import risk
from backend.data import database as db

MODE = "paper"


class PaperEngine:
    def __init__(self, start_balance: float | None = None):
        stored = db.get_state("paper_balance")
        if stored is not None:
            self.balance = float(stored)
        else:
            self.balance = start_balance or config.PAPER_START_BALANCE
            db.set_state("paper_balance", str(self.balance))

    # ---------- balance helpers ----------
    def _save_balance(self):
        db.set_state("paper_balance", str(self.balance))

    def reset(self, start_balance: float | None = None):
        # Close any open paper positions at entry (0 PnL) so the wallet is a true
        # clean slate — no phantom holdings the reset cash no longer backs.
        for pos in self.open_positions():
            db.close_trade(pos["id"], pos["entry_price"], 0.0, 0.0, "reset")
        self.balance = start_balance or config.PAPER_START_BALANCE
        self._save_balance()
        db.record_equity(MODE, self.balance, self.balance)
        # A fresh wallet also resets the self-tuner's baseline (see engine.self_tune).
        db.set_state("tune_last_trades", "0")

    def open_positions(self) -> list[dict]:
        return db.get_open_trades(mode=MODE)

    def equity(self, mark_prices: dict[str, float]) -> float:
        """balance + unrealized value of open positions at current prices."""
        eq = self.balance
        for pos in self.open_positions():
            price = mark_prices.get(pos["symbol"], pos["entry_price"])
            eq += pos["quantity"] * price
        return eq

    def _open_cost(self) -> float:
        """Cost-basis value of ALL open positions (qty * entry). Used for the
        equity-curve snapshot so it isn't understated when several are open."""
        return sum(p["quantity"] * p["entry_price"] for p in self.open_positions())

    # ---------- trade actions ----------
    def open_trade(self, symbol: str, price: float, reason: str = "") -> dict | None:
        if not risk.can_open_position(len(self.open_positions())):
            return None
        # one position per symbol at a time
        if any(p["symbol"] == symbol for p in self.open_positions()):
            return None

        qty = risk.position_size(self.balance, price, mode=MODE,
                                 open_count=len(self.open_positions()))
        cost = qty * price
        if qty <= 0 or cost > self.balance:
            return None

        self.balance -= cost
        self._save_balance()

        trade = {
            "mode": MODE,
            "symbol": symbol,
            "side": "buy",
            "entry_price": price,
            "quantity": qty,
            "stop_loss": risk.stop_loss_price(price, "buy"),
            "take_profit": risk.take_profit_price(price, "buy"),
            "entry_reason": reason,
            "opened_at": datetime.now(timezone.utc).isoformat(),
        }
        trade_id = db.insert_trade(trade)
        trade["id"] = trade_id
        # equity = free cash + value of every open position (this one included)
        db.record_equity(MODE, self.balance, self.balance + self._open_cost())
        return trade

    def close_trade(self, position: dict, price: float, reason: str = "") -> dict:
        qty = position["quantity"]
        entry = position["entry_price"]
        proceeds = qty * price
        cost = qty * entry
        pnl = proceeds - cost
        pnl_pct = (price - entry) / entry * 100.0 if entry else 0.0

        self.balance += proceeds
        self._save_balance()

        db.close_trade(position["id"], price, pnl, pnl_pct, reason)
        # equity = free cash + value of positions STILL open after this close
        db.record_equity(MODE, self.balance, self.balance + self._open_cost())
        return {
            "id": position["id"],
            "symbol": position["symbol"],
            "pnl": round(pnl, 4),
            "pnl_pct": round(pnl_pct, 2),
            "exit_reason": reason,
        }

    def check_exits(self, mark_prices: dict[str, float]) -> list[dict]:
        """Close positions that hit stop-loss or take-profit."""
        closed = []
        for pos in self.open_positions():
            price = mark_prices.get(pos["symbol"])
            if price is None:
                continue
            if pos["stop_loss"] and price <= pos["stop_loss"]:
                closed.append(self.close_trade(pos, price, "stop_loss"))
            elif pos["take_profit"] and price >= pos["take_profit"]:
                closed.append(self.close_trade(pos, price, "take_profit"))
        return closed
