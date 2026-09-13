"""Sentinel report model: verdicts, per-check results, aggregation, renderers."""
from __future__ import annotations

import datetime
import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import Enum

_ORDER = {"PASS": 0, "HOLD": 1, "FAIL": 2}


class Verdict(str, Enum):
    PASS = "PASS"
    HOLD = "HOLD"
    FAIL = "FAIL"


def worst(verdicts: Iterable[Verdict]) -> Verdict:
    worst_v = Verdict.PASS
    for v in verdicts:
        if _ORDER[v.value] > _ORDER[worst_v.value]:
            worst_v = v
    return worst_v


@dataclass
class CheckResult:
    check: str
    verdict: Verdict
    summary: str
    evidence: list[str] = field(default_factory=list)
    scanned: int = 0

    def as_dict(self) -> dict:
        return {"check": self.check, "verdict": self.verdict.value,
                "summary": self.summary, "evidence": self.evidence, "scanned": self.scanned}


@dataclass
class AgentReport:
    id: str
    dir: str
    effective_trust: int
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def verdict(self) -> Verdict:
        return worst(c.verdict for c in self.checks)

    def as_dict(self) -> dict:
        return {"id": self.id, "dir": self.dir, "effective_trust": self.effective_trust,
                "verdict": self.verdict.value, "checks": [c.as_dict() for c in self.checks]}


@dataclass
class FleetReport:
    agents: list[AgentReport] = field(default_factory=list)
    sentinel_version: str = "0.1.0"
    policy_version: int = 1
    generated_at: str = field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC).isoformat())

    @property
    def verdict(self) -> Verdict:
        return worst(a.verdict for a in self.agents) if self.agents else Verdict.PASS

    def exit_code(self) -> int:
        v = self.verdict
        return 2 if v == Verdict.FAIL else 1 if v == Verdict.HOLD else 0

    def as_dict(self) -> dict:
        return {"generated_at": self.generated_at, "sentinel_version": self.sentinel_version,
                "policy_version": self.policy_version, "verdict": self.verdict.value,
                "agents": [a.as_dict() for a in self.agents]}

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), indent=2)

    def to_table(self) -> str:
        lines = [f"Sentinel {self.sentinel_version} — fleet verdict: {self.verdict.value}", ""]
        for a in self.agents:
            lines.append(f"  {a.id:<5} {a.verdict.value:<5} trust={a.effective_trust}  {a.dir}")
            for c in a.checks:
                if c.verdict != Verdict.PASS:
                    lines.append(f"      - [{c.verdict.value}] {c.check}: {c.summary}")
                    for ev in c.evidence[:10]:
                        lines.append(f"          {ev}")
        return "\n".join(lines)
