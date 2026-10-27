---
slug: darvas
trader: Nicolas Darvas
market_origin: stocks
mechanical: green
status: implemented
agent: $003-darvas
sources: ["[WP-Darvas]", "[Investopedia-Darvas]", "[Darvas]"]
---

# Nicolas Darvas — Box Theory (breakout on volume, trailing stop)

## Who & why they matter
Nicolas Darvas (1920–1977) — a professional dancer who, trading only from weekly *Barron's* price &
volume data while touring, reportedly turned ~$10,000 into ~$2,000,000 in 1957–1959. He wrote *How I
Made $2,000,000 in the Stock Market* (1960) describing his **"BOX theory."** `[WP-Darvas]`
`[Investopedia-Darvas]` `[Darvas]`

## The exact rules (cited)
- **The box:** a stock's recent **low = floor**, recent **high = ceiling**; while price stays inside,
  wait. Draw boxes along highs/lows; only trade **rising boxes** (uptrend). `[WP-Darvas]` `[Investopedia-Darvas]`
- **Entry (long):** **buy when price breaks above the ceiling** of the current box — a new high — on
  **strong/increasing volume**. `[WP-Darvas]` `[Investopedia-Darvas]`
- **Stop-loss:** set **just under the trade price / box floor**; as new higher boxes are breached,
  **trail the stop up** to the new box levels. `[WP-Darvas]` `[Investopedia-Darvas]`
- **Add / exit:** pyramid ("I would buy more") as the trend runs; **exit when the trailing stop is
  hit** ("when the trend reversed, I would run like a thief"). `[Investopedia-Darvas]`
- **Long-only.** Darvas bought new highs; he did not short. `[Investopedia-Darvas]`

**Discretionary part (be honest, R-E.5):** Darvas was a self-described "techno-fundamentalist" — he
also picked **growth industries** with strong earnings. `[Investopedia-Darvas]` That fundamental
filter is 🔴 not backtestable from OHLCV and is **not** modeled here; we implement the mechanical
price+volume box breakout only.

## How it becomes a signal
`position ∈ {0, +1}` (long-only), via prior-bar windows (`.shift(1)`; backtester acts next bar → no
look-ahead):
- **box ceiling** = highest high of prior `box_period` bars; **box floor (trailing stop)** = lowest
  low of prior `stop_period` bars.
- **Enter long** when close > box ceiling **and** (if `vol_confirm`) breakout-bar volume > average
  volume over `vol_period`.
- **Exit to flat** when close < box floor (trailing stop). Never short.

## Parameters
| Param | Meaning | Default | Range |
|---|---|---|---|
| box_period | ceiling-breakout lookback | 20 | [20, 40, 55] |
| stop_period | trailing-stop (floor) lookback | 10 | [10, 20] |
| vol_confirm | require above-average breakout volume | true | [true, false] |
| vol_period | volume-average window | 20 | (fixed) |

## Open questions / caveats
- Works best in **bullish/trending** markets (Investopedia notes it produces small losses when trends
  fail). `[Investopedia-Darvas]`
- Exact "box" formation (3-day unbroken high/low) is a discretionary detail in the book; we
  approximate the box with rolling extremes — re-verify against the book if tightening (R-E.6).

## Sources
- `[WP-Darvas]`, `[Investopedia-Darvas]`, `[Darvas]` — see ../sources/SOURCES.md
- Raw evidence: [`darvas.raw.md`](darvas.raw.md)
