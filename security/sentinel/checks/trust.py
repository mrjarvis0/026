from __future__ import annotations

from security.sentinel.fleet import AgentRecord
from security.sentinel.report import CheckResult, Verdict


def _has_tests(agent_dir) -> bool:
    tests = agent_dir / "tests"
    return tests.is_dir() and any(tests.glob("test_*.py"))


def check_trust(record: AgentRecord, policy: dict) -> tuple[CheckResult, int]:
    level = int((record.manifest.get("trust") or {}).get("level", 0))
    threshold = policy["trust"]["min_level_requiring_evidence"]
    if level < threshold:
        return CheckResult("trust", Verdict.PASS, f"level {level} needs no evidence"), level
    detectors = (record.manifest.get("evidence") or {}).get("detectors") or []
    has_tests = _has_tests(record.dir)
    if detectors and has_tests:
        return CheckResult("trust", Verdict.PASS,
                           f"level {level} earned ({len(detectors)} detectors, tests present)"), level
    reasons = []
    if not detectors:
        reasons.append("no evidence.detectors")
    if not has_tests:
        reasons.append("no tests/test_*.py")
    return CheckResult("trust", Verdict.HOLD,
                       f"level {level} not earned ({'; '.join(reasons)}) -> capped to 1",
                       evidence=reasons), 1
