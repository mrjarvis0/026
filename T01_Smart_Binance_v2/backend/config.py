"""Central configuration for T01 Smart Binance Intelligence v2.

All configuration is loaded from environment variables (.env file).
This module provides a single source of truth for all settings.
"""

import os
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _get_float(key: str, default: float) -> float:
    """Get float value from environment, with fallback."""
    try:
        return float(os.getenv(key, default))
    except (TypeError, ValueError):
        return default


def _get_int(key: str, default: int) -> int:
    """Get integer value from environment, with fallback."""
    try:
        return int(os.getenv(key, default))
    except (TypeError, ValueError):
        return default


def _get_bool(key: str, default: bool) -> bool:
    """Get boolean value from environment, with fallback."""
    val = os.getenv(key)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


def _get_list(key: str, default: List[str]) -> List[str]:
    """Get list value from environment (comma-separated), with fallback."""
    val = os.getenv(key)
    if val is None:
        return default
    return [v.strip() for v in val.split(",") if v.strip()]


# ============================================================================
# BINANCE API CREDENTIALS
# ============================================================================

BINANCE_API_KEY: str = os.getenv("BINANCE_API_KEY", "")
BINANCE_API_SECRET: str = os.getenv("BINANCE_API_SECRET", "")
BINANCE_TESTNET: bool = _get_bool("BINANCE_TESTNET", True)

# ============================================================================
# PAPER TRADING SETTINGS
# ============================================================================

PAPER_START_BALANCE: float = _get_float("PAPER_START_BALANCE", 1000.0)
PAPER_FEE_PCT: float = _get_float("PAPER_FEE_PCT", 0.001)  # 0.10%

# ============================================================================
# ACCURACY GATE SETTINGS
# ============================================================================

ACCURACY_UNLOCK_THRESHOLD: float = _get_float("ACCURACY_UNLOCK_THRESHOLD", 70.0)
ACCURACY_MIN_TRADES: int = _get_int("ACCURACY_MIN_TRADES", 50)

# ============================================================================
# RISK MANAGEMENT SETTINGS
# ============================================================================

RISK_PER_TRADE_PAPER: float = _get_float("RISK_PER_TRADE_PAPER", 0.02)  # 2%
RISK_PER_TRADE_REAL: float = _get_float("RISK_PER_TRADE_REAL", 0.01)  # 1%
STOP_LOSS_PCT: float = _get_float("STOP_LOSS_PCT", 0.02)  # 2%
TAKE_PROFIT_PCT: float = _get_float("TAKE_PROFIT_PCT", 0.04)  # 4%
MAX_CONCURRENT_POSITIONS: int = _get_int("MAX_CONCURRENT_POSITIONS", 3)
DAILY_LOSS_LIMIT_PCT: float = _get_float("DAILY_LOSS_LIMIT_PCT", 0.03)  # 3%

# ============================================================================
# ADAPTIVE (ATR) STOPS & TRAILING SETTINGS
# ============================================================================

USE_ATR_STOPS: bool = _get_bool("USE_ATR_STOPS", True)
ATR_PERIOD: int = _get_int("ATR_PERIOD", 14)
ATR_STOP_MULT: float = _get_float("ATR_STOP_MULT", 1.5)
ATR_TP_MULT: float = _get_float("ATR_TP_MULT", 3.0)
TRAIL_ENABLED: bool = _get_bool("TRAIL_ENABLED", True)
TRAIL_PCT: float = _get_float("TRAIL_PCT", 0.015)  # 1.5%

# ============================================================================
# REGIME & LOSS-REFLECTION SETTINGS
# ============================================================================

ADX_TREND_MIN: float = _get_float("ADX_TREND_MIN", 20.0)
REFLECT_MIN_TRADES: int = _get_int("REFLECT_MIN_TRADES", 8)
REFLECT_LOSS_RATE: float = _get_float("REFLECT_LOSS_RATE", 0.4)  # 40%

# ============================================================================
# WEBSOCKET SETTINGS (Phase 2)
# ============================================================================

WEBSOCKET_ENABLED: bool = _get_bool("WEBSOCKET_ENABLED", True)
WEBSOCKET_URL: str = os.getenv("WEBSOCKET_URL", "wss://stream.binance.com:9443/ws")
WEBSOCKET_RECONNECT_DELAY: float = _get_float("WEBSOCKET_RECONNECT_DELAY", 1.0)
WEBSOCKET_MAX_RECONNECT_DELAY: float = _get_float("WEBSOCKET_MAX_RECONNECT_DELAY", 60.0)
WEBSOCKET_RECONNECT_BACKOFF: float = _get_float("WEBSOCKET_RECONNECT_BACKOFF", 1.5)
WEBSOCKET_PING_INTERVAL: float = _get_float("WEBSOCKET_PING_INTERVAL", 30.0)

