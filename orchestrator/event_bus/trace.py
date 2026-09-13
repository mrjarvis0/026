"""An append-only, replayable trace of everything that crosses the bus."""
from __future__ import annotations

import datetime
from dataclasses import dataclass, field

from .message import Message


@dataclass
class TraceLog:
    entries: list[dict] = field(default_factory=list)

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

    def replay(self, trace_id: str) -> list[dict]:
        return [e for e in self.entries if e["trace_id"] == trace_id]
