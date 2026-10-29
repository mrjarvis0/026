"""A015 relay + health monitor — each test names the rule or defect it guards (design spec 10)."""
import json
from datetime import datetime, timedelta

import pytest

from bootstrap import relay
from bootstrap.relays import a015 as relay_a015
from bootstrap.relays.a015 import EVENT_TYPES, relay_once, to_envelope
from orchestrator.event_bus.envelope import load_schemas, validate_event
from orchestrator.event_bus.store import EventStore, StoreBusy
from orchestrator.event_bus.tests.helpers import MANIFESTS, FakeClock

OBSERVED = "2026-10-28T09:15:02+00:00"
SYMBOL = "XYZ/USDT"


def report(event_type="DELISTING", n=1, **over):
    base = {"event_type": event_type, "exchange": "binance", "symbol": SYMBOL,
            "detected_at": OBSERVED, "detected_via": "structured-diff", "phase": 1, "evidence_backed": True,
            "event_id": f"evt_{n:016x}", "snapshot_digest": "3f9a21c0e4b1",
            "old_snapshot_at": "2026-10-28T09:00:00+00:00", "observed_at": OBSERVED, "spot_markets": 3705}
    extra = {
        "DELISTING": {"stated_reason": "unspecified", "last_seen_ts": OBSERVED,
                      "historical_context": "reason not specified", "median_crash_pct": -25},
        "NEW_LISTING": {"first_seen_ts": OBSERVED, "trading_pairs": [SYMBOL],
                        "historical_context": "~41% median day-1 effect", "median_day_1_effect_pct": 41},
        "STATUS_CHANGE": {"status_from": "active", "status_to": "inactive", "historical_context": "ops signal"},
        "PAIR_CHANGE": {"base_asset": "XYZ", "quote_asset": "BTC", "pair_added": "XYZ/BTC",
                        "pair_removed": None, "historical_context": "note", "median_effect_pct": None},
    }[event_type]
    return {**base, **extra, **over}


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def store(tmp_path, clock):
    return EventStore(tmp_path / "bus.db", manifests=MANIFESTS, clock=clock)


@pytest.fixture
def log_dir(tmp_path):
    d = tmp_path / "event_log"
    d.mkdir()
    return d


def write_events(log_dir, name, reports):
    (log_dir / name).write_text(json.dumps(reports), encoding="utf-8")


FILE_1 = "20261028T091502000000-000-binance.json"
FILE_2 = "20261028T093002000000-000-okx.json"


# ---- pure mapping ----------------------------------------------------------------------------

@pytest.mark.parametrize("event_type", sorted(EVENT_TYPES))
def test_golden_envelope_for_each_type(event_type):
    env = to_envelope(report(event_type), {})
    assert env["type"] == EVENT_TYPES[event_type] and env["source"] == "A015"
    assert env["subject"] == f"market:binance:{SYMBOL}"
    assert env["detector"] == {"id": event_type, "maturity": "implemented", "ceiling": None}
    assert env["confidence"] is None and env["untrusted"] is False
    assert env["event_window"] == {"from": "2026-10-28T09:00:00+00:00", "to": OBSERVED}
    assert env["evidence"][0]["locator"] == "snapshot:3f9a21c0e4b1"
    validate_event(env, load_schemas(), MANIFESTS)


def test_detector_maturity_comes_from_the_manifest():
    assert to_envelope(report(), {"DELISTING": "validated"})["detector"]["maturity"] == "validated"


def test_report_without_digest_still_publishes_with_unknown_locator():
    old = report()
    del old["snapshot_digest"], old["old_snapshot_at"]
    env = to_envelope(old, {})
    assert env["evidence"][0]["locator"] == "snapshot:unknown" and env["event_window"] is None
    validate_event(env, load_schemas(), MANIFESTS)


# ---- relay_once ------------------------------------------------------------------------------

