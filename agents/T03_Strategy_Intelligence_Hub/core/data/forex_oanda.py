"""Forex OHLCV.

For *history* we use yfinance FX pairs (free, no key) — pass symbols like
'EURUSD=X', 'GBPJPY=X'. For live/practice **paper trading**, use OANDA's v20 API
(see core/paper/oanda_practice.py); the OANDA candle endpoint below is provided
for parity but requires OANDA_PRACTICE_TOKEN in .env.
"""
from __future__ import annotations

import pandas as pd


def _yf_symbol(symbol: str) -> str:
    """Accept 'EURUSD', 'EUR/USD', or 'EURUSD=X' and return a yfinance FX symbol."""
    s = symbol.upper().replace("/", "").replace(" ", "")
    if s.endswith("=X"):
        return s
    return f"{s}=X"


def fetch(symbol: str, timeframe: str, start: str, end: str) -> pd.DataFrame:
    """Fetch FX OHLCV history via yfinance. e.g. symbol='EURUSD', timeframe='1d'."""
    from .stocks_yf import fetch as yf_fetch  # reuse the yfinance path

    df = yf_fetch(_yf_symbol(symbol), timeframe, start, end)
    if "Volume" in df.columns:
        # FX has no real volume on Yahoo; keep the column but it is ~0
        df["Volume"] = df["Volume"].fillna(0.0)
    return df


def fetch_oanda_candles(symbol: str, timeframe: str, count: int = 500):  # pragma: no cover
    """Live/practice candles via OANDA v20 (requires OANDA_PRACTICE_TOKEN).

    Stubbed intentionally: returns instructions rather than a silent failure so a
    build step re-verifies the API (Constitution R-E.6).
    """
    from ..config import get_secret, load_env

    load_env()
    if not get_secret("OANDA_PRACTICE_TOKEN"):
        raise RuntimeError(
            "OANDA_PRACTICE_TOKEN not set. For history, prefer fetch() (yfinance). "
            "For live OANDA candles: pip install oandapyV20 and set OANDA_PRACTICE_TOKEN."
        )
    raise NotImplementedError(
        "Wire up oandapyV20 instruments.InstrumentsCandles here; verify the v20 API "
        "signature at build time (R-E.6)."
    )
