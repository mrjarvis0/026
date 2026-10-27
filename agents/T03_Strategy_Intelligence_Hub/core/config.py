"""Central paths and environment loading for the hub.

Config is separated from code (Constitution R-C.3): secrets come from the
environment / a local .env, never from source.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# --- repository paths ---------------------------------------------------------
# core/config.py -> core/ -> repo root
HUB_ROOT: Path = Path(__file__).resolve().parent.parent
AGENTS_DIR: Path = HUB_ROOT / "agents"
DATA_DIR: Path = HUB_ROOT / "data"
LOGS_DIR: Path = HUB_ROOT / "logs"
TEMPLATES_DIR: Path = HUB_ROOT / "templates"
REGISTRY_FILE: Path = HUB_ROOT / "AGENTS_INDEX.md"
ENV_FILE: Path = HUB_ROOT / ".env"

for _d in (DATA_DIR, LOGS_DIR):
    _d.mkdir(parents=True, exist_ok=True)


def load_env(env_file: Path = ENV_FILE) -> None:
    """Load .env into os.environ if python-dotenv is available.

    Degrades gracefully: backtesting on public crypto data needs no secrets, so a
    missing .env or missing python-dotenv is not fatal.
    """
    try:
        from dotenv import load_dotenv
    except ImportError:  # pragma: no cover - optional dependency
        return
    if env_file.exists():
        load_dotenv(env_file)


def get_secret(name: str, default: str | None = None) -> str | None:
    """Fetch a secret from the environment (after load_env). Never logged."""
    return os.environ.get(name, default)


@dataclass(frozen=True)
class BacktestConfig:
    """Default backtest assumptions. Overridable per-agent via config.yaml."""

    starting_cash: float = 10_000.0
    commission: float = 0.001          # 0.1% per side (round-trip ~0.2%)
    risk_free_rate: float = 0.0        # annualized, for Sharpe/Sortino
    periods_per_year: int = 365        # crypto trades 365d; equities use 252

    @staticmethod
    def periods_for(timeframe: str, market: str) -> int:
        """Bars per year for annualizing metrics, given timeframe & market."""
        base = 365 if market == "crypto" else 252
        tf = timeframe.strip().lower()
        per_day = {
            "1d": 1, "1day": 1, "d": 1,
            "12h": 2, "8h": 3, "6h": 4, "4h": 6, "2h": 12,
            "1h": 24, "30m": 48, "15m": 96, "5m": 288, "1m": 1440,
        }.get(tf, 1)
        return base * per_day


@dataclass(frozen=True)
class LiveConfig:
    """Live paper-trading limits & sizing. Overridable per-agent via config.yaml `live:`.

    All monetary values are in the quote currency (USDT for crypto). These are
    guardrails (Constitution R-B.9: bound consumption) — testnet only.
    """

    size_frac: float = 0.99          # fraction of equity to deploy when target = long
    min_order_usdt: float = 10.0     # Binance spot min notional is ~10 USDT
    max_order_usdt: float = 100_000  # refuse any single order larger than this
    max_trades_per_day: int = 5      # cap orders/day per agent (daily strategy => ~1)

    @classmethod
    def from_dict(cls, d: dict | None) -> "LiveConfig":
        d = d or {}
        return cls(
            size_frac=float(d.get("size_frac", cls.size_frac)),
            min_order_usdt=float(d.get("min_order_usdt", cls.min_order_usdt)),
            max_order_usdt=float(d.get("max_order_usdt", cls.max_order_usdt)),
            max_trades_per_day=int(d.get("max_trades_per_day", cls.max_trades_per_day)),
        )
