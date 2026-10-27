---
slug: donchian
trader: Richard Donchian
market_origin: futures
mechanical: green
status: implemented
agent: $002-donchian
sources: ["[WP-Donchian]", "[WP-DonchianChannel]", "[Kaufman]", "[Covel]"]
---

# Richard Donchian — Donchian channel breakout (trend timing)

## Who & why they matter
Richard Davoud Donchian (1905–1993) — American commodities trader, pioneer of **managed futures**
(started the first publicly managed futures fund, Futures Inc., 1949), and known as **"the father of
trend following."** `[WP-Donchian]` `[Covel]` His rule-based approach assumed commodity prices move in
long, sustained trends; he published the *Commodity Trend Timing* newsletter based on his **5-20
moving-average method** and a **weekly rule** system. `[WP-Donchian]`

## The exact rules (cited)
The mechanical core is the **Donchian channel breakout**: `[WP-DonchianChannel]`
- **Channel:** `Upper = HighestHigh(N)`, `Lower = LowestLow(N)`, `Middle = (Upper+Lower)/2`, with
  **N usually = 20**. `[WP-DonchianChannel]`
- **Entry (long):** price trades **above the highest high of the last N periods** → establish long.
  `[WP-DonchianChannel]`
- **Entry (short):** price trades **below the lowest low of the last N periods** → establish short.
  `[WP-DonchianChannel]`
- It is a **stop-and-reverse** system — always in the market, flipping long↔short on the opposite
  breakout (the basis of the classic **4-week / weekly rule**, N=20 trading days ≈ 4 weeks). `[Kaufman]`

**Also his (not implemented here):** the **5-20 dual moving-average** crossover method (buy when the
5-day MA crosses above the 20-day MA, sell when below). `[WP-Donchian]` `[Kaufman]` — a good future
variant/mode.

## How it becomes a signal
`position ∈ {-1, 0, +1}` from the N-period channel (prior-bar windows via `.shift(1)`; the backtester
acts next bar → no look-ahead):
- close > prior-N-day high → **+1** (long); close < prior-N-day low → **-1** (short); otherwise
  **hold** the current position (stop-and-reverse → almost always fully invested).
- `allow_short=false` makes it long-only (short signal → flat), suitable for crypto spot.

## Parameters
| Param | Meaning | Default | Range |
|---|---|---|---|
| channel | N periods for the high/low channel | 20 | [10, 20, 40, 55] |
| allow_short | permit short positions (stop-and-reverse) | true | [true, false] |

## Open questions / caveats
- Wikipedia cites a large backtest (4,887 trades, N=20) with a **~35% win rate** and 2:1 reward:risk —
  positive expectancy but **marginal after slippage**. `[WP-DonchianChannel]` Trend systems win seldom
  but big; judge on Sharpe/profit-factor, not win rate.
- The exact weekly-rule numbers (4 weeks = 20 trading days) come from trading literature `[Kaufman]`;
  the N=20 channel + breakout logic is directly from the source. Re-verify the 5-20 MA specifics
  before building that mode (R-E.6).

## Sources
- `[WP-Donchian]`, `[WP-DonchianChannel]`, `[Kaufman]`, `[Covel]` — see ../sources/SOURCES.md
- Raw evidence: [`donchian.raw.md`](donchian.raw.md)
