"""Active net-momentum signal engine.

Instead of requiring rare unanimous conditions, we score several weighted
sub-signals into a net bull/bear score and act when the net crosses a
tunable threshold. This produces regular, explainable trades that the
dashboard can visualize live.
"""
from dataclasses import dataclass, field
from typing import Literal

import pandas as pd

Action = Literal["buy", "sell", "hold"]


@dataclass
class Signal:
    action: Action
    confidence: float          # 0..1
    reason: str
    price: float
    details: dict = field(default_factory=dict)


def _safe(value, default=0.0):
    try:
        if pd.isna(value):
            return default
    except (TypeError, ValueError):
        return default
    return float(value)


# Max achievable magnitude on one side, used to normalise confidence:
# rsi_oversold 2.0 + macd_pos 1.0 + macd_turn_up 1.0 + trend_up 0.8
# + bb_below 1.2 + vol 0.6 + vwap 0.7 = 7.3 (mirror on the bearish side).
_MAX_SCORE = 7.3

# Minimum closed bars before we trust the indicators. Below this, RSI(14)/
# BB(20)/MACD(26) are still NaN or warming up; _safe() would default the
# Bollinger bounds to `price`, making `price <= bb_lower` trivially true and
# fabricating a phantom "bb_below" buy. An empty frame would also make
# df.iloc[-1] raise. Hold until there is enough history.
_MIN_BARS = 30


# Each sub-signal is scored in its own helper so the weighting rules stay small
# and testable in isolation; generate_signal just concatenates their outputs.
# Positive score = bullish, negative = bearish.
def _evaluate_rsi(rsi_v: float, rsi_buy: float, rsi_sell: float) -> list[tuple[str, float]]:
    if rsi_v < 30:
        return [("rsi_oversold", +2.0)]
    if rsi_v < rsi_buy:
        return [("rsi_low", +1.0)]
    if rsi_v > 70:
        return [("rsi_overbought", -2.0)]
    if rsi_v > rsi_sell:
        return [("rsi_high", -1.0)]
    return []


def _evaluate_macd(macd_hist: float, macd_hist_prev: float, price: float,
                   macd_eps_frac: float) -> list[tuple[str, float]]:
    # Three-state. Only counts when the histogram is clearly off zero; within the
    # dead-band (near a crossover) it contributes nothing, so a flat tape no longer
    # forces a side every single bar. The "turn" factor fires on a fresh cross OUT
    # of the dead-band (a real momentum shift), not a hairline wiggle across zero.
    factors: list[tuple[str, float]] = []
    macd_eps = macd_eps_frac * price
    if macd_hist > macd_eps:
        factors.append(("macd_pos", +1.0))
    elif macd_hist < -macd_eps:
        factors.append(("macd_neg", -1.0))
    if macd_hist > macd_eps and macd_hist_prev <= macd_eps:
        factors.append(("macd_turn_up", +1.0))
    elif macd_hist < -macd_eps and macd_hist_prev >= -macd_eps:
        factors.append(("macd_turn_down", -1.0))
    return factors


def _evaluate_trend(ema50: float, ema200: float, trend_band: float) -> list[tuple[str, float]]:
    # Three-state. Only when EMA50/EMA200 are meaningfully separated; when they are
    # coiled together (a range) trend is neutral (0), not ±0.8.
    trend_sep = (ema50 - ema200) / ema200 if ema200 else 0.0
    if trend_sep > trend_band:
        return [("trend_up", +0.8)]
    if trend_sep < -trend_band:
        return [("trend_down", -0.8)]
    return []


def _evaluate_bollinger(price: float, bb_lower: float, bb_upper: float) -> list[tuple[str, float]]:
    if price <= bb_lower:
        return [("bb_below", +1.2)]
    if price >= bb_upper:
        return [("bb_above", -1.2)]
    return []


def _evaluate_volume(vol: float, vol_avg: float, price: float,
                     ema50: float) -> list[tuple[str, float]]:
    # Volume confirmation nudges in the direction of the candle.
    if vol > vol_avg:
        return [("vol_up_bull" if price >= ema50 else "vol_up_bear",
                 +0.6 if price >= ema50 else -0.6)]
    return []


