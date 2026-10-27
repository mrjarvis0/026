# `$009-scalper` — Futures Scalper

A synthetic scalper that fuses all 8 strategy agents' signals with multi-timeframe
analysis, a calibrated next-candle predictor, and sentiment data.

See [`$009-scalper.agent.md`](./%24009-scalper.agent.md) for the full spec.

## Quick start

```bash
# From T03 root — dry-run (safe: nothing sent)
python scripts/run_scalper.py '$009-scalper'

# Arm it (needs BINANCE_FUTURES_TESTNET_API_KEY/SECRET in .env)
python scripts/run_scalper.py '$009-scalper' --arm --confirm I-CONFIRM-PAPER-ORDER

# Continuous loop
python scripts/run_scalper.py '$009-scalper' --loop
```

## Safety

- Testnet only; dry-run by default.
- RiskEngine circuit breakers: -5% daily halt, -25% DD halt, 1% risk/trade.
- Pre-trade guard warns if this pattern has historically lost money.
- chop (MTF alignment = 0) → stand aside, no exceptions.
