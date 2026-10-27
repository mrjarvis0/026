"""Nicolas Darvas — Box Theory (breakout above the box on volume, trailing stop).

Implements the signal contract in core/strategy_base.py. Long-only mechanical core
of the Darvas box:
- **Box ceiling** = highest high of the last `box_period` bars; **box floor** =
  lowest low of the last `stop_period` bars (the trailing stop).
- **Buy** when close breaks above the box ceiling (a new high) AND — if
  `vol_confirm` — the breakout bar's volume is above its `vol_period` average
  (Darvas required strong volume).
- **Exit to flat** when close falls below the box floor (trailing stop). Never
  shorts (Darvas only bought rising boxes).

See the cited dossier knowledge/strategies/darvas.md. The fundamental "growth
industry / earnings" filter Darvas also used is NOT modeled (not in OHLCV).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from core.strategy_base import StrategySpec


class DarvasStrategy(StrategySpec):
    name = "Darvas Box breakout (long-only, volume-confirmed)"

    params = {
        "box_period": 20,     # ceiling-breakout lookback (box top)
        "stop_period": 10,    # trailing-stop lookback (box floor)
        "vol_confirm": True,  # require above-average breakout volume
        "vol_period": 20,     # volume-average window
    }

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        data = self.validate_ohlcv(data)
        box_period = int(self.params["box_period"])
        stop_period = int(self.params["stop_period"])
        vol_confirm = bool(self.params["vol_confirm"])
        vol_period = int(self.params["vol_period"])

        high, low, close, volume = data["High"], data["Low"], data["Close"], data["Volume"]
        # prior-bar windows (shift(1)) -> no same-bar look-ahead
        box_ceiling = high.rolling(box_period).max().shift(1)
        box_floor = low.rolling(stop_period).min().shift(1)

        breakout = (close > box_ceiling).to_numpy()
        if vol_confirm and volume.sum() > 0:
            vol_ok = (volume > volume.rolling(vol_period).mean()).to_numpy()
        else:
            vol_ok = np.ones(len(close), dtype=bool)
        long_entry = breakout & vol_ok
        long_exit = (close < box_floor).to_numpy()

        m = len(close)
        pos = np.zeros(m, dtype=float)
        state = 0
        for i in range(m):
            if state == 0:
                if long_entry[i]:
                    state = 1
            elif state == 1:
                if long_exit[i]:
                    state = 0
            pos[i] = state

        out = self.blank_signals(data)
        out["position"] = pos
        return out
