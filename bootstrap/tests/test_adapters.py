from pathlib import Path

from bootstrap.wire import build_bus
from orchestrator.event_bus import Message

ROOT = Path(__file__).resolve().parents[2]  # F:\026


def test_a002_sources_query_through_bus():
    bus = build_bus(ROOT)
    res = bus.send(Message(to="A002", type="task.query", payload={"op": "sources"}))
    assert res.ok and res.status == "ok"
    assert res.payload["count"] >= 1
    assert "news" in res.payload["kinds"]


def test_a002_settings_query_through_bus():
    bus = build_bus(ROOT)
    res = bus.send(Message(to="A002", type="task.query", payload={"op": "settings"}))
    assert res.ok and res.payload["agent"] == "A002"


def test_a001_detectors_catalogue_through_bus():
    bus = build_bus(ROOT)
    res = bus.send(Message(to="A001", type="task.query", payload={"op": "detectors"}))
    assert res.ok and res.status == "ok"
    assert res.payload["op"] == "detectors"
    assert res.payload["ok"] is True  # A001's own ServiceResult.ok


def test_bus_gate_denies_execution_to_real_agent():
    bus = build_bus(ROOT)
    res = bus.send(Message(to="A001", type="task.act",
                           action={"tool": "rpc.call", "kind": "trade"}))
    assert res.status == "denied" and not res.ok


def test_a001_metrics_db_query_through_bus():
    bus = build_bus(ROOT)
    res = bus.send(Message(to="A001", type="task.query", payload={"op": "metrics"}))
    assert res.ok and res.payload["op"] == "metrics"


def test_a001_coverage_with_chain_arg_through_bus():
    bus = build_bus(ROOT)
    res = bus.send(Message(to="A001", type="task.query",
                           payload={"op": "coverage", "chain": "ethereum"}))
    assert res.ok and res.payload["op"] == "coverage"


def test_a002_stats_db_query_through_bus():
    bus = build_bus(ROOT)
    res = bus.send(Message(to="A002", type="task.query", payload={"op": "stats"}))
    assert res.ok and res.payload["op"] == "stats"
    assert res.payload["items"] >= 0 and res.payload["entities"] >= 0
