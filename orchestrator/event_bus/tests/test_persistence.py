"""Persisted bus trace + the approval queue for held actions (design spec 12, Slice 1b)."""
import pytest

from orchestrator.event_bus import Message, MessageBus
from orchestrator.event_bus.store import EventStore
from orchestrator.event_bus.trace import TraceLog
from orchestrator.event_bus.tests.helpers import MANIFESTS, FakeClock

BUS_MANIFEST = {
    "trust": {"level": 2, "requires_approval": ["external.post", "store.delete"]},
    "tools": ["rpc.call", "brain.query", "store.read"],
    "invariants": {"execution_enabled": False},
}


def echo(msg):
    return {"echo": msg.payload}


@pytest.fixture
def store(tmp_path):
    return EventStore(tmp_path / "bus.db", manifests=MANIFESTS, clock=FakeClock())


def held_message():
    return Message(to="A001", type="task.act", action={"tool": "external.post", "kind": "external"})


# ---- trace sink ---------------------------------------------------------------------------

def test_trace_sink_receives_every_entry():
    seen: list = []
    log = TraceLog(sink=seen.append)
    bus = MessageBus(trace=log)
    bus.register("A001", echo, BUS_MANIFEST)
    bus.send(Message(to="A001", type="query"))
    assert [e["kind"] for e in seen] == ["send", "response"] == [e["kind"] for e in log.entries]


def test_failing_sink_never_breaks_delivery():
    def boom(entry):
        raise RuntimeError("disk full")

    log = TraceLog(sink=boom)
    bus = MessageBus(trace=log)
    bus.register("A001", echo, BUS_MANIFEST)
    assert bus.send(Message(to="A001", type="query")).ok
    assert log.sink_errors == 2 and len(log.entries) == 2          # still traced in memory, and counted


def test_store_records_and_replays_a_trace(store):
    log = TraceLog(sink=store.record_trace)
    bus = MessageBus(trace=log)
    bus.register("A001", echo, BUS_MANIFEST)
    msg = Message(to="A001", type="query", payload={"q": 1})
    bus.send(msg)
    replay = store.trace_for(msg.trace_id)
    assert [e["kind"] for e in replay] == ["send", "response"]
    assert replay[0]["to"] == "A001" and replay[0]["id"] == msg.id and replay[0]["type"] == "query"


# ---- approvals ----------------------------------------------------------------------------

def bus_with_queue(store):
    bus = MessageBus(trace=TraceLog(sink=store.record_trace),
                     on_hold=lambda message, reason: store.hold(message.as_dict(), reason))
    bus.register("A001", echo, BUS_MANIFEST)
    return bus


def test_held_message_creates_a_pending_approval(store):
    # regression: `held` was only an in-memory trace entry; nothing persisted it for the operator
    msg = held_message()
    res = bus_with_queue(store).send(msg)
    assert res.status == "held" and not res.ok and res.payload["approval_id"] == 1
    [pending] = store.pending_approvals()
    assert pending["to_agent"] == "A001" and pending["status"] == "pending"
    assert pending["action"] == {"tool": "external.post", "kind": "external"}
    assert "approval" in pending["reason"] and pending["msg_id"] == msg.id
    assert any(e["kind"] == "gate_hold" for e in store.trace_for(msg.trace_id))


def test_decide_once(store):
    bus_with_queue(store).send(held_message())
    assert store.decide(1, True, "operator") is True
    assert store.decide(1, False, "operator") is False            # already decided
    assert store.decide(99, True, "operator") is False            # unknown id
    assert store.pending_approvals() == []


def test_bus_without_a_hold_hook_is_unchanged():
    bus = MessageBus()
    bus.register("A001", echo, BUS_MANIFEST)
    res = bus.send(held_message())
    assert res.status == "held" and res.payload == {}


def test_a_failing_hold_hook_still_holds_the_message():
    def boom(message, reason):
        raise RuntimeError("queue down")

    bus = MessageBus(on_hold=boom)
    bus.register("A001", echo, BUS_MANIFEST)
    res = bus.send(held_message())
    assert res.status == "held" and not res.ok                       # never silently allowed through
    assert any(e["kind"] == "hold_unrecorded" for e in bus.trace.entries)
