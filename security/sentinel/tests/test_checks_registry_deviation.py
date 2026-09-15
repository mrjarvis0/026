from security.sentinel.fleet import AgentRecord
from security.sentinel.report import Verdict
from security.sentinel.checks.registry import check_registry
from security.sentinel.checks.deviation import check_deviation
from security.sentinel.policy import load_policy

POLICY = load_policy()


def test_registry_absent_from_fleet_table_fails(tmp_path):
    rec = AgentRecord("A99", tmp_path, {"id": "A99", "name": "X", "status": "partial"},
                      {"name": "X", "status": "partial"}, fleet_row=None)
    assert check_registry(rec, POLICY).verdict == Verdict.FAIL


def test_registry_status_drift_holds(tmp_path):
    rec = AgentRecord("A001", tmp_path,
                      {"id": "A001", "name": "Blockchain Intelligence", "status": "partial"},
                      {"name": "Blockchain Intelligence", "status": "partial"},
                      fleet_row={"id": "A001", "name": "Blockchain Intelligence", "status": "substantial"})
    assert check_registry(rec, POLICY).verdict == Verdict.HOLD


def test_registry_all_agree_passes(tmp_path):
    row = {"id": "A001", "name": "Blockchain Intelligence", "status": "substantial"}
    rec = AgentRecord("A001", tmp_path,
                      {"id": "A001", "name": "Blockchain Intelligence", "status": "substantial"},
                      {"name": "Blockchain Intelligence", "status": "substantial"}, fleet_row=row)
    assert check_registry(rec, POLICY).verdict == Verdict.PASS


def test_deviation_advice_word_holds_never_fails(tmp_path):
    d = tmp_path / "A99"
    (d / "decision").mkdir(parents=True)
    (d / "decision" / "out.py").write_text('MSG = "you should buy now"\n')
    rec = AgentRecord("A99", d, {"invariants": {"reports_deviation_only": True}}, {}, None)
    res = check_deviation(rec, POLICY)
    assert res.verdict == Verdict.HOLD  # never FAIL


def test_deviation_clean_output_passes(tmp_path):
    d = tmp_path / "A99"
    (d / "decision").mkdir(parents=True)
    (d / "decision" / "out.py").write_text('MSG = "deviation z-score 7.1, not a recommendation"\n')
    rec = AgentRecord("A99", d, {"invariants": {"reports_deviation_only": True}}, {}, None)
    assert check_deviation(rec, POLICY).verdict == Verdict.PASS


def test_deviation_docstring_advice_not_flagged(tmp_path):
    # A docstring that DECLINES advice must not itself read as advice (AST-aware).
    d = tmp_path / "A99"
    (d / "decision").mkdir(parents=True)
    (d / "decision" / "rec.py").write_text(
        '"""Say what unblocks the next answer, and nothing about what to buy or\n'
        'sell — you should buy is never A001\'s to say."""\n\nACTIONS = ["widen_window"]\n')
    rec = AgentRecord("A99", d, {"invariants": {"reports_deviation_only": True}}, {}, None)
    assert check_deviation(rec, POLICY).verdict == Verdict.PASS
