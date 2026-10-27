"""Live multi-strategy scanner.

Run EVERY agent's strategy on the SAME chosen token/timeframe and report what each
one signals right now (LONG / SHORT / flat), plus the consensus. This is the
"what is this candle pattern, and which strategies are firing on it" view.

Strategies are symbol-agnostic (they only need OHLCV), so we override each agent's
configured symbol with whatever the user is watching.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .config import AGENTS_DIR
from .data import get_data
from .registry import load_agent_config, load_strategy

_NAME = {1: "LONG", -1: "SHORT", 0: "flat"}


@dataclass
class AgentSignal:
    agent: str
    strategy: str
    signal: str            # LONG | SHORT | flat | ERR
    position: float = 0.0
    error: str | None = None


def list_agent_dirs() -> list[Path]:
    if not AGENTS_DIR.exists():
        return []
    return sorted(p for p in AGENTS_DIR.iterdir() if p.is_dir() and not p.name.startswith("."))


def scan(
    symbol: str,
    market: str = "crypto",
    timeframe: str = "1h",
    start: str = "2023-01-01",
    agent_filter: list[str] | None = None,
    use_cache: bool = False,
) -> tuple[pd.DataFrame, list[AgentSignal]]:
    """Return (closed_bars, [AgentSignal...]) for one symbol across all agents."""
    data = get_data(market, symbol, timeframe, start, None, use_cache=use_cache)
    closed = data.iloc[:-1]  # drop the still-forming bar -> act on last closed
    if len(closed) < 2:
        raise RuntimeError("not enough closed bars to scan")

    out: list[AgentSignal] = []
    for adir in list_agent_dirs():
        if agent_filter and not any(f.strip("$") in adir.name for f in agent_filter):
            continue
        try:
            cfg = load_agent_config(adir)
            strat = load_strategy(adir, **cfg.get("params", {}))
            sig = strat.generate_signals(closed)
            pos = float(sig["position"].iloc[-1])
            out.append(AgentSignal(adir.name, strat.name, _NAME.get(int(pos), "?"), pos))
        except Exception as exc:  # a broken agent shouldn't sink the whole scan
            out.append(AgentSignal(adir.name, "?", "ERR", error=str(exc)))
    return closed, out


def consensus(signals: list[AgentSignal]) -> dict:
    """Tally LONG/SHORT/flat and a net bias across agents."""
    longs = sum(1 for s in signals if s.signal == "LONG")
    shorts = sum(1 for s in signals if s.signal == "SHORT")
    flats = sum(1 for s in signals if s.signal == "flat")
    errs = sum(1 for s in signals if s.signal == "ERR")
    net = longs - shorts
    bias = "LONG" if net > 0 else "SHORT" if net < 0 else "NEUTRAL"
    return {"long": longs, "short": shorts, "flat": flats, "err": errs,
            "net": net, "bias": bias, "total": len(signals)}
