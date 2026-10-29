"""The brain's storage: versioned writes + logged reads over namespaced records.

Backed by stdlib sqlite3 (no new dependency). A write never overwrites — it appends a
new version — and every read is recorded, because in 026 nothing about the shared memory
is silent (AGENTS.md §7).
"""
from __future__ import annotations

import json
import re
import sqlite3
import time
from typing import Any

# Valid namespaces: bare agent/shared tokens (global, entities, chain, news, ...) or a
# scoped `projects/<id>` / `private/<agent>`.
_SINGLE = re.compile(r"^[a-z][a-z0-9_]*$")
_SCOPED = re.compile(r"^(projects|private)/[A-Za-z0-9_.-]+$")


def valid_namespace(namespace: str) -> bool:
    return bool(_SINGLE.match(namespace) or _SCOPED.match(namespace))


class Brain:
    def __init__(self, db_path: str = ":memory:") -> None:
        self._db = sqlite3.connect(db_path)
        if db_path != ":memory:":   # WAL: no fsync per commit, and readers (dashboard) don't block the writer
            self._db.execute("PRAGMA journal_mode=WAL")
            self._db.execute("PRAGMA synchronous=NORMAL")
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS records ("
            " namespace TEXT, key TEXT, version INTEGER, value_json TEXT,"
            " written_by TEXT, written_at REAL,"
            " PRIMARY KEY (namespace, key, version))")
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS read_log ("
            " namespace TEXT, key TEXT, read_by TEXT, read_at REAL)")
        self._db.commit()

    def write(self, namespace: str, key: str, value: Any, *, by: str) -> int:
        if not valid_namespace(namespace):
            raise ValueError(f"invalid namespace {namespace!r}")
        row = self._db.execute(
            "SELECT COALESCE(MAX(version), 0) FROM records WHERE namespace=? AND key=?",
            (namespace, key)).fetchone()
        version = int(row[0]) + 1
        self._db.execute(
            "INSERT INTO records VALUES (?,?,?,?,?,?)",
            (namespace, key, version, json.dumps(value), by, time.time()))
        self._db.commit()
        return version

    def read(self, namespace: str, key: str, *, by: str) -> Any | None:
        self._db.execute("INSERT INTO read_log VALUES (?,?,?,?)",
                         (namespace, key, by, time.time()))
        self._db.commit()
        row = self._db.execute(
            "SELECT value_json FROM records WHERE namespace=? AND key=?"
            " ORDER BY version DESC LIMIT 1", (namespace, key)).fetchone()
        return json.loads(row[0]) if row else None

    def history(self, namespace: str, key: str) -> list[dict]:
        rows = self._db.execute(
            "SELECT version, value_json, written_by, written_at FROM records"
            " WHERE namespace=? AND key=? ORDER BY version", (namespace, key)).fetchall()
        return [{"version": v, "value": json.loads(vj), "by": b, "at": a}
                for v, vj, b, a in rows]

    def reads_of(self, namespace: str, key: str) -> list[dict]:
        rows = self._db.execute(
            "SELECT read_by, read_at FROM read_log WHERE namespace=? AND key=?"
            " ORDER BY read_at", (namespace, key)).fetchall()
        return [{"by": b, "at": a} for b, a in rows]
