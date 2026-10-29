"""Stock OHLCV via yfinance (free history).

Note: intraday history from Yahoo is limited (roughly last ~60 days for <1d
intervals). For long intraday backtests use Alpaca market data instead.
"""
from __future__ import annotations

import pandas as pd

# yfinance interval strings differ slightly from our timeframe codes
_TF_MAP = {
    "1d": "1d", "1h": "1h", "30m": "30m", "15m": "15m", "5m": "5m", "1m": "1m",
    "1wk": "1wk", "1w": "1wk",
}


def fetch(symbol: str, timeframe: str, start: str, end: str) -> pd.DataFrame:
    """Fetch OHLCV for e.g. symbol='AAPL', timeframe='1d'."""
    try:
        import yfinance as yf
    except ImportError as exc:  # pragma: no cover
        raise ImportError("yfinance not installed. `pip install yfinance`") from exc

    interval = _TF_MAP.get(timeframe, "1d")
    df = yf.download(
        symbol, start=start, end=end, interval=interval,
        auto_adjust=True, progress=False,
    )
    if df is None or df.empty:
        raise ValueError(f"yfinance returned no data for {symbol} {interval} {start}..{end}")

    # yfinance may return MultiIndex columns for a single ticker; flatten them
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    return df
