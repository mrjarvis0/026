# Data module for T01 Smart Binance Intelligence v2
"""
Data collection and management module.

This module provides:
- REST API data collection via ccxt
- WebSocket real-time data streaming
- Data buffering and caching
- Historical data loading
"""

from .collector import DataCollector

__all__ = ['DataCollector']
