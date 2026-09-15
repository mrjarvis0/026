import json

from security.sentinel.report import Verdict, worst, CheckResult, AgentReport, FleetReport


def test_worst_ordering():
    assert worst([Verdict.PASS, Verdict.HOLD, Verdict.FAIL]) == Verdict.FAIL
    assert worst([Verdict.PASS, Verdict.HOLD]) == Verdict.HOLD
    assert worst([Verdict.PASS, Verdict.PASS]) == Verdict.PASS
    assert worst([]) == Verdict.PASS


def test_agent_and_fleet_verdict_and_exit_code():
    a = AgentReport(id="A001", dir="agents/A001", effective_trust=2, checks=[
        CheckResult("manifest", Verdict.PASS, "ok"),
        CheckResult("trust", Verdict.HOLD, "capped"),
    ])
    assert a.verdict == Verdict.HOLD
    fleet = FleetReport(agents=[a])
    assert fleet.verdict == Verdict.HOLD
    assert fleet.exit_code() == 1
    fleet.agents[0].checks.append(CheckResult("execution", Verdict.FAIL, "lie"))
    assert fleet.exit_code() == 2


def test_to_json_roundtrips_structure():
    fleet = FleetReport(agents=[AgentReport("A002", "agents/A002", 2,
        [CheckResult("secrets", Verdict.PASS, "clean", ["scanned 5 files"], 5)])])
    data = json.loads(fleet.to_json())
    assert data["agents"][0]["id"] == "A002"
    assert data["agents"][0]["checks"][0]["verdict"] == "PASS"
    assert data["agents"][0]["verdict"] == "PASS"
