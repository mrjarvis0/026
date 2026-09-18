"""Universal market-data collector — works on ANY Binance pair via ccxt."""
import time
from typing import Optional

import ccxt

from backend import config

# Single shared exchange client (public data needs no API key)
_exchange: Optional[ccxt.binance] = None


def get_exchange() -> ccxt.binance:
    global _exchange
    if _exchange is None:
        params = {
            "enableRateLimit": True,
            "timeout": 30000,   # 30s — avoids transient klines timeouts
            "options": {"defaultType": "spot", "adjustForTimeDifference": True},
        }
        if config.BINANCE_API_KEY and config.BINANCE_API_SECRET:
            params["apiKey"] = config.BINANCE_API_KEY
            params["secret"] = config.BINANCE_API_SECRET
        _exchange = ccxt.binance(params)
        if config.BINANCE_TESTNET and config.BINANCE_API_KEY:
            _exchange.set_sandbox_mode(True)
    return _exchange


def _retry(fn, attempts: int = 3, delay: float = 0.6):
    """Retry a ccxt call on transient network/exchange errors."""
    last = None
    for i in range(attempts):
        try:
            return fn()
        except (ccxt.NetworkError, ccxt.ExchangeNotAvailable, ccxt.RequestTimeout) as exc:
            last = exc
            time.sleep(delay * (i + 1))
    raise last


def list_symbols(quote: str = "USDT", limit: int = 400) -> list[str]:
    """Return available spot trading pairs (any coin), filtered by quote currency."""
    ex = get_exchange()
    markets = ex.load_markets()
    symbols = [
        s for s, m in markets.items()
        if m.get("spot") and m.get("active") and s.endswith(f"/{quote}")
    ]
    symbols.sort()
    return symbols[:limit]


def fetch_ohlcv(symbol: str, timeframe: str = "5m", limit: int = 200) -> list[list]:
    """Fetch OHLCV candles for any symbol. Returns [[ts, o, h, l, c, v], ...]."""
    ex = get_exchange()
    return _retry(lambda: ex.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit))


def fetch_ticker(symbol: str) -> dict:
    """Latest price + 24h stats for any symbol."""
    ex = get_exchange()
    t = _retry(lambda: ex.fetch_ticker(symbol))
    return {
        "symbol": symbol,
        "last": t.get("last"),
        "bid": t.get("bid"),
        "ask": t.get("ask"),
        "high": t.get("high"),
        "low": t.get("low"),
        "volume": t.get("baseVolume"),
        "change_pct": t.get("percentage"),
        "timestamp": t.get("timestamp"),
    }


def fetch_order_book(symbol: str, limit: int = 20) -> dict:
    ex = get_exchange()
    ob = _retry(lambda: ex.fetch_order_book(symbol, limit=limit))
    return {"bids": ob["bids"][:limit], "asks": ob["asks"][:limit]}
