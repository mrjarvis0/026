import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from agents.A002_News_Intelligence.intelligence.verification import (
    FactCheckClient,
    get_fact_check_client,
)


def test_disabled_without_key_makes_no_call():
    """No API key -> disabled -> returns [] offline (never touches the network)."""
    client = FactCheckClient(api_key=None)
    assert client.enabled is False
    assert client.check_claim("Bitcoin is dead") == []


def test_enabled_with_key():
    client = FactCheckClient(api_key="test_key")
    assert client.enabled is True


def test_get_fact_check_client_singleton():
    a = get_fact_check_client()
    b = get_fact_check_client()
    assert a is b


if __name__ == "__main__":
    test_disabled_without_key_makes_no_call()
    test_enabled_with_key()
    test_get_fact_check_client_singleton()
    print("ok")
