"""Futures Trading module for T01 Smart Binance Intelligence v2.

This module provides comprehensive futures trading capabilities including:
- Futures contract trading
- Leverage management
- Margin management
- Liquidation risk calculation
- Funding rate monitoring
- Position sizing for futures
- Futures-specific order types
"""

from backend.futures.futures_manager import FuturesManager
from backend.futures.leverage_manager import LeverageManager
from backend.futures.margin_manager import MarginManager
from backend.futures.liquidation_watcher import LiquidationWatcher

__all__ = [
    "FuturesManager",
    "LeverageManager",
    "MarginManager",
    "LiquidationWatcher",
]
