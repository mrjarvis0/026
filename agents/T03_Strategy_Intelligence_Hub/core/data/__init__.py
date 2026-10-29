"""Market-data adapters (crypto / forex / stocks) with a single entrypoint.

Use `core.data.get_data(...)`; it dispatches to the right provider by market and
caches results under `data/`. All returned frames are validated OHLCV with a
DatetimeIndex (Constitution R-B.1/R-B.6: external data is untrusted, validated on load).
"""
from .base import get_data, clear_cache  # noqa: F401
