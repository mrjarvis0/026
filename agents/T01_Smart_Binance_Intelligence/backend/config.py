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
# Round-trip trading fee applied to paper fills so simulated PnL is net-of-fee
# (0.001 = 0.10 %, Binance spot taker default).
PAPER_FEE_PCT = _get_float("PAPER_FEE_PCT", 0.001)
# Fee used when recording REAL fills. The exchange charges the real account on
# both legs, so the DB-recorded PnL subtracts the same round-trip fee — set this
# to your actual VIP/maker tier so paper and real metrics stay comparable (F2).
REAL_FEE_PCT = _get_float("REAL_FEE_PCT", 0.001)

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

# --- Adaptive (ATR) stops & trailing ---
# When enabled and an ATR reading is available, stop/target distances scale with
# recent volatility (ATR * multiplier) instead of a flat % of price — tighter in
# calm tape, wider in volatile tape. Falls back to STOP_LOSS_PCT/TAKE_PROFIT_PCT
# whenever ATR is missing (e.g. too few bars), so behaviour is never worse than
# the fixed-% baseline.
USE_ATR_STOPS = _get_bool("USE_ATR_STOPS", True)
ATR_PERIOD = _get_int("ATR_PERIOD", 14)
ATR_STOP_MULT = _get_float("ATR_STOP_MULT", 1.5)    # stop distance = ATR * this
ATR_TP_MULT = _get_float("ATR_TP_MULT", 3.0)        # target distance = ATR * this (2:1 RR)
# Trailing stop: once a long is in profit, ratchet the stop up to lock gains.
# Never loosens a stop; only moves it in the profitable direction.
TRAIL_ENABLED = _get_bool("TRAIL_ENABLED", True)
TRAIL_PCT = _get_float("TRAIL_PCT", 0.015)          # trail distance below peak (1.5%)

# --- Regime & loss-reflection (roadmap #16) ---
# ADX at/above this reads as a trending regime; below it as chop/range. Used to
# label each trade's entry regime so the reflection engine can tell "lost in chop"
# apart from "lost in a trend" and correct the specific cause.
ADX_TREND_MIN = _get_float("ADX_TREND_MIN", 20.0)
# Reflection only acts once it has at least this many recent closed trades and the
# recent loss rate is elevated — so it reacts to a real losing streak, not noise.
REFLECT_MIN_TRADES = _get_int("REFLECT_MIN_TRADES", 8)
REFLECT_LOSS_RATE = _get_float("REFLECT_LOSS_RATE", 0.4)   # >40% recent losses -> diagnose

# --- Server ---
HOST = os.getenv("HOST", "127.0.0.1")
PORT = _get_int("PORT", 8000)
# Extra hostnames allowed to reach the API (comma-separated), e.g. a LAN IP.
# Leave empty to restrict to localhost only (secure default).
TRUSTED_HOSTS = [h.strip() for h in os.getenv("TRUSTED_HOSTS", "").split(",") if h.strip()]

# --- T03 Strategy Intelligence Hub integration ---
# Set T03_ENABLED=true in .env to activate T03 consensus as a soft veto on entries (engine.apply_t03_veto).
# T03 is located automatically (fleet layout: agents/T01_... and agents/T03_... are siblings).
# T03_SYMBOL is only the fallback; the veto asks T03 about the symbol T01 is trading.
T03_ENABLED = _get_bool("T03_ENABLED", True)
T03_SYMBOL = os.getenv("T03_SYMBOL", "BTC/USDT")
T03_TIMEFRAME = os.getenv("T03_TIMEFRAME", "1h")

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
