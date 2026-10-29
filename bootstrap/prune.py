"""Retention.   python -m bootstrap.prune --once   (the supervisor runs it weekly)

Archives (JSONL, by month) then deletes events older than ``retention_days`` (config/bus.json, 90) —
but never past a consumer's cursor, so nothing a consumer has not seen is ever removed.
"""
from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
from pathlib import Path

from bootstrap.wire import build_store, load_bus_config
from orchestrator.event_bus.store import DEFAULT_DB, StoreBusy

DEFAULT_ARCHIVE_DIR = DEFAULT_DB.parent / "archive"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bootstrap.prune")
    parser.add_argument("--once", action="store_true", help="run one retention pass and exit")
    parser.add_argument("--db", default=None, help="bus database path (default data/bus/bus.db)")
    parser.add_argument("--archive-dir", default=None, help="where the JSONL archives go")
    parser.add_argument("--days", type=int, default=None, help="override retention_days from config/bus.json")
    args = parser.parse_args(argv)
    days = args.days if args.days is not None else int(load_bus_config()["retention_days"])
    now = datetime.now(UTC)
    archive = Path(args.archive_dir or DEFAULT_ARCHIVE_DIR) / f"events-{now:%Y%m}.jsonl"
    try:
        removed = build_store(args.db).prune(now - timedelta(days=days), archive)
    except StoreBusy as exc:
        print(f"[prune] bus database busy: {exc}")
        return 1
    print(f"[prune] retention {days} days: archived and removed {removed} event(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
