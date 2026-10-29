"""build_bus(store=...) wires the persisted trace and approval queue; bus_stats lists approvals."""
from pathlib import Path

from bootstrap import bus_stats
from bootstrap.wire import build_bus
from orchestrator.event_bus import Message
from orchestrator.event_bus.store import EventStore

ROOT = Path(__file__).resolve().parents[2]


def test_trace_survives_a_new_bus_instance(tmp_path):
    db = tmp_path / "bus.db"
    msg = Message(to="A002", type="query", payload={"intent": "settings"})
    assert build_bus(ROOT, store=EventStore(db)).send(msg).ok
    replay = EventStore(db).trace_for(msg.trace_id)            # a brand-new store object, same file
    assert [e["kind"] for e in replay] == ["send", "response"]


def test_held_real_agent_message_is_queued_and_listed(tmp_path, capsys):
    db = tmp_path / "bus.db"
    res = build_bus(ROOT, store=EventStore(db)).send(
        Message(to="A001", type="task.act", action={"tool": "external.post", "kind": "external"}))
    assert res.status == "held" and res.payload["approval_id"] == 1
    bus_stats.main(["--db", str(db), "--approvals"])
    out = capsys.readouterr().out
    assert "approval #1" in out and "A001" in out and "external.post" in out


def test_build_bus_without_a_store_is_unchanged():
    res = build_bus(ROOT).send(Message(to="A001", type="task.act",
                                       action={"tool": "external.post", "kind": "external"}))
    assert res.status == "held" and res.payload == {}
