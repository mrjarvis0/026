"""The message bus: route a message to its target agent, under gate + budget + trace.

Delivery order per message: trace it, refuse if no handler, run the sentinel gate on
any declared action (DENY/HOLD short-circuit), enforce the budget (exhausted -> degrade),
then route to the registered handler. A handler returns a payload dict; the bus wraps it
in a Response. Handlers are thin adapters over an agent's own entry points; real A01/A02
adapters come later (SP-4 next slice) — this slice proves the path with any handler.
"""
from __future__ import annotations

from collections.abc import Callable

from security.sentinel.gate import check_action, Decision
from .message import Message, Response
from .trace import TraceLog

# A handler takes a Message and returns a payload dict.
AgentHandler = Callable[[Message], dict]


class MessageBus:
    def __init__(self, trace: TraceLog | None = None,
                 manifests: dict[str, dict] | None = None) -> None:
        self._handlers: dict[str, AgentHandler] = {}
        self._manifests: dict[str, dict] = manifests or {}
        self.trace = trace or TraceLog()

    def register(self, agent_id: str, handler: AgentHandler, manifest: dict | None = None) -> None:
        self._handlers[agent_id] = handler
        if manifest is not None:
            self._manifests[agent_id] = manifest

    def _resp(self, message: Message, ok: bool, status: str,
              payload: dict | None = None, reason: str = "") -> Response:
        return Response(ok=ok, status=status, payload=payload or {}, reason=reason,
                        message_id=message.id, trace_id=message.trace_id)

    def send(self, message: Message) -> Response:
        self.trace.record("send", message)

        if message.to not in self._handlers:
            self.trace.record("no_handler", message)
            return self._resp(message, False, "no_handler", reason=f"no agent {message.to!r}")

        # Sentinel gate — only when the message declares an action to take.
        if message.action is not None:
            gate = check_action(message.action, self._manifests.get(message.to, {}))
            if gate.decision == Decision.DENY:
                self.trace.record("gate_deny", message, {"reason": gate.reason})
                return self._resp(message, False, "denied", reason=gate.reason)
            if gate.decision == Decision.HOLD:
                self.trace.record("gate_hold", message, {"reason": gate.reason})
                return self._resp(message, False, "held", reason=gate.reason)

        # Budget — an exhausted message degrades rather than going dark.
        if message.budget.exhausted:
            self.trace.record("degraded", message, {"reason": "budget exhausted"})
            return self._resp(message, False, "degraded", reason="budget exhausted")
        message.budget.spend(calls=1)

        try:
            payload = self._handlers[message.to](message)
        except Exception as exc:  # a handler crash must not take the bus down
            self.trace.record("error", message, {"reason": f"{type(exc).__name__}: {exc}"})
            return self._resp(message, False, "error", reason=f"{type(exc).__name__}: {exc}")

        self.trace.record("response", message)
        return self._resp(message, True, "ok", payload=payload if isinstance(payload, dict) else {"result": payload})
