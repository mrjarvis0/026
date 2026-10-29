"""The pause-flags file (Slice 2 design, 2026-10-29): ``data/risk/pause_flags.json``.

A flag means "do not open NEW entries on this market". It can only restrict; nothing here enables or loosens
anything. The file is the platform's single hand-off to the trading side (a reader lives in T01, S2b).
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from orchestrator.event_bus.envelope import make_event_id

FLAGS_FILE = Path(__file__).resolve().parents[1] / "data" / "risk" / "pause_flags.json"
VERSION = 1


def load_flags(path: Path | None = None) -> dict:
    """subject -> flag. A missing or torn file reads as "no flags" (the writer is atomic, so torn = foreign)."""
    try:
        raw = json.loads(Path(path or FLAGS_FILE).read_text(encoding="utf-8"))
        flags = raw.get("flags")
        return flags if isinstance(flags, dict) else {}
    except (OSError, ValueError, AttributeError):
        return {}


def save_flags(path: Path | None, flags: dict) -> None:
    """Atomic write: the reader sees the old file or the new one, never half of either."""
    path = Path(path or FLAGS_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps({"version": VERSION, "flags": flags}, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def active_flags(flags: dict, now: datetime) -> dict:
    """Flags that have not expired (``expires_at`` null = until cleared)."""
    return {k: v for k, v in flags.items()
            if not v.get("expires_at") or datetime.fromisoformat(v["expires_at"]) > now}


def audit_event(kind: str, *, event_id: str, subject: str, now: datetime, reason: str, by: str,
                expires_at: str | None = None, trigger: dict | None = None) -> dict:
    """``system.risk.flag_set`` / ``flag_cleared``: the platform's record that a flag changed and why."""
    at = now.astimezone(timezone.utc).isoformat()
    data = {"subject": subject, "reason": reason, "by": by}
    if kind == "flag_set":
        data["expires_at"] = expires_at
    if trigger:
        data["trigger"] = trigger["event_id"]
    return {
        "event_id": event_id, "type": f"system.risk.{kind}", "schema_version": 1, "source": "SYS",
        "subject": subject, "event_time": None, "event_window": None, "observed_at": at, "known_at": None,
        "trace_id": trigger["trace_id"] if trigger else "trc_" + event_id[4:],
        "causation_id": trigger["event_id"] if trigger else None,
        "detector": None, "confidence": None,
        "coverage": {"complete": None, "as_of": at, "lag_s": None, "note": "pause-flag change"},
        "evidence": [], "untrusted": False, "data": data,
    }


def operator_event_id(kind: str, subject: str, now: datetime) -> str:
    return make_event_id(kind, subject, now.isoformat(), "operator")
