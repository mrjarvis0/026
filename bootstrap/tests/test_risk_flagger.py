"""Slice 2a: A015 events -> pause flags file (+ audit events). T01 is not involved (design 2026-10-29).

The flags only ever say "do not open NEW entries on this market"; nothing here can enable or loosen anything.
"""
import json
from datetime import datetime, timedelta

import pytest

from bootstrap import flags as flags_cli
from bootstrap import risk_flags
from bootstrap.consumers import risk_flagger
from orchestrator.event_bus.store import EventStore
from orchestrator.event_bus.tests.helpers import MANIFESTS, FakeClock, event_n, sample_event

SUBJECT = "market:binance:XYZ/USDT"


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def store(tmp_path, clock):
    return EventStore(tmp_path / "bus.db", manifests=MANIFESTS, clock=clock)


@pytest.fixture
def path(tmp_path):
    return tmp_path / "risk" / "pause_flags.json"


def delisted(n=1, exchange="binance", symbol="XYZ/USDT"):
    return sample_event(event_id=f"evt_{n:016x}", trace_id=f"trc_{n:016x}", subject=f"market:{exchange}:{symbol}",
                        data={"exchange": exchange, "symbol": symbol, "base": symbol.split("/")[0],
                              "stated_reason": "unspecified"})


def status(n, to, exchange="binance", symbol="XYZ/USDT"):
    return sample_event(event_id=f"evt_{n:016x}", trace_id=f"trc_{n:016x}", type="a015.market.status_changed",
                        subject=f"market:{exchange}:{symbol}", detector={"id": "STATUS_CHANGE", "maturity": "implemented", "ceiling": None},
                        data={"exchange": exchange, "symbol": symbol, "status_from": "TRADING", "status_to": to})


def listed(n, exchange="binance", symbol="XYZ/USDT"):
    return sample_event(event_id=f"evt_{n:016x}", trace_id=f"trc_{n:016x}", type="a015.listing.new", detector=None,
                        subject=f"market:{exchange}:{symbol}",
                        data={"exchange": exchange, "symbol": symbol, "base": symbol.split("/")[0]})


def run(store, path):
    return risk_flagger.run_once(store, path)


def flags(path):
    return risk_flags.load_flags(path)


def audit(store, kind):
    return store.read(types=[f"system.risk.{kind}"])


# ---- rules ------------------------------------------------------------------------------------------------

def test_a_delisting_sets_a_flag_with_no_expiry_and_an_audit_event(store, path):
    store.publish(delisted(1))
    run(store, path)
    flag = flags(path)[SUBJECT]
    assert flag["expires_at"] is None and flag["event_id"] == delisted(1)["event_id"]
    assert flag["maturity"] == "implemented" and "delist" in flag["reason"]
    [ev] = audit(store, "flag_set")
    assert ev["source"] == "SYS" and ev["causation_id"] == delisted(1)["event_id"] and ev["data"]["subject"] == SUBJECT


def test_break_sets_a_24h_flag_and_trading_clears_it(store, path, clock):
    store.publish(status(1, "BREAK"))
    run(store, path)
    expires = datetime.fromisoformat(flags(path)[SUBJECT]["expires_at"])
    assert expires == clock() + timedelta(hours=24)
    store.publish(status(2, "TRADING"))
    run(store, path)
    assert SUBJECT not in flags(path) and len(audit(store, "flag_cleared")) == 1


def test_a_new_listing_clears_the_flag(store, path):
    store.publish(delisted(1))
    store.publish(listed(2))
    run(store, path)
    assert SUBJECT not in flags(path)


def test_other_exchanges_are_ignored(store, path):
    store.publish(delisted(1, exchange="okx"))
    run(store, path)
    assert flags(path) == {} and audit(store, "flag_set") == []


def test_a_later_break_never_shortens_a_no_expiry_flag(store, path):
    store.publish(delisted(1))
    store.publish(status(2, "BREAK"))
    run(store, path)
    assert flags(path)[SUBJECT]["expires_at"] is None


def test_halt_is_treated_like_break(store, path):
    store.publish(status(1, "HALT"))
    run(store, path)
    assert SUBJECT in flags(path)


# ---- idempotency / durability --------------------------------------------------------------------------------

