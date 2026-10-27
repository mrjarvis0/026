"""Turtle Trading (Richard Dennis / William Eckhardt) — Donchian channel breakout.

Implements the signal contract in core/strategy_base.py. The classic Turtle system:
- **Entry:** go long when price closes above the highest high of the last `entry_donchian`
  bars; go short when it closes below the lowest low of that window.
- **Exit:** exit a long when price closes below the lowest low of the last `exit_donchian`
  bars (opposite for shorts).

The original Turtles used ATR ("N") for position *sizing* and pyramiding; our signal
contract expresses position as a target in {-1, 0, +1}, so sizing is abstracted to full
size here. See $001-dennis.agent.md for the cited rules and this simplification.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from core.strategy_base import StrategySpec


class DennisStrategy(StrategySpec):
    name = "Turtle Trading (Donchian breakout)"

    params = {
        "entry_donchian": 20,   # System 1 breakout window (20); System 2 uses 55
        "exit_donchian": 10,    # System 1 exit window (10); System 2 uses 20
        "allow_short": True,    # set False for long-only markets/accounts
    }

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        data = self.validate_ohlcv(data)
        entry_n = int(self.params["entry_donchian"])
        exit_n = int(self.params["exit_donchian"])
        allow_short = bool(self.params["allow_short"])

        high, low, close = data["High"], data["Low"], data["Close"]
        # channels formed by the PRIOR n bars (shift(1)) → no same-bar look-ahead
        upper_entry = high.rolling(entry_n).max().shift(1)
        lower_entry = low.rolling(entry_n).min().shift(1)
        upper_exit = high.rolling(exit_n).max().shift(1)
        lower_exit = low.rolling(exit_n).min().shift(1)

        long_signal = (close > upper_entry).to_numpy()
        short_signal = (close < lower_entry).to_numpy()
        long_exit = (close < lower_exit).to_numpy()
        short_exit = (close > upper_exit).to_numpy()

        n = len(close)
        pos = np.zeros(n, dtype=float)
        state = 0
        for i in range(n):
            if state == 0:
                if long_signal[i]:
                    state = 1
                elif allow_short and short_signal[i]:
                    state = -1
            elif state == 1:
                if long_exit[i]:
                    state = -1 if (allow_short and short_signal[i]) else 0
            elif state == -1:
                if short_exit[i]:
                    state = 1 if long_signal[i] else 0
            pos[i] = state

        out = self.blank_signals(data)
        out["position"] = pos
        return out
