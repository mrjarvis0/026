"""Generate an agent's performance review (REVIEW.md + equity curve).

Usage:
    python scripts/review.py '$001-dennis'
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _common import backtest_kwargs, fetch_for, load_agent  # noqa: E402
from core.backtest.runner import run_backtest  # noqa: E402
from core.review.report import generate_review  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate REVIEW.md for an agent.")
    ap.add_argument("agent", help="agent id, e.g. '$001-dennis'")
    ap.add_argument("--engine", default="vectorized", choices=["vectorized", "backtesting"])
    args = ap.parse_args()

    agent_dir, config, strategy = load_agent(args.agent)
    _, _, data = fetch_for(config)
    result = run_backtest(strategy, data, engine=args.engine, **backtest_kwargs(config))

    # include walk-forward results if present
    wf_path = agent_dir / "results" / "training" / "walk_forward.json"
    training = json.loads(wf_path.read_text(encoding="utf-8")) if wf_path.exists() else None

    review_path = generate_review(agent_dir, result, config, training)
    print(f"Review written: {review_path}")
    print(f"Verdict line -> see top of {review_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
