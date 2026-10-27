"""Binance Spot **Testnet** paper trading via ccxt.

Uses testnet keys only (BINANCE_TESTNET_API_KEY/SECRET). Get them at
https://testnet.binance.vision/ . Never put mainnet keys here.
"""
from __future__ import annotations

from typing import Any

from ..config import get_secret, load_env
from . import PaperOrder, require_confirmation


def connect() -> Any:
    """Return a ccxt Binance client in sandbox (testnet) mode."""
    try:
        import ccxt
    except ImportError as exc:  # pragma: no cover
        raise ImportError("ccxt not installed. `pip install ccxt`") from exc

    load_env()
    key = get_secret("BINANCE_TESTNET_API_KEY")
    secret = get_secret("BINANCE_TESTNET_API_SECRET")
    if not key or not secret:
        raise RuntimeError(
            "BINANCE_TESTNET_API_KEY/SECRET not set in .env. "
            "Create testnet keys at https://testnet.binance.vision/ (testnet only)."
        )
    client = ccxt.binance({"apiKey": key, "secret": secret, "enableRateLimit": True})
    client.set_sandbox_mode(True)  # route to testnet
    return client


def submit_order(client: Any, order: PaperOrder, confirm_token: str | None = None) -> dict:
    """Transmit an order to the **testnet**. Requires the human-confirm token.

    BUG-FIX: market orders must NOT pass a price to ccxt — some exchanges reject
    the call if price is set for a MARKET order type. Only pass price for limit/stop orders.
    """
    require_confirmation(confirm_token)
    kwargs: dict = {}
    if order.order_type != "market" and order.price is not None:
        kwargs["price"] = order.price
    return client.create_order(
        symbol=order.symbol,
        type=order.order_type,
        side=order.side,
        amount=order.qty,
        **kwargs,
    )


# --- read helpers for live reconciliation (no orders placed) ------------------
def _base_quote(symbol: str) -> tuple[str, str]:
    base, quote = symbol.split("/")
    return base, quote


def get_price(client: Any, symbol: str) -> float:
    """Last traded price from the testnet ticker."""
    return float(client.fetch_ticker(symbol)["last"])


def get_balance(client: Any) -> dict:
    """Full balance dict from the testnet account (ccxt fetch_balance)."""
    return client.fetch_balance()


def get_position_units(client: Any, symbol: str) -> float:
    """Base-asset units currently held on the testnet (spot 'position')."""
    base, _ = _base_quote(symbol)
    bal = client.fetch_balance()
    return float(bal.get("total", {}).get(base, 0.0) or 0.0)


def get_equity(client: Any, symbol: str, price: float | None = None) -> float:
    """Account equity in the quote currency = quote_free + base_units * price."""
    base, quote = _base_quote(symbol)
    bal = client.fetch_balance()
    quote_total = float(bal.get("total", {}).get(quote, 0.0) or 0.0)
    base_total = float(bal.get("total", {}).get(base, 0.0) or 0.0)
    if price is None:
        price = get_price(client, symbol)
    return quote_total + base_total * price


def round_qty(client: Any, symbol: str, qty: float) -> float:
    """Round an amount to the market's lot-size precision (best-effort)."""
    try:
        return float(client.amount_to_precision(symbol, qty))
    except Exception:
        return round(qty, 6)
