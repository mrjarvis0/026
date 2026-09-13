"""
CIE-OS
A01 Blockchain Intelligence Agent

Whale skill USD valuation: native transfers valued in dollars when a price
provider is injected, undetermined (never fabricated) when it is not.

No network: the price provider is a fake.
"""
from __future__ import annotations

import pytest

from skills.whale_detection.transfers import WhaleTransferSkill


class _FakeRecord:
    def __init__(self, price: float) -> None:
        self.payload = {"price_usd": price}


class _FakeResult:
    def __init__(self, price: float, determined: bool) -> None:
        self.determined = determined
        self.record = _FakeRecord(price) if determined else None


class FakePrice:
    """A price provider stand-in: returns one fixed price, no network."""

    def __init__(self, price: float, determined: bool = True) -> None:
        self._price = price
        self._determined = determined

    def native_price(self, chain: str) -> _FakeResult:
        return _FakeResult(self._price, self._determined)

    def historical_native_price(self, chain: str, at: int) -> _FakeResult:
        return _FakeResult(self._price, self._determined)


def test_native_usd_uses_injected_price():
    skill = WhaleTransferSkill(price=FakePrice(2000.0))
    # 1.5 ETH (1.5e18 wei) at $2000 = $3000
    assert skill._native_usd("ethereum", 1_500_000_000_000_000_000) == pytest.approx(3000.0)


def test_native_usd_is_none_without_a_price_provider():
    skill = WhaleTransferSkill()
    assert skill._native_usd("ethereum", 10**18) is None


def test_native_usd_is_none_when_price_undetermined():
    skill = WhaleTransferSkill(price=FakePrice(0.0, determined=False))
    assert skill._native_usd("ethereum", 10**18) is None


def test_native_usd_honours_bitcoin_decimals():
    skill = WhaleTransferSkill(price=FakePrice(60000.0))
    # 2 BTC (2e8 sats) at $60000 = $120000
    assert skill._native_usd("bitcoin", 200_000_000) == pytest.approx(120000.0)
