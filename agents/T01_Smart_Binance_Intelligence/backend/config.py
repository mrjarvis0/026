"""Central configuration, loaded from environment variables (.env)."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _get_float(key: str, default: float) -> float:
    try:
        return float(os.getenv(key, default))
    except (TypeError, ValueError):
        return default


def _get_int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, default))
    except (TypeError, ValueError):
        return default


def _get_bool(key: str, default: bool) -> bool:
    val = os.getenv(key)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


# --- Binance credentials (only used for real trading) ---
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET", "")
BINANCE_TESTNET = _get_bool("BINANCE_TESTNET", True)

# --- Paper trading ---
PAPER_START_BALANCE = _get_float("PAPER_START_BALANCE", 1000.0)
PAPER_FEE_PCT = _get_float("PAPER_FEE_PCT", 0.001)

# --- Accuracy gate ---
ACCURACY_UNLOCK_THRESHOLD = _get_float("ACCURACY_UNLOCK_THRESHOLD", 70.0)
ACCURACY_MIN_TRADES = _get_int("ACCURACY_MIN_TRADES", 50)

# --- Risk ---
RISK_PER_TRADE_PAPER = _get_float("RISK_PER_TRADE_PAPER", 0.02)
RISK_PER_TRADE_REAL = _get_float("RISK_PER_TRADE_REAL", 0.01)
STOP_LOSS_PCT = _get_float("STOP_LOSS_PCT", 0.02)
TAKE_PROFIT_PCT = _get_float("TAKE_PROFIT_PCT", 0.04)
MAX_CONCURRENT_POSITIONS = _get_int("MAX_CONCURRENT_POSITIONS", 3)
DAILY_LOSS_LIMIT_PCT = _get_float("DAILY_LOSS_LIMIT_PCT", 0.03)

# --- Server ---
HOST = os.getenv("HOST", "127.0.0.1")
PORT = _get_int("PORT", 8000)
# Extra hostnames allowed to reach the API (comma-separated), e.g. a LAN IP.
# Leave empty to restrict to localhost only (secure default).
TRUSTED_HOSTS = [h.strip() for h in os.getenv("TRUSTED_HOSTS", "").split(",") if h.strip()]

# --- Paths ---
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
FRONTEND_DIR = BASE_DIR / "frontend"
DB_PATH = DATA_DIR / "trades.db"

DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# Default symbol shown on first load (user can pick any Binance pair)
DEFAULT_SYMBOL = "BTC/USDT"
DEFAULT_TIMEFRAME = "5m"
