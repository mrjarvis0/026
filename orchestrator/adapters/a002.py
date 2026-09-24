"""A002 News Intelligence — message-bus adapter (SP-4 slice).

The bus (``orchestrator/event_bus/bus.py``) routes a ``Message`` to a handler
``Callable[[Message], dict]``. This module is the *thin* adapter over A002's own
read surface — it does not reimplement A002, it calls it. Registering it puts A002
on the shared kernel:

* routed under the **sentinel gate + budget** (the bus already enforces both);
* reading / writing the **shared brain** only within A002's manifest-declared
  namespaces (``brain.access.AgentBrainView``), per AGENTS.md §5 / §7.

Honest by construction: the default reader returns real counts from A002's own
store — with no data it returns ``count: 0``, never a fabricated finding (A002
charter: degraded, never invented).

Scope: the operator chose to wire **A002 only** for this slice; A001's adapter is
deliberately not built here (its imports + ~30 % build need untangling first).
"""
from __future__ import annotations

import asyncio
from collections.abc import Callable
from pathlib import Path

import yaml

from brain.access import AgentBrainView
from brain.store import Brain
from orchestrator.event_bus.message import Message

AGENT_ID = "A002"
_AGENT_DIR = Path(__file__).resolve().parents[2] / "agents" / "A002_News_Intelligence"
_MANIFEST_PATH = _AGENT_DIR / "agent.yaml"

# A reader answers one intent: payload dict -> result dict.
Reader = Callable[[dict], dict]


def load_manifest(path: Path | str = _MANIFEST_PATH) -> dict:
    """A002's parsed manifest — the contract the bus + brain view read."""
    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}


def _read_narratives(payload: dict) -> dict:
    """Real read over A002's own store: active narratives ranked by FOMO."""
    from agents.A002_News_Intelligence.core.storage import Storage
    from agents.A002_News_Intelligence.intelligence.narrative import _narrative_from_row

    db_path = payload.get("db_path")
    if not db_path:
        from agents.A002_News_Intelligence.config import paths
        db_path = str(paths.DATABASE_FILE)

    async def run() -> dict:
        storage = Storage(db_path)
        await storage.init()
        rows = await storage.load_active_narratives("1970-01-01T00:00:00")
        narratives = sorted(
            (_narrative_from_row(r) for r in rows),
            key=lambda n: n.fomo_score,
            reverse=True,
        )
        top = [
            {
                "id": n.id,
                "claim": n.claim_text[:120],
                "fomo": n.fomo_score,
                "epistemic_status": n.epistemic_status,
                "confidence": n.confidence,
            }
            for n in narratives[:10]
        ]
        return {"count": len(narratives), "narratives": top}

    return asyncio.run(run())


_INTENTS: dict[str, Reader] = {
    "narratives": _read_narratives,
}


def build_handler(
    brain_view: AgentBrainView | None = None,
    intents: dict[str, Reader] | None = None,
) -> Callable[[Message], dict]:
    """A bus handler over A002. ``intents`` is injectable for tests."""
    table = intents if intents is not None else _INTENTS

    def handle(message: Message) -> dict:
        intent = (message.payload or {}).get("intent", "narratives")
        reader = table.get(intent)
        if reader is None:
            return {"agent": AGENT_ID, "intent": intent, "error": "unknown intent"}
        result = reader(message.payload or {})
        finding = result.get("finding")
        if brain_view is not None and finding is not None:
            # Manifest-scoped: A002 declares writes: [news, projects.*]. A write
            # outside that surface raises NamespaceDenied — deny-by-default.
            brain_view.write("news", finding["key"], finding["value"])
        return {"agent": AGENT_ID, "intent": intent, **result}

    return handle


def register(
    bus,
    brain: Brain | None = None,
    manifest: dict | None = None,
    intents: dict[str, Reader] | None = None,
) -> None:
    """Register A002 on the message bus with a manifest-scoped brain view."""
    manifest = manifest if manifest is not None else load_manifest()
    brain_view = AgentBrainView(brain, AGENT_ID, manifest) if brain is not None else None
    bus.register(AGENT_ID, build_handler(brain_view, intents), manifest)
