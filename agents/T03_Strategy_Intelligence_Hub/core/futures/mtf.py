"""Multi-Timeframe (MTF) analyzer — SCALPER.md component #3.

Fetches OHLCV for multiple timeframes and computes per-TF indicators:
    - EMA trend (short vs long EMA)
    - ADX slope (trending vs choppy regime)
    - RSI momentum
    - ATR volatility %

Then produces an alignment score: +1 (all TFs bullish), -1 (all bearish), 0 (mixed/chop).
If alignment is 0 (chop), the scalper should STAND ASIDE regardless of the signal.

Usage:
    analyzer = MTFAnalyzer("BTC/USDT", timeframes=["1m","5m","15m","1h"])
    signal = analyzer.run()
    if signal.alignment == 0:
        print("chop – stand aside")
    else:
        print(f"direction={signal.alignment}, confidence={signal.confidence:.2f}")
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from ..data import get_data


# ---------------------------------------------------------------------------
# Per-TF indicator computation
# ---------------------------------------------------------------------------

def _ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def _adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Average Directional Index — measures trend strength (not direction)."""
    up = high.diff()
    down = -low.diff()
    plus_dm = np.where((up > down) & (up > 0), up, 0.0)
    minus_dm = np.where((down > up) & (down > 0), down, 0.0)
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs(),
    ], axis=1).max(axis=1)
    atr = tr.ewm(span=period, adjust=False).mean()
    safe_atr = atr.replace(0, np.nan)
    plus_di = 100 * pd.Series(plus_dm, index=close.index).ewm(span=period, adjust=False).mean() / safe_atr
    minus_di = 100 * pd.Series(minus_dm, index=close.index).ewm(span=period, adjust=False).mean() / safe_atr
    dx = (100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)).fillna(0)
    return dx.ewm(span=period, adjust=False).mean()


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(span=period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(span=period, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


@dataclass
class TFResult:
    timeframe: str
    trend: int              # +1 (bullish), -1 (bearish), 0 (unclear)
    adx: float              # 0–100; >= 25 = trending
    rsi: float              # 0–100
    atr_pct: float          # ATR as % of close (volatility proxy)
    ema_fast: float
    ema_slow: float
    close: float
    is_trending: bool       # ADX >= 25
    raw: dict[str, Any] = field(default_factory=dict)


def analyze_timeframe(
    symbol: str,
    timeframe: str,
    start: str = "2024-01-01",
    fast: int = 9,
    slow: int = 21,
    adx_period: int = 14,
    rsi_period: int = 14,
    use_cache: bool = False,
) -> TFResult:
    """Fetch OHLCV for one timeframe and return per-TF indicators on the last closed bar."""
    data = get_data("crypto", symbol, timeframe, start, None, use_cache=use_cache)
    closed = data.iloc[:-1]          # drop the still-forming bar
    if len(closed) < max(slow + 10, adx_period * 3):
        raise RuntimeError(f"Not enough bars on {timeframe} to compute indicators (got {len(closed)})")

    close = closed["Close"]
    high = closed["High"]
    low = closed["Low"]

    ema_f = _ema(close, fast)
    ema_s = _ema(close, slow)
    adx_vals = _adx(high, low, close, adx_period)
    rsi_vals = _rsi(close, rsi_period)
    atr = (high - low).ewm(span=adx_period, adjust=False).mean()

    last_ema_f = float(ema_f.iloc[-1])
    last_ema_s = float(ema_s.iloc[-1])
    last_adx = float(adx_vals.iloc[-1])
    last_rsi = float(rsi_vals.iloc[-1])
    last_close = float(close.iloc[-1])
    last_atr_pct = float(atr.iloc[-1] / last_close) if last_close else 0.0

    # Trend: fast EMA above slow EMA → bullish; slope must also be positive for confirmation.
    ema_slope = float(ema_f.diff(3).iloc[-1])
    if last_ema_f > last_ema_s and ema_slope > 0:
        trend = 1
    elif last_ema_f < last_ema_s and ema_slope < 0:
        trend = -1
    else:
        trend = 0

    return TFResult(
        timeframe=timeframe,
        trend=trend,
        adx=round(last_adx, 2),
        rsi=round(last_rsi, 2),
        atr_pct=round(last_atr_pct, 5),
        ema_fast=round(last_ema_f, 6),
        ema_slow=round(last_ema_s, 6),
        close=round(last_close, 6),
        is_trending=last_adx >= 25.0,
        raw={"ema_slope": round(ema_slope, 8)},
    )


# ---------------------------------------------------------------------------
# Multi-TF aggregation
# ---------------------------------------------------------------------------

@dataclass
class MTFSignal:
    symbol: str
    timeframes: list[TFResult]
    alignment: int          # +1 all bullish, -1 all bearish, 0 mixed/chop
    confidence: float       # 0.0–1.0 fraction of TFs agreeing on direction
    dominant_trend: int     # direction of the majority (even if not all aligned)
    is_chop: bool           # True → stand aside regardless of signal
    adx_mean: float         # mean ADX across TFs (> 25 = trending regime)

    def summary(self) -> str:
        dir_str = {1: "BULLISH", -1: "BEARISH", 0: "NEUTRAL"}[self.alignment]
        chop = " [CHOP — stand aside]" if self.is_chop else ""
        tfs = ", ".join(
            f"{r.timeframe}:{'+' if r.trend > 0 else ('-' if r.trend < 0 else '~')}"
            for r in self.timeframes
        )
        return (f"MTF {self.symbol}: {dir_str} (conf={self.confidence:.0%}, "
                f"adx_mean={self.adx_mean:.1f}){chop}  [{tfs}]")


class MTFAnalyzer:
    """Run multi-timeframe analysis on a single symbol."""

    DEFAULT_TFS = ["1m", "5m", "15m", "1h"]
    DEFAULT_START = "2024-01-01"   # short history is fine for intraday indicators

    def __init__(
        self,
        symbol: str = "BTC/USDT",
        timeframes: list[str] | None = None,
        start: str = DEFAULT_START,
        fast: int = 9,
        slow: int = 21,
        adx_period: int = 14,
        rsi_period: int = 14,
        use_cache: bool = False,
    ) -> None:
        self.symbol = symbol
        self.timeframes = timeframes or self.DEFAULT_TFS
        self.start = start
        self.fast = fast
        self.slow = slow
        self.adx_period = adx_period
        self.rsi_period = rsi_period
        self.use_cache = use_cache

    def run(self) -> MTFSignal:
        """Fetch all TFs and return the MTFSignal."""
        results: list[TFResult] = []
        errors: list[str] = []
        for tf in self.timeframes:
            try:
                results.append(analyze_timeframe(
                    self.symbol, tf, self.start,
                    self.fast, self.slow, self.adx_period, self.rsi_period,
                    use_cache=self.use_cache,
                ))
            except Exception as exc:
                errors.append(f"{tf}: {exc}")

        if not results:
            raise RuntimeError(f"All TFs failed for {self.symbol}: {errors}")

        trends = [r.trend for r in results]
        n = len(trends)
        bulls = trends.count(1)
        bears = trends.count(-1)

        dominant = 1 if bulls > bears else (-1 if bears > bulls else 0)
        agree = max(bulls, bears)
        confidence = agree / n

        # Alignment: all non-zero and same direction
        non_flat = [t for t in trends if t != 0]
        if non_flat and len(set(non_flat)) == 1:
            alignment = non_flat[0]
        else:
            alignment = 0

        adx_mean = float(np.mean([r.adx for r in results]))
        is_chop = (alignment == 0) or (adx_mean < 20)

        return MTFSignal(
            symbol=self.symbol,
            timeframes=results,
            alignment=alignment,
            confidence=round(confidence, 3),
            dominant_trend=dominant,
            is_chop=is_chop,
            adx_mean=round(adx_mean, 2),
        )
