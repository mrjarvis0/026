from security.sentinel.policy import load_policy


def test_load_policy_has_expected_sections():
    pol = load_policy()
    assert pol["version"] == 1
    for section in ("execution", "secrets", "trust", "deviation", "registry"):
        assert section in pol, section
    assert "eth_sendTransaction" in pol["execution"]["banned_primitives"]
    assert pol["trust"]["min_level_requiring_evidence"] == 2
