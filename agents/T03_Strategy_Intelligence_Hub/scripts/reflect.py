"""Reflect on an agent's trades: learn from losses so they aren't repeated.

Runs the agent's backtest, reconstructs every trade, diagnoses the losers into
categorized lessons, updates the mistakes memory (results/MISTAKES.md), and shows
whether the agent's CURRENT signal would repeat a known mistake (the pre-trade guard).

Usage:
    python scripts/reflect.py '$004-williams'
    python scripts/reflect.py '$001-dennis' --reset   # clear memory first
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _common import backtest_kwargs, fetch_for, load_agent  # noqa: E402
from core.backtest.runner import run_backtest  # noqa: E402
from core.learn import (MistakeMemory, check_trade, diagnose,  # noqa: E402
                        extract_trades, latest_context)


def main() -> int:
    ap = argparse.ArgumentParser(description="Learn from an agent's losing trades.")
    ap.add_argument("agent", help="agent id, e.g. '$004-williams'")
    ap.add_argument("--reset", action="store_true", help="clear the mistakes memory first")
    args = ap.parse_args()

    agent_dir, config, strategy = load_agent(args.agent)
    _, _, data = fetch_for(config)
    result = run_backtest(strategy, data, **backtest_kwargs(config))

    mem = MistakeMemory(agent_dir)
    if args.reset and mem.jsonl.exists():
        mem.jsonl.unlink()

    trades = extract_trades(data, result.applied_pos)
    losers = [t for t in trades if t.is_loss]
    lessons = [les for t in losers if (les := diagnose(t)) is not None]
    mem.record_many(lessons, source="backtest")
    mem.render_markdown(agent_dir.name)

    print(f"Agent {agent_dir.name}: {len(trades)} trades, {len(losers)} losers "
          f"({len(losers)/max(1,len(trades)):.0%} loss rate)")
    print(f"Lessons recorded -> {mem.md}")
    print("\nTop recurring mistakes (costliest first):")
    for g in mem.aggregate()[:5]:
        print(f"  [{g['category']}] x{g['repeats']}  total {g['total_loss']:.1%}  "
              f"avg {g['avg_loss']:.1%}")
        print(f"      RULE: {g['rule']}")

    # pre-trade guard on the agent's CURRENT signal
    signals = strategy.generate_signals(data)
    cur = int(signals["position"].iloc[-1])
    print(f"\nCurrent signal: {'LONG' if cur>0 else 'SHORT' if cur<0 else 'flat'}")
    if cur != 0:
        warns = check_trade(cur, latest_context(data), mem, min_repeats=2)
        if warns:
            print("Pre-trade GUARD warnings:")
            for w in warns:
                print(f"  {w['message']}")
        else:
            print("Pre-trade guard: no known-mistake match for the current setup. OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
