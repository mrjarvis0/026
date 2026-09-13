from security.sentinel.fleet import AgentRecord
from security.sentinel.report import Verdict
from security.sentinel.checks.manifest import check_manifest
from security.sentinel.checks.trust import check_trust
from security.sentinel.policy import load_policy

POLICY = load_policy()


def _rec(tmp_path, manifest, make_tests=False, detectors=None):
    d = tmp_path / "A99_Fake"
    if make_tests:
        (d / "tests").mkdir(parents=True)
        (d / "tests" / "test_x.py").write_text("def test_x():\n    assert True\n")
    else:
        d.mkdir()
    m = dict(manifest)
    if detectors is not None:
        m.setdefault("evidence", {})["detectors"] = detectors
    return AgentRecord(id="A99", dir=d, manifest=m, registry_row={"dir": str(d)}, fleet_row=None)


def test_manifest_missing_keys_fails(tmp_path):
    rec = _rec(tmp_path, {"id": "A99"})
    assert check_manifest(rec, POLICY).verdict == Verdict.FAIL


def test_manifest_complete_passes(tmp_path):
    rec = _rec(tmp_path, {"id": "A99", "name": "X", "status": "partial",
        "trust": {"level": 1}, "invariants": {"execution_enabled": False},
        "evidence": {}, "charter": "x"})
    assert check_manifest(rec, POLICY).verdict == Verdict.PASS


def test_trust_level2_without_evidence_holds_to_1(tmp_path):
    rec = _rec(tmp_path, {"id": "A99", "trust": {"level": 2}}, make_tests=False, detectors=[])
    res, eff = check_trust(rec, POLICY)
    assert res.verdict == Verdict.HOLD and eff == 1


def test_trust_level2_with_evidence_and_tests_passes(tmp_path):
    rec = _rec(tmp_path, {"id": "A99", "trust": {"level": 2}}, make_tests=True,
               detectors=[{"id": "DET-X-01"}])
    res, eff = check_trust(rec, POLICY)
    assert res.verdict == Verdict.PASS and eff == 2
