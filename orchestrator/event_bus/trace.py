"""An append-only, replayable trace of everything that crosses the bus.

Entries are always kept in memory. An optional ``sink`` (e.g. ``EventStore.record_trace``) also
persists each one; a failing sink never breaks delivery — it is counted in ``sink_errors``.
"""
from __future__ import annotations

import datetime
from collections.abc import Callable
from dataclasses import dataclass, field

from .message import Message


@dataclass
class TraceLog:
    entries: list[dict] = field(default_factory=list)
    sink: Callable[[dict], None] | None = None
    sink_errors: int = 0

    def record(self, kind: str, message: Message, extra: dict | None = None) -> None:
        entry = {
            "at": datetime.datetime.now(datetime.UTC).isoformat(),
            "kind": kind,
            "id": message.id,
            "trace_id": message.trace_id,
            "from": message.sender,
            "to": message.to,
            "type": message.type,
        }
        if extra:
            entry.update(extra)
        self.entries.append(entry)
        if self.sink is not None:
            try:
                self.sink(entry)
            except Exception:  # persistence must never take the bus down
                self.sink_errors += 1

    def replay(self, trace_id: str) -> list[dict]:
        return [e for e in self.entries if e["trace_id"] == trace_id]
