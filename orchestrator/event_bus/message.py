"""The message contract on the bus (AGENTS.md §5)."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


@dataclass
class Budget:
    """A message's call/cost allowance. An agent that exhausts it degrades."""

    calls: int = 100
    usd: float = 0.0  # 0.0 means "no cost budget declared"; negative means overspent

    def spend(self, calls: int = 1, usd: float = 0.0) -> None:
        self.calls -= calls
        self.usd -= usd

    @property
    def exhausted(self) -> bool:
        return self.calls <= 0 or self.usd < 0


@dataclass
class Message:
    to: str
    type: str
    payload: dict = field(default_factory=dict)
    sender: str = "orchestrator"          # rendered as "from" in the wire dict
    id: str = field(default_factory=lambda: _new_id("msg"))
    trace_id: str = field(default_factory=lambda: _new_id("trc"))
    parent_id: str | None = None
    budget: Budget = field(default_factory=Budget)
    action: dict | None = None            # optional declared action, for the sentinel gate

    def as_dict(self) -> dict:
        return {
            "id": self.id, "from": self.sender, "to": self.to, "type": self.type,
            "payload": self.payload, "trace_id": self.trace_id, "parent_id": self.parent_id,
            "budget": {"calls": self.budget.calls, "usd": self.budget.usd},
            "action": self.action,
        }


@dataclass
class Response:
    ok: bool
    status: str        # ok | denied | held | error | degraded | no_handler
    payload: dict = field(default_factory=dict)
    reason: str = ""
    message_id: str = ""
    trace_id: str = ""
