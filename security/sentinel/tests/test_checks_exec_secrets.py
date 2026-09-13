from security.sentinel.fleet import AgentRecord
from security.sentinel.report import Verdict
from security.sentinel.checks.execution import check_execution
from security.sentinel.checks.secrets import check_secrets
from security.sentinel.policy import load_policy

POLICY = load_policy()


def _rec(tmp_path):
    d = tmp_path / "A99_Fake"
    d.mkdir()
    return d, AgentRecord("A99", d, {"invariants": {"execution_enabled": False}},
                          {"dir": str(d)}, None)


def test_execution_live_signing_call_fails(tmp_path):
    d, rec = _rec(tmp_path)
    (d / "mod.py").write_text("def go(w):\n    return sign_transaction(w)\n")
    res = check_execution(rec, POLICY)
    assert res.verdict == Verdict.FAIL
    assert any("mod.py:2" in e for e in res.evidence)


def test_execution_mention_in_comment_or_string_passes(tmp_path):
    d, rec = _rec(tmp_path)
    (d / "mod.py").write_text('# never call sign_transaction here\nBANNED = "eth_sendTransaction"\n')
    assert check_execution(rec, POLICY).verdict == Verdict.PASS


def test_execution_skips_tests_dir(tmp_path):
    d, rec = _rec(tmp_path)
    (d / "tests").mkdir()
    (d / "tests" / "test_sec.py").write_text("x = sign_transaction\n")
    assert check_execution(rec, POLICY).verdict == Verdict.PASS


def test_secrets_hardcoded_key_fails(tmp_path):
    d, rec = _rec(tmp_path)
    (d / "conf.py").write_text('api_key = "abcd1234efgh5678ijkl"\n')
    assert check_secrets(rec, POLICY).verdict == Verdict.FAIL


def test_secrets_clean_passes(tmp_path):
    d, rec = _rec(tmp_path)
    (d / "conf.py").write_text('api_key = os.environ["X"]\n')
    assert check_secrets(rec, POLICY).verdict == Verdict.PASS


def test_secrets_event_topic_hash_not_flagged(tmp_path):
    # A public Ethereum event-topic hash (0x + 64 hex) is NOT a credential.
    d, rec = _rec(tmp_path)
    (d / "signatures.py").write_text(
        'TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"\n')
    assert check_secrets(rec, POLICY).verdict == Verdict.PASS


def test_secrets_private_key_material_flagged(tmp_path):
    # The same shape assigned to a key-named var IS a credential leak.
    d, rec = _rec(tmp_path)
    (d / "leak.py").write_text(
        'PRIVATE_KEY = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"\n')
    assert check_secrets(rec, POLICY).verdict == Verdict.FAIL
