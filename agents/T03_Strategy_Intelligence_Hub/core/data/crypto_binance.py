"""Crypto OHLCV via ccxt → Binance public data (no API key required).

Handles pagination so multi-year daily/4h history downloads fully.
"""
from __future__ import annotations

import time

import pandas as pd

_TF_MS = {
    "1m": 60_000, "5m": 300_000, "15m": 900_000, "30m": 1_800_000,
    "1h": 3_600_000, "2h": 7_200_000, "4h": 14_400_000, "6h": 21_600_000,
    "8h": 28_800_000, "12h": 43_200_000, "1d": 86_400_000,
}


def fetch(symbol: str, timeframe: str, start: str, end: str) -> pd.DataFrame:
    """Fetch OHLCV for e.g. symbol='BTC/USDT', timeframe='1d'."""
    try:
        import ccxt
    except ImportError as exc:  # pragma: no cover
        raise ImportError("ccxt not installed. `pip install ccxt`") from exc

    exchange = ccxt.binance({"enableRateLimit": True})
    since = exchange.parse8601(f"{start}T00:00:00Z")
    end_ms = exchange.parse8601(f"{end}T23:59:59Z")
    step = _TF_MS.get(timeframe, 86_400_000)

    all_rows: list[list[float]] = []
    limit = 1000
    while since < end_ms:
        batch = exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=limit)
        if not batch:
            break
        all_rows.extend(batch)
        since = batch[-1][0] + step
        if len(batch) < limit:
            break
        time.sleep(exchange.rateLimit / 1000)

    if not all_rows:
        raise ValueError(f"Binance returned no data for {symbol} {timeframe} {start}..{end}")

    df = pd.DataFrame(all_rows, columns=["ts", "Open", "High", "Low", "Close", "Volume"])
    df = df[~df["ts"].duplicated(keep="last")]
    df.index = pd.to_datetime(df["ts"], unit="ms", utc=True)
    df = df.drop(columns=["ts"])
    return df[df.index <= pd.Timestamp(end_ms, unit="ms", tz="UTC")]