def _evaluate_vwap(price: float, vwap_v: float) -> list[tuple[str, float]]:
    # VWAP confluence — a 'fair value / smart-money' proxy: trading above the
    # rolling VWAP leans bullish, below it bearish.
    if price > vwap_v:
        return [("above_vwap", +0.7)]
    if price < vwap_v:
        return [("below_vwap", -0.7)]
    return []


def generate_signal(df: pd.DataFrame, params: dict | None = None) -> Signal:
    p = {
        "rsi_buy": 45.0,
        "rsi_sell": 60.0,
        "net_threshold": 1.0,    # net score needed to fire a trade
        "macd_eps": 0.0002,      # MACD histogram dead-band, as a fraction of price (2 bps)
        "trend_band": 0.001,     # EMA50/EMA200 separation dead-band (0.1%)
    }
    if params:
        p.update(params)

    # Guard against too little history: no crash on an empty frame, and no
    # phantom signals from defaulted (NaN) indicators on a handful of bars.
    if len(df) < _MIN_BARS:
        price = _safe(df.iloc[-1]["close"]) if len(df) else 0.0
        return Signal("hold", 0.0, f"insufficient data ({len(df)} bars)", price,
                      {"indicators": {}, "factors": [], "net_score": 0.0,
                       "bull_score": 0.0, "bear_score": 0.0,
                       "threshold": p["net_threshold"]})

    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else last
    price = _safe(last["close"])
    rsi_v = _safe(last["rsi"], 50)
    macd_v = _safe(last["macd"])
    macd_sig = _safe(last["macd_signal"])
    macd_hist = _safe(last["macd_hist"])
    macd_hist_prev = _safe(prev["macd_hist"])
    ema50 = _safe(last["ema_50"], price)
    ema200 = _safe(last["ema_200"], price)
    bb_upper = _safe(last["bb_upper"], price)
    bb_lower = _safe(last["bb_lower"], price)
    vol = _safe(last["volume"])
    vol_avg = _safe(last["vol_sma_20"], vol)
    vwap_v = _safe(last.get("vwap"), price)   # optional column; falls back to price

    # ---- weighted sub-signals: (name, score) — positive = bullish ----
    factors: list[tuple[str, float]] = []
    factors.extend(_evaluate_rsi(rsi_v, p["rsi_buy"], p["rsi_sell"]))
    factors.extend(_evaluate_macd(macd_hist, macd_hist_prev, price, p["macd_eps"]))
    factors.extend(_evaluate_trend(ema50, ema200, p["trend_band"]))
    factors.extend(_evaluate_bollinger(price, bb_lower, bb_upper))
    factors.extend(_evaluate_volume(vol, vol_avg, price, ema50))
    factors.extend(_evaluate_vwap(price, vwap_v))

    bull = sum(s for _, s in factors if s > 0)
    bear = -sum(s for _, s in factors if s < 0)
    net = bull - bear
    confidence = min(1.0, abs(net) / _MAX_SCORE)

    details = {
        "indicators": {
            "rsi": round(rsi_v, 2),
            "macd": round(macd_v, 6),
            "macd_signal": round(macd_sig, 6),
            "macd_hist": round(macd_hist, 6),
            "ema_50": round(ema50, 6),
            "ema_200": round(ema200, 6),
            "bb_upper": round(bb_upper, 6),
            "bb_lower": round(bb_lower, 6),
            "volume": round(vol, 2),
            "vol_avg": round(vol_avg, 2),
            "vwap": round(vwap_v, 6),
            "trend": "up" if ema50 >= ema200 else "down",
        },
        "factors": [{"name": n, "score": round(s, 2)} for n, s in factors],
        "bull_score": round(bull, 2),
        "bear_score": round(bear, 2),
        "net_score": round(net, 2),
        "threshold": p["net_threshold"],
    }

    if net >= p["net_threshold"]:
        drivers = ", ".join(n for n, s in factors if s > 0) or "momentum"
        return Signal("buy", confidence,
                      f"BUY net={net:+.1f} · {drivers}", price, details)
    if net <= -p["net_threshold"]:
        drivers = ", ".join(n for n, s in factors if s < 0) or "momentum"
        return Signal("sell", confidence,
                      f"SELL net={net:+.1f} · {drivers}", price, details)

    return Signal("hold", confidence,
                  f"HOLD net={net:+.1f} (bull {bull:.1f} / bear {bear:.1f})",
                  price, details)
