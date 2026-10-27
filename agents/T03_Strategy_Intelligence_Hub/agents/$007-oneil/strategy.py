"""William O'Neil — CANSLIM (technical subset for a single crypto asset).

Implements the signal contract in core/strategy_base.py. Real CANSLIM is mostly
FUNDAMENTAL (C/A quarterly & annual earnings, I institutional ownership) — none of
which exist for a single crypto asset. This models only the technical pillars, plus
O'Neil's 7-8% loss-cutting rule. See knowledge/strategies/oneil.md (read the honesty
section — this is CANSLIM-technical, not CANSLIM).

- N: enter on a breakout to a new high over the last `base_period` bars.
- S: require above-average volume on the breakout (`vol_confirm`).
- M: only enter when close > SMA(`market_ma`) (general market/trend up).
- Risk: exit at `stop_pct` below entry (7-8% rule) OR when close < SMA(`exit_ma`).
- Long-only (O'Neil goes to cash, never short).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from core.strategy_base import StrategySpec


class OneilStrategy(StrategySpec):
    name = "CANSLIM technical (new-high breakout + market filter + 8% stop)"

    params = {
        "base_period": 50,    # N: breakout to a new high over prior N bars
        "market_ma": 200,     # M: only buy when close > SMA(market_ma)
        "exit_ma": 50,        # sell when close < SMA(exit_ma) (trend break)
        "stop_pct": 0.08,     # O'Neil 7-8% loss-cutting rule
        "vol_confirm": True,  # S: breakout on above-average volume
        "vol_period": 50,
    }

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        data = self.validate_ohlcv(data)
        base_period = int(self.params["base_period"])
        market_ma = int(self.params["market_ma"])
        exit_ma = int(self.params["exit_ma"])
        stop_pct = float(self.params["stop_pct"])
        vol_confirm = bool(self.params["vol_confirm"])
        vol_period = int(self.params["vol_period"])

        high, close, volume = data["High"], data["Close"], data["Volume"]
        base_high = high.rolling(base_period).max().shift(1)
        sma_market = close.rolling(market_ma).mean()
        sma_exit = close.rolling(exit_ma).mean()

        breakout = (close > base_high).to_numpy()
        market_up = (close > sma_market).to_numpy()
        if vol_confirm and volume.sum() > 0:
            vol_ok = (volume > volume.rolling(vol_period).mean()).to_numpy()
        else:
            vol_ok = np.ones(len(close), dtype=bool)
        entry_cond = breakout & market_up & vol_ok

        c = close.to_numpy()
        exit_line = sma_exit.to_numpy()
        m = len(c)
        pos = np.zeros(m, dtype=float)
        state = 0
        entry_price = 0.0
        for i in range(m):
            if state == 0:
                if entry_cond[i]:
                    state = 1
                    entry_price = c[i]
            else:  # long
                stop_hit = c[i] < entry_price * (1.0 - stop_pct)
                trend_break = (not np.isnan(exit_line[i])) and c[i] < exit_line[i]
                if stop_hit or trend_break:
                    state = 0
            pos[i] = state

        out = self.blank_signals(data)
        out["position"] = pos
        return out
