"""Technical indicators computed with pure pandas/numpy (no C-extension deps)."""
import pandas as pd

from backend import config


def ohlcv_to_df(ohlcv: list[list]) -> pd.DataFrame:
    df = pd.DataFrame(ohlcv, columns=["ts", "open", "high", "low", "close", "volume"])
    df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    return df


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-12)
    return 100 - (100 / (1 + rs))


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(window=period, min_periods=period).mean()


def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    macd_line = ema(series, fast) - ema(series, slow)
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def bollinger_bands(series: pd.Series, period: int = 20, std_mult: float = 2.0):
    mid = sma(series, period)
    std = series.rolling(window=period, min_periods=period).std()
    upper = mid + std_mult * std
    lower = mid - std_mult * std
    return upper, mid, lower


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Average True Range — a volatility gauge used to scale stops/targets.

    True range is the greatest of: this bar's high-low, |high - prev close|, and
    |low - prev close|. Averaged over `period` bars (simple mean). Warms up to NaN
    for the first `period` bars, so callers must tolerate a missing reading.
    """
    prev_close = close.shift()
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(window=period, min_periods=period).mean()


def adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Average Directional Index — trend *strength* (not direction), 0–100.

    High ADX (≳20–25) = a directional trend; low ADX = a choppy/ranging tape. Used
    to label each trade's entry regime for loss reflection (roadmap #16). Simple
    rolling means (consistent with atr() above), so it warms up to NaN for the
    first ~2·period bars.
    """
    prev_close = close.shift()
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    up = high.diff()
    down = -low.diff()
    plus_dm = up.where((up > down) & (up > 0), 0.0)
    minus_dm = down.where((down > up) & (down > 0), 0.0)
    atr_ = tr.rolling(window=period, min_periods=period).mean().replace(0, 1e-12)
    plus_di = 100.0 * plus_dm.rolling(window=period, min_periods=period).mean() / atr_
    minus_di = 100.0 * minus_dm.rolling(window=period, min_periods=period).mean() / atr_
    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, 1e-12)
    return dx.rolling(window=period, min_periods=period).mean()


def vwap(df: pd.DataFrame, period: int = 24) -> pd.Series:
    """Rolling Volume-Weighted Average Price over `period` bars.

    A rolling window (not a true session-anchored VWAP) — a lightweight
    'fair value / smart-money' proxy: price above it leans bullish, below bearish.
    """
    typical = (df["high"] + df["low"] + df["close"]) / 3.0
    num = (typical * df["volume"]).rolling(window=period, min_periods=period).sum()
    den = df["volume"].rolling(window=period, min_periods=period).sum()
    return num / den.replace(0, 1e-12)


def compute_all(ohlcv: list[list]) -> pd.DataFrame:
    """Attach all indicators to an OHLCV dataframe."""
    df = ohlcv_to_df(ohlcv)
    close = df["close"]

    df["rsi"] = rsi(close)
    macd_line, signal_line, hist = macd(close)
    df["macd"] = macd_line
    df["macd_signal"] = signal_line
    df["macd_hist"] = hist
    df["ema_50"] = ema(close, 50)
    df["ema_100"] = ema(close, 100)
    df["ema_200"] = ema(close, 200)
    df["sma_20"] = sma(close, 20)
    upper, mid, lower = bollinger_bands(close)
    df["bb_upper"] = upper
    df["bb_mid"] = mid
    df["bb_lower"] = lower
    df["vol_sma_20"] = sma(df["volume"], 20)
    df["atr"] = atr(df["high"], df["low"], close, config.ATR_PERIOD)
    df["adx"] = adx(df["high"], df["low"], close, config.ATR_PERIOD)
    df["vwap"] = vwap(df)
    return df
