from __future__ import annotations

from security.sentinel.fleet import AgentRecord
from security.sentinel.report import CheckResult, Verdict


def check_registry(record: AgentRecord, policy: dict) -> CheckResult:
    if record.fleet_row is None:
        return CheckResult("registry", Verdict.FAIL,
                           f"{record.id} enabled in registry but absent from AGENTS.md §3")
    reg_name = record.registry_row.get("name")
    man_name = record.manifest.get("name")
    tbl_name = record.fleet_row.get("name")
    names = {n for n in (reg_name, man_name, tbl_name) if n}
    if len(names) > 1:
        return CheckResult("registry", Verdict.FAIL,
                           f"name mismatch: registry={reg_name!r} manifest={man_name!r} table={tbl_name!r}")
    reg_status = record.registry_row.get("status")
    tbl_status = record.fleet_row.get("status")
    man_status = record.manifest.get("status")
    statuses = {s for s in (reg_status, tbl_status, man_status) if s}
    if len(statuses) > 1:
        return CheckResult("registry", Verdict.HOLD,
                           f"status drift: registry={reg_status!r} table={tbl_status!r} manifest={man_status!r}")
    return CheckResult("registry", Verdict.PASS, "registry, manifest and §3 agree")
