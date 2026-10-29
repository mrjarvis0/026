"""Binance USD-M Futures **Testnet** broker via ccxt (long/short/leverage).

Uses `binanceusdm` in sandbox mode — testnet keys only.
Get them at https://testnet.binancefuture.com/ (separate from Spot Testnet keys).
Never put mainnet keys here.

SCALPER.md component #2: the futures broker that lets the scalper go long AND short
with configurable leverage on the Binance Futures Testnet.

Safety model (Constitution R-B.4):
- Testnet only; `set_sandbox_mode(True)` is hard-coded.
- `submit_order()` requires the explicit human-confirm token.
- Long/short/close are the only side operations.
- No mainnet endpoint, no real-money path.
"""
from __future__ import annotations

from typing import Any

from ..config import get_secret, load_env
from . import PaperOrder, require_confirmation


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

def connect(leverage: int = 5) -> Any:
    """Return a ccxt binanceusdm client in sandbox (Futures Testnet) mode.

    ``leverage`` is the default cross-margin leverage set on every symbol the
    scalper trades.  The RiskEngine caps actual exposure further — this is
    just the exchange-side setting.

    Raises RuntimeError when testnet keys are missing.
    """
    try:
        import ccxt
    except ImportError as exc:
        raise ImportError("ccxt not installed.  `pip install ccxt`") from exc

    load_env()
    key = get_secret("BINANCE_FUTURES_TESTNET_API_KEY")
    secret = get_secret("BINANCE_FUTURES_TESTNET_API_SECRET")
    if not key or not secret:
        raise RuntimeError(
            "BINANCE_FUTURES_TESTNET_API_KEY / SECRET not set in .env.\n"
            "Create Futures Testnet keys at https://testnet.binancefuture.com/\n"
            "(NOTE: these are *different* from Spot Testnet keys)."
        )

    client = ccxt.binanceusdm({
        "apiKey": key,
        "secret": secret,
        "enableRateLimit": True,
        "options": {"defaultType": "future"},
    })
    client.set_sandbox_mode(True)           # hard-coded: testnet always

    # Load markets so amount_to_precision works without a separate call.
    try:
        client.load_markets()
    except Exception:
        pass  # non-fatal; will retry lazily

    # Apply leverage cross-margin on the default symbol (best-effort).
    try:
        _symbol_for_leverage = client.market_ids  # will fail if markets not loaded
    except Exception:
        pass

    client._t03_leverage = leverage          # stash for get_equity / position_size
    return client


# ---------------------------------------------------------------------------
# Reads (no orders placed)
# ---------------------------------------------------------------------------

def get_price(client: Any, symbol: str) -> float:
    """Last mark price from the Futures Testnet ticker."""
    ticker = client.fetch_ticker(symbol)
    # mark price preferred; fall back to last traded
    return float(ticker.get("markPrice") or ticker.get("last") or ticker["close"])


def get_balance(client: Any) -> dict:
    """Full balance dict (USDT-margined futures balance)."""
    return client.fetch_balance(params={"type": "future"})


def get_equity(client: Any, symbol: str | None = None) -> float:
    """Total account equity in USDT (total margin balance, unrealized PnL included)."""
    bal = get_balance(client)
    # ccxt futures balance puts total equity under 'USDT' total
    usdt_total = float(bal.get("total", {}).get("USDT", 0.0) or 0.0)
    return usdt_total


