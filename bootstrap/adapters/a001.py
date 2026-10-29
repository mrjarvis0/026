"""A001 Blockchain Intelligence — message-bus adapter (read-only).

Takes a bus Message (duck-typed: only ``.payload`` is read) and returns a plain dict. It
calls A001's own read-only entry point — no network, no data writes, no keys.

Read ops: catalogue (no DB) — detectors, skills, chains; DB-backed reads over the migrated
a001.db — metrics, coverage, flows, labels, health. The op is read from ``intent`` (the
fleet-wide key) or the legacy ``op``.

A001 uses bare top-level imports, so this adapter puts the A001 directory on ``sys.path``
just-in-time (a known wart until A001 is packaged).
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_A001_DIR = _REPO_ROOT / "agents" / "A001_Blockchain_Intelligence"
_A001_DB = _A001_DIR / "data" / "a001.db"

_A001_CATALOGUE = ("detectors", "skills", "chains")
_A001_DB_OPS = ("metrics", "coverage", "flows", "labels", "health")
_A001_CHAIN_OPS = ("coverage", "flows", "labels")


def a001_handler(message) -> dict:
    """Read-only query into A001's IntelligenceService (read-only by construction)."""
    payload = getattr(message, "payload", None) or {}
    op = payload.get("intent") or payload.get("op") or "detectors"
    if op not in _A001_CATALOGUE + _A001_DB_OPS:
        return {"error": f"unknown op {op!r}", "ops": list(_A001_CATALOGUE + _A001_DB_OPS)}
    if str(_A001_DIR) not in sys.path:
        sys.path.insert(0, str(_A001_DIR))
    from interfaces.service import IntelligenceService  # noqa: E402 (path set above)

    db = str(_A001_DB) if (op in _A001_DB_OPS and _A001_DB.exists()) else None
    svc = IntelligenceService(database_path=db)
    if op in _A001_CHAIN_OPS:
        result = getattr(svc, op)(chain=payload.get("chain", "ethereum"))
    else:
        result = getattr(svc, op)()
    return {"op": op, "ok": result.ok, "status": result.status, "data": result.data}
