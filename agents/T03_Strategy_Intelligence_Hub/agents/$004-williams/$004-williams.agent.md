# `$004-williams` — Larry Williams, Volatility Breakout

- **Serial:** $004
- **Owner (trader):** Larry Williams — 1987 World Cup of Futures Trading winner (+11,376%)
- **Market:** crypto (start: BTC/USDT, daily)
- **Strategy:** Volatility breakout — thrust past `Open + k × prior-day range` (short-term)
- **Created:** 2026-08-29
- **Binding law:** inherits [`../../AGENT_CONSTITUTION.md`](../../../AGENT_CONSTITUTION.md) and the [hub spec](../../%24trategy-master.agent.md).
- **Research dossier:** [`../../knowledge/strategies/williams.md`](../../knowledge/strategies/williams.md)

## 1. The trader & the strategy (research)

Larry Williams (b. 1942) — commodity trader, creator of **Williams %R** & the **Ultimate Oscillator**,
who won the **1987 World Cup Championship of Futures Trading**, turning $10k into $1,137,600 (**+11,376%**)
in 12 months. `[WP-LWilliams]` His short-term methods are in *Long-Term Secrets to Short-Term Trading*
(1998). `[LW-Book]`

**Volatility Breakout:** `[LW-Book]`
- Range = `High[t-1] − Low[t-1]`.
- **Long trigger** = `Open[t] + k × Range[t-1]`; **short trigger** = `Open[t] − k × Range[t-1]`; k ≈ 0.5.
- A thrust of k×(yesterday's range) beyond today's open = momentum entry; classic exit at the close.

This is the hub's first **short-term / active** system — a different flavor from the trend-following
channel breakouts of $001–$003.

## 2. How it maps to signals

`strategy.py` (`WilliamsStrategy`) emits `position ∈ {-1, 0, +1}`. Because the engine is **daily
Close-to-Close with next-bar execution** (can't fill an intraday stop without look-ahead), it uses a
**close-confirmed** breakout held for `hold_days` bars:
- `+1` if `Close > Open + k×priorRange`; `-1` if `Close < Open − k×priorRange`; else hold/flat.
- `allow_short: false` → long-only.

**Simplification (R-E.5):** this is a **1-day swing**, not the original same-day daytrade (which needs
intraday fills). Results will differ from book figures; a future intraday-aware engine could close the gap.

## 3. Parameters

| Param | Meaning | Default | Search range |
|---|---|---|---|
| `k` | breakout multiple of prior-day range | 0.5 | [0.3, 0.5, 0.8, 1.0] |
| `hold_days` | bars to hold after a trigger | 1 | [1, 2, 3] |
| `allow_short` | permit downside thrusts | true | [true, false] |

## 4. Backtest & review

- Config: [`config.yaml`](config.yaml) · Implementation: [`strategy.py`](strategy.py)
- Latest review: [`results/REVIEW.md`](results/REVIEW.md)

## 5. Caveat

Short-term = **many trades**, so commission/slippage matter a lot — judge on profit factor & net Sharpe.

## 6. Sources

- `[WP-LWilliams]`, `[LW-Book]` — resolved in
  [`../../knowledge/sources/SOURCES.md`](../../knowledge/sources/SOURCES.md).
