"""Librarian consumer, persistent brain and the consume / bus_stats CLIs (design spec 11)."""
import sqlite3

import pytest

from bootstrap import bus_stats, consume
from bootstrap.consumers.librarian import NAME, NAMESPACE, run_once
from brain.store import Brain
from orchestrator.event_bus.store import EventStore
from orchestrator.event_bus.tests.helpers import MANIFESTS, FakeClock, event_n


@pytest.fixture
def store(tmp_path):
    return EventStore(tmp_path / "bus.db", manifests=MANIFESTS, clock=FakeClock())


@pytest.fixture
def brain(tmp_path):
    return Brain(str(tmp_path / "brain.db"))


def test_event_lands_in_markets_with_its_label(store, brain):
    store.publish(event_n(1))                                     # detector maturity: implemented
    stats = run_once(store, brain)
    key = f"event:{event_n(1)['event_id']}"
    assert stats.delivered == 1
    value = brain.read(NAMESPACE, key, by="test")
    assert value["type"] == "a015.listing.delisted" and value["detector"]["maturity"] == "implemented"
    assert "seq" not in value                                     # the bus-local counter is not part of the fact
    [version] = brain.history(NAMESPACE, key)
    assert version["by"] == NAME == "librarian"


def test_redelivery_adds_no_new_version(store, brain, tmp_path):
    # at-least-once delivery: a crash between handler and cursor redelivers the event
    store.publish(event_n(1))
    run_once(store, brain)
    sqlite3.connect(tmp_path / "bus.db").execute("UPDATE consumers SET cursor = 0").connection.commit()
    assert run_once(store, brain).delivered == 1                  # delivered again ...
    assert len(brain.history(NAMESPACE, f"event:{event_n(1)['event_id']}")) == 1   # ... but recorded once


def test_run_once_is_idempotent(store, brain):
    store.publish(event_n(1))
    run_once(store, brain)
    assert run_once(store, brain).delivered == 0


def test_brain_persists_across_instances(store, tmp_path):
    store.publish(event_n(1))
    run_once(store, Brain(str(tmp_path / "persist.db")))
    reopened = Brain(str(tmp_path / "persist.db"))
    assert reopened.read(NAMESPACE, f"event:{event_n(1)['event_id']}", by="test")["subject"].startswith("market:")


def test_only_a015_events_are_recorded(store, brain):
    store.publish({**event_n(2), "event_id": "evt_00000000000000aa", "type": "system.source.stale",
                   "source": "SYS", "detector": None, "evidence": [],
                   "data": {"source": "A015:okx", "max_age_s": 1800, "last_ok_at": None}})
    stats = run_once(store, brain)
    assert stats.delivered == 0 and stats.skipped_other_type == 1


def test_consume_main_runs_against_temp_paths(store, tmp_path, capsys):
    store.publish(event_n(1))
    assert consume.main(["--once", "--db", str(tmp_path / "bus.db"), "--brain", str(tmp_path / "b.db")]) == 0
    assert "delivered 1" in capsys.readouterr().out


def test_bus_stats_prints_lag_and_flags_stale_sources(tmp_path, capsys):
    live = EventStore(tmp_path / "bus.db", manifests=MANIFESTS)           # real clock: health must be "now"
    live.publish(event_n(1))
    live.publish(event_n(2))
    live.consume(NAME, lambda e: None, types=["a015.*"], min_maturity="implemented", batch=1)
    live.record_health("A015:binance", ok=True)
    code = bus_stats.main(["--db", str(tmp_path / "bus.db")])
    out = capsys.readouterr().out
    assert "events 2" in out and "consumer librarian: cursor 1 lag 1" in out
    assert "A015:binance" in out and "A015:okx" in out and "STALE" in out
    assert code == 1                                                     # stale sources make the check fail


# ---- found by the first live run: 2235 events were left pending after a run ---------------------------

def test_run_once_drains_a_backlog_bigger_than_one_batch(store, brain):
    # regression: one batch (50) per run meant a 2285-event backlog needed ~45 supervisor cycles
    store.publish_many([event_n(i) for i in range(1, 121)])
    stats = run_once(store, brain)
    assert stats.delivered == 120
    assert store.stats()["consumers"][NAME]["lag"] == 0


def test_a_failing_handler_does_not_spin_the_drain(store, brain, monkeypatch):
    store.publish_many([event_n(i) for i in range(1, 6)])

    def broken(*a, **k):
        raise RuntimeError("brain unavailable")

    monkeypatch.setattr(brain, "write", broken)
    stats = run_once(store, brain)                       # must return, not loop on the same event
    assert stats.delivered == 0 and stats.failed == 1
    assert store.stats()["consumers"][NAME]["lag"] == 5


def test_librarian_tolerates_a_long_outage_before_parking(store, brain, monkeypatch):
    # review #7: 5 attempts at one per 5-minute cycle parked facts after ~25 minutes
    seen = {}
    real = store.consume
    monkeypatch.setattr(store, "consume", lambda *a, **k: seen.update(k) or real(*a, **k))
    run_once(store, brain)
    assert seen["max_attempts"] >= 20


def test_consume_cli_can_retry_parked_events(store, brain, tmp_path, capsys):
    store.publish(event_n(1))
    store.consume(NAME, lambda e: (_ for _ in ()).throw(RuntimeError("down")), types=["a015.*"],
                  min_maturity="implemented", max_attempts=1)
    assert len(store.parked(NAME)) == 1
    assert consume.main(["--once", "--retry-parked", "--db", str(tmp_path / "bus.db"),
                         "--brain", str(tmp_path / "b2.db")]) == 0
    assert "retried 1" in capsys.readouterr().out and store.parked(NAME) == []
