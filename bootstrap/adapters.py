"""Thin, read-only bus adapters over the real A01 / A02 agents.

Each handler takes a bus Message (duck-typed: only `.payload` is read) and returns a
plain dict. They call the agents' own read-only entry points — no network, no data
writes, no keys.

Read ops exposed:
  A01 — catalogue (no DB): detectors, skills, chains; DB-backed reads over the migrated
        a01.db: metrics, coverage, flows, labels, health.
  A02 — static registry/settings: sources, settings; DB-backed read over a02.db: stats.

A01 uses bare top-level imports, so its adapter puts the A01 directory on `sys.path`
just-in-time (a known wart until A01 is packaged). A02 imports cleanly as
`agents.A02_News_Intelligence.*` from the repo root.
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_A01_DIR = _REPO_ROOT / "agents" / "A01_Blockchain_Intelligence"
_A01_DB = _A01_DIR / "data" / "a01.db"

_A01_CATALOGUE = ("detectors", "skills", "chains")
_A01_DB_OPS = ("metrics", "coverage", "flows", "labels", "health")
_A01_CHAIN_OPS = ("coverage", "flows", "labels")


def a01_handler(message) -> dict:
    """Read-only query into A01's IntelligenceService (read-only by construction)."""
    payload = getattr(message, "payload", None) or {}
    op = payload.get("op", "detectors")
    if op not in _A01_CATALOGUE + _A01_DB_OPS:
        return {"error": f"unknown op {op!r}", "ops": list(_A01_CATALOGUE + _A01_DB_OPS)}
    if str(_A01_DIR) not in sys.path:
        sys.path.insert(0, str(_A01_DIR))
    from interfaces.service import IntelligenceService  # noqa: E402 (path set above)

    db = str(_A01_DB) if (op in _A01_DB_OPS and _A01_DB.exists()) else None
    svc = IntelligenceService(database_path=db)
    if op in _A01_CHAIN_OPS:
        result = getattr(svc, op)(chain=payload.get("chain", "ethereum"))
    else:
        result = getattr(svc, op)()
    return {"op": op, "ok": result.ok, "status": result.status, "data": result.data}


def a02_handler(message) -> dict:
    """Read-only registry / settings / stats query into A02 (static + a02.db read)."""
    payload = getattr(message, "payload", None) or {}
    op = payload.get("op", "sources")

    if op == "settings":
        from agents.A02_News_Intelligence.config.settings import get_settings
        s = get_settings()
        return {"op": "settings", "agent": s.agent.id, "name": s.agent.name,
                "version": s.agent.version}

    if op == "stats":
        import asyncio

        from agents.A02_News_Intelligence.config.paths import DATABASE_FILE
        from agents.A02_News_Intelligence.core.storage import Storage

        async def _stats() -> dict:
            store = Storage(str(DATABASE_FILE))
            await store.init()  # schema-ensure (idempotent; no data mutation) — as A02 doctor does
            return {"items": await store.count_items(), "entities": await store.count_entities()}

        return {"op": "stats", **asyncio.run(_stats())}

    # default: the static source registry
    from agents.A02_News_Intelligence.config.sources import SOURCES, sources_by_kind
    kind = payload.get("kind")
    srcs = sources_by_kind(kind) if kind else SOURCES
    return {"op": "sources", "count": len(srcs), "kinds": sorted({s.kind for s in SOURCES})}
