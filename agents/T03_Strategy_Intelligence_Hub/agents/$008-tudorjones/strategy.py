"""Paul Tudor Jones — the 200-day MA rule (defensive trend/regime filter).

Implements the signal contract in core/strategy_base.py. PTJ's actual trading is
discretionary global macro; this models his single famous mechanical heuristic:
"nothing good happens below the 200-day moving average" — stay invested above it,
get out (or short) below it. See knowledge/strategies/tudorjones.md.

- Long while close > SMA(ma_period).
- Flat while below (the "play defense / get out" rule), or short if allow_short.
- confirm_days requires N consecutive closes on one side before flipping (whipsaw filter).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from core.strategy_base import StrategySpec


class TudorjonesStrategy(StrategySpec):
    name = "200-day MA rule (defensive regime filter)"

    params = {
        "ma_period": 200,      # PTJ's rule = 200-day moving average of closes
        "allow_short": False,  # rule is "get out" -> cash; True to short below the MA
        "confirm_days": 1,     # consecutive closes needed to flip (whipsaw filter)
    }

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        data = self.validate_ohlcv(data)
        ma_period = int(self.params["ma_period"])
        allow_short = bool(self.params["allow_short"])
        confirm_days = max(1, int(self.params["confirm_days"]))

        close = data["Close"]
        sma = close.rolling(ma_period).mean()
        above = (close > sma).to_numpy()
        below = (close < sma).to_numpy()
        ready = (~sma.isna()).to_numpy()

        m = len(close)
        pos = np.zeros(m, dtype=float)
        state = 0.0
        up_streak = 0
        down_streak = 0
        for i in range(m):
            if not ready[i]:
                pos[i] = 0.0
                continue
            if above[i]:
                up_streak += 1
                down_streak = 0
            elif below[i]:
                down_streak += 1
                up_streak = 0
            if up_streak >= confirm_days:
                state = 1.0
            elif down_streak >= confirm_days:
                state = -1.0 if allow_short else 0.0
            pos[i] = state

        out = self.blank_signals(data)
        out["position"] = pos
        return out
