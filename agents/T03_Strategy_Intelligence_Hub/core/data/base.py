"""Unified data entrypoint + caching + validation.

`get_data(market, symbol, timeframe, start, end)` returns a validated OHLCV frame
(columns Open/High/Low/Close/Volume, DatetimeIndex, UTC). Results are cached as CSV
under `data/` so repeated backtests don't re-download.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

from ..config import DATA_DIR

OHLCV = ["Open", "High", "Low", "Close", "Volume"]


def _cache_path(market: str, symbol: str, timeframe: str, start: str, end: str) -> Path:
    key = f"{market}|{symbol}|{timeframe}|{start}|{end}"
    digest = hashlib.md5(key.encode()).hexdigest()[:10]
    safe = symbol.replace("/", "-").replace("=", "").replace(":", "-")
    return DATA_DIR / f"{market}_{safe}_{timeframe}_{digest}.csv"


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce any provider frame to the canonical OHLCV shape."""
    rename = {c: c.title() for c in df.columns if c.lower() in {"open", "high", "low", "close", "volume"}}
    df = df.rename(columns=rename)
    if "Volume" not in df.columns:
        df["Volume"] = 0.0
    df = df[[c for c in OHLCV if c in df.columns]].copy()
    df = df.apply(pd.to_numeric, errors="coerce")
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index, utc=True)
    df = df[~df.index.duplicated(keep="last")].sort_index()
    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    if df.empty:
        raise ValueError("No usable rows after normalization (check symbol/date range)")
    df.index.name = "Date"
    return df


def get_data(
    market: str,
    symbol: str,
    timeframe: str = "1d",
    start: str = "2020-01-01",
    end: str | None = None,
    use_cache: bool = True,
) -> pd.DataFrame:
    """Fetch validated OHLCV for a symbol.

    market : 'crypto' | 'forex' | 'stocks'
    symbol : e.g. 'BTC/USDT' (crypto), 'EURUSD=X' (forex), 'AAPL' (stocks)
    """
    end = end or pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d")
    market = market.lower()
    cache = _cache_path(market, symbol, timeframe, start, end)

    if use_cache and cache.exists():
        df = pd.read_csv(cache, index_col=0, parse_dates=True)
        return _normalize(df)

    if market == "crypto":
        from .crypto_binance import fetch as _fetch
    elif market == "forex":
        from .forex_oanda import fetch as _fetch
    elif market == "stocks":
        from .stocks_yf import fetch as _fetch
    else:
        raise ValueError(f"Unknown market '{market}' (use crypto/forex/stocks)")

    df = _normalize(_fetch(symbol, timeframe, start, end))
    try:
        df.to_csv(cache)
    except OSError:
        pass  # caching is best-effort
    return df


def clear_cache(market: str | None = None) -> int:
    """Delete cached data files; returns count removed."""
    pattern = f"{market}_*.csv" if market else "*.csv"
    removed = 0
    for f in DATA_DIR.glob(pattern):
        f.unlink()
        removed += 1
    return removed
