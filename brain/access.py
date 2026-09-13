"""Manifest-scoped access to the brain.

An agent may only read/write the namespaces its manifest declares (`memory.reads` /
`memory.writes`). A declared entry may be an exact namespace (`chain`) or a wildcard
(`projects.*`, matching any `projects/<id>`). This is how "write like others will read"
(§7) stays honest: an agent cannot quietly reach outside its declared surface.
"""
from __future__ import annotations

from brain.store import Brain


class NamespaceDenied(Exception):
    pass


def _matches(declared: str, namespace: str) -> bool:
    if declared == namespace:
        return True
    if declared.endswith(".*"):
        return namespace.startswith(declared[:-2] + "/")
    return False


def _allowed(declared: list[str] | None, namespace: str) -> bool:
    return any(_matches(d, namespace) for d in (declared or []))


class AgentBrainView:
    """A view of the brain scoped to one agent's declared memory contract."""

    def __init__(self, brain: Brain, agent_id: str, manifest: dict) -> None:
        self.brain = brain
        self.agent_id = agent_id
        memory = manifest.get("memory") or {}
        self._reads = memory.get("reads") or []
        self._writes = memory.get("writes") or []

    def read(self, namespace: str, key: str):
        if not _allowed(self._reads, namespace):
            raise NamespaceDenied(f"{self.agent_id} may not read {namespace!r}")
        return self.brain.read(namespace, key, by=self.agent_id)

    def write(self, namespace: str, key: str, value) -> int:
        if not _allowed(self._writes, namespace):
            raise NamespaceDenied(f"{self.agent_id} may not write {namespace!r}")
        return self.brain.write(namespace, key, value, by=self.agent_id)