# ============================================================================
# SERVER SETTINGS
# ============================================================================

HOST: str = os.getenv("HOST", "127.0.0.1")
PORT: int = _get_int("PORT", 8000)
TRUSTED_HOSTS: List[str] = _get_list("TRUSTED_HOSTS", [])

# ============================================================================
# DEFAULT SETTINGS
# ============================================================================

DEFAULT_SYMBOL: str = os.getenv("DEFAULT_SYMBOL", "BTC/USDT")
DEFAULT_TIMEFRAME: str = os.getenv("DEFAULT_TIMEFRAME", "5m")

# ============================================================================
# BACKTESTING SETTINGS (Phase 1)
# ============================================================================

BACKTEST_DATA_DIR: Path = BASE_DIR / _get_list("BACKTEST_DATA_DIR", ["data/historical"])[0]
BACKTEST_LIMIT: int = _get_int("BACKTEST_LIMIT", 10000)
BACKTEST_FEE_PCT: float = _get_float("BACKTEST_FEE_PCT", 0.001)
BACKTEST_SLIPPAGE_PCT: float = _get_float("BACKTEST_SLIPPAGE_PCT", 0.0005)

# ============================================================================
# SCANNER SETTINGS (Phase 2)
# ============================================================================

SCANNER_ENABLED: bool = _get_bool("SCANNER_ENABLED", False)
SCANNER_INTERVAL: int = _get_int("SCANNER_INTERVAL", 60)
SCANNER_CONCURRENCY: int = _get_int("SCANNER_CONCURRENCY", 10)
SCANNER_MAX_SYMBOLS: int = _get_int("SCANNER_MAX_SYMBOLS", 500)
SCANNER_MIN_VOLUME: float = _get_float("SCANNER_MIN_VOLUME", 1000000)

# ============================================================================
# MULTI-TIMEFRAME SETTINGS (Phase 2)
# ============================================================================

MTF_ENABLED: bool = _get_bool("MTF_ENABLED", False)
MTF_TIMEFRAMES: List[str] = _get_list("MTF_TIMEFRAMES", ["1m", "5m", "15m", "1h"])
MTF_WEIGHTS: List[float] = [float(w) for w in _get_list("MTF_WEIGHTS", ["0.4", "0.3", "0.2", "0.1"])]
MTF_TREND_FILTER: bool = _get_bool("MTF_TREND_FILTER", True)

# ============================================================================
# PATTERN DETECTION SETTINGS (Phase 3)
# ============================================================================

PATTERN_DETECTION_ENABLED: bool = _get_bool("PATTERN_DETECTION_ENABLED", False)
PATTERN_MIN_CONFIDENCE: float = _get_float("PATTERN_MIN_CONFIDENCE", 0.5)
PATTERN_REQUIRE_CONFIRMATION: bool = _get_bool("PATTERN_REQUIRE_CONFIRMATION", False)
PATTERN_CONFIRMATION_CANDLES: int = _get_int("PATTERN_CONFIRMATION_CANDLES", 1)

# ============================================================================
# STRATEGY SETTINGS (Phase 3)
# ============================================================================

STRATEGY_MODE: str = os.getenv("STRATEGY_MODE", "single")  # single/multi/all
STRATEGY_DEFAULT: str = os.getenv("STRATEGY_DEFAULT", "swing")
STRATEGY_SELECTION_CRITERIA: str = os.getenv("STRATEGY_SELECTION_CRITERIA", "performance")
STRATEGY_AUTO_SELECT: bool = _get_bool("STRATEGY_AUTO_SELECT", False)

# ============================================================================
# FUTURES TRADING SETTINGS (Phase 4)
# ============================================================================

FUTURES_ENABLED: bool = _get_bool("FUTURES_ENABLED", False)
FUTURES_EXCHANGE: str = os.getenv("FUTURES_EXCHANGE", "binance")
FUTURES_TESTNET: bool = _get_bool("FUTURES_TESTNET", True)
FUTURES_DEFAULT_LEVERAGE: int = _get_int("FUTURES_DEFAULT_LEVERAGE", 5)
FUTURES_MAX_LEVERAGE: int = _get_int("FUTURES_MAX_LEVERAGE", 20)
FUTURES_MARGIN_MODE: str = os.getenv("FUTURES_MARGIN_MODE", "cross")
FUTURES_RISK_PER_TRADE: float = _get_float("FUTURES_RISK_PER_TRADE", 0.005)
FUTURES_MAX_DRAWDOWN: float = _get_float("FUTURES_MAX_DRAWDOWN", 0.10)
FUTURES_LIQUIDATION_RISK_THRESHOLD: float = _get_float("FUTURES_LIQUIDATION_RISK_THRESHOLD", 0.10)
FUTURES_MAX_POSITIONS: int = _get_int("FUTURES_MAX_POSITIONS", 5)
FUTURES_FUNDING_RATE_WARNING: float = _get_float("FUTURES_FUNDING_RATE_WARNING", 0.05)

