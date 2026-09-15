"""
CIE-OS
A001 Blockchain Intelligence Agent

Historical (block-time) USD price reads for the price feed sensor.

No test here touches the network: every read is served by a scripted client,
so the test measures the sensor, not the provider's uptime.
"""
from __future__ import annotations

import pytest

from sensors.envelope import RecordKind
from sensors.market.price_sensor import MarketResponse, PriceFeedSensor

TS = 1_700_000_000


class ScriptedMarketClient:
    def __init__(self, responses: dict[str, MarketResponse] | None = None) -> None:
        self.responses = responses or {}
        self.calls: list[tuple[str, str]] = []

    def get(self, url: str, *, provider: str) -> MarketResponse:
        self.calls.append((url, provider))
        for pattern, resp in self.responses.items():
            if pattern in url:
                return resp
        return MarketResponse(ok=False, body=None, provider=provider,
                              duration_ms=0.1, reason="no scripted response")


def llama(coin_key: str, price: float, symbol: str = "ETH") -> MarketResponse:
    return MarketResponse(
        ok=True,
        body={"coins": {coin_key: {"price": price, "symbol": symbol,
                                   "timestamp": TS, "confidence": 0.99}}},
        provider="defillama-coins", duration_ms=42.0,
    )


def sensor_with(responses: dict[str, MarketResponse]):
    client = ScriptedMarketClient(responses)
    return PriceFeedSensor(client=client, cache_ttl=5), client


def test_historical_native_price_returns_price_at_timestamp():
    sensor, client = sensor_with({"coingecko:ethereum": llama("coingecko:ethereum", 1800.0)})
    result = sensor.historical_native_price("ethereum", TS)
    assert result.determined
    assert result.record.payload["price_usd"] == 1800.0
    assert result.record.payload["at"] == TS
    assert result.record.kind is RecordKind.PRICE
    assert any(f"/prices/historical/{TS}/" in url for url, _ in client.calls)


def test_historical_token_price_uses_platform_and_timestamp():
    coin = "ethereum:0xabc"
    sensor, client = sensor_with({coin: llama(coin, 2.5, symbol="TKN")})
    result = sensor.historical_token_price("ethereum", "0xABC", TS)
    assert result.determined
    assert result.record.payload["price_usd"] == 2.5
    assert result.record.payload["contract"] == "0xabc"
    assert any(f"/prices/historical/{TS}/" in url for url, _ in client.calls)


def test_historical_native_price_unmapped_chain_is_undetermined():
    sensor, _ = sensor_with({})
    result = sensor.historical_native_price("no_such_chain", TS)
    assert not result.determined
    assert result.outcome == "undetermined"


def test_historical_native_price_rejects_nonpositive_timestamp():
    sensor, _ = sensor_with({})
    with pytest.raises(ValueError):
        sensor.historical_native_price("ethereum", 0)


def test_historical_price_is_cached_per_timestamp():
    sensor, client = sensor_with({"coingecko:ethereum": llama("coingecko:ethereum", 1800.0)})
    sensor.historical_native_price("ethereum", TS)
    sensor.historical_native_price("ethereum", TS)
    assert len(client.calls) == 1  # second served from cache
