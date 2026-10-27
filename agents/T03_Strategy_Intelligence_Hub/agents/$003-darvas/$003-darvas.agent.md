# `$003-darvas` — Nicolas Darvas, Box Theory

- **Serial:** $003
- **Owner (trader):** Nicolas Darvas — dancer turned trader, "BOX theory"
- **Market:** crypto (start: BTC/USDT, daily)
- **Strategy:** Darvas Box — breakout above the box ceiling on volume, trailing stop, long-only
- **Created:** 2026-08-29
- **Binding law:** inherits [`../../AGENT_CONSTITUTION.md`](../../../AGENT_CONSTITUTION.md) and the [hub spec](../../%24trategy-master.agent.md).
- **Research dossier:** [`../../knowledge/strategies/darvas.md`](../../knowledge/strategies/darvas.md)

## 1. The trader & the strategy (research)

Nicolas Darvas turned ~$10k into ~$2M (1957–1959) trading only weekly *Barron's* price & volume data
while touring as a dancer, described in *How I Made $2,000,000 in the Stock Market* (1960). `[WP-Darvas]`
`[Investopedia-Darvas]` `[Darvas]`

**Box Theory (mechanical core):** `[WP-Darvas]` `[Investopedia-Darvas]`
- A box = recent **low (floor)** to recent **high (ceiling)**; trade only **rising boxes** (uptrends).
- **Buy** when price **breaks above the box ceiling** (new high) on **strong volume**.
- **Trailing stop** just under the box floor; **raise it** as higher boxes are breached.
- **Long-only**; pyramid into strength; **exit when the trailing stop is hit**.

## 2. How it maps to signals

`strategy.py` (`DarvasStrategy`) emits `position ∈ {0, +1}` (long-only):
- box ceiling = highest high of prior `box_period` bars; box floor = lowest low of prior `stop_period` bars.
- **Enter** when close > ceiling **and** (if `vol_confirm`) breakout volume > `vol_period` average.
- **Exit** when close < floor (trailing stop). Prior-bar windows + next-bar execution → no look-ahead.

**Not modeled (R-E.5):** Darvas's fundamental filter (growth industries / earnings) — he was a
self-described "techno-fundamentalist"; that part isn't in OHLCV, so this agent is the price+volume
box breakout only.

## 3. Parameters

| Param | Meaning | Default | Search range |
|---|---|---|---|
| `box_period` | ceiling-breakout lookback | 20 | [20, 40, 55] |
| `stop_period` | trailing-stop (floor) lookback | 10 | [10, 20] |
| `vol_confirm` | require above-average breakout volume | true | [true, false] |

## 4. Backtest & review

- Config: [`config.yaml`](config.yaml) · Implementation: [`strategy.py`](strategy.py)
- Latest review: [`results/REVIEW.md`](results/REVIEW.md)

## 5. Caveat (cited)

Works best in **bullish/trending** markets; produces small losses when trends fail to develop.
`[Investopedia-Darvas]`

## 6. Sources

- `[WP-Darvas]`, `[Investopedia-Darvas]`, `[Darvas]` — resolved in
  [`../../knowledge/sources/SOURCES.md`](../../knowledge/sources/SOURCES.md).
