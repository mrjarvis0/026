"""SP-4 wiring proof for A015: on the shared kernel, gated + budgeted, writing the
shared brain only within its declared surface.
"""
from brain.access import AgentBrainView, NamespaceDenied
from brain.store import Brain
from agents.A015_Exchange_Listing_Delisting_Intelligence.core import event_log
from bootstrap.adapters import a015
from orchestrator.event_bus import Message, MessageBus


def _fake_intents(count: int = 2):
    def latest_events(payload: dict) -> dict:
        return {
            "count": count,
            "events": [{"event_type": "NEW_LISTING", "exchange": "binance", "symbol": "FOO/USDT"}],
            "finding": {"key": "latest", "value": {"n": count}},
        }

    return {"latest_events": latest_events}


def test_a015_routes_on_bus_and_returns_payload():
    bus = MessageBus()
    a015.register(bus, manifest=a015.load_manifest(), intents=_fake_intents())
    res = bus.send(Message(to="A015", type="task.query", payload={"intent": "latest_events"}))
    assert res.ok and res.status == "ok"
    assert res.payload["agent"] == "A015" and res.payload["count"] == 2


def test_a015_execution_action_denied_by_gate():
    bus = MessageBus()
    a015.register(bus, manifest=a015.load_manifest(), intents=_fake_intents())
    res = bus.send(Message(to="A015", type="task.act",
                           action={"tool": "brain.write", "kind": "order"}))
    assert res.status == "denied" and not res.ok


def test_a015_brain_write_is_scoped_to_manifest():
    brain = Brain(":memory:")
    manifest = a015.load_manifest()
    bus = MessageBus()
    a015.register(bus, brain=brain, manifest=manifest, intents=_fake_intents())
    res = bus.send(Message(to="A015", type="task.query", payload={"intent": "latest_events"}))
    assert res.ok
    view = AgentBrainView(brain, "A015", manifest)
    assert view.read("markets", "latest") == {"n": 2}   # wrote to its declared namespace
    try:
        view.write("chain", "x", 1)                      # A001's namespace -> denied
        raise AssertionError("expected NamespaceDenied")
    except NamespaceDenied:
        pass


def test_a015_manifest_declares_markets_write_and_no_execution():
    m = a015.load_manifest()
    assert m["id"] == "A015"
    assert "markets" in (m.get("memory") or {}).get("writes", [])
    assert (m.get("invariants") or {}).get("execution_enabled") is False


def test_a015_real_event_log_reader_is_honest_when_empty(tmp_path):
    out = a015._read_latest_events({"event_log_dir": str(tmp_path)})
    assert out["count"] == 0 and out["events"] == []


def test_adapter_reads_what_a015_actually_writes(tmp_path):
    # contract: the adapter read an event_log nothing ever wrote (count was always 0).
    # What A015's own event_log writes must come back through the adapter, oldest first.
    from datetime import datetime, timezone

    older = datetime(2026, 1, 1, tzinfo=timezone.utc)
    newer = datetime(2026, 1, 2, tzinfo=timezone.utc)
    event_log.append_events("okx", [{"event_type": "NEW_LISTING", "exchange": "okx", "symbol": "A/USDT"}],
                            "d1", log_dir=tmp_path, now=newer)
    event_log.append_events("binance", [{"event_type": "DELISTING", "exchange": "binance", "symbol": "B/USDT"}],
                            "d2", log_dir=tmp_path, now=older)
    out = a015._read_latest_events({"event_log_dir": str(tmp_path)})
    assert out["count"] == 2
    assert [e["symbol"] for e in out["events"]] == ["B/USDT", "A/USDT"]   # chronological, not by exchange
    assert all(e["event_id"].startswith("evt_") for e in out["events"])
