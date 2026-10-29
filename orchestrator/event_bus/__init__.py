"""The message bus: the only path between the orchestrator and the fleet.

Agents never call each other (AGENTS.md §5); every message goes through here, and
every message is traced and budgeted. Before delivery the bus consults the sentinel's
runtime gate, so no action crosses a boundary the agent did not declare.
"""
from security.sentinel.gate import Decision
from .message import Budget, Message, Response
from .trace import TraceLog
from .bus import MessageBus, AgentHandler
from .envelope import EnvelopeError
from .store import EventStore, StoreBusy

__all__ = ["Budget", "Message", "Response", "TraceLog", "MessageBus", "AgentHandler", "Decision",
           "EnvelopeError", "EventStore", "StoreBusy"]
