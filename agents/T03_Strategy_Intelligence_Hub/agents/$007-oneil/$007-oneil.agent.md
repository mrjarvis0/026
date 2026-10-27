# `$007-oneil` — William O'Neil, CANSLIM (technical subset)

- **Serial:** $007
- **Owner (trader):** William O'Neil — founder of Investor's Business Daily, creator of CAN SLIM
- **Market:** crypto (start: BTC/USDT, daily)
- **Strategy:** CANSLIM **technical subset** — new-high breakout + volume + market filter + 8% stop
- **Created:** 2026-08-29
- **Binding law:** inherits [`../../AGENT_CONSTITUTION.md`](../../../AGENT_CONSTITUTION.md) and the [hub spec](../../%24trategy-master.agent.md).
- **Research dossier:** [`../../knowledge/strategies/oneil.md`](../../knowledge/strategies/oneil.md)

## 1. The trader & the strategy (research)

William O'Neil (1933–2023) — founder of William O'Neil & Co and *Investor's Business Daily*, author of
*How to Make Money in Stocks*, creator of **CAN SLIM**. `[WP-ONeil]` `[ONeil]` CANSLIM combines
fundamental + technical factors: `[Investopedia-CANSLIM]`
**C**urrent EPS, **A**nnual EPS, **N**ew highs, **S**upply/demand (volume), **L**eader,
**I**nstitutional sponsorship, **M**arket direction. Plus O'Neil's rule: **cut losses at ~7–8%**. `[ONeil]`

## 2. Honesty — this is CANSLIM-*technical* only (R-E.3/R-E.5)

The target is **one crypto asset (BTC)** — no earnings, no institutions, no industry group, so **C, A, I
are omitted** and **L** (relative strength vs a universe) is N/A. This agent models the **technical
shell** only: **N** (new-high breakout), **S** (volume), **M** (market/trend filter), and O'Neil's
**8% stop**. It is **not** full CANSLIM; a stocks version with a fundamentals feed would be far more faithful.

## 3. How it maps to signals

`strategy.py` (`OneilStrategy`) emits `position ∈ {0, +1}` (long-only; O'Neil goes to cash, never short):
- **Enter** when close > highest high of prior `base_period` bars **and** close > SMA(`market_ma`)
  **and** (if `vol_confirm`) volume > its `vol_period` average.
- **Exit** when close > `stop_pct` below entry (8% rule) **or** close < SMA(`exit_ma`). No look-ahead.

## 4. Parameters

| Param | Meaning | Default | Search range |
|---|---|---|---|
| `base_period` | new-high breakout lookback (N) | 50 | [20, 50, 100] |
| `market_ma` | market/trend filter SMA (M) | 200 | [100, 200] |
| `exit_ma` | trend-break exit SMA | 50 | fixed |
| `stop_pct` | O'Neil 7–8% loss cut | 0.08 | fixed |
| `vol_confirm` | above-average breakout volume (S) | true | [true, false] |

## 5. Backtest & review

- Config: [`config.yaml`](config.yaml) · Implementation: [`strategy.py`](strategy.py)
- Latest review: [`results/REVIEW.md`](results/REVIEW.md)

## 6. Sources

- `[WP-ONeil]`, `[Investopedia-CANSLIM]`, `[ONeil]` — resolved in
  [`../../knowledge/sources/SOURCES.md`](../../knowledge/sources/SOURCES.md).
