"""Backtesting: a controlled vectorized engine + performance metrics."""
from .runner import BacktestResult, run_backtest  # noqa: F401
from .metrics import compute_metrics  # noqa: F401