def test_relay_publishes_and_advances_mark(store, log_dir, tmp_path):
    write_events(log_dir, FILE_1, [report(n=1), report("NEW_LISTING", n=2)])
    res = relay_once(store, event_log_dir=log_dir, poll_status_path=tmp_path / "none.json", detector_maturity={})
    assert (res.published, res.duplicates, res.files) == (2, 0, 1) and res.rejected == []
    assert len(store.read()) == 2 and store.get_state("a015", "last_file") == FILE_1
    again = relay_once(store, event_log_dir=log_dir, poll_status_path=tmp_path / "none.json", detector_maturity={})
    assert (again.published, again.files) == (0, 0)


def test_replaying_the_log_only_produces_duplicates(store, log_dir, tmp_path):
    write_events(log_dir, FILE_1, [report(n=1), report(n=2)])
    kw = dict(event_log_dir=log_dir, poll_status_path=tmp_path / "none.json", detector_maturity={})
    relay_once(store, **kw)
    store.set_state("a015", "last_file", "")                       # lose the high-water mark
    res = relay_once(store, **kw)
    assert (res.published, res.duplicates) == (0, 2) and len(store.read()) == 2


def test_torn_event_file_is_skipped_not_fatal(store, log_dir, tmp_path):
    (log_dir / FILE_1).write_text("[{torn", encoding="utf-8")
    write_events(log_dir, FILE_2, [report(n=1)])
    res = relay_once(store, event_log_dir=log_dir, poll_status_path=tmp_path / "none.json", detector_maturity={})
    assert res.published == 1 and any("unreadable" in r for r in res.rejected)
    assert store.get_state("a015", "last_file") == FILE_2           # a bad file never stalls the relay


def test_bad_reports_are_rejected_and_the_run_continues(store, log_dir, tmp_path):
    no_symbol = report(n=1)
    del no_symbol["symbol"]
    write_events(log_dir, FILE_1, [no_symbol, report("ANNOUNCED_LISTING_X" if False else "DELISTING", n=2),
                                   {"event_type": "MYSTERY", "event_id": "evt_x"}])
    res = relay_once(store, event_log_dir=log_dir, poll_status_path=tmp_path / "none.json", detector_maturity={})
    assert res.published == 1 and len(res.rejected) == 2


def test_baseline_poll_is_not_ok_health(store, log_dir, tmp_path):
    status = tmp_path / "poll_status.json"
    status.write_text(json.dumps({
        "binance": {"ok": True, "error": None, "baseline": True, "polled_at": OBSERVED, "spot_markets": 9},
        "okx": {"ok": True, "error": None, "baseline": False, "polled_at": OBSERVED, "spot_markets": 9},
        "bybit": {"ok": False, "error": "net down", "baseline": False, "polled_at": OBSERVED, "spot_markets": 0},
    }), encoding="utf-8")
    res = relay_once(store, event_log_dir=log_dir, poll_status_path=status, detector_maturity={})
    assert res.health_updated == 3
    assert store.health("A015:binance")["ok"] is False and "baseline" in store.health("A015:binance")["detail"]
    assert store.health("A015:okx")["ok"] is True
    assert store.health("A015:okx")["last_ok_at"] == OBSERVED
    assert store.health("A015:bybit")["ok"] is False and "net down" in store.health("A015:bybit")["detail"]


def test_corrupt_poll_status_updates_no_health(store, log_dir, tmp_path):
    status = tmp_path / "poll_status.json"
    status.write_text("{torn", encoding="utf-8")
    res = relay_once(store, event_log_dir=log_dir, poll_status_path=status, detector_maturity={})
    assert res.health_updated == 0 and store.stats()["sources"] == {}


# ---- health monitor -----------------------------------------------------------------------------

def stale_events(store):
    return [e for e in store.read(types=["system.source.stale"])]


def test_monitor_flags_once_per_outage_and_clears_on_recovery(store, clock):
    sources, max_age = ["A015:binance"], 1800
    assert relay.monitor_once(store, sources, max_age) == ["A015:binance"]      # never seen -> stale
    assert relay.monitor_once(store, sources, max_age) == []                    # same outage: silent
    assert len(stale_events(store)) == 1
    ev = stale_events(store)[0]
    assert ev["source"] == "SYS" and ev["data"]["source"] == "A015:binance" and ev["data"]["max_age_s"] == 1800

    store.record_health("A015:binance", ok=True)
    assert relay.monitor_once(store, sources, max_age) == []                    # recovered, flag cleared
    assert store.get_state("monitor", "stale:A015:binance") == "0"

    clock.advance(1801)
    assert relay.monitor_once(store, sources, max_age) == ["A015:binance"]      # a new outage flags again
    assert len(stale_events(store)) == 2


