"""Configuration for backtesting module.

This module provides default configuration values for backtesting.
"""

from typing import Dict, Any, List
from backend import config


# Default backtest settings
DEFAULT_BACKTEST_SETTINGS: Dict[str, Any] = {
    'initial_balance': config.PAPER_START_BALANCE,
    'fee_pct': config.PAPER_FEE_PCT,
    'slippage_pct': 0.0005,  # 0.05%
    'start_date': None,
    'end_date': None,
    'limit': config.BACKTEST_LIMIT,
    'timeframes': ['1m', '5m', '15m', '1h', '4h', '1d'],
}


# Default walk-forward settings
DEFAULT_WALKFORWARD_SETTINGS: Dict[str, Any] = {
    'in_sample_periods': 30,
    'out_sample_periods': 10,
    'metric': 'sharpe_ratio',
    'maximize': True,
}


# Default parameter grids for optimization
DEFAULT_PARAMETER_GRIDS: Dict[str, Dict[str, List[Any]]] = {
    'basic': {
        'rsi_buy': [30, 35, 40, 45],
        'rsi_sell': [55, 60, 65, 70],
        'net_threshold': [0.5, 1.0, 1.5, 2.0],
    },
    'advanced': {
        'rsi_buy': [30, 35, 40, 45, 50],
        'rsi_sell': [50, 55, 60, 65, 70],
        'net_threshold': [0.5, 1.0, 1.5, 2.0, 2.5],
        'macd_eps': [0.0001, 0.0002, 0.0005],
        'trend_band': [0.0005, 0.001, 0.002],
    },
    'comprehensive': {
        'rsi_buy': [30, 35, 40, 45, 50, 55],
        'rsi_sell': [45, 50, 55, 60, 65, 70],
        'net_threshold': [0.5, 1.0, 1.5, 2.0, 2.5, 3.0],
        'macd_eps': [0.0001, 0.0002, 0.0005, 0.001],
        'trend_band': [0.0005, 0.001, 0.002, 0.005],
        'atr_stop_mult': [1.0, 1.5, 2.0, 2.5],
        'atr_tp_mult': [2.0, 2.5, 3.0, 3.5],
    },
}


# Metric weights for multi-metric optimization
METRIC_WEIGHTS: Dict[str, float] = {
    'sharpe_ratio': 0.4,
    'win_rate': 0.2,
    'profit_factor': 0.2,
    'max_drawdown': -0.2,  # Negative weight (we want to minimize this)
}


# Default symbols for scanning
DEFAULT_SYMBOLS: List[str] = [
    'BTC/USDT',
    'ETH/USDT',
    'BNB/USDT',
    'SOL/USDT',
    'ADA/USDT',
    'XRP/USDT',
    'DOT/USDT',
    'DOGE/USDT',
    'AVAX/USDT',
    'MATIC/USDT',
]


# Default timeframes for multi-timeframe analysis
DEFAULT_TIMEFRAMES: List[str] = ['1m', '5m', '15m', '1h', '4h']


# Backtest validation rules
BACKTEST_VALIDATION_RULES: Dict[str, Any] = {
    'min_candles': 100,
    'min_trades': 10,
    'max_drawdown_threshold': 0.5,  # 50%
    'min_win_rate': 0.4,  # 40%
    'min_profit_factor': 1.0,
}


def get_backtest_config(symbol: str, timeframe: str) -> Dict[str, Any]:
    """Get backtest configuration for a specific symbol and timeframe.
    
    Args:
        symbol: Trading pair
        timeframe: Timeframe
        
    Returns:
        Configuration dictionary
    """
    config = DEFAULT_BACKTEST_SETTINGS.copy()
    config['symbol'] = symbol
    config['timeframe'] = timeframe
    return config


def get_walkforward_config(
    in_sample_periods: int = 30,
    out_sample_periods: int = 10,
    metric: str = 'sharpe_ratio'
) -> Dict[str, Any]:
    """Get walk-forward optimization configuration.
    
    Args:
        in_sample_periods: Number of in-sample periods
        out_sample_periods: Number of out-sample periods
        metric: Metric to optimize
        
    Returns:
        Configuration dictionary
    """
    config = DEFAULT_WALKFORWARD_SETTINGS.copy()
    config['in_sample_periods'] = in_sample_periods
    config['out_sample_periods'] = out_sample_periods
    config['metric'] = metric
    return config


def get_parameter_grid(grid_name: str = 'basic') -> Dict[str, List[Any]]:
    """Get parameter grid for optimization.
    
    Args:
        grid_name: Name of the parameter grid ('basic', 'advanced', 'comprehensive')
        
    Returns:
        Parameter grid dictionary
    """
    return DEFAULT_PARAMETER_GRIDS.get(grid_name, DEFAULT_PARAMETER_GRIDS['basic'])
