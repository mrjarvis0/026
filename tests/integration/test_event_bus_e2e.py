"""Phase 1 exit test: a fake A015 poll becomes a recorded fact in the persistent brain.

fake exchange -> `cli poll` (event_log + poll_status) -> relay -> bus.db -> librarian -> brain.db
Nothing is mocked inside the chain; only the exchange and the clock are fake.
"""
from datetime import UTC, datetime

import pytest

from agents.A015_Exchange_Listing_Delisting_Intelligence import cli
from agents.A015_Exchange_Listing_Delisting_Intelligence.core import event_log, poll_status
from agents.A015_Exchange_Listing_Delisting_Intelligence.tests.test_poller_hardening import (
    FakeExchange,
    seed,
    spot,
)
from agents.A015_Exchange_Listing_Delisting_Intelligence.tools import ccxt_market_poller as poller
from bootstrap.adapters import a015 as a015_adapter
from bootstrap.consumers.librarian import NAMESPACE, run_once
from bootstrap.relay import monitor_once
from bootstrap.relays.a015 import relay_once
from brain.store import Brain
from orchestrator.event_bus.store import EventStore
from orchestrator.event_bus.tests.helpers import FakeClock


@pytest.fixture
def chain(tmp_path, monkeypatch):
    monkeypatch.setattr(poller, "_SNAPSHOT_DIR", tmp_path / "snaps")
    monkeypatch.setattr(event_log, "EVENT_LOG_DIR", tmp_path / "events")
    monkeypatch.setattr(poll_status, "POLL_STATUS_FILE", tmp_path / "poll_status.json")
    clock = FakeClock(datetime.now(UTC))                       # the poll stamps real time; keep them aligned
    manifest = a015_adapter.load_manifest()                    # the REAL A015 manifest authorizes the producer
    store = EventStore(tmp_path / "bus.db", manifests={"A015": manifest}, clock=clock)
    brain = Brain(str(tmp_path / "brain.db"))
    seed(tmp_path / "snaps", spot(100), "binance")
    monkeypatch.setattr(poller, "_init_exchange", lambda eid: FakeExchange(spot(99)))   # T99/USDT vanishes
    return store, brain, clock


def test_a015_poll_to_brain_end_to_end(chain):
    store, brain, clock = chain

    assert cli.poll(None, ["binance"]) == 0
    first = relay_once(store)
    assert (first.published, first.rejected, first.health_updated) == (1, [], 1)
    assert store.health("A015:binance")["ok"] is True
    assert monitor_once(store, ["A015:binance"], 1800) == []              # polled just now: not stale

    assert run_once(store, brain).delivered == 1
    [event] = store.read()
    recorded = brain.read(NAMESPACE, f"event:{event['event_id']}", by="test")
    assert recorded["type"] == "a015.listing.delisted"
    assert recorded["data"]["symbol"] == "T99/USDT" and recorded["data"]["base"] == "T99"
    assert recorded["detector"]["maturity"] == "implemented" and recorded["confidence"] is None
    assert recorded["evidence"][0]["locator"].startswith("snapshot:")
    assert recorded["event_window"]["from"] <= recorded["event_window"]["to"]

    # run the whole chain again: nothing multiplies
    assert cli.poll(None, ["binance"]) == 0                                # snapshot already at 99 -> no change
    assert relay_once(store).published == 0
    assert run_once(store, brain).delivered == 0
    assert len(brain.history(NAMESPACE, f"event:{event['event_id']}")) == 1

    # lose the relay's high-water mark: the log is replayed, the bus de-duplicates
    store.set_state("a015", "last_file", "")
    replay = relay_once(store)
    assert (replay.published, replay.duplicates) == (0, 1)
    assert run_once(store, brain).delivered == 0 and len(store.read()) == 1

    # the poller goes quiet: after the stale window the monitor says so, once
    clock.advance(31 * 60)
    assert monitor_once(store, ["A015:binance"], 30 * 60) == ["A015:binance"]
    assert monitor_once(store, ["A015:binance"], 30 * 60) == []
    assert len(store.read(types=["system.source.stale"])) == 1


def test_a_failed_poll_is_never_read_as_a_quiet_exchange(chain, monkeypatch):
    store, brain, clock = chain
    monkeypatch.setattr(poller, "_init_exchange", lambda eid: FakeExchange(exc=RuntimeError("net down")))
    assert cli.poll(None, ["binance"]) == 1
    relay_once(store)
    assert store.health("A015:binance")["ok"] is False
    assert store.health("A015:binance")["last_ok_at"] is None             # no successful observation, ever
    assert monitor_once(store, ["A015:binance"], 1800) == ["A015:binance"]
    assert store.read(types=["a015.*"]) == []                             # and no events were invented
