"""Linda Raschke — "Turtle Soup" false-breakout reversal (short-term mean-reversion).

Implements the signal contract in core/strategy_base.py. Deliberately fades a false
breakout (the opposite of $001's Turtle breakout entry), from Connors & Raschke's
*Street Smarts* (1995). See knowledge/strategies/raschke.md.

- Buy: a new N-day LOW is made but price CLOSES back above the prior low (failed
  breakdown) -> go long, expecting a snap-back.
- Sell: a new N-day HIGH fails and closes back below the prior high -> go short.
- Hold the reversal for `hold_days` bars, then flat (short-term).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from core.strategy_base import StrategySpec


class RaschkeStrategy(StrategySpec):
    name = "Turtle Soup (false-breakout reversal)"

    params = {
        "lookback": 20,       # N-day high/low that gets faded
        "hold_days": 3,       # bars to hold the reversal
        "allow_short": True,  # fade false breakouts to the upside too
    }

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        data = self.validate_ohlcv(data)
        n = int(self.params["lookback"])
        hold_days = max(1, int(self.params["hold_days"]))
        allow_short = bool(self.params["allow_short"])

        high, low, close = data["High"], data["Low"], data["Close"]
        prior_low = low.rolling(n).min().shift(1)
        prior_high = high.rolling(n).max().shift(1)

        # failed breakdown -> long; failed breakout -> short
        long_signal = ((low < prior_low) & (close > prior_low)).to_numpy()
        short_signal = ((high > prior_high) & (close < prior_high)).to_numpy() if allow_short \
            else np.zeros(len(close), dtype=bool)

        raw = np.where(long_signal, 1.0, np.where(short_signal, -1.0, 0.0))

        # hold each reversal for `hold_days` bars, unless a new signal overrides it
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
