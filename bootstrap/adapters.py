"""Thin, read-only bus adapters over the real A001 / A002 agents.

Each handler takes a bus Message (duck-typed: only `.payload` is read) and returns a
plain dict. They call the agents' own read-only entry points — no network, no data
writes, no keys.

Read ops exposed:
  A001 — catalogue (no DB): detectors, skills, chains; DB-backed reads over the migrated
        a001.db: metrics, coverage, flows, labels, health.
  A002 — static registry/settings: sources, settings; DB-backed read over a002.db: stats.

A001 uses bare top-level imports, so its adapter puts the A001 directory on `sys.path`
just-in-time (a known wart until A001 is packaged). A002 imports cleanly as
`agents.A002_News_Intelligence.*` from the repo root.
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_A001_DIR = _REPO_ROOT / "agents" / "A001_Blockchain_Intelligence"
_A001_DB = _A001_DIR / "data" / "a001.db"

_A001_CATALOGUE = ("detectors", "skills", "chains")
_A001_DB_OPS = ("metrics", "coverage", "flows", "labels", "health")
_A001_CHAIN_OPS = ("coverage", "flows", "labels")


def a001_handler(message) -> dict:
    """Read-only query into A001's IntelligenceService (read-only by construction)."""
    payload = getattr(message, "payload", None) or {}
    op = payload.get("op", "detectors")
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


def a002_handler(message) -> dict:
    """Read-only registry / settings / stats query into A002 (static + a002.db read)."""
    payload = getattr(message, "payload", None) or {}
    op = payload.get("op", "sources")

    if op == "settings":
        from agents.A002_News_Intelligence.config.settings import get_settings
        s = get_settings()
        return {"op": "settings", "agent": s.agent.id, "name": s.agent.name,
                "version": s.agent.version}

    if op == "stats":
        import asyncio

        from agents.A002_News_Intelligence.config.paths import DATABASE_FILE
        from agents.A002_News_Intelligence.core.storage import Storage

        async def _stats() -> dict:
            store = Storage(str(DATABASE_FILE))
            await store.init()  # schema-ensure (idempotent; no data mutation) — as A002 doctor does
            return {"items": await store.count_items(), "entities": await store.count_entities()}

        return {"op": "stats", **asyncio.run(_stats())}

    # default: the static source registry
    from agents.A002_News_Intelligence.config.sources import SOURCES, sources_by_kind
    kind = payload.get("kind")
    srcs = sources_by_kind(kind) if kind else SOURCES
    return {"op": "sources", "count": len(srcs), "kinds": sorted({s.kind for s in SOURCES})}
