---
slug: williams
trader: Larry Williams
market_origin: futures
mechanical: green
status: implemented
agent: $004-williams
sources: ["[WP-LWilliams]", "[LW-Book]"]
---

# Larry Williams — Volatility Breakout (short-term)

## Who & why they matter
Larry Richard Williams (b. 1942) — American commodity trader & author; creator of **Williams %R**, the
**Ultimate Oscillator**, and COT indices. He won the **1987 World Cup Championship of Futures Trading**,
turning $10,000 into **$1,137,600 (+11,376%) in 12 months**. `[WP-LWilliams]` His short-term methods are
set out in *Long-Term Secrets to Short-Term Trading* (Wiley, 1998). `[WP-LWilliams]` `[LW-Book]`

## The exact rules (cited)
**Volatility Breakout** — an intraday momentum-thrust entry keyed to the *prior day's range*: `[LW-Book]`
- **Range** = `High[t-1] − Low[t-1]` (previous bar's range).
- **Long trigger** = `Open[t] + k × Range[t-1]`  (buy stop above the open).
- **Short trigger** = `Open[t] − k × Range[t-1]`  (sell stop below the open).
- **k** ≈ 0.5 (commonly 0.3–1.0). A move of k×(yesterday's range) beyond today's open signals a thrust.
- Classic exit: **at the close** (day trade) or after a short hold.

Different "flavor" from trend-following channel systems ($001–$003): it is **short-term, active, and
volatility-scaled**, not a hold-the-trend system.

## How it becomes a signal
Our engine is **daily Close-to-Close with next-bar execution**, so it cannot fill an intraday stop at
the trigger price without look-ahead. Faithful adaptation (stated simplification, R-E.5):
- Use a **close-confirmed** breakout: `+1` if `Close[t] > Open[t] + k×Range[t-1]`; `-1` if
  `Close[t] < Open[t] − k×Range[t-1]`; else `0`.
- Hold the signal for `hold_days` bars (default 1 → a short-term swing), then flat unless re-triggered.
- `allow_short=false` → long-only (for crypto spot).

This keeps the volatility-scaled thrust idea but is a **1-day-hold swing**, not the same-day daytrade of
the original (which needs intraday fills). Re-verify the exact k/exit against the book before live use (R-E.6).

## Parameters
| Param | Meaning | Default | Range |
|---|---|---|---|
| k | breakout multiple of prior-day range | 0.5 | [0.3, 0.5, 0.8, 1.0] |
| hold_days | bars to hold after a trigger | 1 | [1, 2, 3] |
| allow_short | permit short thrusts | true | [true, false] |

## Open questions / caveats
- The original is an **intraday daytrade**; the daily adaptation will differ from book results. A future
  version could add an intraday-aware backtest path.
- Short-term systems trade often → **commission/slippage sensitive**; watch turnover and profit factor.

## Sources
- `[WP-LWilliams]`, `[LW-Book]` — see ../sources/SOURCES.md
- Raw evidence: [`williams.raw.md`](williams.raw.md)
