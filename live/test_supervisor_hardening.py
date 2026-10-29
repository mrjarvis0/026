"""Phase 0 hardening of the live supervisor — each test names the defect it guards.

    python -m pytest live/test_supervisor_hardening.py -q
"""
from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime, timedelta

import pytest

from live import supervisor as sup

NOW = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(sup, "STATE_FILE", tmp_path / "state.json")
    monkeypatch.setattr(sup, "LOG_FILE", tmp_path / "supervisor.log")
    monkeypatch.setattr(sup, "refresh_events", lambda state, now: None)  # no agent calls


@pytest.fixture
def quiet_bus(monkeypatch):
    """The older tick tests are about A001/A002; keep the A015 + bus jobs out of them."""
    monkeypatch.setattr(sup, "a015_poll", lambda: True)
    monkeypatch.setattr(sup, "bus_cycle", lambda: True)


# ---- run() reports the outcome -----------------------------------------------------

def test_run_reports_success_and_failure():
    # regression: run() returned nothing, so a failed or timed-out job was stamped as done
    assert sup.run(["json.tool", "--help"], "ok") is True
    assert sup.run(["no_such_module_xyz"], "bad") is False


def test_run_reports_timeout_as_failure(monkeypatch):
    def hang(*a, **k):
        raise subprocess.TimeoutExpired(cmd="x", timeout=1)

    monkeypatch.setattr(sup.subprocess, "run", hang)
    assert sup.run(["json.tool"], "slow") is False


# ---- tick(): failures back off instead of being stamped as success ----------------

def _fresh():
    return sup.load_state()


def test_failed_job_is_not_stamped_and_backs_off(monkeypatch, quiet_bus):
    calls = []
    monkeypatch.setattr(sup, "a001_ingest", lambda: calls.append("a001") or False)
    monkeypatch.setattr(sup, "a002_scan", lambda: True)
    state = _fresh()
    sup.tick(state, NOW, clock=lambda: NOW)
    assert state["a001_last"] is None            # not stamped: it failed
    assert state["a001_fails"] == 1 and state["a001_retry_at"] > NOW.isoformat()
    sup.tick(state, NOW + timedelta(seconds=1), clock=lambda: NOW)
    assert calls == ["a001"]                      # not hammered again before retry_at


def test_retry_happens_after_backoff_and_success_resets(monkeypatch, quiet_bus):
    results = iter([False, True])
    monkeypatch.setattr(sup, "a001_ingest", lambda: next(results))
    monkeypatch.setattr(sup, "a002_scan", lambda: True)
    state = _fresh()
    sup.tick(state, NOW, clock=lambda: NOW)
    later = datetime.fromisoformat(state["a001_retry_at"]) + timedelta(seconds=1)
    sup.tick(state, later, clock=lambda: later)
    assert state["a001_last"] == later.isoformat()
    assert state["a001_fails"] == 0 and state["a001_retry_at"] is None


def test_backoff_is_capped_and_jittered():
    assert sup.backoff_sec(1, rnd=lambda: 0.0) == sup.BACKOFF_BASE_SEC / 2
    assert sup.backoff_sec(1, rnd=lambda: 1.0) == sup.BACKOFF_BASE_SEC
    assert sup.backoff_sec(50, rnd=lambda: 1.0) == sup.BACKOFF_CAP_SEC


def test_event_run_counts_only_when_a_job_succeeded(monkeypatch):
    monkeypatch.setattr(sup, "a001_ingest", lambda: False)
    monkeypatch.setattr(sup, "a002_scan", lambda: False)
    when = NOW + timedelta(minutes=1)
    state = _fresh()
    state["events"]["k"] = {"when": when.isoformat(), "matched": "t", "runs_done": 0,
                            "next_run": when.isoformat()}
    sup.process_events(state, when)
    assert state["events"]["k"]["runs_done"] == 0
    assert datetime.fromisoformat(state["events"]["k"]["next_run"]) > when


# ---- single instance -------------------------------------------------------------

def test_lock_is_exclusive(tmp_path):
    # regression: nothing stopped 5 supervisors starting within 37s (see supervisor.log)
    path = tmp_path / "supervisor.lock"
    first = sup.acquire_lock(path)
    assert first is not None
    assert sup.acquire_lock(path) is None
    first.close()
    again = sup.acquire_lock(path)
    assert again is not None
    again.close()


# ---- state file ------------------------------------------------------------------

def test_failed_save_leaves_the_previous_state_intact(monkeypatch):
    # regression: write_text() truncated state.json in place, so a crash mid-write lost it
    sup.STATE_FILE.write_text(json.dumps({"a001_last": "keep-me"}), encoding="utf-8")

    def boom(*a, **k):
        raise OSError("disk full")

    monkeypatch.setattr(sup.os, "replace", boom)
    sup.save_state({"a001_last": "new"})
    assert json.loads(sup.STATE_FILE.read_text(encoding="utf-8"))["a001_last"] == "keep-me"


