---
slug: raschke
trader: Linda Bradford Raschke
market_origin: futures
mechanical: green
status: implemented
agent: $006-raschke
sources: ["[WP-Raschke]", "[Street-Smarts]", "[Market-Wizards]"]
---

# Linda Raschke — "Turtle Soup" (short-term false-breakout reversal / mean-reversion)

## Who & why they matter
Linda Bradford Raschke (b. 1959) — futures trader, hedge-fund manager (LBRGroup, Granat Fund), and
technical analyst; featured in Schwager's *The New Market Wizards* (1992). `[WP-Raschke]`
`[Market-Wizards]` She co-authored **Street Smarts: High Probability Short-Term Trading Strategies**
(with Larry Connors, 1995) — a widely referenced book of short-term setups. `[WP-Raschke]`
`[Street-Smarts]` This is the hub's first **mean-reversion** agent (vs the trend/breakout agents
$001–$005).

## The exact rules (cited)
**"Turtle Soup"** — a **fade of a false breakout** (deliberately the opposite of the Turtles' $001
breakout entry): `[Street-Smarts]`
- **Buy setup:** market makes a **new 20-day low**, then **reverses back up** through the prior low
  (a failed breakdown). Enter long on the reversal; stop below the day's low; **exit within a few days**
  (short-term). `[Street-Smarts]`
- **Sell setup:** mirror — a **new 20-day high** that fails and reverses back below the prior high →
  short. `[Street-Smarts]`

She also documented other short-term setups (80-20's, Holy Grail ADX pullback, the Anti); Turtle Soup
is the cleanest to backtest and the most iconic. `[Street-Smarts]`

## How it becomes a signal
Daily adaptation to `position ∈ {-1, 0, +1}` (prior-bar windows via `.shift(1)`, act next bar → no
look-ahead):
- `prior_low = min(Low, N).shift(1)`, `prior_high = max(High, N).shift(1)`.
- **Long** when `Low < prior_low` (dipped below the N-day low) **and** `Close > prior_low` (closed back
  above → false breakdown).
- **Short** when `High > prior_high` **and** `Close < prior_high` (false breakout), if `allow_short`.
- Hold `hold_days` bars, then flat (short-term mean-reversion).

**Simplification (R-E.5):** the book uses an intraday buy-stop just above the prior low and a next-bar
time/stop exit; we approximate with a **close-confirmed** reversal + fixed-bar hold on daily data.

## Parameters
| Param | Meaning | Default | Range |
|---|---|---|---|
| lookback | N-day high/low that gets faded | 20 | [10, 20, 55] |
| hold_days | bars to hold the reversal | 3 | [1, 3, 5] |
| allow_short | fade false breakouts (up) too | true | [true, false] |

## Open questions / caveats
- Mean-reversion **fights** strong trends — expect it to behave very differently from $001–$005; may do
  poorly in one-way markets and better in choppy ranges.
- Original entry/stop are intraday; re-verify exact trigger/stop against *Street Smarts* before live use (R-E.6).

## Sources
- `[WP-Raschke]`, `[Street-Smarts]`, `[Market-Wizards]` — see ../sources/SOURCES.md
- Raw evidence: [`raschke.raw.md`](raschke.raw.md)
