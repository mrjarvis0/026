---
slug: oneil
trader: William O'Neil
market_origin: stocks
mechanical: yellow
status: implemented
agent: $007-oneil
sources: ["[WP-ONeil]", "[Investopedia-CANSLIM]", "[ONeil]"]
---

# William O'Neil — CANSLIM (technical subset)

## Who & why they matter
William J. O'Neil (1933–2023) — stockbroker, founder of **William O'Neil & Co** (1963) and **Investor's
Business Daily** (1984), author of *How to Make Money in Stocks*, creator of the **CAN SLIM** growth-stock
system. `[WP-ONeil]` `[ONeil]`

## The exact rules (cited)
CANSLIM = **fundamental + technical** growth-stock selection. Each letter: `[Investopedia-CANSLIM]`
- **C** — Current quarterly EPS up sharply (>25% YoY). *(fundamental)*
- **A** — Annual EPS growth >25% over 3–5 yrs. *(fundamental)*
- **N** — New products/events pushing the stock to **new price highs**. *(technical)*
- **S** — Supply & demand: shares outstanding + **volume** on the move. *(technical)*
- **L** — **Leader** not laggard: high relative strength / leading group. *(technical)*
- **I** — Institutional sponsorship. *(fundamental)*
- **M** — **Market direction**: only buy when the general market is in an uptrend. *(technical)*

Plus O'Neil's signature risk rule: **cut every loss at ~7–8%** below the buy price. `[ONeil]`

## Honesty: what we can and cannot model (R-E.3 / R-E.5)
This agent targets **crypto (a single asset, BTC)**, which has **no earnings, no institutions, no
industry group** — so **C, A, I are impossible to model** and are **omitted**. Relative strength (L)
against a universe is also N/A on one asset. We implement the **technical shell only**:
- **N** — breakout to a new high over a base (`base_period`).
- **S** — breakout on above-average **volume** (`vol_confirm`).
- **M** — buy only when `close > SMA(market_ma)` (market/trend up).
- **L** — approximated as trend leadership (the same MA/breakout filters).
- **Risk** — O'Neil's **7–8% stop** + exit on trend break (`close < SMA(exit_ma)`).

This is **CANSLIM-technical**, not CANSLIM. On stocks with a fundamentals feed, C/A/I could be added.

## How it becomes a signal
`position ∈ {0, +1}` (long-only; O'Neil goes to cash, never short), prior-bar windows + next-bar
execution → no look-ahead:
- **Enter** when close > highest high of prior `base_period` bars **and** close > SMA(`market_ma`)
  **and** (if `vol_confirm`) volume > its `vol_period` average.
- **Exit** when close falls > `stop_pct` below entry (7–8% rule) **or** close < SMA(`exit_ma`).

## Parameters
| Param | Meaning | Default | Range |
|---|---|---|---|
| base_period | N: new-high breakout lookback | 50 | [20, 50, 100] |
| market_ma | M: market/trend filter SMA | 200 | [100, 200] |
| exit_ma | trend-break exit SMA | 50 | (fixed) |
| stop_pct | O'Neil 7–8% loss cut | 0.08 | (fixed) |
| vol_confirm | S: above-average breakout volume | true | [true, false] |

## Open questions / caveats
- Bullish strategy for fast markets; CANSLIM stocks "decline quickly if the market shifts."
  `[Investopedia-CANSLIM]` The M filter is meant to keep us out during downtrends.
- The fundamental engine (C/A/I) is the heart of real CANSLIM — this crypto version is a shadow of it.
  A stocks version with earnings data (R-E.6) would be far more faithful.

## Sources
- `[WP-ONeil]`, `[Investopedia-CANSLIM]`, `[ONeil]` — see ../sources/SOURCES.md
- Raw evidence: [`oneil.raw.md`](oneil.raw.md)