def test_redelivery_changes_nothing_and_adds_no_second_audit_event(store, path):
    store.publish(delisted(1))
    run(store, path)
    before = path.read_text(encoding="utf-8")
    import sqlite3
    sqlite3.connect(store.db_path).execute("UPDATE consumers SET cursor = 0").connection.commit()
    run(store, path)
    assert path.read_text(encoding="utf-8") == before and len(audit(store, "flag_set")) == 1


def test_a_failed_file_write_is_retried_and_the_audit_is_not_duplicated(store, path, monkeypatch):
    store.publish(delisted(1))
    real = risk_flags.save_flags
    monkeypatch.setattr(risk_flags, "save_flags", lambda *a, **k: (_ for _ in ()).throw(OSError("disk full")))
    stats = run(store, path)
    assert stats.failed == 1 and not path.exists()
    monkeypatch.setattr(risk_flags, "save_flags", real)
    import sqlite3
    sqlite3.connect(store.db_path).execute("UPDATE attempts SET next_at = '2000-01-01T00:00:00+00:00'").connection.commit()
    run(store, path)
    assert SUBJECT in flags(path) and len(audit(store, "flag_set")) == 1


def test_the_file_is_written_atomically(path, monkeypatch):
    risk_flags.save_flags(path, {SUBJECT: {"reason": "a"}})
    before = path.read_text(encoding="utf-8")
    monkeypatch.setattr(risk_flags.os, "replace", lambda *a, **k: (_ for _ in ()).throw(OSError("boom")))
    with pytest.raises(OSError):
        risk_flags.save_flags(path, {SUBJECT: {"reason": "b"}})
    assert path.read_text(encoding="utf-8") == before


def test_missing_or_corrupt_file_reads_as_no_flags(path):
    assert risk_flags.load_flags(path) == {}
    path.parent.mkdir(parents=True)
    path.write_text("{torn", encoding="utf-8")
    assert risk_flags.load_flags(path) == {}


def test_expired_flags_are_not_active():
    now = datetime.fromisoformat("2026-10-29T12:00:00+00:00")
    flags_ = {"a": {"expires_at": "2026-10-29T11:00:00+00:00"}, "b": {"expires_at": "2026-10-29T13:00:00+00:00"},
              "c": {"expires_at": None}}
    assert set(risk_flags.active_flags(flags_, now)) == {"b", "c"}


# ---- operator CLI ------------------------------------------------------------------------------------------------

def test_cli_set_list_clear_roundtrip_with_audit(store, path, tmp_path, capsys):
    db = str(tmp_path / "bus.db")
    assert flags_cli.main(["set", SUBJECT, "--hours", "2", "--reason", "drill", "--db", db, "--file", str(path)]) == 0
    assert SUBJECT in flags(path)
    flags_cli.main(["list", "--file", str(path)])
    assert SUBJECT in capsys.readouterr().out
    assert flags_cli.main(["clear", SUBJECT, "--db", db, "--file", str(path)]) == 0
    assert flags(path) == {}
    assert audit(store, "flag_set")[0]["data"]["by"] == "operator" and len(audit(store, "flag_cleared")) == 1


def test_cli_clear_of_an_unknown_subject_fails(tmp_path, path):
    assert flags_cli.main(["clear", "market:binance:NOPE/USDT", "--db", str(tmp_path / "b.db"), "--file", str(path)]) == 1


def test_consume_cli_runs_the_flagger_after_the_librarian(tmp_path, path, capsys):
    from bootstrap import consume
    db = EventStore(tmp_path / "bus.db", manifests=MANIFESTS)
    db.publish(delisted(1))
    db.close()
    rc = consume.main(["--once", "--db", str(tmp_path / "bus.db"), "--brain", str(tmp_path / "brain.db"),
                       "--flags", str(path)])
    assert rc == 0 and SUBJECT in flags(path)
    assert "risk_flagger: delivered" in capsys.readouterr().out


def test_consume_without_flags_option_never_writes_the_live_file(tmp_path):
    """Regression: wiring the flagger into bootstrap.consume made older CLI tests write data/risk/."""
    from bootstrap import consume
    live = risk_flags.FLAGS_FILE
    assert "isolated" in live.parts                       # conftest redirected it
    db = EventStore(tmp_path / "bus.db", manifests=MANIFESTS)
    db.publish(delisted(1))
    db.close()
    consume.main(["--once", "--db", str(tmp_path / "bus.db"), "--brain", str(tmp_path / "brain.db")])
    assert SUBJECT in risk_flags.load_flags(live)
