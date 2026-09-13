from security.sentinel.gate import check_action, Decision

# A manifest shaped like A01/A02 (trust 2, read-only, execution disabled).
MANIFEST = {
    "trust": {"level": 2, "requires_approval": ["external.post", "store.delete"]},
    "tools": ["rpc.call", "brain.query", "brain.write", "store.read"],
    "invariants": {"execution_enabled": False},
}


def test_execution_action_is_denied():
    res = check_action({"tool": "rpc.call", "kind": "trade"}, MANIFEST)
    assert res.decision == Decision.DENY


def test_declared_tool_is_allowed():
    res = check_action({"tool": "rpc.call", "kind": "read"}, MANIFEST)
    assert res.decision == Decision.ALLOW


def test_requires_approval_tool_is_held():
    res = check_action({"tool": "external.post", "kind": "external"}, MANIFEST)
    assert res.decision == Decision.HOLD


def test_undeclared_tool_is_denied():
    res = check_action({"tool": "os.system", "kind": "read"}, MANIFEST)
    assert res.decision == Decision.DENY


def test_action_above_trust_is_denied():
    res = check_action({"tool": "rpc.call", "kind": "read", "trust_required": 3}, MANIFEST)
    assert res.decision == Decision.DENY
