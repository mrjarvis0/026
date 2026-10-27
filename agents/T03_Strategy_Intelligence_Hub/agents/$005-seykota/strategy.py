"""Ed Seykota — EMA trend-following (classic dual-EMA crossover).

Implements the signal contract in core/strategy_base.py. Seykota "based his first
trading system on exponential moving averages" (Wikipedia); his exact parameters are
proprietary and evolved, so this is the canonical dual-EMA crossover as a faithful
representation of that documented core, not his literal numbers. See
knowledge/strategies/seykota.md.

- Long when the fast EMA is above the slow EMA (uptrend).
- Short when the fast EMA is below the slow EMA (allow_short), else flat.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from core.strategy_base import StrategySpec


class SeykotaStrategy(StrategySpec):
    name = "EMA trend-following (dual-EMA crossover)"

    params = {
        "fast": 20,           # fast EMA span
        "slow": 100,          # slow EMA span
        "allow_short": True,  # stop-and-reverse; False => long-only
    }

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        data = self.validate_ohlcv(data)
        fast = int(self.params["fast"])
        slow = int(self.params["slow"])
        allow_short = bool(self.params["allow_short"])

        close = data["Close"]
        ema_fast = close.ewm(span=fast, adjust=False, min_periods=fast).mean()
        ema_slow = close.ewm(span=slow, adjust=False, min_periods=slow).mean()

        uptrend = (ema_fast > ema_slow).to_numpy()
        if allow_short:
            pos = np.where(uptrend, 1.0, -1.0)
        else:
            pos = np.where(uptrend, 1.0, 0.0)

        # flat until BOTH EMAs are warmed up (avoid trading on unstable early values)
        not_ready = ema_fast.isna().to_numpy() | ema_slow.isna().to_numpy()
        pos = np.where(not_ready, 0.0, pos)

        out = self.blank_signals(data)
        out["position"] = pos
        return out
