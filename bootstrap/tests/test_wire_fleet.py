from pathlib import Path

import pytest

from bootstrap.wire import build_bus
from orchestrator.event_bus import Message

ROOT = Path(__file__).resolve().parents[2]  # F:\026


@pytest.mark.parametrize("agent,intent", [
    ("A001", "detectors"), ("A002", "settings"), ("A015", "latest_events"),
])
def test_wire_registers_every_kernel_wired_agent(agent, intent):
    # regression: A015 was claimed kernel_wired but only the dashboard registered it by hand
    res = build_bus(ROOT).send(Message(to=agent, type="task.query", payload={"intent": intent}))
    assert res.status != "no_handler" and res.ok


def test_a002_answers_to_intent_and_to_legacy_op():
    # regression: A002 had two handlers, one keyed `op` and one `intent`; whichever
    # registered last won. Now one handler that reads `intent` and still honours `op`.
    bus = build_bus(ROOT)
    by_intent = bus.send(Message(to="A002", type="task.query", payload={"intent": "settings"}))
    by_op = bus.send(Message(to="A002", type="task.query", payload={"op": "settings"}))
    assert by_intent.ok and by_op.ok
    assert by_intent.payload["intent"] == by_op.payload["intent"] == "settings"
    assert by_intent.payload["agent"] == "A002"


def test_a001_answers_to_intent_alias():
    res = build_bus(ROOT).send(Message(to="A001", type="task.query", payload={"intent": "detectors"}))
    assert res.ok and res.payload["op"] == "detectors"
