"""The durable event store: one SQLite (WAL) file, stdlib only (ADR-0005, design spec section 8).

Append-only ``events`` with a never-reused ``seq``; per-consumer cursors, retry/park state, source
health (coverage proof), relay high-water marks, the persisted bus trace and the approval queue
all live in the same file. Every call opens its own short-lived connection (WAL: readers don't
block the single writer; keep write transactions tiny).
"""
from __future__ import annotations

import json
import os
import random
import sqlite3
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .envelope import canonical_json, load_schemas, passes_maturity, type_matches, validate_event

DEFAULT_DB = Path(__file__).resolve().parents[2] / "data" / "bus" / "bus.db"
SCHEMA_VERSION = 1

_DDL = """
CREATE TABLE IF NOT EXISTS events (
  seq INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id TEXT NOT NULL UNIQUE,
  type TEXT NOT NULL, source TEXT NOT NULL, subject TEXT NOT NULL,
  maturity TEXT, schema_version INTEGER NOT NULL,
  published_at TEXT NOT NULL, envelope TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS events_type ON events(type, seq);
CREATE INDEX IF NOT EXISTS events_subject ON events(subject, seq);
CREATE TRIGGER IF NOT EXISTS events_immutable BEFORE UPDATE ON events
  BEGIN SELECT RAISE(ABORT, 'events are immutable'); END;
CREATE TABLE IF NOT EXISTS consumers (name TEXT PRIMARY KEY, cursor INTEGER NOT NULL DEFAULT 0, updated_at TEXT);
CREATE TABLE IF NOT EXISTS attempts (consumer TEXT, seq INTEGER, n INTEGER, last_error TEXT, next_at TEXT,
  PRIMARY KEY (consumer, seq));
CREATE TABLE IF NOT EXISTS parked (consumer TEXT, seq INTEGER, attempts INTEGER, last_error TEXT, parked_at TEXT,
  PRIMARY KEY (consumer, seq));
CREATE TABLE IF NOT EXISTS source_health (source TEXT PRIMARY KEY, last_attempt_at TEXT, last_ok_at TEXT,
  ok INTEGER, detail TEXT);
CREATE TABLE IF NOT EXISTS relay_state (relay TEXT, key TEXT, value TEXT, PRIMARY KEY (relay, key));
CREATE TABLE IF NOT EXISTS trace (id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT, kind TEXT, msg_id TEXT,
  trace_id TEXT, sender TEXT, recipient TEXT, type TEXT, reason TEXT);
CREATE INDEX IF NOT EXISTS trace_trace_id ON trace(trace_id, id);
CREATE TABLE IF NOT EXISTS approvals (id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT, trace_id TEXT, msg_id TEXT,
  to_agent TEXT, action_json TEXT, reason TEXT, status TEXT NOT NULL DEFAULT 'pending',
  decided_at TEXT, decided_by TEXT);
PRAGMA user_version = 1;
"""


BACKOFF_BASE_SEC = 5.0     # consumer retry spacing: capped exponential + equal jitter
BACKOFF_CAP_SEC = 300.0


def backoff_sec(attempt: int, rnd=random.random) -> float:
    delay = min(BACKOFF_CAP_SEC, BACKOFF_BASE_SEC * 2 ** (attempt - 1))
    return delay / 2 + rnd() * delay / 2


@dataclass
class ConsumeStats:
    delivered: int = 0
    skipped_other_type: int = 0
    skipped_low_maturity: int = 0
    failed: int = 0
    parked: int = 0
    last_seq: int = 0


class StoreBusy(RuntimeError):
    """Another writer held the database longer than ``busy_timeout_ms``; nothing was written."""


