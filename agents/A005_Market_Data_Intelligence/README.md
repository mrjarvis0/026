# A005 — Market Data Intelligence (empty scaffold)

> **Status: empty scaffold** — folder + this note only. No code / manifest /
> registry entry yet. A-series (read-only intelligence). Build deferred.

**Layer:** Data / Ingestion · **Markets:** crypto · forex · stocks

## What it will do
Owns raw market microstructure: OHLCV, quotes, and Level-2 order book. Derives
order-flow evidence — bid/ask imbalance, large / iceberg order detection, and
liquidity zones — read-only, as fuel for the analysis and risk agents.

## Reserved slot
A005 was already reserved in `AGENTS.md` §3 as *"Market Data Intelligence —
OHLCV / quotes / orderbook across crypto, equities, FX."*

**Maps to:** operator research #6 (OrderFlowAgent) + the market-data feeds.
