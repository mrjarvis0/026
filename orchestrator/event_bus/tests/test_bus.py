import time

import pytest

from orchestrator.event_bus import MessageBus, Message, Budget

MANIFEST = {
    "trust": {"level": 2, "requires_approval": ["external.post", "store.delete"]},
    "tools": ["rpc.call", "brain.query", "store.read"],
    "invariants": {"execution_enabled": False},
}


def echo(msg):
    return {"echo": msg.payload}


def test_round_trip_ok_and_budget_and_trace():
    bus = MessageBus()
    bus.register("A001", echo, MANIFEST)
    msg = Message(to="A001", type="task.assign", payload={"q": "hi"})
    before = msg.budget.calls
    res = bus.send(msg)
    assert res.ok and res.status == "ok"
    assert res.payload == {"echo": {"q": "hi"}}
    assert msg.budget.calls == before - 1
    assert any(e["kind"] == "response" for e in bus.trace.entries)
    assert bus.trace.replay(msg.trace_id)


def test_unknown_target_no_handler():
    bus = MessageBus()
    res = bus.send(Message(to="A99", type="task.assign"))
    assert res.status == "no_handler" and not res.ok


def test_execution_action_denied():
    bus = MessageBus()
    bus.register("A001", echo, MANIFEST)
    res = bus.send(Message(to="A001", type="task.act", action={"tool": "rpc.call", "kind": "trade"}))
    assert res.status == "denied" and not res.ok


def test_requires_approval_action_held():
    bus = MessageBus()
    bus.register("A001", echo, MANIFEST)
    res = bus.send(Message(to="A001", type="task.act",
                           action={"tool": "external.post", "kind": "external"}))
    assert res.status == "held" and not res.ok


def test_budget_exhausted_degrades():
    bus = MessageBus()
    bus.register("A001", echo, MANIFEST)
    res = bus.send(Message(to="A001", type="task.assign", budget=Budget(calls=0)))
    assert res.status == "degraded" and not res.ok


def test_handler_error_is_caught():
    bus = MessageBus()

    def boom(msg):
        raise RuntimeError("nope")

    bus.register("A001", boom, MANIFEST)
    res = bus.send(Message(to="A001", type="task.assign"))
    assert res.status == "error" and "nope" in res.reason


# --- Phase 0 hardening: each test names the defect it guards -----------------------


def test_act_message_without_declared_action_is_denied():
    # regression: the gate only ran when `action` was set, so omitting it skipped the gate
    bus = MessageBus()
    bus.register("A001", echo, MANIFEST)
    res = bus.send(Message(to="A001", type="task.act"))
    assert res.status == "denied" and not res.ok
    assert any(e["kind"] == "gate_deny" for e in bus.trace.entries)


def test_unknown_message_type_without_action_is_denied():
    bus = MessageBus()
    bus.register("A001", echo, MANIFEST)
    res = bus.send(Message(to="A001", type="task.whatever"))
    assert res.status == "denied" and not res.ok


@pytest.mark.parametrize("mtype", ["query", "task.query", "task.assign"])
def test_read_types_need_no_declared_action(mtype):
    bus = MessageBus()
    bus.register("A001", echo, MANIFEST)
    assert bus.send(Message(to="A001", type=mtype)).ok


def test_duplicate_register_is_refused_unless_replace():
    # regression: a second register() silently overwrote the first handler
    bus = MessageBus()
    bus.register("A001", echo, MANIFEST)
    with pytest.raises(ValueError):
        bus.register("A001", echo, MANIFEST)
    bus.register("A001", echo, MANIFEST, replace=True)


def test_handler_error_payload_is_not_ok():
    # regression: {"error": ...} from a handler was wrapped as ok=True ("unknown intent")
    bus = MessageBus()
    bus.register("A001", lambda m: {"error": "unknown intent", "intent": "nope"}, MANIFEST)
    res = bus.send(Message(to="A001", type="task.query"))
    assert not res.ok and res.status == "error"
    assert res.reason == "unknown intent" and res.payload["intent"] == "nope"
    assert any(e["kind"] == "error" for e in bus.trace.entries)


def test_slow_handler_times_out():
    # regression: a hung handler blocked the bus forever (no timeout)
    bus = MessageBus(timeout_s=0.05)
    bus.register("A001", lambda m: time.sleep(0.5) or {}, MANIFEST)
    res = bus.send(Message(to="A001", type="task.query"))
    assert res.status == "timeout" and not res.ok
    assert any(e["kind"] == "timeout" for e in bus.trace.entries)


def test_usd_overspend_by_handler_blocks_next_message():
    # the usd budget is spent by the handler that incurs the cost; the bus enforces it
    budget = Budget(calls=10, usd=0.10)

    def pricey(msg):
        msg.budget.spend(usd=0.25)
        return {}

    bus = MessageBus()
    bus.register("A001", pricey, MANIFEST)
    assert bus.send(Message(to="A001", type="task.query", budget=budget)).ok
    res = bus.send(Message(to="A001", type="task.query", budget=budget))
    assert res.status == "degraded" and not res.ok
