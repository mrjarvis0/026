"""The message bus: route a message to its target agent, under gate + budget + trace.

Delivery order per message: trace it, refuse if no handler, run the sentinel gate (a
message that is not a plain read must declare its action; DENY/HOLD short-circuit),
enforce the budget (exhausted -> degrade), then route to the registered handler. A handler
returns a payload dict; the bus wraps it in a Response. A payload carrying an ``error`` is
a failed Response, never ``ok``. Handlers are thin adapters over an agent's own entry
points. The usd budget is spent by the handler that incurs the cost
(``message.budget.spend(usd=...)``); the bus refuses the next message once it is overspent.
"""
from __future__ import annotations

import threading
from collections.abc import Callable

from security.sentinel.gate import check_action, Decision
from .message import READ_ONLY_TYPES, Message, Response
from .trace import TraceLog

# A handler takes a Message and returns a payload dict.
AgentHandler = Callable[[Message], dict]


class _HandlerTimeout(Exception):
    pass


class MessageBus:
    def __init__(self, trace: TraceLog | None = None,
                 manifests: dict[str, dict] | None = None,
                 timeout_s: float | None = None,
                 on_hold: Callable[[Message, str], int | None] | None = None) -> None:
        self._handlers: dict[str, AgentHandler] = {}
        self._manifests: dict[str, dict] = manifests or {}
        self.timeout_s = timeout_s  # None = call the handler inline, no time limit
        self.on_hold = on_hold      # queue a held action for the operator; returns an approval id
        self.trace = trace or TraceLog()

    def register(self, agent_id: str, handler: AgentHandler, manifest: dict | None = None,
                 *, replace: bool = False) -> None:
        if agent_id in self._handlers and not replace:
            raise ValueError(f"agent {agent_id!r} already registered (pass replace=True)")
        self._handlers[agent_id] = handler
        if manifest is not None:
            self._manifests[agent_id] = manifest

    def _resp(self, message: Message, ok: bool, status: str,
              payload: dict | None = None, reason: str = "") -> Response:
        return Response(ok=ok, status=status, payload=payload or {}, reason=reason,
                        message_id=message.id, trace_id=message.trace_id)

    def _call(self, handler: AgentHandler, message: Message) -> dict:
        if self.timeout_s is None:
            return handler(message)
        # ponytail: a timed-out handler keeps running in its daemon thread (Python cannot kill
        # a thread); move handlers to a subprocess if a leaked worker ever matters.
        box: dict = {}

        def run() -> None:
            try:
                box["result"] = handler(message)
            except BaseException as exc:  # re-raised below, on the caller's thread
                box["exc"] = exc

        worker = threading.Thread(target=run, daemon=True, name=f"bus-{message.to}")
        worker.start()
        worker.join(self.timeout_s)
        if worker.is_alive():
            raise _HandlerTimeout()
        if "exc" in box:
            raise box["exc"]
        return box["result"]

    def send(self, message: Message) -> Response:
        self.trace.record("send", message)

        if message.to not in self._handlers:
            self.trace.record("no_handler", message)
            return self._resp(message, False, "no_handler", reason=f"no agent {message.to!r}")

        # Sentinel gate. Only a plain read may omit its action; anything else must declare it.
        if message.action is None and message.type not in READ_ONLY_TYPES:
            reason = f"message type {message.type!r} must declare an action"
            self.trace.record("gate_deny", message, {"reason": reason})
            return self._resp(message, False, "denied", reason=reason)
        if message.action is not None:
            gate = check_action(message.action, self._manifests.get(message.to, {}))
            if gate.decision == Decision.DENY:
                self.trace.record("gate_deny", message, {"reason": gate.reason})
                return self._resp(message, False, "denied", reason=gate.reason)
            if gate.decision == Decision.HOLD:
                approval_id = None
                if self.on_hold is not None:
                    try:
                        approval_id = self.on_hold(message, gate.reason)
                    except Exception as exc:  # still held — never silently allowed through
                        self.trace.record("hold_unrecorded", message, {"reason": f"{type(exc).__name__}: {exc}"})
                self.trace.record("gate_hold", message, {"reason": gate.reason, "approval_id": approval_id})
                payload = {"approval_id": approval_id} if approval_id is not None else None
                return self._resp(message, False, "held", payload=payload, reason=gate.reason)

        # Budget — an exhausted message degrades rather than going dark.
        if message.budget.exhausted:
            self.trace.record("degraded", message, {"reason": "budget exhausted"})
            return self._resp(message, False, "degraded", reason="budget exhausted")
        message.budget.spend(calls=1)

        try:
            payload = self._call(self._handlers[message.to], message)
        except _HandlerTimeout:
            reason = f"handler exceeded {self.timeout_s}s"
            self.trace.record("timeout", message, {"reason": reason})
            return self._resp(message, False, "timeout", reason=reason)
        except Exception as exc:  # a handler crash must not take the bus down
            self.trace.record("error", message, {"reason": f"{type(exc).__name__}: {exc}"})
            return self._resp(message, False, "error", reason=f"{type(exc).__name__}: {exc}")

        payload = payload if isinstance(payload, dict) else {"result": payload}
        if payload.get("error"):  # a handler declining/failing is not ok (MCP: execution error)
            reason = str(payload["error"])
            self.trace.record("error", message, {"reason": reason})
            return self._resp(message, False, "error", payload=payload, reason=reason)

        self.trace.record("response", message)
        return self._resp(message, True, "ok", payload=payload)