class EventStore:
    def __init__(self, db_path=DEFAULT_DB, *, schemas=None, manifests=None, clock=None, rnd=None,
                 busy_timeout_ms: int = 5000) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.schemas = schemas if schemas is not None else load_schemas()
        self.manifests = manifests or {}
        self._clock = clock or (lambda: datetime.now(UTC))
        self._rnd = rnd or random.random
        self._busy_ms = busy_timeout_ms
        self._lock = threading.RLock()
        self._shared: sqlite3.Connection | None = None
        with self._conn() as conn:
            if conn.execute("PRAGMA user_version").fetchone()[0] < SCHEMA_VERSION:
                conn.executescript(_DDL)

    # ---- plumbing ---------------------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        """One long-lived connection per store. Closing the last WAL connection checkpoints and
        fsyncs, which made every call cost ~400 ms on a slow disk (first live run, 2026-10-28)."""
        if self._shared is None:
            conn = sqlite3.connect(self.db_path, timeout=self._busy_ms / 1000, isolation_level=None,
                                   check_same_thread=False)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(f"PRAGMA busy_timeout={self._busy_ms}")
            conn.execute("PRAGMA synchronous=NORMAL")
            self._shared = conn
        return self._shared

    def _conn(self):
        return _Locked(self)

    def close(self) -> None:
        with self._lock:
            if self._shared is not None:
                self._shared.close()
                self._shared = None

    def now(self) -> datetime:
        return self._clock()

    def _write(self, fn):
        """Run ``fn(conn)`` inside BEGIN IMMEDIATE ... COMMIT; a held lock becomes StoreBusy."""
        with self._lock:
            conn = self._connect()
            try:
                conn.execute("BEGIN IMMEDIATE")
                try:
                    result = fn(conn)
                    conn.execute("COMMIT")
                    return result
                except BaseException:
                    if conn.in_transaction:
                        conn.execute("ROLLBACK")
                    raise
            except sqlite3.OperationalError as exc:
                if "locked" in str(exc) or "busy" in str(exc):
                    raise StoreBusy(f"{self.db_path.name} is locked by another writer") from exc
                raise

    # ---- events -----------------------------------------------------------------------

    def validate(self, event: dict) -> None:
        """Raise EnvelopeError if the event would be refused; stores nothing."""
        validate_event(event, self.schemas, self.manifests)

    def _row(self, event: dict) -> tuple:
        self.validate(event)
        stored = {**event, "published_at": self.now().isoformat()}
        return (stored["event_id"], stored["type"], stored["source"], stored["subject"],
                (stored.get("detector") or {}).get("maturity"), stored["schema_version"],
                stored["published_at"], canonical_json(stored))

    def publish_many(self, events: list[dict]) -> list[tuple[int, bool]]:
        """Validate every event first (one bad event writes nothing), then append them all in ONE
        transaction. Returns (seq, duplicate) per event; a repeated event_id is a no-op."""
        rows = [self._row(e) for e in events]
        if not rows:
            return []

        def append_all(conn):
            out = []
            for row in rows:
                cur = conn.execute(
                    "INSERT OR IGNORE INTO events (event_id, type, source, subject, maturity, schema_version,"
                    " published_at, envelope) VALUES (?,?,?,?,?,?,?,?)", row)
                if cur.rowcount == 1:
                    out.append((cur.lastrowid, False))
                else:
                    out.append((conn.execute("SELECT seq FROM events WHERE event_id = ?", (row[0],)).fetchone()[0], True))
            return out

        return self._write(append_all)

    def publish(self, event: dict) -> tuple[int, bool]:
        """Validate and append one event. Returns (seq, duplicate)."""
        return self.publish_many([event])[0]

    def read(self, after_seq: int = 0, limit: int = 100, types: list[str] | None = None) -> list[dict]:
        """Events after ``after_seq`` in seq order, optionally only ``types`` (patterns allowed)."""
        out: list[dict] = []
        with self._conn() as conn:
            for seq, envelope in conn.execute(
                    "SELECT seq, envelope FROM events WHERE seq > ? ORDER BY seq", (after_seq,)):
                event = json.loads(envelope)
                if types is not None and not any(type_matches(p, event["type"]) for p in types):
                    continue
                out.append({**event, "seq": seq})
                if len(out) >= limit:
                    break
        return out


    # ---- delivery (spec section 9) -------------------------------------------------------

    def consume(self, name: str, handler: Callable[[dict], None], *, types: list[str],
                min_maturity: str = "validated", batch: int = 50, max_attempts: int = 5) -> ConsumeStats:
        """Deliver events after this consumer's cursor, in seq order, at-least-once.

        Events of other types or below ``min_maturity`` are skipped (and counted). A failing
        handler stops the batch (order kept) and is retried after a backoff; at ``max_attempts``
        the event is parked and the stream moves on. The handler runs outside any transaction;
        the cursor moves only after it succeeds, so a crash redelivers: handlers must be idempotent.
        """
        stats = ConsumeStats()
        # Register the consumer first: one that never advances (every event failing) must still show
        # up in stats() with its lag, not vanish from the report.
        self._write(lambda conn: conn.execute(
            "INSERT OR IGNORE INTO consumers (name, cursor, updated_at) VALUES (?, 0, ?)",
            (name, self.now().isoformat())))
        with self._conn() as conn:
            row = conn.execute("SELECT cursor FROM consumers WHERE name = ?", (name,)).fetchone()
            cursor = row[0] if row else 0
            rows = conn.execute("SELECT seq, envelope FROM events WHERE seq > ? ORDER BY seq LIMIT ?",
                                (cursor, batch)).fetchall()
            tries = {seq: (n, next_at) for seq, n, next_at in conn.execute(
                "SELECT seq, n, next_at FROM attempts WHERE consumer = ?", (name,))}
        for seq, envelope in rows:
            event = {**json.loads(envelope), "seq": seq}
            if not any(type_matches(p, event["type"]) for p in types):
                stats.skipped_other_type += 1
                self._advance(name, seq)
            elif not passes_maturity(event, min_maturity):
                stats.skipped_low_maturity += 1
                self._advance(name, seq)
            else:
                n_before, next_at = tries.get(seq, (0, None))
                if next_at and self.now() < datetime.fromisoformat(next_at):
                    break                                   # still backing off: order preserved
                try:
                    handler(event)
                except Exception as exc:
                    n = n_before + 1
                    stats.failed += 1
                    err = f"{type(exc).__name__}: {exc}"
                    if n >= max_attempts:
                        self._park(name, seq, n, err)
                        stats.parked += 1
                    else:
                        self._record_failure(name, seq, n, err)
                        break
                else:
                    self._advance(name, seq, clear_attempts=True)
                    stats.delivered += 1
            stats.last_seq = seq
        return stats

    def _advance(self, name: str, seq: int, *, clear_attempts: bool = False) -> None:
        when = self.now().isoformat()

        def w(conn):
            conn.execute("INSERT INTO consumers (name, cursor, updated_at) VALUES (?,?,?) ON CONFLICT(name)"
                         " DO UPDATE SET cursor = excluded.cursor, updated_at = excluded.updated_at",
                         (name, seq, when))
            if clear_attempts:
                conn.execute("DELETE FROM attempts WHERE consumer = ? AND seq = ?", (name, seq))

        self._write(w)

    def _record_failure(self, name: str, seq: int, n: int, err: str) -> None:
        next_at = datetime.fromtimestamp(self.now().timestamp() + backoff_sec(n, self._rnd), UTC).isoformat()
        self._write(lambda conn: conn.execute(
            "INSERT INTO attempts (consumer, seq, n, last_error, next_at) VALUES (?,?,?,?,?)"
            " ON CONFLICT(consumer, seq) DO UPDATE SET n = excluded.n, last_error = excluded.last_error,"
            " next_at = excluded.next_at", (name, seq, n, err, next_at)))

    def _park(self, name: str, seq: int, n: int, err: str) -> None:
        when = self.now().isoformat()

        def w(conn):
            conn.execute("INSERT OR REPLACE INTO parked (consumer, seq, attempts, last_error, parked_at)"
                         " VALUES (?,?,?,?,?)", (name, seq, n, err, when))
            conn.execute("DELETE FROM attempts WHERE consumer = ? AND seq = ?", (name, seq))
            conn.execute("INSERT INTO consumers (name, cursor, updated_at) VALUES (?,?,?) ON CONFLICT(name)"
                         " DO UPDATE SET cursor = excluded.cursor, updated_at = excluded.updated_at",
                         (name, seq, when))

        self._write(w)

    def parked(self, consumer: str | None = None) -> list[dict]:
        sql = "SELECT consumer, seq, attempts, last_error, parked_at FROM parked"
        args: tuple = ()
        if consumer:
            sql, args = sql + " WHERE consumer = ?", (consumer,)
        with self._conn() as conn:
            return [dict(zip(("consumer", "seq", "attempts", "last_error", "parked_at"), r))
                    for r in conn.execute(sql + " ORDER BY seq", args)]

    # ---- source health: the coverage proof for "nothing happened" ---------------------------

    def record_health(self, source: str, *, ok: bool, detail: str = "", at: datetime | None = None) -> None:
        when = (at or self.now()).isoformat()
        self._write(lambda conn: conn.execute(
            "INSERT INTO source_health (source, last_attempt_at, last_ok_at, ok, detail) VALUES (?,?,?,?,?)"
            " ON CONFLICT(source) DO UPDATE SET last_attempt_at = excluded.last_attempt_at,"
            " last_ok_at = COALESCE(excluded.last_ok_at, source_health.last_ok_at),"
            " ok = excluded.ok, detail = excluded.detail",
            (source, when, when if ok else None, int(ok), detail)))

    def health(self, source: str) -> dict | None:
        with self._conn() as conn:
            row = conn.execute("SELECT source, last_attempt_at, last_ok_at, ok, detail FROM source_health"
                               " WHERE source = ?", (source,)).fetchone()
        if row is None:
            return None
        return {"source": row[0], "last_attempt_at": row[1], "last_ok_at": row[2],
                "ok": bool(row[3]), "detail": row[4]}

    def stale_sources(self, sources: list[str], max_age_s: float) -> list[str]:
        """Sources never seen ok, or not ok for longer than ``max_age_s``."""
        stale = []
        for source in sources:
            h = self.health(source)
            if h is None or h["last_ok_at"] is None or (
                    self.now() - datetime.fromisoformat(h["last_ok_at"])).total_seconds() > max_age_s:
                stale.append(source)
        return stale

    # ---- small state, stats, retention ---------------------------------------------------------

    def get_state(self, relay: str, key: str, default: str | None = None) -> str | None:
        with self._conn() as conn:
            row = conn.execute("SELECT value FROM relay_state WHERE relay = ? AND key = ?", (relay, key)).fetchone()
        return row[0] if row else default

    def set_state(self, relay: str, key: str, value: str) -> None:
        self._write(lambda conn: conn.execute(
            "INSERT INTO relay_state (relay, key, value) VALUES (?,?,?) ON CONFLICT(relay, key)"
            " DO UPDATE SET value = excluded.value", (relay, key, value)))

    def stats(self) -> dict:
        with self._conn() as conn:
            head, count = conn.execute("SELECT COALESCE(MAX(seq), 0), COUNT(*) FROM events").fetchone()
            consumers = {n: {"cursor": c, "lag": head - c}
                         for n, c in conn.execute("SELECT name, cursor FROM consumers")}
            parked = conn.execute("SELECT COUNT(*) FROM parked").fetchone()[0]
            names = [r[0] for r in conn.execute("SELECT source FROM source_health ORDER BY source")]
        sources = {name: self.health(name) for name in names}
        return {"events": count, "head_seq": head, "parked": parked, "consumers": consumers, "sources": sources}

    def prune(self, older_than: datetime, archive_to: Path) -> int:
        """Archive (JSONL) then delete events older than ``older_than`` that every consumer has
        passed. The only delete path. Returns the number removed."""
        with self._conn() as conn:
            floor = conn.execute("SELECT MIN(cursor) FROM consumers").fetchone()[0]
            rows = conn.execute("SELECT seq, published_at, envelope FROM events WHERE seq <= ? ORDER BY seq",
                                (floor if floor is not None else 2**62,)).fetchall()
        doomed = [(seq, env) for seq, at, env in rows if datetime.fromisoformat(at) < older_than]
        if not doomed:
            return 0
        archive_to = Path(archive_to)
        archive_to.parent.mkdir(parents=True, exist_ok=True)
        with archive_to.open("a", encoding="utf-8") as fh:
            for _, env in doomed:
                fh.write(env + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        self._write(lambda conn: conn.executemany("DELETE FROM events WHERE seq = ?", [(s,) for s, _ in doomed]))
        with self._conn() as conn:
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        return len(doomed)


    # ---- persisted bus trace and the approval queue (Slice 1b) ---------------------------------

    def record_trace(self, entry: dict) -> None:
        self._write(lambda conn: conn.execute(
            "INSERT INTO trace (at, kind, msg_id, trace_id, sender, recipient, type, reason) VALUES (?,?,?,?,?,?,?,?)",
            (entry.get("at"), entry.get("kind"), entry.get("id"), entry.get("trace_id"), entry.get("from"),
             entry.get("to"), entry.get("type"), entry.get("reason"))))

    def trace_for(self, trace_id: str) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute("SELECT at, kind, msg_id, trace_id, sender, recipient, type, reason FROM trace"
                                " WHERE trace_id = ? ORDER BY id", (trace_id,)).fetchall()
        return [{"at": at, "kind": kind, "id": msg_id, "trace_id": tid, "from": sender, "to": to,
                 "type": type_, "reason": reason} for at, kind, msg_id, tid, sender, to, type_, reason in rows]

    def hold(self, message: dict, reason: str) -> int:
        """Queue a held action for the operator; returns the approval id."""
        return self._write(lambda conn: conn.execute(
            "INSERT INTO approvals (at, trace_id, msg_id, to_agent, action_json, reason, status)"
            " VALUES (?,?,?,?,?,?, 'pending')",
            (self.now().isoformat(), message.get("trace_id"), message.get("id"), message.get("to"),
             json.dumps(message.get("action")), reason)).lastrowid)

    def pending_approvals(self) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute("SELECT id, at, trace_id, msg_id, to_agent, action_json, reason, status"
                                " FROM approvals WHERE status = 'pending' ORDER BY id").fetchall()
        return [{"id": i, "at": at, "trace_id": tid, "msg_id": mid, "to_agent": to,
                 "action": json.loads(action) if action else None, "reason": reason, "status": status}
                for i, at, tid, mid, to, action, reason, status in rows]

    def decide(self, approval_id: int, approved: bool, by: str) -> bool:
        """Approve or reject a pending item. False if it is unknown or already decided."""
        return self._write(lambda conn: conn.execute(
            "UPDATE approvals SET status = ?, decided_at = ?, decided_by = ? WHERE id = ? AND status = 'pending'",
            ("approved" if approved else "rejected", self.now().isoformat(), by, approval_id)).rowcount == 1)


class _Locked:
    """``with store._conn() as c``: the store's shared connection, under the store's lock."""

    def __init__(self, store: EventStore) -> None:
        self.store = store

    def __enter__(self) -> sqlite3.Connection:
        self.store._lock.acquire()
        return self.store._connect()

    def __exit__(self, *exc) -> None:
        self.store._lock.release()
