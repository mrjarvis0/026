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
    bus.register("A01", echo, MANIFEST)
    msg = Message(to="A01", type="task.assign", payload={"q": "hi"})
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
    bus.register("A01", echo, MANIFEST)
    res = bus.send(Message(to="A01", type="task.act", action={"tool": "rpc.call", "kind": "trade"}))
    assert res.status == "denied" and not res.ok


def test_requires_approval_action_held():
    bus = MessageBus()
    bus.register("A01", echo, MANIFEST)
    res = bus.send(Message(to="A01", type="task.act",
                           action={"tool": "external.post", "kind": "external"}))
    assert res.status == "held" and not res.ok


def test_budget_exhausted_degrades():
    bus = MessageBus()
    bus.register("A01", echo, MANIFEST)
    res = bus.send(Message(to="A01", type="task.assign", budget=Budget(calls=0)))
    assert res.status == "degraded" and not res.ok


def test_handler_error_is_caught():
    bus = MessageBus()

    def boom(msg):
        raise RuntimeError("nope")

    bus.register("A01", boom, MANIFEST)
    res = bus.send(Message(to="A01", type="task.assign"))
    assert res.status == "error" and "nope" in res.reason
