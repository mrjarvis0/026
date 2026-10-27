"""OANDA fxTrade **Practice** (demo) forex paper trading via the v20 API.

Requires OANDA_PRACTICE_TOKEN + OANDA_PRACTICE_ACCOUNT_ID in .env (practice only).
Install: `pip install oandapyV20`. Verify the v20 endpoint signatures at build
time (Constitution R-E.6).
"""
from __future__ import annotations

from typing import Any

from ..config import get_secret, load_env
from . import PaperOrder, require_confirmation

PRACTICE_HOST = "https://api-fxpractice.oanda.com"


def connect() -> Any:  # pragma: no cover - requires creds + optional dep
    load_env()
    token = get_secret("OANDA_PRACTICE_TOKEN")
    account = get_secret("OANDA_PRACTICE_ACCOUNT_ID")
    if not token or not account:
        raise RuntimeError(
            "OANDA_PRACTICE_TOKEN / OANDA_PRACTICE_ACCOUNT_ID not set in .env "
            "(practice account only)."
        )
    try:
        from oandapyV20 import API
    except ImportError as exc:
        raise ImportError("oandapyV20 not installed. `pip install oandapyV20`") from exc
    return {"api": API(access_token=token, environment="practice"), "account": account}


def submit_order(client: Any, order: PaperOrder, confirm_token: str | None = None) -> dict:  # pragma: no cover
    """Transmit a market order to the practice account (human-confirm required)."""
    require_confirmation(confirm_token)
    from oandapyV20.endpoints import orders

    units = int(order.qty) if order.side == "buy" else -int(order.qty)
    body = {"order": {"instrument": order.symbol, "units": str(units), "type": "MARKET"}}
    req = orders.OrderCreate(accountID=client["account"], data=body)
    return client["api"].request(req)
