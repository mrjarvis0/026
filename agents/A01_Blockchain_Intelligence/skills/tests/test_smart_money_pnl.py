"""
CIE-OS
A01 Blockchain Intelligence Agent

smart_money native-flow USD valuation: value an address's native in/out flows
in dollars when a price provider is wired. Not full P&L (that needs cost basis +
token prices) -- an honest USD-flow signal, undetermined without a price.

No network: the price provider is a fake.
"""
from __future__ import annotations

import pytest

from skills.smart_money.tracker import SmartMoneySkill


class _Rec:
    def __init__(self, price: float) -> None:
        self.payload = {"price_usd": price}


class _Result:
    def __init__(self, price: float, determined: bool) -> None:
        self.determined = determined
        self.record = _Rec(price) if determined else None


class FakePrice:
    def __init__(self, price: float, determined: bool = True) -> None:
        self._price = price
        self._determined = determined

    def native_price(self, chain: str) -> _Result:
        return _Result(self._price, self._determined)


class _Amt:
    def __init__(self, raw: int) -> None:
        self.raw = raw


class _Transfer:
    def __init__(self, frm: str, to: str, raw: int) -> None:
        self.from_address = frm
        self.to_address = to
        self.value = _Amt(raw)


class _Addr:
    def __init__(self, value: str) -> None:
        self.value = value


ETH = 10**18


def test_native_flow_usd_values_inflow_and_outflow():
    skill = SmartMoneySkill(price=FakePrice(2000.0))
    me = _Addr("0xME")
    transfers = [_Transfer("0xX", "0xME", ETH), _Transfer("0xME", "0xY", 2 * ETH)]
    flow = skill._native_flow_usd("ethereum", transfers, me)
    assert flow["inflow_usd"] == pytest.approx(2000.0)
    assert flow["outflow_usd"] == pytest.approx(4000.0)
    assert flow["net_usd"] == pytest.approx(-2000.0)


def test_native_flow_usd_is_none_without_price():
    skill = SmartMoneySkill()
    assert skill._native_flow_usd("ethereum", [], _Addr("0xME")) is None


def test_native_flow_usd_is_none_when_price_undetermined():
    skill = SmartMoneySkill(price=FakePrice(0.0, determined=False))
    transfers = [_Transfer("0xX", "0xME", ETH)]
    assert skill._native_flow_usd("ethereum", transfers, _Addr("0xME")) is None
