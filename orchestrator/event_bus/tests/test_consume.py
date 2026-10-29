"""EventStore delivery, health, state, stats, prune — each test names the rule it guards (spec 9)."""
import json
from datetime import datetime, timedelta

import pytest

from orchestrator.event_bus.store import EventStore, backoff_sec
from orchestrator.event_bus.tests.helpers import MANIFESTS, FakeClock, event_n, listing_n


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def store(tmp_path, clock):
    return EventStore(tmp_path / "bus.db", manifests=MANIFESTS, clock=clock, rnd=lambda: 0.0)


def collector():
    seen: list[dict] = []
    return seen, seen.append


def cursor_of(store, name):
    return store.stats()["consumers"][name]["cursor"]


def validated(n):
    return event_n(n, detector={"id": "DELISTING", "maturity": "validated", "ceiling": 0.6})


# ---- delivery ----------------------------------------------------------------------------

def test_delivers_in_order_and_advances_cursor(store):
    for n in (1, 2, 3):
        store.publish(event_n(n))
    seen, handler = collector()
    stats = store.consume("c", handler, types=["a015.*"], min_maturity="implemented")
    assert [e["seq"] for e in seen] == [1, 2, 3]
    assert stats.delivered == 3 and stats.last_seq == 3 and cursor_of(store, "c") == 3


def test_second_consume_delivers_nothing(store):
    store.publish(event_n(1))
    seen, handler = collector()
    store.consume("c", handler, types=["a015.*"], min_maturity="implemented")
    assert store.consume("c", handler, types=["a015.*"], min_maturity="implemented").delivered == 0
    assert len(seen) == 1


def test_other_types_skipped_and_counted(store):
    store.publish(listing_n(1))
    store.publish(event_n(2))
    seen, handler = collector()
    stats = store.consume("c", handler, types=["a015.listing.delisted"], min_maturity="implemented")
    assert [e["seq"] for e in seen] == [2]
    assert stats.skipped_other_type == 1 and cursor_of(store, "c") == 2


def test_low_maturity_skipped_counted_and_handler_not_called(store):
    # the maturity gate is a code path: an unvalidated detector never reaches an acting consumer
    store.publish(event_n(1))                      # detector maturity: implemented
    store.publish(validated(2))
    seen, handler = collector()
    stats = store.consume("acting", handler, types=["a015.*"])      # default min_maturity="validated"
    assert [e["seq"] for e in seen] == [2]
    assert stats.skipped_low_maturity == 1 and stats.delivered == 1


def test_recorder_with_min_maturity_implemented_receives(store):
    store.publish(event_n(1))
    seen, handler = collector()
    store.consume("recorder", handler, types=["a015.*"], min_maturity="implemented")
    assert len(seen) == 1 and seen[0]["detector"]["maturity"] == "implemented"


def test_null_detector_event_passes_validated_gate(store):
    store.publish(listing_n(1))
    seen, handler = collector()
    store.consume("acting", handler, types=["a015.*"])
    assert len(seen) == 1


# ---- failures ----------------------------------------------------------------------------

def failing_on(*bad_seqs, times=999):
    calls: dict[int, int] = {}
    seen: list[int] = []

    def handler(event):
        calls[event["seq"]] = calls.get(event["seq"], 0) + 1
        if event["seq"] in bad_seqs and calls[event["seq"]] <= times:
            raise RuntimeError("boom")
        seen.append(event["seq"])

    return seen, calls, handler


def test_failure_stops_batch_and_records_attempt(store):
    for n in (1, 2, 3):
        store.publish(event_n(n))
    seen, calls, handler = failing_on(2)
    stats = store.consume("c", handler, types=["a015.*"], min_maturity="implemented")
    assert seen == [1] and stats.delivered == 1 and stats.failed == 1
    assert cursor_of(store, "c") == 1                  # cursor only moves after success; order kept


def test_retry_waits_for_backoff(store, clock):
    store.publish(event_n(1))
    seen, calls, handler = failing_on(1, times=1)
    store.consume("c", handler, types=["a015.*"], min_maturity="implemented")
    store.consume("c", handler, types=["a015.*"], min_maturity="implemented")
    assert calls[1] == 1                               # too early: handler not called again
    clock.advance(10)
    store.consume("c", handler, types=["a015.*"], min_maturity="implemented")
    assert calls[1] == 2 and seen == [1]


def test_poison_event_parked_and_stream_continues(store, clock):
    for n in (1, 2):
        store.publish(event_n(n))
    seen, calls, handler = failing_on(1)
    kw = dict(types=["a015.*"], min_maturity="implemented", max_attempts=2)
    store.consume("c", handler, **kw)
    clock.advance(10)
    stats = store.consume("c", handler, **kw)
    assert stats.parked == 1 and seen == [2]
    [row] = store.parked("c")
    assert row["seq"] == 1 and row["attempts"] == 2 and "boom" in row["last_error"]
    assert cursor_of(store, "c") == 2


def test_handler_may_publish_without_deadlock(store):
    store.publish(event_n(1))

    def handler(event):
        store.publish(event_n(2))                      # handlers run outside any DB transaction

    store.consume("c", handler, types=["a015.*"], min_maturity="implemented")
    assert [e["seq"] for e in store.read()] == [1, 2]


