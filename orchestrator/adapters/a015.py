"""A015 Exchange Listing/Delisting — message-bus adapter (SP-4 slice).

Thin adapter over A015's own read surface: it reads A015's append-only event log
(the canonical fact store) and returns recent events. Registering it puts A015 on
the shared kernel — routed under the sentinel gate + budget (the bus), reading /
writing the shared brain only within A015's manifest-declared namespaces
(`markets`, per AGENTS.md §5/§7).

Honest by construction: with no events logged yet it returns ``count: 0`` rather
than a fabricated finding.
"""
from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import yaml

from brain.access import AgentBrainView
from brain.store import Brain
from orchestrator.event_bus.message import Message

AGENT_ID = "A015"
_AGENT_DIR = (Path(__file__).resolve().parents[2]
              / "agents" / "A015_Exchange_Listing_Delisting_Intelligence")
_MANIFEST_PATH = _AGENT_DIR / "agent.yaml"
_EVENT_LOG_DIR = _AGENT_DIR / "memory" / "event_log"

Reader = Callable[[dict], dict]


def load_manifest(path: Path | str = _MANIFEST_PATH) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}


def _read_latest_events(payload: dict) -> dict:
    """Real read over A015's own event log. Empty -> [] (never fabricated)."""
    log_dir = Path(payload.get("event_log_dir") or _EVENT_LOG_DIR)
    events: list = []
    if log_dir.is_dir():
        for path in sorted(log_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            events.extend(data if isinstance(data, list) else [data])
    limit = int(payload.get("limit", 20))
    return {"count": len(events), "events": events[-limit:]}


_INTENTS: dict[str, Reader] = {
    "latest_events": _read_latest_events,
}


def build_handler(brain_view: AgentBrainView | None = None,
                  intents: dict[str, Reader] | None = None) -> Callable[[Message], dict]:
    table = intents if intents is not None else _INTENTS

    def handle(message: Message) -> dict:
        intent = (message.payload or {}).get("intent", "latest_events")
        reader = table.get(intent)
        if reader is None:
            return {"agent": AGENT_ID, "intent": intent, "error": "unknown intent"}
        result = reader(message.payload or {})
        finding = result.get("finding")
        if brain_view is not None and finding is not None:
            # Manifest-scoped: A015 declares writes: [markets, projects.*].
            brain_view.write("markets", finding["key"], finding["value"])
        return {"agent": AGENT_ID, "intent": intent, **result}

    return handle


def register(bus, brain: Brain | None = None, manifest: dict | None = None,
             intents: dict[str, Reader] | None = None) -> None:
    manifest = manifest if manifest is not None else load_manifest()
    brain_view = AgentBrainView(brain, AGENT_ID, manifest) if brain is not None else None
    bus.register(AGENT_ID, build_handler(brain_view, intents), manifest)
