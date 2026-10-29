"""Run the consumers once.   python -m bootstrap.consume --once

The librarian (A015 events -> persistent brain) and the risk flagger (A015 events -> pause flags).
Exit 1 if an event had to be parked.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from bootstrap.consumers import librarian, risk_flagger
from bootstrap.wire import build_brain, build_store
from orchestrator.event_bus.store import StoreBusy


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bootstrap.consume")
    parser.add_argument("--once", action="store_true", help="deliver what is pending and exit")
    parser.add_argument("--retry-parked", action="store_true", help="first re-deliver dead-lettered events")
    parser.add_argument("--db", default=None, help="bus database path (default data/bus/bus.db)")
    parser.add_argument("--brain", default=None, help="brain database path (default data/brain/brain.db)")
    parser.add_argument("--flags", default=None, help="pause-flags file (default data/risk/pause_flags.json)")
    args = parser.parse_args(argv)
    try:
        store, brain = build_store(args.db), build_brain(args.brain)
        if args.retry_parked:
            print(f"[consume] librarian: retried {librarian.retry_parked(store, brain)} parked event(s)")
        stats = librarian.run_once(store, brain)
        flagger = risk_flagger.run_once(store, Path(args.flags) if args.flags else None)
    except StoreBusy as exc:
        print(f"[consume] bus database busy: {exc}")
        return 1
    print(f"[consume] librarian: delivered {stats.delivered}, skipped {stats.skipped_other_type + stats.skipped_low_maturity},"
          f" failed {stats.failed}, parked {stats.parked}")
    print(f"[consume] risk_flagger: delivered {flagger.delivered}, failed {flagger.failed}, parked {flagger.parked}")
    return 1 if stats.parked or flagger.parked else 0


if __name__ == "__main__":
    raise SystemExit(main())
