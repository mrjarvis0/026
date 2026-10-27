"""Larry Williams — Volatility Breakout (short-term, prior-range thrust).

Implements the signal contract in core/strategy_base.py.

Original (intraday): buy stop at Open + k*Range[t-1], sell stop at Open - k*Range[t-1],
exit at the close. Range = High[t-1] - Low[t-1]. See knowledge/strategies/williams.md.

The hub's engine is daily Close-to-Close with next-bar execution, so it cannot fill an
intraday stop at the trigger price without look-ahead. Faithful adaptation used here:
a **close-confirmed** breakout (Close beyond the trigger) held for `hold_days` bars — a
short-term swing rather than a same-day daytrade. This is a stated simplification.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from core.strategy_base import StrategySpec


class WilliamsStrategy(StrategySpec):
    name = "Volatility Breakout (Open + k*prior range)"

    params = {
        "k": 0.5,             # breakout multiple of the prior-day range
        "hold_days": 1,       # bars to hold after a trigger (1 => short-term swing)
        "allow_short": True,  # permit downside thrusts; False => long-only
    }

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        data = self.validate_ohlcv(data)
        k = float(self.params["k"])
        hold_days = max(1, int(self.params["hold_days"]))
        allow_short = bool(self.params["allow_short"])

        open_, high, low, close = data["Open"], data["High"], data["Low"], data["Close"]
        prior_range = (high - low).shift(1)
        upper = open_ + k * prior_range
        lower = open_ - k * prior_range

        raw = np.where(
            close > upper, 1.0,
            np.where(close < lower, (-1.0 if allow_short else 0.0), 0.0),
        )

        # hold each trigger for `hold_days` bars, unless a new trigger overrides it
        m = len(close)
        pos = np.zeros(m, dtype=float)
        state = 0.0
        countdown = 0
        for i in range(m):
            if raw[i] != 0.0:
                state = raw[i]
                countdown = hold_days - 1
            elif countdown > 0:
                countdown -= 1
            else:
                state = 0.0
            pos[i] = state

        out = self.blank_signals(data)
        out["position"] = pos
        return out
