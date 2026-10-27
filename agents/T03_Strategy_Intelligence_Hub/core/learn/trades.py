"""Reconstruct individual trades (with entry context) from a position series.

A trade = a contiguous run of the same non-zero position. For each we record entry/
exit and a snapshot of market *context* at entry (trend regime, momentum, volatility,
extension) — the raw material the reflector uses to diagnose why a loss happened.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd


@dataclass
class TradeRecord:
    direction: int              # +1 long, -1 short
    entry_ts: str
    exit_ts: str
    entry_price: float
    exit_price: float
    pnl_pct: float              # signed return of the trade
    bars_held: int
    context: dict[str, Any] = field(default_factory=dict)

    @property
    def is_loss(self) -> bool:
        return self.pnl_pct < 0


def _context_frame(data: pd.DataFrame) -> pd.DataFrame:
    """Vectorized market-context features, aligned to data.index."""
    close, high, low = data["Close"], data["High"], data["Low"]
    n = len(data)
    trend_win = min(200, max(20, n // 3))
    sma_trend = close.rolling(trend_win, min_periods=trend_win // 2).mean()
    atr = (high - low).rolling(14, min_periods=5).mean()
    ctx = pd.DataFrame(index=data.index)
    ctx["trend_regime"] = np.sign((close - sma_trend).fillna(0.0))      # +1 above / -1 below long MA
    ctx["momentum_20"] = close.pct_change(20).fillna(0.0)
    ctx["atr_pct"] = (atr / close).fillna(0.0)
    ctx["dist_from_high50"] = (close / high.rolling(50, min_periods=10).max() - 1).fillna(0.0)
    # volatility bucket by rolling percentile of atr_pct
    ctx["vol_bucket"] = pd.qcut(ctx["atr_pct"].rank(method="first"), 3,
                                labels=["low", "mid", "high"]).astype(str)
    return ctx


def latest_context(data: pd.DataFrame) -> dict[str, Any]:
    """Context features on the most recent bar (for the pre-trade guard)."""
    c = _context_frame(data).iloc[-1]
    return {
        "trend_regime": int(c["trend_regime"]),
        "momentum_20": round(float(c["momentum_20"]), 4),
        "atr_pct": round(float(c["atr_pct"]), 4),
        "dist_from_high50": round(float(c["dist_from_high50"]), 4),
        "vol_bucket": str(c["vol_bucket"]),
    }


def extract_trades(data: pd.DataFrame, applied_pos: pd.Series) -> list[TradeRecord]:
    """Turn a held-position series into a list of TradeRecords with entry context."""
    pos = applied_pos.reindex(data.index).fillna(0.0)
    ctx = _context_frame(data)
    close = data["Close"]

    trades: list[TradeRecord] = []
    seg_id = (pos != pos.shift()).cumsum()
    for _, idx in pos.groupby(seg_id).groups.items():
        idx = list(idx)
        direction = int(np.sign(pos.loc[idx[0]]))
        if direction == 0:
            continue
        entry_i, last_i = idx[0], idx[-1]
        entry_price = float(close.loc[entry_i])
        exit_price = float(close.loc[last_i])
        pnl = direction * (exit_price / entry_price - 1.0) if entry_price else 0.0
        c = ctx.loc[entry_i]
        trades.append(TradeRecord(
            direction=direction,
            entry_ts=str(entry_i), exit_ts=str(last_i),
            entry_price=entry_price, exit_price=exit_price,
            pnl_pct=round(pnl, 6), bars_held=len(idx),
            context={
                "trend_regime": int(c["trend_regime"]),
                "momentum_20": round(float(c["momentum_20"]), 4),
                "atr_pct": round(float(c["atr_pct"]), 4),
                "dist_from_high50": round(float(c["dist_from_high50"]), 4),
                "vol_bucket": str(c["vol_bucket"]),
            },
        ))
    return trades
