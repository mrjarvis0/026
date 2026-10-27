# Review — `$006-raschke`

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
| Total return | -39.16% | 1947.97% |
| CAGR | -6.28% | 48.27% |
| Sharpe | 0.011 | 0.953 |
| Sortino | 0.008 | — |
| Calmar | -0.096 | — |
| Max drawdown | -65.75% | -76.63% |
| Ann. volatility | 36.12% | — |
| Exposure | 26.66% | 100% |

## Trade quality

- **Trades:** 105
- **Win rate:** 55.24%
- **Profit factor:** 1.044
- **Avg trade:** 0.13%

![Equity curve](backtest/equity_curve.png)

## Walk-forward (out-of-sample) validation

- **Folds:** 4
- **OOS mean sharpe:** 0.122
- **Recommended params:** `{'allow_short': False, 'hold_days': 5, 'lookback': 10}`

> Out-of-sample is the number that matters; strong in-sample with weak OOS = overfit.

## Notes & caveats

- Historical simulation only. **Not financial advice**; past performance ≠ future results.
- Costs modeled: commission only (see metrics meta). Slippage, funding, and liquidity are not fully modeled.
- Re-run on out-of-sample / a second symbol before trusting. Paper-trade before any real capital (human-gated).
