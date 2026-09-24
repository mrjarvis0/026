"""SP-4 wiring proof: A002 is on the shared kernel — routed under the sentinel
gate + budget, reading/writing the shared brain only within its declared surface.
"""
from brain.access import AgentBrainView, NamespaceDenied
from brain.store import Brain
from orchestrator.adapters import a002
from orchestrator.event_bus import Message, MessageBus


def _fake_intents(count: int = 2):
    """A deterministic stand-in for A002's store reader (no DB / network)."""

    def narratives(payload: dict) -> dict:
        return {
            "count": count,
            "narratives": [
                {"id": 1, "claim": "x", "fomo": 9.0,
                 "epistemic_status": "unconfirmed", "confidence": 0.3}
            ],
            "finding": {"key": "latest", "value": {"n": count}},
        }

    return {"narratives": narratives}


def test_a002_routes_on_bus_and_returns_payload():
    bus = MessageBus()
    a002.register(bus, manifest=a002.load_manifest(), intents=_fake_intents())
    res = bus.send(Message(to="A002", type="task.query", payload={"intent": "narratives"}))
    assert res.ok and res.status == "ok"
    assert res.payload["agent"] == "A002"
    assert res.payload["count"] == 2


def test_a002_unknown_intent_is_honest():
    bus = MessageBus()
    a002.register(bus, manifest=a002.load_manifest(), intents=_fake_intents())
    res = bus.send(Message(to="A002", type="task.query", payload={"intent": "nope"}))
    assert res.ok  # routed fine...
    assert res.payload.get("error") == "unknown intent"  # ...but declines honestly


def test_a002_execution_action_denied_by_gate():
    bus = MessageBus()
    a002.register(bus, manifest=a002.load_manifest(), intents=_fake_intents())
    res = bus.send(Message(to="A002", type="task.act",
                           action={"tool": "brain.write", "kind": "trade"}))
    assert res.status == "denied" and not res.ok


def test_a002_declared_write_action_allowed():
    bus = MessageBus()
    a002.register(bus, manifest=a002.load_manifest(), intents=_fake_intents())
    res = bus.send(Message(to="A002", type="task.act", payload={"intent": "narratives"},
                           action={"tool": "brain.write", "kind": "write"}))
    assert res.ok and res.status == "ok"


def test_a002_store_delete_action_held_for_approval():
    bus = MessageBus()
    a002.register(bus, manifest=a002.load_manifest(), intents=_fake_intents())
    res = bus.send(Message(to="A002", type="task.act",
                           action={"tool": "store.delete", "kind": "write"}))
    assert res.status == "held" and not res.ok


def test_a002_brain_write_is_scoped_to_manifest():
    brain = Brain(":memory:")
    manifest = a002.load_manifest()
    bus = MessageBus()
    a002.register(bus, brain=brain, manifest=manifest, intents=_fake_intents())
    res = bus.send(Message(to="A002", type="task.query", payload={"intent": "narratives"}))
    assert res.ok
    # the finding landed in the declared `news` namespace, written by A002
    view = AgentBrainView(brain, "A002", manifest)
    assert view.read("news", "latest") == {"n": 2}
    # and A002 may NOT write outside its declared surface (e.g. A001's `chain`)
    try:
        view.write("chain", "x", 1)
        raise AssertionError("expected NamespaceDenied")
    except NamespaceDenied:
        pass


def test_a002_manifest_declares_news_write():
    m = a002.load_manifest()
    assert m["id"] == "A002"
    assert "news" in (m.get("memory") or {}).get("writes", [])


def test_a002_real_store_reader_is_honest_when_empty(tmp_path):
    # real reader over an empty A002 store returns count 0, never a fabricated finding
    out = a002._read_narratives({"db_path": str(tmp_path / "a002.db")})
    assert out["count"] == 0 and out["narratives"] == []
