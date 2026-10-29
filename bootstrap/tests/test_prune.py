"""Retention: archive then delete old events (design spec section 8); never past a consumer's cursor."""
import json
from datetime import UTC, datetime, timedelta

from bootstrap import prune
from orchestrator.event_bus.store import EventStore
from orchestrator.event_bus.tests.helpers import MANIFESTS, FakeClock, event_n


def seeded(tmp_path, days_old=100, consume_all=True):
    db = tmp_path / "bus.db"
    old = EventStore(db, manifests=MANIFESTS, clock=FakeClock(datetime.now(UTC) - timedelta(days=days_old)))
    old.publish(event_n(1))
    new = EventStore(db, manifests=MANIFESTS)
    new.publish(event_n(2))                                   # published just now
    if consume_all:
        new.consume("librarian", lambda e: None, types=["a015.*"], min_maturity="implemented")
    return db, new


def test_old_events_are_archived_then_deleted_recent_ones_kept(tmp_path):
    db, store = seeded(tmp_path)
    arch = tmp_path / "archive"
    assert prune.main(["--once", "--db", str(db), "--archive-dir", str(arch), "--days", "90"]) == 0
    assert [e["seq"] for e in store.read()] == [2]
    [file] = list(arch.glob("events-*.jsonl"))
    assert [json.loads(l)["event_id"] for l in file.read_text(encoding="utf-8").splitlines()] == [event_n(1)["event_id"]]


def test_prune_never_removes_events_a_consumer_has_not_passed(tmp_path):
    db, store = seeded(tmp_path, consume_all=False)
    store.consume("librarian", lambda e: None, types=["a015.*"], min_maturity="implemented", batch=1)
    sqlite_cursor = store.stats()["consumers"]["librarian"]["cursor"]
    prune.main(["--once", "--db", str(db), "--archive-dir", str(tmp_path / "a"), "--days", "0"])
    assert all(e["seq"] > sqlite_cursor for e in store.read())


def test_days_default_to_the_configured_retention(tmp_path, capsys):
    db, _ = seeded(tmp_path, days_old=100)
    prune.main(["--once", "--db", str(db), "--archive-dir", str(tmp_path / "a")])
    assert "retention 90 days" in capsys.readouterr().out
