# Review — `$004-williams`

- **Generated:** 2026-08-29
- **Market / symbols:** crypto / BTC/USDT
- **Timeframe:** 1d
- **Backtest engine:** vectorized
- **Window:** 7.666 years (2798 bars)

## Verdict

❌ Does not beat buy-&-hold here. Needs rework or a different regime/market.

## Headline metrics

| Metric | Strategy | Buy & Hold |
|---|---|---|
| Total return | 440.35% | 1947.97% |
| CAGR | 24.62% | 48.27% |
| Sharpe | 0.704 | 0.953 |
| Sortino | 0.922 | — |
| Calmar | 0.425 | — |
| Max drawdown | -57.95% | -76.63% |
| Ann. volatility | 46.43% | — |
| Exposure | 66.94% | 100% |

## Trade quality

- **Trades:** 305
- **Win rate:** 38.03%
- **Profit factor:** 1.511
- **Avg trade:** 1.11%

![Equity curve](backtest/equity_curve.png)

## Walk-forward (out-of-sample) validation

- **Folds:** 4
- **OOS mean sharpe:** 0.318
- **Recommended params:** `{'allow_short': False, 'hold_days': 3, 'k': 0.3}`

> Out-of-sample is the number that matters; strong in-sample with weak OOS = overfit.

## Notes & caveats

- Historical simulation only. **Not financial advice**; past performance ≠ future results.
- Costs modeled: commission only (see metrics meta). Slippage, funding, and liquidity are not fully modeled.
- Re-run on out-of-sample / a second symbol before trusting. Paper-trade before any real capital (human-gated).
