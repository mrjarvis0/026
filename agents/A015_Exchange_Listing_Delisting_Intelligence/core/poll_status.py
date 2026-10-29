"""A015's per-exchange poll status — the fact that lets "no delisting seen" be believed.

``memory/poll_status.json`` records, per exchange, whether the last poll succeeded, whether it
was only a baseline (no diff was checked), when it ran and how many spot markets it saw. The
bus relay turns it into ``source_health``; without it a quiet exchange and a poll that never
ran look identical. Written atomically; unreadable -> treated as empty, never as "all fine".
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

POLL_STATUS_FILE = Path(__file__).resolve().parents[1] / "memory" / "poll_status.json"


def read_poll_status(path: Path | None = None) -> dict:
    try:
        data = json.loads(Path(path or POLL_STATUS_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def write_poll_status(results: dict[str, dict], path: Path | None = None,
                      now: datetime | None = None) -> dict:
    """Merge this run's per-exchange results into the file (other exchanges are kept)."""
    target = Path(path or POLL_STATUS_FILE)
    status = read_poll_status(target)
    fallback = (now or datetime.now(timezone.utc)).isoformat()
    for exchange_id, res in results.items():
        status[exchange_id] = {
            "ok": bool(res["ok"]),
            "error": res.get("error"),
            "baseline": bool(res.get("baseline")),
            "polled_at": res.get("observed_at") or fallback,
            "spot_markets": int(res.get("spot_markets", 0)),
        }
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".tmp")
    tmp.write_text(json.dumps(status, indent=2), encoding="utf-8")
    os.replace(tmp, target)
    return status
