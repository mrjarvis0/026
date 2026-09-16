"""Loss reflection and self-correction module."""
import json
import logging

from backend.data import database as db
from backend.strategy import engine

log = logging.getLogger("trading.reflection")

def reflect_on_losses(mode: str = "paper") -> None:
    """Analyze recent losing trades to identify patterns and adjust parameters."""
    closed = db.get_closed_trades(mode=mode, limit=20)
    # Consider only recent trades that aren't resets and were losses
    losses = [t for t in closed if t.get("exit_reason") != "reset" and (t.get("pnl") or 0.0) < 0]

    if not losses:
        return

    total_trades = len([t for t in closed if t.get("exit_reason") != "reset"])
    if total_trades == 0:
        return

    loss_rate = len(losses) / total_trades

    # If loss rate in the recent window is high, we might need a corrective action
    if loss_rate > 0.4:
        params = engine.load_params()
        # Nudge the net_threshold up to become more selective
        old_threshold = params["net_threshold"]
        params["net_threshold"] = min(3.0, params["net_threshold"] + 0.1)

        # We can also tighten RSI parameters for entry to avoid weak momentum
        if params["rsi_buy"] > 35.0:
            params["rsi_buy"] -= 1.0
        if params["rsi_sell"] < 70.0:
            params["rsi_sell"] += 1.0

        if old_threshold != params["net_threshold"]:
            log.info(f"Reflection: high recent loss rate ({loss_rate:.0%}). Raising threshold from {old_threshold:.2f} to {params['net_threshold']:.2f}")
            engine.save_params(params)
