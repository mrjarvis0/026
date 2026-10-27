# Review — `$008-tudorjones`

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
| Total return | 2002.15% | 1947.97% |
| CAGR | 48.78% | 48.27% |
| Sharpe | 1.123 | 0.953 |
| Sortino | 1.223 | — |
| Calmar | 1.013 | — |
| Max drawdown | -48.15% | -76.63% |
| Ann. volatility | 43.93% | — |
| Exposure | 55.18% | 100% |

## Trade quality

- **Trades:** 20
- **Win rate:** 35.00%
- **Profit factor:** 8.069
- **Avg trade:** 34.48%

![Equity curve](backtest/equity_curve.png)

## Walk-forward (out-of-sample) validation

- **Folds:** 4
- **OOS mean sharpe:** 0.651
- **Recommended params:** `{'allow_short': False, 'confirm_days': 3, 'ma_period': 100}`

> Out-of-sample is the number that matters; strong in-sample with weak OOS = overfit.

## Notes & caveats

- Historical simulation only. **Not financial advice**; past performance ≠ future results.
- Costs modeled: commission only (see metrics meta). Slippage, funding, and liquidity are not fully modeled.
- Re-run on out-of-sample / a second symbol before trusting. Paper-trade before any real capital (human-gated).
