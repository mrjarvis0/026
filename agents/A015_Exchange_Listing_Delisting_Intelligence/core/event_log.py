"""A015's durable event log — the canonical fact store the bus adapter reads.

One JSON file per poll that produced events (``<UTC time>-<seq>-<exchange>.json``, a list of
reports), written atomically. The filename sorts chronologically. Each report gets a stable
``event_id`` derived from the snapshot the diff was taken against, so re-detecting the same
diff (e.g. after a crash before the snapshot advanced) yields the same ids and a consumer can
de-duplicate (at-least-once delivery, idempotent consumers).
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

EVENT_LOG_DIR = Path(__file__).resolve().parents[1] / "memory" / "event_log"


def event_id(old_digest: str, exchange: str, event_type: str, symbol: str | None) -> str:
    raw = f"{old_digest}|{exchange}|{event_type}|{symbol}"
    return "evt_" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def append_events(exchange_id: str, reports: list[dict], old_digest: str,
                  log_dir: Path | str | None = None, now: datetime | None = None) -> Path | None:
    """Write ``reports`` as one event file; None (and no file) when there are none."""
    if not reports:
        return None
    directory = Path(log_dir) if log_dir else EVENT_LOG_DIR
    directory.mkdir(parents=True, exist_ok=True)
    stamped = [{**r, "event_id": event_id(old_digest, exchange_id, r.get("event_type", ""),
                                          r.get("symbol"))} for r in reports]
    ts = (now or datetime.now(timezone.utc)).strftime("%Y%m%dT%H%M%S%f")
    seq = 0
    path = directory / f"{ts}-{seq:03d}-{exchange_id}.json"
    while path.exists():
        seq += 1
        path = directory / f"{ts}-{seq:03d}-{exchange_id}.json"
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(stamped, indent=2, default=str), encoding="utf-8")
    os.replace(tmp, path)
    return path
