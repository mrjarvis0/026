"""Offline checks for the supervisor's scheduling logic (no real agents run).

    python live/test_supervisor.py
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from live import supervisor as sup

PASS = 0
FAIL = 0


def check(label: str, ok: bool) -> None:
    global PASS, FAIL
    PASS, FAIL = (PASS + 1, FAIL) if ok else (PASS, FAIL + 1)
    print(f"  [{'OK' if ok else 'FAIL'}] {label}")


def main() -> None:
    now = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)

    # _due
    check("never-run is due", sup._due(None, 30, now) is True)
    check("just-ran not due", sup._due((now - timedelta(minutes=5)).isoformat(), 30, now) is False)
    check("stale is due", sup._due((now - timedelta(minutes=31)).isoformat(), 30, now) is True)

    # event state machine — stub the agent calls so nothing hits the network
    fired = []
    sup.a001_ingest = lambda: fired.append("a001")
    sup.a002_scan = lambda: fired.append("a002")

    state = {"a001_last": None, "a002_last": None, "events": {}}
    when = now + timedelta(minutes=1)
    state["events"]["k"] = {"when": when.isoformat(), "matched": "test", "runs_done": 0, "next_run": when.isoformat()}

    # before the event: nothing fires
    sup.process_events(state, now)
    check("future event does not fire early", fired == [])

    # at the event: both agents fire once (a pair), second run deferred 5 min
    sup.process_events(state, when)
    check("event fires both agents", fired == ["a001", "a002"])
    check("one run done", state["events"]["k"]["runs_done"] == 1)

    # 5 min later: the second pair fires
    sup.process_events(state, when + timedelta(minutes=sup.EVENT_GAP_MIN))
    check("second run fires the pair", fired == ["a001", "a002", "a001", "a002"])
    check("event complete", state["events"]["k"]["runs_done"] == sup.EVENT_SCANS)

    # a stale unfired event (PC was off past the grace window) is skipped, not fired
    fired.clear()
    old = now - timedelta(minutes=sup.EVENT_GRACE_MIN + 30)
    state["events"]["old"] = {"when": old.isoformat(), "matched": "late", "runs_done": 0, "next_run": old.isoformat()}
    sup.process_events(state, now)
    check("missed event is skipped, not fired", fired == [])
    check("missed event marked done", state["events"]["old"]["runs_done"] == sup.EVENT_SCANS)


if __name__ == "__main__":
    main()
    print(f"RESULT: {PASS} passed, {FAIL} failed")
    sys.exit(1 if FAIL else 0)
