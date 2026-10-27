---
slug: tudorjones
trader: Paul Tudor Jones
market_origin: futures
mechanical: yellow
status: implemented
agent: $008-tudorjones
sources: ["[WP-PTJ]", "[PTJ-200MA]", "[Market-Wizards]"]
---

# Paul Tudor Jones — the 200-day MA rule (defensive trend/regime filter)

## Who & why they matter
Paul Tudor Jones II — founder of **Tudor Investment Corporation** (~$12B AUM), one of the great
**global macro** traders. Famously **predicted & profited from 1987 Black Monday** (+125.9% after fees,
~$100M, via large shorts). His style is "based primarily on **technical analysis... with an emphasis on
momentum**," not value; he has also said he owns bitcoin as an inflation hedge. `[WP-PTJ]` `[Market-Wizards]`

## The exact rule (cited)
PTJ's actual trading is **discretionary macro** (🔴 not mechanically reproducible), but his single most
famous, quotable, mechanical heuristic is the **200-day moving-average rule**: `[PTJ-200MA]`
- **"My metric for everything I look at is the 200-day moving average of closing prices... nothing good
  happens below the 200-day moving average."** The idea: stay invested while price is **above** its
  200-day MA; **get out (play defense)** when it drops **below**. A capital-preservation regime filter.

## How it becomes a signal
`position ∈ {-1, 0, +1}`, prior-bar-safe (SMA of closes through the current bar is known at its close;
backtester acts next bar → no look-ahead):
- **Long (+1)** while `close > SMA(ma_period)`.
- **Flat (0)** while below (the "get out / play defense" rule) — or **short (-1)** if `allow_short`
  (PTJ did short, e.g. 1987; but the rule itself is about *getting out*, so long-only-to-cash is default).
- Optional `confirm_days` requires N consecutive closes on one side before flipping (whipsaw filter).

## Parameters
| Param | Meaning | Default | Range |
|---|---|---|---|
| ma_period | moving-average length (his rule = 200) | 200 | [100, 150, 200] |
| allow_short | short below the MA vs go to cash | false | [true, false] |
| confirm_days | consecutive closes needed to flip | 1 | [1, 3] |

## Open questions / caveats
- This is **one heuristic**, not PTJ's real macro process (which reads fundamentals, positioning,
  intermarket flows, sentiment) — honestly a shadow of his method (R-E.5).
- The exact quote wording/source should be re-verified (R-E.6); the 200-day MA rule attribution is
  widely documented across his interviews.
- As a pure regime filter it will resemble a slow trend follower; on strongly-trending BTC expect solid
  drawdown control but return capped by time spent in cash.

## Sources
- `[WP-PTJ]`, `[PTJ-200MA]`, `[Market-Wizards]` — see ../sources/SOURCES.md
- Raw evidence: [`tudorjones.raw.md`](tudorjones.raw.md)
