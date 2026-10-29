"""Poll status + enriched event reports (design spec section 10) — each test names the rule it guards.

Run: pytest agents/A015_*/tests -q   (no network: exchanges are fakes)
"""
import json
from datetime import datetime

import pytest

from agents.A015_Exchange_Listing_Delisting_Intelligence import cli
from agents.A015_Exchange_Listing_Delisting_Intelligence.core import event_log, poll_status
from agents.A015_Exchange_Listing_Delisting_Intelligence.tests.test_poller_hardening import (
    FakeExchange,
    seed,
    spot,
)
from agents.A015_Exchange_Listing_Delisting_Intelligence.tools import ccxt_market_poller as poller


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(poller, "_SNAPSHOT_DIR", tmp_path / "snaps")
    monkeypatch.setattr(event_log, "EVENT_LOG_DIR", tmp_path / "events")
    monkeypatch.setattr(poll_status, "POLL_STATUS_FILE", tmp_path / "poll_status.json")
    return tmp_path


def serve_each(monkeypatch, fakes: dict, asked: list | None = None):
    def init(exchange_id):
        if asked is not None:
            asked.append(exchange_id)
        return fakes[exchange_id]

    monkeypatch.setattr(poller, "_init_exchange", init)


def status_file(env):
    return json.loads((env / "poll_status.json").read_text(encoding="utf-8"))


def test_poll_writes_status_for_ok_failed_and_baseline(env, monkeypatch):
    seed(env / "snaps", spot(100), "binance")
    seed(env / "snaps", spot(100), "okx")
    serve_each(monkeypatch, {"binance": FakeExchange(spot(99)),
                             "okx": FakeExchange(exc=RuntimeError("net down")),
                             "bybit": FakeExchange(spot(3))})
    assert cli.poll(None, ["binance", "okx", "bybit"]) == 1          # okx failed -> exit 1
    st = status_file(env)
    assert st["binance"]["ok"] is True and st["binance"]["baseline"] is False
    assert st["binance"]["spot_markets"] == 99
    assert st["okx"]["ok"] is False and "net down" in st["okx"]["error"]
    assert st["bybit"]["ok"] is True and st["bybit"]["baseline"] is True and st["bybit"]["spot_markets"] == 3
    assert datetime.fromisoformat(st["binance"]["polled_at"]).tzinfo is not None


def test_status_merge_keeps_other_exchanges(env, monkeypatch):
    serve_each(monkeypatch, {"binance": FakeExchange(spot(3)), "okx": FakeExchange(spot(4))})
    cli.poll(None, ["binance"])
    cli.poll(None, ["okx"])
    assert set(status_file(env)) == {"binance", "okx"}


def test_corrupt_or_missing_status_reads_empty(env):
    assert poll_status.read_poll_status() == {}
    (env / "poll_status.json").write_text("{torn", encoding="utf-8")
    assert poll_status.read_poll_status() == {}


def test_status_write_is_atomic(env, monkeypatch):
    poll_status.write_poll_status({"binance": {"ok": True, "error": None, "baseline": False,
                                               "observed_at": "2026-10-28T09:00:00+00:00",
                                               "spot_markets": 5}})
    before = (env / "poll_status.json").read_text(encoding="utf-8")

    def boom(*a, **k):
        raise OSError("disk full")

    monkeypatch.setattr(poll_status.os, "replace", boom)
    with pytest.raises(OSError):
        poll_status.write_poll_status({"okx": {"ok": True, "error": None, "baseline": False,
                                               "observed_at": "2026-10-28T09:01:00+00:00",
                                               "spot_markets": 1}})
    assert (env / "poll_status.json").read_text(encoding="utf-8") == before


def test_event_log_reports_carry_digest_window_and_markets(env, monkeypatch):
    seed(env / "snaps", spot(100), "binance")
    serve_each(monkeypatch, {"binance": FakeExchange(spot(99))})
    assert cli.poll(None, ["binance"]) == 0
    [event_file] = list((env / "events").glob("*.json"))
    [report] = json.loads(event_file.read_text(encoding="utf-8"))
    assert report["event_type"] == "DELISTING"
    assert len(report["snapshot_digest"]) == 12
    assert datetime.fromisoformat(report["old_snapshot_at"]) <= datetime.fromisoformat(report["observed_at"])
    assert report["spot_markets"] == 99


def test_exchange_flag_polls_exactly_the_listed_exchanges(env, monkeypatch):
    asked: list = []
    serve_each(monkeypatch, {e: FakeExchange(spot(3)) for e in ("binance", "bybit", "coinbase")}, asked)
    assert cli.main(["poll", "--exchange", "binance", "--exchange", "bybit", "--exchange", "coinbase"]) == 0
    assert asked == ["binance", "bybit", "coinbase"]               # the default --limit 2 must not cut the list


def test_poll_survives_an_unwritable_status_file(env, monkeypatch):
    serve_each(monkeypatch, {"binance": FakeExchange(spot(3))})

    def boom(*a, **k):
        raise OSError("read-only")

    monkeypatch.setattr(poll_status, "write_poll_status", boom)
    assert cli.poll(None, ["binance"]) == 0            # a status-file problem must not fail the poll itself


# ---- found by the first live run: bybit unreachable made the whole A015 job "fail" -------------------------

def test_partial_ok_exit_code(env, monkeypatch):
    # one unreachable exchange must not make the supervisor back off from the healthy ones;
    # its failure is still recorded per exchange in poll_status (and flagged stale on the bus)
    serve_each(monkeypatch, {"binance": FakeExchange(spot(3)), "okx": FakeExchange(exc=RuntimeError("down"))})
    argv = ["poll", "--exchange", "binance", "--exchange", "okx"]
    assert cli.main(argv) == 1
    assert cli.main(argv + ["--partial-ok"]) == 0
    assert status_file(env)["okx"]["ok"] is False


def test_partial_ok_still_fails_when_every_exchange_failed(env, monkeypatch):
    serve_each(monkeypatch, {"binance": FakeExchange(exc=RuntimeError("a")), "okx": FakeExchange(exc=RuntimeError("b"))})
    assert cli.main(["poll", "--exchange", "binance", "--exchange", "okx", "--partial-ok"]) == 1
