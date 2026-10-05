# Backtesting module for T01 Smart Binance Intelligence v2
"""
Backtesting and walk-forward validation module.

This module provides:
- Historical data backtesting
- Walk-forward optimization
- Performance metrics calculation
- Report generation
"""

from .engine import BacktestingEngine
from .data_loader import HistoricalDataLoader
from .walkforward import WalkForwardOptimizer
from .metrics import BacktestMetrics

__all__ = ['BacktestingEngine', 'HistoricalDataLoader', 'WalkForwardOptimizer', 'BacktestMetrics']
