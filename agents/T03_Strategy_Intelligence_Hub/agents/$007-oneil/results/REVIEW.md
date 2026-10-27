# Review — `$007-oneil`

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
| Total return | 2508.21% | 1947.97% |
| CAGR | 53.02% | 48.27% |
| Sharpe | 1.282 | 0.953 |
| Sortino | 1.244 | — |
| Calmar | 1.306 | — |
| Max drawdown | -40.62% | -76.63% |
| Ann. volatility | 39.12% | — |
| Exposure | 40.96% | 100% |

## Trade quality

- **Trades:** 27
- **Win rate:** 59.26%
- **Profit factor:** 9.792
- **Avg trade:** 22.43%

![Equity curve](backtest/equity_curve.png)

## Walk-forward (out-of-sample) validation

- **Folds:** 4
- **OOS mean sharpe:** 1.047
- **Recommended params:** `{'base_period': 20, 'market_ma': 100, 'vol_confirm': True}`

> Out-of-sample is the number that matters; strong in-sample with weak OOS = overfit.

## Notes & caveats

- Historical simulation only. **Not financial advice**; past performance ≠ future results.
- Costs modeled: commission only (see metrics meta). Slippage, funding, and liquidity are not fully modeled.
- Re-run on out-of-sample / a second symbol before trusting. Paper-trade before any real capital (human-gated).
