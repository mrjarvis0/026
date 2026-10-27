"""The contract every strategy-agent implements.

A strategy is *pure signal logic*: given OHLCV data, it declares the desired
market position for each bar. It does NOT load data, place orders, or compute
metrics — the shared core library does that (Constitution R-D.8: deterministic
code you control; R-C.5: own your control flow).

Signal contract
---------------
`generate_signals(data)` returns a DataFrame indexed exactly like `data` with a
column **`position`** in {-1, 0, +1}:

    +1  -> want to be LONG on this bar
     0  -> want to be FLAT
    -1  -> want to be SHORT on this bar

The backtester applies the position on the *next* bar (`shift(1)`) so there is no
look-ahead bias. An optional **`size`** column (float in (0, 1]) sets the fraction
of equity to deploy; default is full size.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import pandas as pd

OHLCV_COLUMNS = ["Open", "High", "Low", "Close", "Volume"]


class StrategySpec(ABC):
    """Base class for all agent strategies.

    Subclasses set class-level ``params`` defaults and implement
    :meth:`generate_signals`. Instances are constructed with keyword overrides,
    e.g. ``MyStrat(entry_lookback=55)``.
    """

    #: default parameters; overridden per-instance and by config.yaml
    params: dict[str, Any] = {}
    #: human-readable name, set by subclass
    name: str = "unnamed-strategy"

    def __init__(self, **overrides: Any) -> None:
        merged = dict(self.params)
        merged.update(overrides)
        self.params = merged

    # -- the one method every agent must implement ---------------------------
    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """Return a DataFrame with a ``position`` column in {-1, 0, +1}.

        ``data`` has columns Open/High/Low/Close/Volume and a DatetimeIndex.
        Must not modify ``data`` in place.
        """
        raise NotImplementedError

    # -- helpers -------------------------------------------------------------
    @staticmethod
    def validate_ohlcv(data: pd.DataFrame) -> pd.DataFrame:
        """Validate & normalize incoming market data (untrusted input, R-B.1/R-B.6)."""
        missing = [c for c in ["Open", "High", "Low", "Close"] if c not in data.columns]
        if missing:
            raise ValueError(f"OHLCV data missing columns: {missing}")
        if not isinstance(data.index, pd.DatetimeIndex):
            raise ValueError("OHLCV data must have a DatetimeIndex")
        if not data.index.is_monotonic_increasing:
            data = data.sort_index()
        return data

    def blank_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """A zero-position frame aligned to ``data`` for subclasses to fill."""
        return pd.DataFrame({"position": 0.0}, index=data.index)

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"<{self.__class__.__name__} {self.name} params={self.params}>"
