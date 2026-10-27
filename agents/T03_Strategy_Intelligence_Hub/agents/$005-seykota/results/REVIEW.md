# Review — `$005-seykota`

- **Generated:** 2026-08-29
- **Market / symbols:** crypto / BTC/USDT
- **Timeframe:** 1d
- **Backtest engine:** vectorized
- **Window:** 7.666 years (2798 bars)

## Verdict

✅ Beats buy-&-hold on both total return and risk-adjusted (Sharpe).

## Headline metrics

| Metric | Strategy | Buy & Hold |
|---|---|---|
| Total return | 2709.19% | 1947.97% |
| CAGR | 54.51% | 48.27% |
| Sharpe | 1.212 | 0.953 |
| Sortino | 1.318 | — |
| Calmar | 1.096 | — |
| Max drawdown | -49.73% | -76.63% |
| Ann. volatility | 43.79% | — |
| Exposure | 53.97% | 100% |

## Trade quality

- **Trades:** 30
- **Win rate:** 50.00%
- **Profit factor:** 6.662
- **Avg trade:** 21.23%

![Equity curve](backtest/equity_curve.png)

## Walk-forward (out-of-sample) validation

- **Folds:** 4
- **OOS mean sharpe:** 0.981
- **Recommended params:** `{'allow_short': False, 'fast': 10, 'slow': 50}`

> Out-of-sample is the number that matters; strong in-sample with weak OOS = overfit.

## Notes & caveats

- Historical simulation only. **Not financial advice**; past performance ≠ future results.
- Costs modeled: commission only (see metrics meta). Slippage, funding, and liquidity are not fully modeled.
- Re-run on out-of-sample / a second symbol before trusting. Paper-trade before any real capital (human-gated).
