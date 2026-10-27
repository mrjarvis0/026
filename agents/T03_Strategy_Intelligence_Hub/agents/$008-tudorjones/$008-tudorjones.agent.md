# `$008-tudorjones` — Paul Tudor Jones, the 200-day MA rule

- **Serial:** $008
- **Owner (trader):** Paul Tudor Jones — founder of Tudor Investment, macro legend
- **Market:** crypto (start: BTC/USDT, daily)
- **Strategy:** the **200-day moving-average rule** — a defensive trend/regime filter
- **Created:** 2026-08-29
- **Binding law:** inherits [`../../AGENT_CONSTITUTION.md`](../../../AGENT_CONSTITUTION.md) and the [hub spec](../../%24trategy-master.agent.md).
- **Research dossier:** [`../../knowledge/strategies/tudorjones.md`](../../knowledge/strategies/tudorjones.md)

## 1. The trader & the strategy (research)

Paul Tudor Jones — founder of **Tudor Investment Corporation**, one of the great **global macro** traders,
who famously **predicted & profited from 1987 Black Monday** (+125.9% after fees). His style is "based
primarily on **technical analysis... momentum**." `[WP-PTJ]` `[Market-Wizards]`

**The 200-day MA rule** (his famous mechanical heuristic): `[PTJ-200MA]`
> "My metric for everything I look at is the 200-day moving average of closing prices... **nothing good
> happens below the 200-day moving average.**"

Stay invested **above** the 200-day MA; **get out / play defense** when price falls **below**.

## 2. How it maps to signals

`strategy.py` (`TudorjonesStrategy`) emits `position ∈ {-1, 0, +1}`:
- **+1** while `close > SMA(ma_period)`; **0** (cash) while below — or **-1** if `allow_short`.
- `confirm_days` requires N consecutive closes on one side before flipping (whipsaw filter). No look-ahead.

**Honesty (R-E.5):** this is **one heuristic**, not PTJ's real discretionary macro process. It behaves
like a slow defensive trend follower — strong drawdown control, return capped by time in cash.

## 3. Parameters

| Param | Meaning | Default | Search range |
|---|---|---|---|
| `ma_period` | moving-average length (his rule = 200) | 200 | [100, 150, 200] |
| `allow_short` | short below the MA vs go to cash | false | [true, false] |
| `confirm_days` | consecutive closes to flip | 1 | [1, 3] |

## 4. Backtest & review

- Config: [`config.yaml`](config.yaml) · Implementation: [`strategy.py`](strategy.py)
- Latest review: [`results/REVIEW.md`](results/REVIEW.md)

## 5. Sources

- `[WP-PTJ]`, `[PTJ-200MA]`, `[Market-Wizards]` — resolved in
  [`../../knowledge/sources/SOURCES.md`](../../knowledge/sources/SOURCES.md).
