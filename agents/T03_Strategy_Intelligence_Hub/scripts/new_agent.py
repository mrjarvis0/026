"""Scaffold a new strategy-agent with the next serial (allocated in order).

Usage:
    python scripts/new_agent.py --owner livermore --market crypto \
        --strategy "Trend breakout / pyramiding" --symbols BTC/USDT --timeframe 1d

Creates agents/$NNN-<owner-slug>/ from templates/ and appends a row to AGENTS_INDEX.md.
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

HUB_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HUB_ROOT))

from core.config import AGENTS_DIR, TEMPLATES_DIR  # noqa: E402
from core.registry import (  # noqa: E402
    agent_folder_name,
    append_agent_row,
    format_serial,
    next_serial,
    slugify,
)

DEFAULT_SYMBOLS = {"crypto": "BTC/USDT", "forex": "EURUSD", "stocks": "AAPL"}


def _class_name(slug: str) -> str:
    return "".join(part.capitalize() for part in slug.split("-")) + "Strategy"


def _fill(template: str, mapping: dict[str, str]) -> str:
    for key, val in mapping.items():
        template = template.replace("{{" + key + "}}", val)
    return template


def main() -> int:
    ap = argparse.ArgumentParser(description="Scaffold a new strategy-agent.")
    ap.add_argument("--owner", required=True, help="Trader name, e.g. 'livermore'")
    ap.add_argument("--market", required=True, choices=["crypto", "forex", "stocks"])
    ap.add_argument("--strategy", default="TODO: describe the strategy")
    ap.add_argument("--symbols", default=None, help="e.g. BTC/USDT")
    ap.add_argument("--timeframe", default="1d")
    args = ap.parse_args()

    slug = slugify(args.owner)
    serial = next_serial()
    folder = agent_folder_name(serial, slug)
    agent_dir = AGENTS_DIR / folder
    if agent_dir.exists():
        print(f"ERROR: {agent_dir} already exists.", file=sys.stderr)
        return 1

    symbols = args.symbols or DEFAULT_SYMBOLS[args.market]
    mapping = {
        "AGENT_NAME": folder,
        "SERIAL": format_serial(serial),
        "OWNER": args.owner,
        "OWNER_SLUG": slug,
        "MARKET": args.market,
        "STRATEGY": args.strategy,
        "SYMBOLS": symbols,
        "TIMEFRAME": args.timeframe,
        "DATE": date.today().isoformat(),
        "CLASS_NAME": _class_name(slug),
    }

    (agent_dir / "results" / "backtest").mkdir(parents=True, exist_ok=True)
    (agent_dir / "results" / "training").mkdir(parents=True, exist_ok=True)

    files = {
        "agent.agent.md.tmpl": f"{folder}.agent.md",
        "strategy.py.tmpl": "strategy.py",
        "config.yaml.tmpl": "config.yaml",
        "README.md.tmpl": "README.md",
    }
    for tmpl_name, out_name in files.items():
        tmpl = (TEMPLATES_DIR / tmpl_name).read_text(encoding="utf-8")
        (agent_dir / out_name).write_text(_fill(tmpl, mapping), encoding="utf-8")

    append_agent_row(serial, args.owner, slug, args.market, args.strategy)

    print(f"Created agent {folder} at {agent_dir}")
    print(f"  spec:     {folder}.agent.md   (fill in {args.owner}'s cited rules)")
    print(f"  strategy: strategy.py         (replace placeholder logic)")
    print(f"  config:   config.yaml         (symbols={symbols}, timeframe={args.timeframe})")
    print(f"Registry updated: next serial is now {format_serial(serial + 1)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
