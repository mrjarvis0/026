"""Train / optimize an agent with walk-forward (out-of-sample) validation.

Usage:
    python scripts/train.py '$001-dennis'
    python scripts/train.py '$001-dennis' --splits 5 --metric sortino
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _common import backtest_kwargs, fetch_for, load_agent  # noqa: E402
from core.train.optimizer import walk_forward  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Walk-forward optimize an agent.")
    ap.add_argument("agent", help="agent id, e.g. '$001-dennis'")
    ap.add_argument("--splits", type=int, default=4)
    ap.add_argument("--metric", default=None, help="override optimize_metric from config")
    args = ap.parse_args()

    agent_dir, config, strategy = load_agent(args.agent)
    symbol, timeframe, data = fetch_for(config)
    metric = args.metric or config.get("optimize_metric", "sharpe")
    grid = config.get("param_grid", {})
    if not grid:
        print("No 'param_grid' in config.yaml — nothing to optimize.", file=sys.stderr)
        return 1

    bt_kwargs = backtest_kwargs(config)
    print(f"Walk-forward on {agent_dir.name}: {len(data)} bars, {args.splits} splits, "
          f"optimizing '{metric}' over grid {grid}")

    report = walk_forward(
        type(strategy), data, grid,
        n_splits=args.splits, metric=metric,
        cash=bt_kwargs["cash"], commission=bt_kwargs["commission"],
        periods_per_year=bt_kwargs["periods_per_year"],
    )

    for f in report["folds"]:
        print(f"  fold {f['fold']}: params={f['chosen_params']} "
              f"OOS {metric}={f['oos_metrics'].get(metric)}")
    print(f"\nOOS mean {metric}: {report['oos_mean_metric']:.4f}")
    print(f"Recommended (most-selected) params: {report['recommended_params']}")

    out = agent_dir / "results" / "training" / "walk_forward.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"Saved {out}")
    print("Tip: copy recommended params into config.yaml -> params, then re-run backtest & review.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
