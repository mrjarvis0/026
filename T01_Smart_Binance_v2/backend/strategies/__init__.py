"""Strategies module for T01 Smart Binance Intelligence v2.

This module provides multiple trading strategies including:
- Scalping Strategy
- Swing Trading Strategy
- Trend Following Strategy
- Mean Reversion Strategy
- Breakout Strategy
- Multi-Strategy Engine
"""

from backend.strategies.scalping import ScalpingStrategy
from backend.strategies.swing import SwingStrategy
from backend.strategies.trend import TrendStrategy
from backend.strategies.mean_reversion import MeanReversionStrategy
from backend.strategies.breakout import BreakoutStrategy
from backend.strategies.multi_strategy import MultiStrategyEngine

__all__ = [
    "ScalpingStrategy",
    "SwingStrategy",
    "TrendStrategy",
    "MeanReversionStrategy",
    "BreakoutStrategy",
    "MultiStrategyEngine",
]
