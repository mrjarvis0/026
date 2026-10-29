"""Phase 0 pipeline hardening — each test names the defect it guards.

Run: pytest agents/A015_*/tests -q   (no network: the exchange is a fake)
"""
import json

import pytest

from agents.A015_Exchange_Listing_Delisting_Intelligence import cli
from agents.A015_Exchange_Listing_Delisting_Intelligence.core import event_log
from agents.A015_Exchange_Listing_Delisting_Intelligence.tools import ccxt_market_poller as poller
from agents.A015_Exchange_Listing_Delisting_Intelligence.tools import diff_engine


def mk(symbol, typ="spot"):
    return {"symbol": symbol, "type": typ, "active": True, "base": symbol.split("/")[0]}


class FakeExchange:
    def __init__(self, markets=None, exc=None):
        self.markets, self.exc = markets or [], exc

    def fetch_markets(self):
        if self.exc:
            raise self.exc
        return list(self.markets)


@pytest.fixture
def snap_dir(tmp_path, monkeypatch):
    d = tmp_path / "snaps"
    monkeypatch.setattr(poller, "_SNAPSHOT_DIR", d)
    monkeypatch.setattr(event_log, "EVENT_LOG_DIR", tmp_path / "events")
    return d


def serve(monkeypatch, markets=None, exc=None):
    monkeypatch.setattr(poller, "_init_exchange", lambda eid: FakeExchange(markets, exc))


def seed(snap_dir, markets, exchange="binance"):
    snap_dir.mkdir(parents=True, exist_ok=True)
    (snap_dir / f"{exchange}.json").write_text(
        json.dumps({m["symbol"]: m for m in markets}), encoding="utf-8")


def saved(snap_dir, exchange="binance"):
    return json.loads((snap_dir / f"{exchange}.json").read_text(encoding="utf-8"))


def spot(n):
    return [mk(f"T{i}/USDT") for i in range(n)]


# ---- baseline / failure / shrink ----------------------------------------------------

def test_first_poll_is_a_baseline_not_a_listing_flood(snap_dir, monkeypatch):
    # regression: with no snapshot every market was "added" -> NEW_LISTING for all of them
    serve(monkeypatch, spot(3))
    res = poller.poll_exchange("binance")
    assert res["ok"] and res["baseline"] is True and res["changes"] == []
    assert len(saved(snap_dir)) == 3


def test_failed_fetch_is_reported_and_keeps_the_snapshot(snap_dir, monkeypatch):
    # regression: a fetch error came back as "0 changes", the same as a quiet exchange
    seed(snap_dir, spot(3))
    serve(monkeypatch, exc=RuntimeError("net down"))
    res = poller.poll_exchange("binance")
    assert res["ok"] is False and "net down" in res["error"]
    assert len(saved(snap_dir)) == 3


def test_suspicious_shrink_is_refused_not_turned_into_delistings(snap_dir, monkeypatch):
    # regression: a truncated market list would have produced mass false DELISTING events
    seed(snap_dir, spot(100))
    serve(monkeypatch, spot(10))
    res = poller.poll_exchange("binance")
    assert res["ok"] is False and "shrank" in res["error"] and res["changes"] == []
    assert len(saved(snap_dir)) == 100


def test_a_real_delisting_is_still_detected(snap_dir, monkeypatch):
    seed(snap_dir, spot(100))
    serve(monkeypatch, spot(99))
    res = poller.poll_exchange("binance")
    assert res["ok"] and [c["change_type"] for c in res["changes"]] == ["removed"]


# ---- market types ---------------------------------------------------------------------

def test_option_and_future_churn_is_not_a_listing(snap_dir, monkeypatch):
    # regression: dated futures/options roll over constantly and read as listings/pair changes
    seed(snap_dir, [mk("BTC/USDT")])
    serve(monkeypatch, [mk("BTC/USDT"), mk("BTC/USDT:USDT-250101", "future"),
                        mk("BTC-250101-90000-C", "option")])
    res = poller.poll_exchange("binance")
    assert res["ok"] and res["changes"] == []
    assert set(saved(snap_dir)) == {"BTC/USDT"}


