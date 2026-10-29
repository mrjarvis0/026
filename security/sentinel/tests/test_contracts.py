"""The `contracts` check: declared event contracts must be real (design spec section 7)."""
from pathlib import Path

from security.sentinel.checks.contracts import check_contracts
from security.sentinel.fleet import AgentRecord
from security.sentinel.report import Verdict
from security.sentinel.sentinel import run_sentinel

ROOT = Path(__file__).resolve().parents[3]  # F:\026

SCHEMAS = {
    "a015.listing.delisted": {"schema_version": 1, "platform": False, "required": {}, "optional": {}},
    "system.source.stale": {"schema_version": 1, "platform": True, "required": {}, "optional": {}},
}


def rec(agent_id, **manifest):
    return AgentRecord(id=agent_id, dir=Path("."), manifest={"id": agent_id, **manifest},
                       registry_row={}, fleet_row=None)


def run(record, fleet):
    return check_contracts(record, {}, fleet, SCHEMAS)


def producer():
    return rec("A015", produces=[{"type": "a015.listing.delisted", "schema_version": 1}])


def test_no_declarations_passes():
    r = rec("A099")
    assert run(r, [r]).verdict == Verdict.PASS


def test_produces_unknown_type_fails():
    r = rec("A099", produces=[{"type": "a099.thing.happened", "schema_version": 1}])
    res = run(r, [r])
    assert res.verdict == Verdict.FAIL and "a099.thing.happened" in " ".join(res.evidence)


def test_produces_wrong_schema_version_fails():
    r = rec("A015", produces=[{"type": "a015.listing.delisted", "schema_version": 2}])
    assert run(r, [r]).verdict == Verdict.FAIL


def test_orphan_consume_holds():
    r = rec("A099", consumes=[{"type": "a077.*"}])
    res = run(r, [r, producer()])
    assert res.verdict == Verdict.HOLD and "a077.*" in " ".join(res.evidence)


def test_consume_matched_by_other_agent_passes():
    r = rec("A099", consumes=[{"type": "a015.listing.*", "min_maturity": "implemented"}])
    assert run(r, [r, producer()]).verdict == Verdict.PASS


def test_consume_matched_by_platform_type_passes():
    r = rec("A099", consumes=[{"type": "system.source.*"}])
    assert run(r, [r]).verdict == Verdict.PASS


def test_invalid_min_maturity_holds():
    r = rec("A099", consumes=[{"type": "a015.listing.*", "min_maturity": "bogus"}])
    assert run(r, [r, producer()]).verdict == Verdict.HOLD


def test_real_fleet_a015_contracts_pass():
    report = run_sentinel(ROOT, only="A015")
    [a015] = report.agents
    [contracts] = [c for c in a015.checks if c.check == "contracts"]
    assert contracts.verdict == Verdict.PASS and "4" in contracts.summary