def test_corrupt_state_is_kept_for_inspection_not_silently_reset():
    sup.STATE_FILE.write_text("{not json", encoding="utf-8")
    state = sup.load_state()
    assert state["a001_last"] is None and state["events"] == {}
    assert list(sup.STATE_FILE.parent.glob("state.json.corrupt*"))


def test_old_state_files_without_new_keys_still_load():
    sup.STATE_FILE.write_text(json.dumps({"a001_last": "x", "a002_last": "y", "events": {}}),
                              encoding="utf-8")
    state = sup.load_state()
    assert state["a001_last"] == "x" and state["a001_fails"] == 0 and "heartbeat" in state


# ---- heartbeat -------------------------------------------------------------------

def test_heartbeat_flags_a_dead_supervisor():
    # regression: the supervisor sat dead for 8 days and nothing noticed
    assert sup.is_stale({"heartbeat": None}, NOW) is True
    fresh = {"heartbeat": (NOW - timedelta(seconds=60)).isoformat()}
    assert sup.is_stale(fresh, NOW) is False
    old = {"heartbeat": (NOW - timedelta(seconds=sup.HEARTBEAT_STALE_SEC + 1)).isoformat()}
    assert sup.is_stale(old, NOW) is True


def test_tick_records_a_heartbeat(monkeypatch, quiet_bus):
    monkeypatch.setattr(sup, "a001_ingest", lambda: True)
    monkeypatch.setattr(sup, "a002_scan", lambda: True)
    state = _fresh()
    sup.tick(state, NOW, clock=lambda: NOW)
    assert state["heartbeat"] == NOW.isoformat()


# ---- A015 poll + relay/consume jobs (Phase 1) --------------------------------------------

def test_a015_command_lists_all_configured_exchanges(monkeypatch):
    # the default A015 `--limit 2` would silently poll only half the list
    calls = []
    monkeypatch.setattr(sup, "run", lambda args, label, **k: calls.append(args) or True)
    assert sup.a015_poll() is True
    [args] = calls
    assert args[0] == "agents.A015_Exchange_Listing_Delisting_Intelligence.cli" and args[1] == "poll"
    exchanges = [args[i + 1] for i, a in enumerate(args) if a == "--exchange"]
    assert exchanges == sup.load_bus_config()["a015_exchanges"] and len(exchanges) == 4
    assert "--partial-ok" in args      # one unreachable exchange must not fail the whole job


def test_bus_cycle_runs_relay_then_consume_even_if_relay_fails(monkeypatch):
    calls = []

    def fake_run(args, label, **k):
        calls.append(args[0])
        return args[0] != "bootstrap.relay"

    monkeypatch.setattr(sup, "run", fake_run)
    assert sup.bus_cycle() is False
    assert calls == ["bootstrap.relay", "bootstrap.consume"]


def test_a015_runs_on_its_own_cadence(monkeypatch):
    polls, cycles = [], []
    monkeypatch.setattr(sup, "a001_ingest", lambda: True)
    monkeypatch.setattr(sup, "a002_scan", lambda: True)
    monkeypatch.setattr(sup, "a015_poll", lambda: polls.append(1) or True)
    monkeypatch.setattr(sup, "bus_cycle", lambda: cycles.append(1) or True)
    state = _fresh()
    sup.tick(state, NOW, clock=lambda: NOW)
    soon = NOW + timedelta(minutes=2)
    sup.tick(state, soon, clock=lambda: soon)                       # neither a015 nor the 5-minute bus cycle is due
    later = NOW + timedelta(minutes=sup.A015_EVERY_MIN + 1)
    sup.tick(state, later, clock=lambda: later)
    assert sup.BUS_EVERY_MIN == 5
    assert len(polls) == 2 and len(cycles) == 2


def test_failed_a015_does_not_block_the_bus_cycle(monkeypatch):
    cycles = []
    monkeypatch.setattr(sup, "a001_ingest", lambda: True)
    monkeypatch.setattr(sup, "a002_scan", lambda: True)
    monkeypatch.setattr(sup, "a015_poll", lambda: False)
    monkeypatch.setattr(sup, "bus_cycle", lambda: cycles.append(1) or True)
    state = _fresh()
    sup.tick(state, NOW, clock=lambda: NOW)
    assert state["a015_fails"] == 1 and state["a015_last"] is None
    assert cycles == [1] and state["bus_last"] == NOW.isoformat()


def test_old_state_gains_a015_and_bus_keys():
    sup.STATE_FILE.write_text(json.dumps({"a001_last": "x", "a002_last": "y", "events": {}}), encoding="utf-8")
    state = sup.load_state()
    assert state["a015_last"] is None and state["a015_fails"] == 0
    assert state["bus_last"] is None and state["bus_retry_at"] is None


def test_missing_bus_config_falls_back_to_defaults(tmp_path):
    cfg = sup.load_bus_config(tmp_path / "nope.json")
    assert cfg["a015_exchanges"] == ["binance", "bybit", "coinbase", "okx"] and cfg["a015_every_min"] == 15
