"""T01 → T03 bridge.

T01 (Smart Binance Intelligence) calls this to use T03's 8 strategy agents
for signal consensus and performance backtesting.

Usage from T01:
    import sys; sys.path.insert(0, str(T03_ROOT))
    from bridge import scan_consensus, backtest_all, best_strategies

All functions are synchronous (T01 is sync) and safe to call repeatedly;
they never write to T01's database or change T03 state.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Make sure T03's core is importable from wherever T01 calls this
_T03_ROOT = Path(__file__).resolve().parent.parent
if str(_T03_ROOT) not in sys.path:
    sys.path.insert(0, str(_T03_ROOT))

from core.scan import scan, consensus  # noqa: E402
from core.data import get_data  # noqa: E402
from core.registry import load_agent_config, load_strategy, resolve_agent  # noqa: E402
from core.backtest.runner import run_backtest as bt_run  # noqa: E402


@dataclass
class BacktestSummary:
    """Per-strategy backtest metrics — the numbers T01 judges by."""
    agent: str
    strategy: str
    win_rate: float          # fraction of winning trades (0–1)
    total_return: float      # net return over the backtest window (e.g. 0.45 = +45%)
    sharpe: float
    max_drawdown: float      # negative fraction (e.g. -0.12 = -12%)
    n_trades: int
    cagr: float
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None

    def summary_line(self) -> str:
        if not self.ok:
            return f"{self.agent:<20}  ERR: {self.error}"
        return (
            f"{self.agent:<20}  win={self.win_rate:.0%}  ret={self.total_return:+.1%}"
            f"  sharpe={self.sharpe:.2f}  dd={self.max_drawdown:.1%}  n={self.n_trades}"
        )


def scan_consensus(
    symbol: str,
    timeframe: str = "1h",
    start: str = "2023-01-01",
    use_cache: bool = True,
) -> dict[str, Any]:
    """Run all 8 strategy agents on `symbol` and return the consensus dict.

    Returns a dict with keys: long, short, flat, err, net, bias, total,
    plus an `agents` list of per-agent signal rows for tracing.
    """
    _bars, signals = scan(symbol, market="crypto", timeframe=timeframe,
                          start=start, use_cache=use_cache)
    c = consensus(signals)
    c["agents"] = [
        {"agent": s.agent, "strategy": s.strategy, "signal": s.signal,
         "error": s.error}
        for s in signals
    ]
    return c


def backtest_all(
    symbol: str,
    timeframe: str = "1h",
    start: str = "2022-01-01",
    cash: float = 10_000.0,
    commission: float = 0.001,
    use_cache: bool = True,
) -> list[BacktestSummary]:
    """Backtest every T03 strategy agent on `symbol` and return sorted results.

    Results are sorted best→worst by Sharpe ratio.
    T01 uses this to see which strategies outperform before letting them
    influence its own decisions.
    """
    from core.scan import list_agent_dirs

    data = get_data("crypto", symbol, timeframe, start, None, use_cache=use_cache)
    closed = data.iloc[:-1]

    results: list[BacktestSummary] = []
    for adir in list_agent_dirs():
        try:
            cfg = load_agent_config(adir)
            strat = load_strategy(adir, **cfg.get("params", {}))
            res = bt_run(strat, closed, cash=cash, commission=commission)
            m = res.metrics
            results.append(BacktestSummary(
                agent=adir.name,
                strategy=strat.name,
                win_rate=m.get("win_rate", 0.0),
                total_return=m.get("total_return", 0.0),
                sharpe=m.get("sharpe", 0.0),
                max_drawdown=m.get("max_drawdown", 0.0),
                n_trades=m.get("num_trades", 0),
                cagr=m.get("cagr", 0.0),
            ))
        except Exception as exc:
            results.append(BacktestSummary(
                agent=adir.name, strategy="?",
                win_rate=0.0, total_return=0.0, sharpe=0.0,
                max_drawdown=0.0, n_trades=0, cagr=0.0,
                error=str(exc),
            ))

    results.sort(key=lambda r: r.sharpe, reverse=True)
    return results


def best_strategies(
    symbol: str,
    timeframe: str = "1h",
    start: str = "2022-01-01",
    min_win_rate: float = 0.50,
    min_sharpe: float = 0.5,
    top_n: int = 3,
) -> list[BacktestSummary]:
    """Return the top N strategies that clear the win-rate and Sharpe bars.

    T01 calls this to decide which T03 strategies to follow.
    """
    all_bt = backtest_all(symbol, timeframe, start)
    passing = [r for r in all_bt if r.ok
               and r.win_rate >= min_win_rate
               and r.sharpe >= min_sharpe]
    return passing[:top_n]