# ---- CLI ------------------------------------------------------------------------------------------

def test_main_exits_1_when_the_store_is_busy(tmp_path, monkeypatch):
    def busy(*a, **k):
        raise StoreBusy("locked")

    monkeypatch.setattr(relay_a015, "relay_once", busy)
    assert relay.main(["--once", "--db", str(tmp_path / "bus.db")]) == 1


def test_main_once_runs_and_flags_unseen_sources(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(relay_a015.event_log, "EVENT_LOG_DIR", tmp_path / "no_events")
    monkeypatch.setattr(relay_a015.poll_status, "POLL_STATUS_FILE", tmp_path / "no_status.json")
    db = tmp_path / "bus.db"
    assert relay.main(["--once", "--db", str(db)]) == 0
    cfg = relay.load_bus_config()
    store = EventStore(db)
    assert len(store.read(types=["system.source.stale"])) == len(cfg["a015_exchanges"])
    assert "published" in capsys.readouterr().out


# ---- found by the first live run: a 2285-event backlog took > 900 s and starved the health step -----------

def test_health_is_recorded_before_events(store, log_dir, tmp_path, monkeypatch):
    # regression: health came last, so a long (or killed) backlog run left every source "never seen"
    status = tmp_path / "poll_status.json"
    status.write_text(json.dumps({"okx": {"ok": True, "error": None, "baseline": False,
                                          "polled_at": OBSERVED, "spot_markets": 9}}), encoding="utf-8")
    write_events(log_dir, FILE_1, [report(n=1)])

    def killed(events):
        raise RuntimeError("killed mid-backlog")

    monkeypatch.setattr(store, "publish_many", killed)
    with pytest.raises(RuntimeError):
        relay_once(store, event_log_dir=log_dir, poll_status_path=status, detector_maturity={})
    assert store.health("A015:okx")["ok"] is True


def test_a_big_file_is_published_in_one_batch(store, log_dir, tmp_path, monkeypatch):
    # regression: one connection + one transaction per event is what made the backlog take 15 minutes
    write_events(log_dir, FILE_1, [report(n=i, symbol=f"T{i}/USDT") for i in range(1, 501)])
    sizes = []
    real = store.publish_many
    monkeypatch.setattr(store, "publish_many", lambda evs: sizes.append(len(evs)) or real(evs))
    monkeypatch.setattr(store, "publish", lambda ev: pytest.fail("published event-by-event"))
    res = relay_once(store, event_log_dir=log_dir, poll_status_path=tmp_path / "none.json", detector_maturity={})
    assert sizes == [500] and res.published == 500 and res.rejected == []


# ---- found by the first live poll: STATUS_CHANGE reports that were not transitions ----------------------------

def test_status_change_without_a_transition_is_rejected(store, log_dir, tmp_path):
    # the old detector bug left thousands of BREAK -> BREAK "changes" in A015's log; the bus must not carry them
    write_events(log_dir, FILE_1, [report("STATUS_CHANGE", n=1, status_from="BREAK", status_to="BREAK"),
                                   report("STATUS_CHANGE", n=2, status_from="TRADING", status_to="BREAK")])
    res = relay_once(store, event_log_dir=log_dir, poll_status_path=tmp_path / "none.json", detector_maturity={})
    assert res.published == 1 and len(res.rejected) == 1 and "transition" in res.rejected[0]


def test_main_prints_only_a_few_rejections(tmp_path, monkeypatch, capsys):
    # a replay of old junk rejected 2191 reports and printed every one into the supervisor log
    monkeypatch.setattr(relay_a015, "relay_once",
                        lambda store: relay_a015.RelayResult(rejected=[f"file[{i}]: bad" for i in range(50)]))
    assert relay.main(["--once", "--db", str(tmp_path / "bus.db")]) == 1
    out = capsys.readouterr().out
    assert out.count("rejected: file[") == 5 and "45 more" in out and "rejected 50" in out
