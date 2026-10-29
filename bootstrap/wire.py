"""Assemble the running system: a MessageBus with the real fleet registered.

Loads each agent's manifest (via the sentinel fleet loader) so the bus can gate actions,
then registers the read-only adapters. This is the composition root; it is not the kernel.
"""
from __future__ import annotations

import json
from pathlib import Path

from brain.store import Brain
from orchestrator.event_bus import MessageBus
from orchestrator.event_bus.store import DEFAULT_DB, EventStore
from orchestrator.event_bus.trace import TraceLog
from security.sentinel.fleet import load_fleet
from security.sentinel.policy import load_policy
from bootstrap.adapters import a001_handler, a002, a015

_REPO_ROOT = Path(__file__).resolve().parents[1]

HANDLER_TIMEOUT_S = 60.0  # one hung agent call must not stall the whole bus
BUS_CONFIG = _REPO_ROOT / "config" / "bus.json"
BRAIN_DB = _REPO_ROOT / "data" / "brain" / "brain.db"
_BUS_DEFAULTS = {"a015_exchanges": ["binance", "bybit", "coinbase", "okx"], "a015_every_min": 15,
                 "stale_factor": 2, "retention_days": 90}


def load_bus_config(path: Path | None = None) -> dict:
    """config/bus.json over built-in defaults (JSON so the stdlib-only supervisor reads it too)."""
    try:
        raw = json.loads(Path(path or BUS_CONFIG).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raw = {}
    return {**_BUS_DEFAULTS, **(raw if isinstance(raw, dict) else {})}


def build_store(db_path=None, repo_root: Path | None = None) -> EventStore:
    """The event store with the real fleet manifests (producers are authorized from them)."""
    repo_root = repo_root or _REPO_ROOT
    manifests = {r.id: r.manifest for r in load_fleet(repo_root, load_policy())}
    return EventStore(db_path or DEFAULT_DB, manifests=manifests)


def build_brain(db_path=None) -> Brain:
    """The persistent shared brain (the first one that exists; the librarian writes `markets`)."""
    path = Path(db_path or BRAIN_DB)
    path.parent.mkdir(parents=True, exist_ok=True)
    return Brain(str(path))


def build_bus(repo_root: Path | None = None, store: EventStore | None = None) -> MessageBus:
    """The message bus with the real fleet. With a ``store`` the trace and held actions persist."""
    repo_root = repo_root or _REPO_ROOT
    manifests = {r.id: r.manifest for r in load_fleet(repo_root, load_policy())}
    bus = MessageBus(
        manifests=manifests, timeout_s=HANDLER_TIMEOUT_S,
        trace=TraceLog(sink=store.record_trace) if store else None,
        on_hold=(lambda message, reason: store.hold(message.as_dict(), reason)) if store else None)
    bus.register("A001", a001_handler, manifests.get("A001"))
    # A002 / A015 carry a manifest-scoped brain view; no persistent Brain exists yet (Phase 1).
    a002.register(bus, manifest=manifests.get("A002"))
    a015.register(bus, manifest=manifests.get("A015"))
    return bus
