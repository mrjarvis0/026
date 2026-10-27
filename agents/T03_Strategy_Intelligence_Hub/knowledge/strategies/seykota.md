---
slug: seykota
trader: Ed Seykota
market_origin: futures
mechanical: green
status: implemented
agent: $005-seykota
sources: ["[WP-Seykota]", "[Market-Wizards]", "[Covel]"]
---

# Ed Seykota — EMA trend-following (classic dual-EMA crossover)

## Who & why they matter
Edward Arthur Seykota (b. 1946, MIT EE + Sloan) **pioneered computerized systems trading** in 1970,
testing trend ideas on punched-card / IBM mainframe computers. Jack Schwager's *Market Wizards* calls
his record "among the best traders of our time." `[WP-Seykota]` `[Market-Wizards]` He is a foundational
figure of systematic **trend following**. `[Covel]`

## The exact rules (cited)
- **"Seykota based his first trading system on exponential moving averages."** `[WP-Seykota]` His
  interest grew from **Richard Donchian's** letter on mechanical trend-following and Donchian's **5- and
  20-day moving-average systems**. `[WP-Seykota]` (See sibling agent `$002-donchian`.)
- Core discipline (documented, not exact params): **ride trends, cut losses, add to winners, and use
  strict money management**; he later layered in "more rules, pattern triggers, and money management
  algorithms." `[WP-Seykota]` `[Market-Wizards]`

**Honesty (R-E.3/R-E.5):** Seykota's *exact* system parameters are **proprietary and evolved over
decades** — they are not public. What is documented and citable is that the **core is an
exponential-moving-average trend-following system.** So we implement the canonical **dual-EMA
crossover** as a faithful representation of that documented core, **not** his literal numbers.

## How it becomes a signal
`position ∈ {-1, 0, +1}` from two EMAs of close (no look-ahead; backtester acts next bar):
- `EMA_fast > EMA_slow` → **+1** (uptrend); `EMA_fast < EMA_slow` → **-1** (if `allow_short`) else **0**.
- Flat until both EMAs are warmed up. `allow_short: false` → long-only (for crypto spot).

## Parameters
| Param | Meaning | Default | Range |
|---|---|---|---|
| fast | fast EMA span | 20 | [10, 20, 50] |
| slow | slow EMA span | 100 | [50, 100, 200] |
| allow_short | permit short (stop-and-reverse) | true | [true, false] |

## Open questions / caveats
- EMA crossover is smooth/late vs channel breakouts — expect fewer whipsaws but later entries/exits.
- Seykota's edge included **money management & position sizing** (risk per trade), not modeled by the
  {-1,0,+1} contract — a future version could add ATR-based sizing via the `size` column.

## Sources
- `[WP-Seykota]`, `[Market-Wizards]`, `[Covel]` — see ../sources/SOURCES.md
- Raw evidence: [`seykota.raw.md`](seykota.raw.md)
