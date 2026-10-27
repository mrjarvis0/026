# `$006-raschke` — Linda Raschke, "Turtle Soup"

- **Serial:** $006
- **Owner (trader):** Linda Bradford Raschke — short-term technical trader, *New Market Wizards*
- **Market:** crypto (start: BTC/USDT, daily)
- **Strategy:** "Turtle Soup" — fade a false N-day breakout (short-term **mean-reversion**)
- **Created:** 2026-08-29
- **Binding law:** inherits [`../../AGENT_CONSTITUTION.md`](../../../AGENT_CONSTITUTION.md) and the [hub spec](../../%24trategy-master.agent.md).
- **Research dossier:** [`../../knowledge/strategies/raschke.md`](../../knowledge/strategies/raschke.md)

## 1. The trader & the strategy (research)

Linda Raschke (b. 1959) — futures trader & hedge-fund manager (LBRGroup/Granat), featured in
*The New Market Wizards*. `[WP-Raschke]` `[Market-Wizards]` Co-author of **Street Smarts: High
Probability Short-Term Trading Strategies** (1995). `[WP-Raschke]` `[Street-Smarts]`

**"Turtle Soup"** — a **fade of a false breakout** (the deliberate opposite of the Turtle breakout in
`$001`): `[Street-Smarts]`
- **Buy:** a **new 20-day low** that **reverses back up** through the prior low (failed breakdown).
- **Sell:** a **new 20-day high** that fails and reverses back below the prior high.
- Short-term hold; stop beyond the day's extreme.

This is the hub's first **mean-reversion** agent (vs the trend/breakout agents $001–$005).

## 2. How it maps to signals

`strategy.py` (`RaschkeStrategy`) emits `position ∈ {-1, 0, +1}` (prior-bar windows, act next bar → no
look-ahead):
- **Long** when `Low < prior_low` and `Close > prior_low` (false breakdown).
- **Short** when `High > prior_high` and `Close < prior_high` (false breakout), if `allow_short`.
- Hold `hold_days` bars, then flat.

**Simplification (R-E.5):** the book uses an intraday buy-stop just above the prior low; we use a
**close-confirmed** reversal + fixed-bar hold on daily data.

## 3. Parameters

| Param | Meaning | Default | Search range |
|---|---|---|---|
| `lookback` | N-day high/low that gets faded | 20 | [10, 20, 55] |
| `hold_days` | bars to hold the reversal | 3 | [1, 3, 5] |
| `allow_short` | fade false breakouts (up) too | true | [true, false] |

## 4. Backtest & review

- Config: [`config.yaml`](config.yaml) · Implementation: [`strategy.py`](strategy.py)
- Latest review: [`results/REVIEW.md`](results/REVIEW.md)

## 5. Caveat

Mean-reversion **fights trends** — expect very different behavior from $001–$005; likely better in
choppy/range markets, worse in one-way runs. Short-term = cost-sensitive.

## 6. Sources

- `[WP-Raschke]`, `[Street-Smarts]`, `[Market-Wizards]` — resolved in
  [`../../knowledge/sources/SOURCES.md`](../../knowledge/sources/SOURCES.md).
