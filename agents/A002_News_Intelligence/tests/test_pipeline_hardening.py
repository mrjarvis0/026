"""Phase 0 pipeline hardening — each test names the defect it guards.

Run: pytest agents/A002_News_Intelligence/tests/test_pipeline_hardening.py -q   (no network)
"""
import asyncio
import sqlite3
import urllib.error
from datetime import UTC, datetime

import pytest

from agents.A002_News_Intelligence.core import fetch
from agents.A002_News_Intelligence.core.normalize import parse_timestamp
from agents.A002_News_Intelligence.core.storage import Storage


# ---- timestamps ---------------------------------------------------------------------

def test_rss_rfc822_dates_are_parsed():
    # regression: RSS pubDate is RFC-822, parse_timestamp was ISO-only -> None -> the item's
    # published_at silently became the fetch time (corrupting first_seen / velocity)
    assert parse_timestamp("Tue, 27 Oct 2026 10:00:00 GMT") == datetime(2026, 10, 27, 10, 0, tzinfo=UTC)
    assert parse_timestamp("Tue, 27 Oct 2026 15:30:00 +0530") == datetime(2026, 10, 27, 10, 0, tzinfo=UTC)


def test_iso_and_garbage_still_behave():
    assert parse_timestamp("2026-01-05T10:00:00Z") == datetime(2026, 1, 5, 10, 0, tzinfo=UTC)
    assert parse_timestamp("not-a-date") is None
    assert parse_timestamp(None) is None


def test_rss_item_keeps_its_publish_time_not_the_fetch_time(monkeypatch):
    xml = (b"<rss><channel><item><title>Fed holds</title><link>http://x/1</link>"
           b"<pubDate>Tue, 27 Oct 2026 10:00:00 GMT</pubDate></item></channel></rss>")
    monkeypatch.setattr(fetch, "http_get_sync", lambda url, **k: xml)
    [item] = fetch.fetch_rss_sync("rss_test", "http://x/feed", 10, 5.0)
    assert item.published_at == datetime(2026, 10, 27, 10, 0, tzinfo=UTC)


# ---- secrets never reach the error report / logs ---------------------------------------

def _boom_connector(message):
    def boom():
        raise ValueError(message)
    return [("tiingo", None, boom)]


def test_connector_errors_do_not_leak_api_keys(monkeypatch):
    # regression: keys live in URL query strings; an exception quoting the URL went to
    # report.errors, was printed by `scan`, and landed in live/supervisor.log
    monkeypatch.setattr(fetch, "_all_connectors", lambda s: _boom_connector(
        "bad url /tiingo/news?token=SECRET123&limit=5 and ?apiKey=SECRET456&x=1 "
        "and /bot12345:SECRET789-abc/getUpdates"))
    _, errors = asyncio.run(fetch.fetch_all(settings=None))
    text = " ".join(errors)
    assert errors and "tiingo" in text
    for secret in ("SECRET123", "SECRET456", "SECRET789"):
        assert secret not in text


def test_redaction_leaves_ordinary_text_alone():
    assert fetch.redact_secrets("HTTP Error 503: Service Unavailable") == "HTTP Error 503: Service Unavailable"


# ---- transient failures are retried, permanent ones are not -----------------------------

class _Resp:
    def __init__(self, body):
        self.body = body

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _http_error(code):
    return urllib.error.HTTPError("http://x", code, "err", {}, None)


def test_transient_errors_are_retried_with_backoff(monkeypatch):
    outcomes = iter([_http_error(503), urllib.error.URLError("reset"), _Resp(b"ok")])
    calls, sleeps = [], []

    def fake_urlopen(req, timeout):
        calls.append(1)
        out = next(outcomes)
        if isinstance(out, Exception):
            raise out
        return out

    monkeypatch.setattr(fetch.urllib.request, "urlopen", fake_urlopen)
    assert fetch.http_get_sync("http://x", sleep=sleeps.append) == b"ok"
    assert len(calls) == 3 and len(sleeps) == 2
    assert all(0 <= s <= 8.0 for s in sleeps)           # capped + jittered


def test_permanent_errors_are_not_retried(monkeypatch):
    calls = []

    def fake_urlopen(req, timeout):
        calls.append(1)
        raise _http_error(404)

    monkeypatch.setattr(fetch.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(urllib.error.HTTPError):
        fetch.http_get_sync("http://x", sleep=lambda s: None)
    assert len(calls) == 1


def test_retries_are_bounded(monkeypatch):
    calls = []

    def fake_urlopen(req, timeout):
        calls.append(1)
        raise _http_error(503)

    monkeypatch.setattr(fetch.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(urllib.error.HTTPError):
        fetch.http_get_sync("http://x", retries=2, sleep=lambda s: None)
    assert len(calls) == 3


# ---- concurrent access ---------------------------------------------------------------

def test_database_uses_wal_so_readers_do_not_block_the_scan(tmp_path):
    # regression: a002.db was in rollback-journal mode while the supervisor scan wrote and
    # the bus adapter / dashboard read the same file
    db = tmp_path / "a002.db"
    asyncio.run(Storage(db).init())
    assert sqlite3.connect(db).execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
