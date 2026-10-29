"""Run the consumers once.   python -m bootstrap.consume --once

Today: the librarian (A015 events -> persistent brain). Exit 1 if an event had to be parked.
"""
from __future__ import annotations

import argparse

from bootstrap.consumers import librarian
from bootstrap.wire import build_brain, build_store
from orchestrator.event_bus.store import StoreBusy


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bootstrap.consume")
    parser.add_argument("--once", action="store_true", help="deliver what is pending and exit")
    parser.add_argument("--db", default=None, help="bus database path (default data/bus/bus.db)")
    parser.add_argument("--brain", default=None, help="brain database path (default data/brain/brain.db)")
    args = parser.parse_args(argv)
    try:
        stats = librarian.run_once(build_store(args.db), build_brain(args.brain))
    except StoreBusy as exc:
        print(f"[consume] bus database busy: {exc}")
        return 1
    print(f"[consume] librarian: delivered {stats.delivered}, skipped {stats.skipped_other_type + stats.skipped_low_maturity},"
          f" failed {stats.failed}, parked {stats.parked}")
    return 1 if stats.parked else 0


if __name__ == "__main__":
    raise SystemExit(main())
