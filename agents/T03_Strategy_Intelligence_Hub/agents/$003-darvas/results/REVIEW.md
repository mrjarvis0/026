# Review — `$003-darvas`

- **Generated:** 2026-08-29
- **Market / symbols:** crypto / BTC/USDT
- **Timeframe:** 1d
- **Backtest engine:** vectorized
- **Window:** 7.666 years (2798 bars)

## Verdict

🟡 Beats buy-&-hold on risk-adjusted return (Sharpe) but not raw return.

## Headline metrics

| Metric | Strategy | Buy & Hold |
|---|---|---|
| Total return | 1494.22% | 1947.97% |
| CAGR | 43.51% | 48.27% |
| Sharpe | 1.077 | 0.953 |
| Sortino | 1.153 | — |
| Calmar | 0.795 | — |
| Max drawdown | -54.74% | -76.63% |
| Ann. volatility | 41.44% | — |
| Exposure | 48.89% | 100% |

## Trade quality

- **Trades:** 36
- **Win rate:** 50.00%
- **Profit factor:** 4.426
- **Avg trade:** 15.45%

![Equity curve](backtest/equity_curve.png)

## Walk-forward (out-of-sample) validation

- **Folds:** 4
- **OOS mean sharpe:** 0.714
- **Recommended params:** `{'box_period': 20, 'stop_period': 10, 'vol_confirm': False}`

> Out-of-sample is the number that matters; strong in-sample with weak OOS = overfit.

## Notes & caveats

- Historical simulation only. **Not financial advice**; past performance ≠ future results.
- Costs modeled: commission only (see metrics meta). Slippage, funding, and liquidity are not fully modeled.
- Re-run on out-of-sample / a second symbol before trusting. Paper-trade before any real capital (human-gated).
