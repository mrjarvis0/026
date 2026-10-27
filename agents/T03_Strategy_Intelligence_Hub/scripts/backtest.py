"""Backtest one agent on real market data.

Usage:
    python scripts/backtest.py '$001-dennis'
    python scripts/backtest.py '$001-dennis' --engine backtesting --start 2021-01-01
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _common import backtest_kwargs, fetch_for, load_agent  # noqa: E402
from core.backtest.runner import run_backtest  # noqa: E402
from core.review.report import save_metrics  # noqa: E402

KEYS = ["total_return", "cagr", "sharpe", "sortino", "max_drawdown",
        "num_trades", "win_rate", "profit_factor", "exposure"]


def main() -> int:
    ap = argparse.ArgumentParser(description="Backtest an agent.")
    ap.add_argument("agent", help="agent id, e.g. '$001-dennis'")
    ap.add_argument("--engine", default="vectorized", choices=["vectorized", "backtesting"])
    ap.add_argument("--start", default=None)
    ap.add_argument("--end", default=None)
    args = ap.parse_args()

    agent_dir, config, strategy = load_agent(args.agent)
    symbol, timeframe, data = fetch_for(config, args.start, args.end)
    print(f"Agent {agent_dir.name}: {config['market']} {symbol} {timeframe}, {len(data)} bars "
          f"({data.index[0].date()} -> {data.index[-1].date()})")

    result = run_backtest(strategy, data, engine=args.engine, **backtest_kwargs(config))
    m = result.metrics

    print(f"\nEngine: {result.engine}")
    print("-" * 40)
    for k in KEYS:
        print(f"  {k:>14}: {m.get(k)}")
    print(f"  {'buy&hold ret':>14}: {m.get('bh_total_return')}   sharpe: {m.get('bh_sharpe')}")

    bt_dir = agent_dir / "results" / "backtest"
    save_metrics(bt_dir, m)
    result.save(bt_dir)
    print(f"\nSaved metrics + equity curve to {bt_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
