from __future__ import annotations

from security.sentinel.fleet import AgentRecord
from security.sentinel.report import CheckResult, Verdict

_REQUIRED = ["id", "name", "status", "trust", "invariants", "evidence", "charter"]


def check_manifest(record: AgentRecord, policy: dict) -> CheckResult:
    m = record.manifest
    if not m:
        return CheckResult("manifest", Verdict.FAIL, "agent.yaml missing or empty")
    if m.get("id") != record.id:
        return CheckResult("manifest", Verdict.FAIL,
                           f"manifest id {m.get('id')!r} != registry id {record.id!r}")
    missing = [k for k in _REQUIRED if k not in m]
    if "trust" in m and "level" not in (m.get("trust") or {}):
        missing.append("trust.level")
    if "invariants" in m and "execution_enabled" not in (m.get("invariants") or {}):
        missing.append("invariants.execution_enabled")
    if missing:
        return CheckResult("manifest", Verdict.FAIL, "missing keys: " + ", ".join(missing),
                           evidence=missing)
    return CheckResult("manifest", Verdict.PASS, "valid manifest", scanned=1)
