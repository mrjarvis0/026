---
slug: dennis
trader: Richard Dennis
market_origin: futures
mechanical: green
status: implemented
agent: $001-dennis
sources: ["[Turtle-Rules]", "[Curtis-Faith]"]
---

# Richard Dennis — Turtle Trading (Donchian breakout)

## Who & why they matter
Richard Dennis & William Eckhardt ran the 1980s "Turtles" experiment proving trading could be taught
as a mechanical rule set. `[Curtis-Faith]`

## The exact rules (cited)
- **Entry:** breakout of the 20-day (System 1) or 55-day (System 2) high/low. `[Turtle-Rules]`
- **Exit:** opposite breakout of the 10-day (System 1) or 20-day (System 2) channel. `[Turtle-Rules]`
- **Position sizing / risk:** volatility "N" = 20-day ATR; size in Units risking a fixed fraction per
  Unit; pyramid as trend runs; ATR stop. `[Turtle-Rules]`

## How it becomes a signal
`position ∈ {-1,0,+1}` from Donchian breakouts (prior-bar channels via `.shift(1)`; backtester acts
next bar → no look-ahead). **Simplification:** ATR sizing & pyramiding are not modeled — every
position is full size. Captures the timing edge, not the full risk management.

## Parameters
| Param | Meaning | Default | Range |
|---|---|---|---|
| entry_donchian | breakout entry window | 20 | [20, 55] |
| exit_donchian | opposite-breakout exit | 10 | [10, 20] |
| allow_short | permit shorts | true | [true, false] |

## Open questions / caveats
- On BTC 2019–2026, long-only (allow_short=false) validated better out-of-sample than shorting.
- ATR sizing/pyramiding would change the risk profile materially — a worthwhile v2.

## Sources
- `[Turtle-Rules]`, `[Curtis-Faith]` — see ../sources/SOURCES.md
