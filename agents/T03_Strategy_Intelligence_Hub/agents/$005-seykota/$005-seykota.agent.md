# `$005-seykota` — Ed Seykota, EMA trend-following

- **Serial:** $005
- **Owner (trader):** Ed Seykota — pioneer of computerized trend following, *Market Wizards*
- **Market:** crypto (start: BTC/USDT, daily)
- **Strategy:** classic dual-EMA crossover trend-following
- **Created:** 2026-08-29
- **Binding law:** inherits [`../../AGENT_CONSTITUTION.md`](../../../AGENT_CONSTITUTION.md) and the [hub spec](../../%24trategy-master.agent.md).
- **Research dossier:** [`../../knowledge/strategies/seykota.md`](../../knowledge/strategies/seykota.md)

## 1. The trader & the strategy (research)

Ed Seykota (b. 1946, MIT) **pioneered computerized systems trading in 1970** and is one of the great
systematic **trend followers** (*Market Wizards*). `[WP-Seykota]` `[Market-Wizards]` `[Covel]`
Wikipedia states plainly: **"Seykota based his first trading system on exponential moving averages,"**
inspired by Richard Donchian's moving-average trend systems. `[WP-Seykota]`

## 2. How it maps to signals

`strategy.py` (`SeykotaStrategy`) emits `position ∈ {-1, 0, +1}` from two EMAs of close:
- `EMA_fast > EMA_slow` → **+1**; `EMA_fast < EMA_slow` → **-1** (if `allow_short`) else **0**; flat
  until both EMAs are warmed up. No look-ahead (backtester acts next bar).

**Honesty (R-E.5):** Seykota's exact parameters are **proprietary and evolved** — not public. This is
the canonical dual-EMA crossover as a faithful representation of his *documented* EMA-trend core, not
his literal numbers. His money-management/position-sizing edge is **not** modeled by the {-1,0,+1}
contract.

## 3. Parameters

| Param | Meaning | Default | Search range |
|---|---|---|---|
| `fast` | fast EMA span | 20 | [10, 20, 50] |
| `slow` | slow EMA span | 100 | [50, 100, 200] |
| `allow_short` | permit short (stop-and-reverse) | true | [true, false] |

## 4. Backtest & review

- Config: [`config.yaml`](config.yaml) · Implementation: [`strategy.py`](strategy.py)
- Latest review: [`results/REVIEW.md`](results/REVIEW.md)

## 5. Sources

- `[WP-Seykota]`, `[Market-Wizards]`, `[Covel]` — resolved in
  [`../../knowledge/sources/SOURCES.md`](../../knowledge/sources/SOURCES.md).
