"""Richard Donchian — Donchian channel breakout (weekly / 4-week rule, trend timing).

Implements the signal contract in core/strategy_base.py. The mechanical core of
Donchian's trend-timing method:
- **Long** when price closes above the highest high of the last `channel` bars.
- **Short** when price closes below the lowest low of the last `channel` bars.
- **Stop-and-reverse:** otherwise hold the current position — the system is almost
  always in the market, flipping long<->short on the opposite breakout. With
  `allow_short=false` a short signal goes flat instead (long-only, for crypto spot).

N usually = 20 (the classic 4-week rule ~= 20 trading days). See the cited dossier
knowledge/strategies/donchian.md.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from core.strategy_base import StrategySpec


class DonchianStrategy(StrategySpec):
    name = "Donchian channel breakout (4-week rule)"

    params = {
        "channel": 20,        # N periods for the high/low channel (classic weekly rule)
        "allow_short": True,  # stop-and-reverse; set False for long-only markets
    }

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        data = self.validate_ohlcv(data)
        n = int(self.params["channel"])
        allow_short = bool(self.params["allow_short"])

        high, low, close = data["High"], data["Low"], data["Close"]
        # channel formed by the PRIOR n bars (shift(1)) -> no same-bar look-ahead
        upper = high.rolling(n).max().shift(1)
        lower = low.rolling(n).min().shift(1)

        long_signal = (close > upper).to_numpy()
        short_signal = (close < lower).to_numpy()

        m = len(close)
        pos = np.zeros(m, dtype=float)
        state = 0
        for i in range(m):
            if long_signal[i]:
                state = 1
            elif short_signal[i]:
                state = -1 if allow_short else 0
            # else: hold current state (stop-and-reverse stays in the market)
            pos[i] = state

        out = self.blank_signals(data)
        out["position"] = pos
        return out
