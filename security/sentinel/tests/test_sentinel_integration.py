import json
from pathlib import Path

from security.sentinel.sentinel import run_sentinel, main
from security.sentinel.report import Verdict

ROOT = Path(__file__).resolve().parents[3]  # F:\026


def test_real_fleet_has_no_fail():
    report = run_sentinel(ROOT)
    ids = {a.id for a in report.agents}
    assert {"A001", "A002"} <= ids
    for a in report.agents:
        fails = [c.summary for c in a.checks if c.verdict == Verdict.FAIL]
        assert a.verdict != Verdict.FAIL, f"{a.id} FAILED: {fails}"


def test_cli_scan_returns_exit_code(capsys):
    code = main(["scan"])
    out = capsys.readouterr().out
    assert "fleet verdict" in out
    assert code in (0, 1)  # PASS or HOLD, never FAIL for the real fleet


def test_cli_json_is_valid(capsys):
    main(["scan", "--json"])
    data = json.loads(capsys.readouterr().out)
    assert "agents" in data and data["agents"]