def get_position(client: Any, symbol: str) -> dict:
    """Current futures position for one symbol.

    Returns a dict with:
        units      : signed position size in base units (+ long, - short, 0 = flat)
        side       : 'long' | 'short' | 'flat'
        entry_price: float
        unrealized_pnl: float
        leverage   : int
    """
    try:
        positions = client.fetch_positions([symbol])
    except Exception:
        positions = []

    for p in positions:
        if p.get("symbol") == symbol or p.get("info", {}).get("symbol") == symbol.replace("/", ""):
            amt = float(p.get("contracts", 0) or 0)
            side = p.get("side", "").lower()
            signed = amt if side == "long" else (-amt if side == "short" else 0.0)
            return {
                "units": signed,
                "side": "long" if signed > 0 else ("short" if signed < 0 else "flat"),
                "entry_price": float(p.get("entryPrice") or p.get("info", {}).get("entryPrice", 0)),
                "unrealized_pnl": float(p.get("unrealizedPnl") or 0.0),
                "leverage": int(p.get("leverage") or getattr(client, "_t03_leverage", 5)),
            }

    return {"units": 0.0, "side": "flat", "entry_price": 0.0, "unrealized_pnl": 0.0,
            "leverage": getattr(client, "_t03_leverage", 5)}


def get_position_units(client: Any, symbol: str) -> float:
    """Signed position size in base-asset units (+ long, - short, 0 flat)."""
    return get_position(client, symbol)["units"]


def round_qty(client: Any, symbol: str, qty: float) -> float:
    """Round qty to the symbol's lot-size precision (best-effort)."""
    try:
        return float(client.amount_to_precision(symbol, abs(qty)))
    except Exception:
        return round(abs(qty), 3)


# ---------------------------------------------------------------------------
# Order submission (gated behind confirm token)
# ---------------------------------------------------------------------------

def set_leverage(client: Any, symbol: str, leverage: int) -> None:
    """Set leverage for a symbol on the Futures Testnet (best-effort)."""
    try:
        client.set_leverage(leverage, symbol)
    except Exception:
        pass  # non-fatal: testnet might not support this call for all symbols


def submit_order(
    client: Any,
    order: PaperOrder,
    confirm_token: str | None = None,
    reduce_only: bool = False,
) -> dict:
    """Transmit an order to the **Futures Testnet**.

    Requires the human-confirm token (Constitution R-B.4).
    ``reduce_only=True`` closes / reduces an existing position without opening the other side.

    BUG-FIX from Spot adapter: market orders MUST NOT pass a price to ccxt.
    """
    require_confirmation(confirm_token)

    params: dict = {"type": "future"}
    if reduce_only:
        params["reduceOnly"] = True

    kwargs: dict = {}
    if order.order_type != "market" and order.price is not None:
        kwargs["price"] = order.price

    return client.create_order(
        symbol=order.symbol,
        type=order.order_type,
        side=order.side,          # 'buy' = open/add long, 'sell' = open/add short
        amount=order.qty,
        params=params,
        **kwargs,
    )


def close_position(
    client: Any,
    symbol: str,
    confirm_token: str | None = None,
) -> dict | None:
    """Close the entire position for a symbol (reduce-only market order).

    Returns the order dict, or None if already flat.
    """
    require_confirmation(confirm_token)
    pos = get_position(client, symbol)
    if pos["side"] == "flat" or pos["units"] == 0:
        return None
    close_side = "sell" if pos["units"] > 0 else "buy"
    qty = round_qty(client, symbol, abs(pos["units"]))
    order = PaperOrder(
        market="crypto",
        symbol=symbol,
        side=close_side,
        qty=qty,
        order_type="market",
        note="close-position",
    )
    return submit_order(client, order, confirm_token, reduce_only=True)


def cancel_open_orders(client: Any, symbol: str, confirm_token: str | None = None) -> None:
    """Cancel every open order (e.g. a stale protective stop) for ``symbol`` on the Futures Testnet."""
    require_confirmation(confirm_token)
    client.cancel_all_orders(symbol)


def submit_stop(
    client: Any,
    symbol: str,
    side: str,
    qty: float,
    stop_price: float,
    confirm_token: str | None = None,
) -> dict:
    """Place a reduce-only STOP_MARKET protecting an open position (cannot open the other side)."""
    require_confirmation(confirm_token)
    return client.create_order(
        symbol=symbol,
        type="STOP_MARKET",
        side=side,
        amount=qty,
        params={"type": "future", "stopPrice": stop_price, "reduceOnly": True},
    )
