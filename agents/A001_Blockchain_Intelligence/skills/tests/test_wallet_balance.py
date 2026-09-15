"""
CIE-OS
A001 Blockchain Intelligence Agent

wallet_profile native balance: the address's current native balance from a
balance provider (a live sensor), or None when no provider is wired -- storage
holds transfers, not state, so absence is honest, never a partial-sum guess.

No network: the balance provider is a fake.
"""
from __future__ import annotations

from skills.wallet_lookup.profile import WalletProfileSkill


class _Rec:
    def __init__(self, wei: int) -> None:
        self.payload = {"address": "0xme", "balance_raw": hex(wei), "balance_wei": wei}


class _Result:
    def __init__(self, wei: int, determined: bool) -> None:
        self.determined = determined
        self.record = _Rec(wei) if determined else None


class FakeBalances:
    def __init__(self, wei: int, determined: bool = True) -> None:
        self._wei = wei
        self._determined = determined

    def native_balance(self, chain: str, address: str) -> _Result:
        return _Result(self._wei, self._determined)


class _Addr:
    def __init__(self, value: str) -> None:
        self.value = value


def test_balance_wei_from_provider():
    skill = WalletProfileSkill(balances=FakeBalances(5 * 10**18))
    assert skill._balance_wei("ethereum", _Addr("0xME")) == 5 * 10**18


def test_balance_wei_is_none_without_a_provider():
    assert WalletProfileSkill()._balance_wei("ethereum", _Addr("0xME")) is None


def test_balance_wei_is_none_when_undetermined():
    skill = WalletProfileSkill(balances=FakeBalances(0, determined=False))
    assert skill._balance_wei("ethereum", _Addr("0xME")) is None
