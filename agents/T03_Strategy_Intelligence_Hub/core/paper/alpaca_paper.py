"""Alpaca **Paper Trading** for US stocks (and crypto).

Requires ALPACA_PAPER_API_KEY/SECRET in .env (paper keys only). Paper endpoint:
https://paper-api.alpaca.markets . Install: `pip install alpaca-py`.
"""
from __future__ import annotations

from typing import Any

from ..config import get_secret, load_env
from . import PaperOrder, require_confirmation


def connect() -> Any:  # pragma: no cover - requires creds + optional dep
    load_env()
    key = get_secret("ALPACA_PAPER_API_KEY")
    secret = get_secret("ALPACA_PAPER_API_SECRET")
    if not key or not secret:
        raise RuntimeError("ALPACA_PAPER_API_KEY/SECRET not set in .env (paper keys only).")
    try:
        from alpaca.trading.client import TradingClient
    except ImportError as exc:
        raise ImportError("alpaca-py not installed. `pip install alpaca-py`") from exc
    return TradingClient(key, secret, paper=True)


def submit_order(client: Any, order: PaperOrder, confirm_token: str | None = None) -> dict:  # pragma: no cover
    """Transmit a market order to the paper account (human-confirm required)."""
    require_confirmation(confirm_token)
    from alpaca.trading.enums import OrderSide, TimeInForce
    from alpaca.trading.requests import MarketOrderRequest

    req = MarketOrderRequest(
        symbol=order.symbol,
        qty=order.qty,
        side=OrderSide.BUY if order.side == "buy" else OrderSide.SELL,
        time_in_force=TimeInForce.DAY,
    )
    resp = client.submit_order(req)
    return {"id": str(getattr(resp, "id", "")), "status": str(getattr(resp, "status", ""))}