def test_backoff_sec_bounds():
    assert backoff_sec(1, rnd=lambda: 0.0) == 2.5
    assert backoff_sec(1, rnd=lambda: 1.0) == 5.0
    assert backoff_sec(40, rnd=lambda: 1.0) == 300.0


# ---- health (coverage proof) -----------------------------------------------------------------

def test_failed_poll_keeps_previous_last_ok_at(store, clock):
    store.record_health("A015:binance", ok=True, detail="polled")
    first_ok = store.health("A015:binance")["last_ok_at"]
    clock.advance(900)
    store.record_health("A015:binance", ok=False, detail="timeout")
    h = store.health("A015:binance")
    assert h["ok"] is False and h["last_ok_at"] == first_ok and h["detail"] == "timeout"
    assert h["last_attempt_at"] != first_ok


def test_record_health_honours_explicit_time(store):
    when = datetime.fromisoformat("2026-10-28T08:00:00+00:00")
    store.record_health("A015:okx", ok=True, at=when)
    assert datetime.fromisoformat(store.health("A015:okx")["last_ok_at"]) == when


def test_stale_sources_never_seen_and_old(store, clock):
    store.record_health("A015:binance", ok=True)
    assert store.stale_sources(["A015:binance", "A015:okx"], 1800) == ["A015:okx"]   # never seen
    clock.advance(1801)
    assert store.stale_sources(["A015:binance"], 1800) == ["A015:binance"]


def test_fresh_source_not_stale(store, clock):
    store.record_health("A015:binance", ok=True)
    clock.advance(1700)
    assert store.stale_sources(["A015:binance"], 1800) == []


# ---- state / stats / prune ----------------------------------------------------------------------

def test_state_roundtrip(store):
    assert store.get_state("a015", "last_file", "none") == "none"
    store.set_state("a015", "last_file", "a.json")
    store.set_state("a015", "last_file", "b.json")
    assert store.get_state("a015", "last_file") == "b.json"


def test_stats_reports_lag(store):
    for n in (1, 2, 3):
        store.publish(event_n(n))
    _, calls, handler = failing_on(2)
    store.consume("c", handler, types=["a015.*"], min_maturity="implemented")
    s = store.stats()
    assert s["events"] == 3 and s["consumers"]["c"] == {"cursor": 1, "lag": 2}


def read_archive(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_prune_archives_then_deletes(store, clock, tmp_path):
    store.publish(event_n(1))
    store.consume("c", lambda e: None, types=["a015.*"], min_maturity="implemented")
    clock.advance(86400 * 100)
    archive = tmp_path / "archive.jsonl"
    assert store.prune(clock() - timedelta(days=90), archive) == 1
    assert [e["event_id"] for e in read_archive(archive)] == [event_n(1)["event_id"]]
    assert store.read() == []


def test_prune_never_deletes_unconsumed(store, clock, tmp_path):
    store.publish(event_n(1))
    store.publish(event_n(2))
    store.consume("c", lambda e: None, types=["a015.*"], min_maturity="implemented", batch=1)
    clock.advance(86400 * 100)
    assert store.prune(clock() - timedelta(days=90), tmp_path / "a.jsonl") == 1
    assert [e["seq"] for e in store.read()] == [2]


def test_seq_not_reused_after_prune(store, clock, tmp_path):
    store.publish(event_n(1))
    clock.advance(86400 * 100)
    store.prune(clock() - timedelta(days=90), tmp_path / "a.jsonl")
    assert store.publish(event_n(2)) == (2, False)


# ---- independent review (2026-10-29) ---------------------------------------------------------------------

def test_cursor_never_moves_backward(store):
    # review #9: two concurrent consumers of one name could regress the cursor
    store.consume("c", lambda e: None, types=["a015.*"])      # registers the consumer
    store._advance("c", 5)
    store._advance("c", 3)
    assert cursor_of(store, "c") == 5


def test_record_health_rejects_a_naive_time(store):
    # review #10: a naive timestamp later broke stale_sources with a TypeError
    with pytest.raises(ValueError, match="timezone"):
        store.record_health("A015:okx", ok=True, at=datetime(2026, 10, 28, 9, 0))


def test_parked_events_can_be_retried(store):
    # review #7: a parked event had no way back
    store.publish(event_n(1))
    kw = dict(types=["a015.*"], min_maturity="implemented", max_attempts=1)
    store.consume("c", failing_on(1)[2], **kw)
    assert len(store.parked("c")) == 1
    seen, _, ok_handler = failing_on()                          # a handler that now works
    assert store.retry_parked("c", ok_handler) == 1
    assert seen == [1] and store.parked("c") == []


def test_a_still_failing_parked_event_stays_parked(store):
    store.publish(event_n(1))
    store.consume("c", failing_on(1)[2], types=["a015.*"], min_maturity="implemented", max_attempts=1)
    assert store.retry_parked("c", failing_on(1)[2]) == 0
    assert len(store.parked("c")) == 1
