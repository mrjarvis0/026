"""EventStore publish/read — each test names the defect or rule it guards (spec section 8)."""
import multiprocessing
import sqlite3

import pytest

from orchestrator.event_bus.envelope import EnvelopeError
from orchestrator.event_bus.store import EventStore, StoreBusy
from orchestrator.event_bus.tests.helpers import MANIFESTS, FakeClock, event_n, listing_n


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def db(tmp_path):
    return tmp_path / "bus.db"


@pytest.fixture
def store(db, clock):
    return EventStore(db, manifests=MANIFESTS, clock=clock)


def test_publish_assigns_increasing_seq(store):
    assert store.publish(event_n(1)) == (1, False)
    assert store.publish(event_n(2)) == (2, False)


def test_duplicate_event_id_returns_same_seq_flagged(store):
    # regression-in-waiting: replaying a producer's log must not multiply events
    assert store.publish(event_n(1)) == (1, False)
    assert store.publish(event_n(1)) == (1, True)
    assert len(store.read()) == 1


def test_published_at_set_by_store_not_payload(store, clock):
    store.publish(event_n(1, published_at="1999-01-01T00:00:00+00:00"))
    [row] = store.read()
    assert row["published_at"] == clock().isoformat()


def test_invalid_event_not_stored(store):
    with pytest.raises(EnvelopeError):
        store.publish(event_n(1, source="A002"))          # A002 does not produce this type
    assert store.read() == []


def test_events_are_immutable(store, db):
    store.publish(event_n(1))
    conn = sqlite3.connect(db)
    with pytest.raises(sqlite3.IntegrityError, match="immutable"):
        conn.execute("UPDATE events SET type = 'x.y.z'")


def test_wal_and_user_version(store, db):
    conn = sqlite3.connect(db)
    assert conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
    assert conn.execute("PRAGMA user_version").fetchone()[0] == 1


def test_all_v1_tables_exist(store, db):
    names = {r[0] for r in sqlite3.connect(db).execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"events", "consumers", "attempts", "parked", "source_health",
            "relay_state", "trace", "approvals"} <= names


def test_read_filters_by_type_and_after_seq(store):
    store.publish(event_n(1))
    store.publish(listing_n(2))
    store.publish(event_n(3))
    assert [r["seq"] for r in store.read(types=["a015.listing.delisted"])] == [1, 3]
    assert [r["seq"] for r in store.read(after_seq=1)] == [2, 3]
    assert [r["seq"] for r in store.read(types=["a015.listing.*"], limit=2)] == [1, 2]


def _publish_in_child(db_path, out):
    child = EventStore(db_path, manifests=MANIFESTS)
    out.put(child.publish(event_n(1)))


def test_two_processes_publish_same_event_once(store, db):
    ctx = multiprocessing.get_context("spawn")
    out = ctx.Queue()
    procs = [ctx.Process(target=_publish_in_child, args=(str(db), out)) for _ in range(2)]
    for p in procs:
        p.start()
    results = [out.get(timeout=60) for _ in procs]
    for p in procs:
        p.join(timeout=60)
    assert {seq for seq, _ in results} == {1}
    assert sorted(dup for _, dup in results) == [False, True]
    assert len(store.read()) == 1


def test_locked_database_raises_store_busy(db, clock):
    busy = EventStore(db, manifests=MANIFESTS, clock=clock, busy_timeout_ms=50)
    other = sqlite3.connect(db, isolation_level=None)
    other.execute("BEGIN IMMEDIATE")
    with pytest.raises(StoreBusy):
        busy.publish(event_n(1))
    other.execute("ROLLBACK")
    assert busy.read() == []


# ---- throughput (found by the first live run: ~400 ms per publish on the F: drive) -----------------------

def test_store_reuses_one_connection(db, clock, monkeypatch):
    # regression: a connection per call made every publish checkpoint + fsync the WAL when it closed
    calls = []
    real = sqlite3.connect
    monkeypatch.setattr(sqlite3, "connect", lambda *a, **k: calls.append(1) or real(*a, **k))
    s = EventStore(db, manifests=MANIFESTS, clock=clock)
    for n in range(1, 21):
        s.publish(event_n(n))
    s.consume("c", lambda e: None, types=["a015.*"], min_maturity="implemented")
    s.read()
    s.stats()
    assert len(calls) == 1


def test_publish_many_is_one_atomic_batch(store):
    assert store.publish_many([event_n(1), event_n(2), event_n(1)]) == [(1, False), (2, False), (1, True)]
    assert [e["seq"] for e in store.read()] == [1, 2]


def test_publish_many_writes_nothing_if_any_event_is_invalid(store):
    with pytest.raises(EnvelopeError):
        store.publish_many([event_n(1), event_n(2, source="A002")])
    assert store.read() == []


def test_validate_checks_without_storing(store):
    store.validate(event_n(1))
    with pytest.raises(EnvelopeError):
        store.validate(event_n(1, source="A002"))
    assert store.read() == []
