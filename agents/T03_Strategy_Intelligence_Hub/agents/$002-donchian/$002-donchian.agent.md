# `$002-donchian` — Richard Donchian, Donchian channel breakout

- **Serial:** $002
- **Owner (trader):** Richard Donchian — "father of trend following"
- **Market:** crypto (start: BTC/USDT, daily)
- **Strategy:** Donchian channel breakout — the weekly / 4-week trend-timing rule
- **Created:** 2026-08-28
- **Binding law:** inherits [`../../AGENT_CONSTITUTION.md`](../../../AGENT_CONSTITUTION.md) and the [hub spec](../../%24trategy-master.agent.md).
- **Research dossier:** [`../../knowledge/strategies/donchian.md`](../../knowledge/strategies/donchian.md)

## 1. The trader & the strategy (research)

Richard Davoud Donchian (1905–1993) pioneered **managed futures** and rule-based **trend following**,
publishing the *Commodity Trend Timing* newsletter built on his **5-20 moving-average method** and a
**weekly rule** system. `[WP-Donchian]` `[Covel]`

**Donchian channel breakout (the mechanical core):** `[WP-DonchianChannel]`
- `Upper = HighestHigh(N)`, `Lower = LowestLow(N)`, `Middle = (Upper+Lower)/2`, **N usually = 20**.
- **Long** when price trades **above the highest high of the last N periods**.
- **Short** when price trades **below the lowest low of the last N periods**.
- **Stop-and-reverse** → almost always in the market (the classic **4-week rule**, N=20 ≈ 4 weeks). `[Kaufman]`

## 2. How it maps to signals

`strategy.py` (`DonchianStrategy`) emits `position ∈ {-1, 0, +1}`:
- close > prior-N-day high → **+1**; close < prior-N-day low → **-1**; else **hold** current position.
- Channels use `.shift(1)` and the backtester acts next bar → **no look-ahead**.
- `allow_short: false` → long-only (short signal goes flat), for crypto spot.

**Not modeled (be honest, R-E.5):** Donchian's separate **5-20 dual-MA** method and any volatility
filters — a good future variant. This agent implements the channel-breakout rule only.

## 3. Parameters

| Param | Meaning | Default | Search range |
|---|---|---|---|
| `channel` | N periods for the high/low channel | 20 | [10, 20, 40, 55] |
| `allow_short` | permit shorts (stop-and-reverse) | true | [true, false] |

## 4. Backtest & review

- Config: [`config.yaml`](config.yaml) · Implementation: [`strategy.py`](strategy.py)
- Latest review: [`results/REVIEW.md`](results/REVIEW.md)

## 5. Caveat (cited)

A large published backtest (4,887 trades, N=20) showed a **~35% win rate** with 2:1 reward:risk —
positive expectancy but marginal after slippage. `[WP-DonchianChannel]` Trend systems win seldom but
big; judge on Sharpe / profit factor, not win rate.

## 6. Sources

- `[WP-Donchian]`, `[WP-DonchianChannel]`, `[Kaufman]`, `[Covel]` — resolved in
  [`../../knowledge/sources/SOURCES.md`](../../knowledge/sources/SOURCES.md).