def test_an_old_mixed_type_snapshot_is_compared_spot_only(snap_dir, monkeypatch):
    # the snapshots on disk predate the filter and hold swaps/options; they must not
    # all read as "removed" now that only spot is tracked
    seed(snap_dir, [mk("BTC/USDT"), mk("ETH/USDT")] + [mk(f"X{i}/USDT:USDT", "swap") for i in range(8)])
    serve(monkeypatch, [mk("BTC/USDT"), mk("ETH/USDT")])
    res = poller.poll_exchange("binance")
    assert res["ok"] and res["changes"] == []


# ---- snapshot file safety ------------------------------------------------------------

def test_snapshot_save_is_atomic(tmp_path, monkeypatch):
    # regression: open('w') truncated the 39 MB snapshot in place; a crash lost it
    path = tmp_path / "s.json"
    diff_engine.save_snapshot({"A/USDT": {"x": 1}}, str(path))

    def boom(*a, **k):
        raise OSError("disk full")

    monkeypatch.setattr(diff_engine.os, "replace", boom)
    with pytest.raises(OSError):
        diff_engine.save_snapshot({"B/USDT": {"x": 2}}, str(path))
    assert json.loads(path.read_text(encoding="utf-8")) == {"A/USDT": {"x": 1}}


def test_a_corrupt_snapshot_means_no_baseline_not_a_crash(snap_dir, monkeypatch):
    # regression: load_snapshot only caught FileNotFoundError, so a torn file crashed every poll
    snap_dir.mkdir(parents=True)
    (snap_dir / "binance.json").write_text("{torn", encoding="utf-8")
    assert diff_engine.load_snapshot(str(snap_dir / "binance.json")) == {}
    serve(monkeypatch, spot(3))
    res = poller.poll_exchange("binance")
    assert res["ok"] and res["baseline"] is True


# ---- events are durable, and logged before the snapshot advances ------------------------

def test_snapshot_does_not_advance_if_event_logging_fails(snap_dir, monkeypatch):
    # regression: the snapshot was overwritten before detection, so a crash lost the diff for good
    seed(snap_dir, spot(100))
    serve(monkeypatch, spot(99))

    def fail(res):
        raise OSError("event log unwritable")

    res = poller.poll_exchange("binance", on_changes=fail)
    assert res["ok"] is False and "event log" in res["error"]
    assert len(saved(snap_dir)) == 100


def test_snapshot_advances_after_events_are_logged(snap_dir, monkeypatch):
    seed(snap_dir, spot(100))
    serve(monkeypatch, spot(99))
    seen = {}

    def log_events(res):
        seen["snapshot_size_at_log_time"] = len(saved(snap_dir))

    assert poller.poll_exchange("binance", on_changes=log_events)["ok"]
    assert seen["snapshot_size_at_log_time"] == 100 and len(saved(snap_dir)) == 99


def test_event_log_writes_stable_ids_and_a_readable_file(tmp_path):
    reports = [{"event_type": "DELISTING", "exchange": "binance", "symbol": "T0/USDT"}]
    first = event_log.append_events("binance", reports, "olddigest", log_dir=tmp_path)
    again = event_log.append_events("binance", reports, "olddigest", log_dir=tmp_path)
    ids = [json.loads(p.read_text(encoding="utf-8"))[0]["event_id"] for p in (first, again)]
    assert ids[0] == ids[1] and ids[0].startswith("evt_")      # replay-safe: same diff, same id
    assert not list(tmp_path.glob("*.tmp"))
    other = event_log.append_events("binance", reports, "newdigest", log_dir=tmp_path)
    assert json.loads(other.read_text(encoding="utf-8"))[0]["event_id"] != ids[0]


def test_no_reports_writes_no_file(tmp_path):
    assert event_log.append_events("binance", [], "d", log_dir=tmp_path) is None
    assert not list(tmp_path.glob("*.json"))


def test_cli_poll_logs_events_and_flags_failures(snap_dir, monkeypatch, tmp_path):
    seed(snap_dir, spot(100))
    serve(monkeypatch, spot(99))                                 # one market disappears
    assert cli.poll(None, ["binance"]) == 0
    files = list((tmp_path / "events").glob("*.json"))
    events = [e for f in files for e in json.loads(f.read_text(encoding="utf-8"))]
    assert [e["event_type"] for e in events] == ["DELISTING"]
    serve(monkeypatch, exc=RuntimeError("down"))
    assert cli.poll(None, ["binance"]) == 1                      # a failed exchange is not a success
