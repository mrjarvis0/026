"""Assemble the running system: a MessageBus with the real fleet registered.

Loads each agent's manifest (via the sentinel fleet loader) so the bus can gate actions,
then registers the read-only adapters. This is the composition root; it is not the kernel.
"""
from __future__ import annotations

from pathlib import Path

from orchestrator.event_bus import MessageBus
from security.sentinel.fleet import load_fleet
from security.sentinel.policy import load_policy
from bootstrap.adapters import a001_handler, a002_handler

_REPO_ROOT = Path(__file__).resolve().parents[1]

_HANDLERS = {"A001": a001_handler, "A002": a002_handler}


def build_bus(repo_root: Path | None = None) -> MessageBus:
    repo_root = repo_root or _REPO_ROOT
    manifests = {r.id: r.manifest for r in load_fleet(repo_root, load_policy())}
    bus = MessageBus(manifests=manifests)
    for agent_id, handler in _HANDLERS.items():
        bus.register(agent_id, handler, manifests.get(agent_id))
    return bus
