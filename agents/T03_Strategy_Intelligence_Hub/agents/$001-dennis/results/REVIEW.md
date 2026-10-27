# Review — `$001-dennis`

- **Generated:** 2026-08-28
- **Market / symbols:** crypto / BTC/USDT
- **Timeframe:** 1d
- **Backtest engine:** vectorized
- **Window:** 7.663 years (2797 bars)

## Verdict

❌ Does not beat buy-&-hold here. Needs rework or a different regime/market.

## Headline metrics

| Metric | Strategy | Buy & Hold |
|---|---|---|
| Total return | 297.81% | 1935.15% |
| CAGR | 19.74% | 48.17% |
| Sharpe | 0.598 | 0.952 |
| Sortino | 0.748 | — |
| Calmar | 0.291 | — |
| Max drawdown | -67.74% | -76.63% |
| Ann. volatility | 55.78% | — |
| Exposure | 73.97% | 100% |

## Trade quality

- **Trades:** 74
- **Win rate:** 40.54%
- **Profit factor:** 2.174
- **Avg trade:** 6.09%

![Equity curve](backtest/equity_curve.png)

## Walk-forward (out-of-sample) validation

- **Folds:** 4
- **OOS mean sharpe:** 0.731
- **Recommended params:** `{'allow_short': False, 'entry_donchian': 20, 'exit_donchian': 20}`

> Out-of-sample is the number that matters; strong in-sample with weak OOS = overfit.

## Notes & caveats

- Historical simulation only. **Not financial advice**; past performance ≠ future results.
- Costs modeled: commission only (see metrics meta). Slippage, funding, and liquidity are not fully modeled.
- Re-run on out-of-sample / a second symbol before trusting. Paper-trade before any real capital (human-gated).