# ============================================================================
# MACHINE LEARNING SETTINGS (Optional)
# ============================================================================

ML_ENABLED: bool = _get_bool("ML_ENABLED", False)
ML_MODEL_PATH: str = os.getenv("ML_MODEL_PATH", "models/trading_model.pkl")
ML_USE_HYBRID: bool = _get_bool("ML_USE_HYBRID", True)
ML_HYBRID_WEIGHTS: List[float] = [float(w) for w in _get_list("ML_HYBRID_WEIGHTS", ["0.7", "0.3"])]

# ============================================================================
# NOTIFICATION SETTINGS (Optional)
# ============================================================================

NOTIFICATIONS_ENABLED: bool = _get_bool("NOTIFICATIONS_ENABLED", False)
TELEGRAM_BOT_TOKEN: Optional[str] = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID: Optional[str] = os.getenv("TELEGRAM_CHAT_ID")
NOTIFICATION_ON_ENTRY: bool = _get_bool("NOTIFICATION_ON_ENTRY", True)
NOTIFICATION_ON_EXIT: bool = _get_bool("NOTIFICATION_ON_EXIT", True)
NOTIFICATION_ON_ERROR: bool = _get_bool("NOTIFICATION_ON_ERROR", True)

# ============================================================================
# LOGGING SETTINGS
# ============================================================================

LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
LOG_DIR: Path = BASE_DIR / os.getenv("LOG_DIR", "logs")
LOG_FILE: str = os.getenv("LOG_FILE", "trading_bot.log")

# ============================================================================
# PERFORMANCE SETTINGS
# ============================================================================

BOT_INTERVAL: int = _get_int("BOT_INTERVAL", 12)  # Seconds between cycles
MAX_CANDLES: int = _get_int("MAX_CANDLES", 250)
MIN_BARS: int = _get_int("MIN_BARS", 30)

# ============================================================================
# PATHS
# ============================================================================

DATA_DIR: Path = BASE_DIR / "data"
LOGS_DIR: Path = BASE_DIR / "logs"
FRONTEND_DIR: Path = BASE_DIR / "frontend"
DB_PATH: Path = DATA_DIR / "trades.db"
MODELS_DIR: Path = BASE_DIR / "models"
HISTORICAL_DATA_DIR: Path = DATA_DIR / "historical"
PROCESSED_DATA_DIR: Path = DATA_DIR / "processed"

# Create directories if they don't exist
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
HISTORICAL_DATA_DIR.mkdir(exist_ok=True)
PROCESSED_DATA_DIR.mkdir(exist_ok=True)
MODELS_DIR.mkdir(exist_ok=True)


# ============================================================================
# VALIDATION
# ============================================================================

def validate_config():
    """Validate configuration values."""
    errors = []
    
    # Check required ranges
    if not 0 < ACCURACY_UNLOCK_THRESHOLD <= 100:
        errors.append("ACCURACY_UNLOCK_THRESHOLD must be between 0 and 100")
    
    if ACCURACY_MIN_TRADES < 1:
        errors.append("ACCURACY_MIN_TRADES must be at least 1")
    
    if not 0 < RISK_PER_TRADE_PAPER <= 1:
        errors.append("RISK_PER_TRADE_PAPER must be between 0 and 1")
    
    if not 0 < RISK_PER_TRADE_REAL <= 1:
        errors.append("RISK_PER_TRADE_REAL must be between 0 and 1")
    
    if MAX_CONCURRENT_POSITIONS < 1:
        errors.append("MAX_CONCURRENT_POSITIONS must be at least 1")
    
    if not 0 < DAILY_LOSS_LIMIT_PCT <= 1:
        errors.append("DAILY_LOSS_LIMIT_PCT must be between 0 and 1")
    
    if BOT_INTERVAL < 1:
        errors.append("BOT_INTERVAL must be at least 1 second")
    
    if MIN_BARS < 10:
        errors.append("MIN_BARS must be at least 10")
    
    if errors:
        raise ValueError(f"Configuration errors: {', '.join(errors)}")


# Validate configuration on import
try:
    validate_config()
except ValueError as e:
    import logging
    logging.getLogger("config").error(f"Configuration validation failed: {e}")
    # Continue with defaults


if __name__ == "__main__":
    # Print all configuration for debugging
    import pprint
    config_dict = {
        k: v for k, v in globals().items() 
        if not k.startswith("_") and not callable(v)
    }
    pprint.pprint(config_dict, width=1)
