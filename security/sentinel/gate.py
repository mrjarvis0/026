"""Runtime gate — the sentinel's per-action face (SP-3 slice 2).

The bus (SP-4) will call :func:`check_action` before an agent action takes effect.
Nothing calls it yet; it is the seam, and it is testable now. The governing rule is
deny-by-default at every boundary — an action is ALLOWed only when it stays inside the
agent's declared surface, HELD when it touches a `requires_approval` tool, and DENIED
when it crosses the execution boundary or steps outside what the manifest declares.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

# Action "kinds" that cross the money/execution boundary. Per ADR-0002 no order fires
# without the execution gate — which is not built — so these are always denied for now.
EXECUTION_KINDS = frozenset({"execution", "trade", "order", "transfer", "sign", "withdraw"})


class Decision(str, Enum):
    ALLOW = "allow"
    HOLD = "hold"
    DENY = "deny"


@dataclass
class GateResult:
    decision: Decision
    reason: str


def check_action(action: dict, agent_manifest: dict, policy: dict | None = None) -> GateResult:
    """Decide a single proposed action against the agent's declared contract.

    ``action`` is a minimal dict: ``{"tool": str, "kind": "read"|"write"|"execution"|...,
    "trust_required": int?}``. ``agent_manifest`` is the agent's parsed ``agent.yaml``.
    """
    tool = action.get("tool")
    kind = action.get("kind", "read")
    trust = agent_manifest.get("trust") or {}
    level = int(trust.get("level", 0))
    declared_tools = set(agent_manifest.get("tools") or [])
    requires_approval = set(trust.get("requires_approval") or [])

    # 1. Execution boundary — deny-by-default. The money-gate does not exist yet
    #    (ADR-0002: the first execution code must be the gate, not an order path).
    if kind in EXECUTION_KINDS:
        return GateResult(Decision.DENY,
                          f"execution boundary ({kind!r}): blocked — no execution gate exists")

    # 2. A tool the manifest marks as requiring approval is held for the operator.
    if tool in requires_approval:
        return GateResult(Decision.HOLD, f"tool {tool!r} requires operator approval")

    # 3. An action needing more trust than the agent holds is denied.
    req_trust = action.get("trust_required")
    if req_trust is not None and int(req_trust) > level:
        return GateResult(Decision.DENY,
                          f"action needs trust {req_trust} > agent trust {level}")

    # 4. A tool outside the declared surface is denied (deny-by-default).
    if tool is not None and tool not in declared_tools:
        return GateResult(Decision.DENY, f"tool {tool!r} not in agent's declared tools")

    # 5. Inside the declared surface.
    return GateResult(Decision.ALLOW, "within declared surface")
