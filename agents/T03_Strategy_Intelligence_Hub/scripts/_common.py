"""Shared loading helpers for the run-scripts (backtest / train / review / papertrade)."""
from __future__ import annotations

import sys
from pathlib import Path

# Windows consoles default to cp1252 and crash on non-ASCII output. Force UTF-8
# (best-effort) so scripts print cleanly on any platform.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

HUB_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HUB_ROOT))

from core.config import BacktestConfig  # noqa: E402
from core.data import get_data  # noqa: E402
from core.registry import load_agent_config, load_strategy, resolve_agent  # noqa: E402


def load_agent(name: str, use_config_params: bool = True):
    """Resolve an agent by name and return (agent_dir, config, strategy)."""
    agent_dir = resolve_agent(name)
    config = load_agent_config(agent_dir)
    overrides = config.get("params", {}) if use_config_params else {}
    strategy = load_strategy(agent_dir, **overrides)
    return agent_dir, config, strategy


def primary_symbol(config: dict) -> str:
    symbols = config.get("symbols", config.get("symbol"))
    if isinstance(symbols, (list, tuple)):
        return symbols[0]
    return symbols


def fetch_for(config: dict, start: str | None = None, end: str | None = None):
    """Fetch OHLCV for an agent's primary symbol. Returns (symbol, timeframe, data)."""
    market = config["market"]
    symbol = primary_symbol(config)
    timeframe = config.get("timeframe", "1d")
    d = config.get("data", {}) or {}
    data = get_data(
        market, symbol, timeframe,
        start or d.get("start", "2020-01-01"),
        end or d.get("end"),
    )
    return symbol, timeframe, data


def backtest_kwargs(config: dict) -> dict:
    """cash / commission / periods_per_year from config + market/timeframe."""
    bt = config.get("backtest", {}) or {}
    ppy = BacktestConfig.periods_for(config.get("timeframe", "1d"), config["market"])
    return {
        "cash": float(bt.get("starting_cash", 10_000)),
        "commission": float(bt.get("commission", 0.001)),
        "periods_per_year": ppy,
    }
