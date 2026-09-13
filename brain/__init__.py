"""The shared brain — namespaced memory the fleet reads and writes (AGENTS.md §7).

Reads are logged and writes are versioned; nothing is silent. Access is scoped to what
an agent's manifest declares in `memory.reads` / `memory.writes`, enforced by
:class:`brain.access.AgentBrainView`.
"""
from .store import Brain, valid_namespace
from .access import AgentBrainView, NamespaceDenied

__all__ = ["Brain", "valid_namespace", "AgentBrainView", "NamespaceDenied"]
