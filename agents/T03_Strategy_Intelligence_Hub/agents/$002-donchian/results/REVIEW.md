# Review — `$002-donchian`

- **Generated:** 2026-08-28
- **Market / symbols:** crypto / BTC/USDT
- **Timeframe:** 1d
- **Backtest engine:** vectorized
- **Window:** 7.663 years (2797 bars)

## Verdict

🟡 Beats buy-&-hold on risk-adjusted return (Sharpe) but not raw return.

## Headline metrics

| Metric | Strategy | Buy & Hold |
|---|---|---|
| Total return | 1811.73% | 1935.15% |
| CAGR | 46.97% | 48.17% |
| Sharpe | 1.066 | 0.952 |
| Sortino | 1.277 | — |
| Calmar | 0.966 | — |
| Max drawdown | -48.60% | -76.63% |
| Ann. volatility | 46.00% | — |
| Exposure | 62.60% | 100% |

## Trade quality

- **Trades:** 29
- **Win rate:** 55.17%
- **Profit factor:** 4.880
- **Avg trade:** 18.87%

![Equity curve](backtest/equity_curve.png)

## Walk-forward (out-of-sample) validation

- **Folds:** 4
- **OOS mean sharpe:** 0.705
- **Recommended params:** `{'allow_short': False, 'channel': 20}`

> Out-of-sample is the number that matters; strong in-sample with weak OOS = overfit.

## Notes & caveats

- Historical simulation only. **Not financial advice**; past performance ≠ future results.
- Costs modeled: commission only (see metrics meta). Slippage, funding, and liquidity are not fully modeled.
- Re-run on out-of-sample / a second symbol before trusting. Paper-trade before any real capital (human-gated).
