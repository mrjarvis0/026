# `$009-scalper` — Futures Scalper Agent

- **Serial:** $009
- **Owner:** System (not a historical trader — a synthetic strategy)
- **Market:** crypto (Binance USD-M Futures Testnet)
- **Status:** implemented
- **Created:** 2026-10-27

---

## Mission

A 24/7 futures scalper that goes **long and short** on BTC/USDT using the full
signal fusion pipeline:

1. **Scanner consensus** — all 8 `$001–$008` strategies vote on the current symbol
2. **MTF alignment** — 1m/5m/15m/1h multi-timeframe EMA/ADX trend check
3. **Next-candle probability** — calibrated LogReg model; only used if OOS accuracy ≥ 52%
4. **Sentiment** — Fear & Greed + CoinGecko (small weight, experimental)
5. **RiskEngine** — capital-preservation enforcer: risk-based sizing, leverage cap,
   daily-loss halt, max-drawdown halt

## Honest scope (R-E.3 / R-E.5)

- **Testnet only.** Dry-run by default. `--arm --confirm I-CONFIRM-PAPER-ORDER` to transmit.
- **"100x profit per day" is not achievable reliably.** The review will show the real numbers.
- **Next-candle prediction is 52–58% on a good day** — a small edge, not a crystal ball.
- Leveraged gaps and liquidations mean no system is 100% ruin-proof. The RiskEngine
  makes ruin very unlikely, not impossible (R-E.5).

## Signal rules (cited from SCALPER.md)

```
TRADE if:
    MTF alignment != 0  (chop = stand aside, no exceptions)
    AND scanner strength >= 50%
    AND |p_up - 0.5| >= 0.02   (if model OOS accuracy >= 52%)
    AND overall fused confidence >= 55%

DIRECTION = sign of weighted vote (MTF 40%, scanner 35%, predict 20%, sentiment 5%)

SIZE = RiskEngine.position_size(equity, price, stop=ATR14)
     ≤ max_leverage × equity / price  (never maximise leverage)
```

## Risk limits (overridable in config.yaml)

| Limit | Value |
|---|---|
| Leverage cap | 5× (cross-margin) |
| Risk per trade | 1% of equity |
| Daily loss halt | -5% on the day |
| Max drawdown halt | -25% from peak |
| Max trades/day | 50 |

## Status

- Pipeline: ✅ built (SCALPER.md components 1–8)
- Backtest: ⏳ not yet run (run `python scripts/run_scalper.py $009 --backtest`)
- OOS accuracy: not measured (run first, then check `results/predictor_state.json`)
- Paper-trade (testnet): requires Futures Testnet keys in `.env`
