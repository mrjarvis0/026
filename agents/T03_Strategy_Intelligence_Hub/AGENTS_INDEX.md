# Agents Index — serial registry

**Single source of truth for serial allocation.** Do not edit serials by hand — create agents via
`python scripts/new_agent.py`, which allocates the next serial in order and appends a row here.

Naming: `$<NNN>-<owner-slug>` (`$` prefix + 3-digit serial + trader name). See
[`$trategy-master.agent.md`](./%24trategy-master.agent.md) §3.

| Serial | Agent | Owner | Market | Strategy | Status | Created |
|--------|-------|-------|--------|----------|--------|---------|
| $001 | $001-dennis | Richard Dennis | crypto | Turtle Trading (Donchian breakout) | reviewed | 2026-08-28 |
| $002 | $002-donchian | Richard Donchian | crypto | Donchian channel breakout (weekly/4-week rule, trend timing) | reviewed | 2026-08-28 |
| $003 | $003-darvas | Nicolas Darvas | crypto | Darvas Box breakout on volume (long-only, trailing stop) | reviewed | 2026-08-29 |
| $004 | $004-williams | Larry Williams | crypto | Volatility breakout (Open + k x prior range, short-term) | reviewed | 2026-08-29 |
| $005 | $005-seykota | Ed Seykota | crypto | EMA trend-following (dual-EMA crossover) | reviewed | 2026-08-29 |
| $006 | $006-raschke | Linda Raschke | crypto | Turtle Soup false-breakout reversal (short-term mean-reversion) | reviewed | 2026-08-29 |
| $007 | $007-oneil | William O'Neil | crypto | CANSLIM technical subset (new-high breakout + market filter + 8% stop) | reviewed | 2026-08-29 |
| $008 | $008-tudorjones | Paul Tudor Jones | crypto | 200-day MA rule (defensive trend/regime filter) | reviewed | 2026-08-29 |
| $009 | $009-scalper | System (synthetic) | crypto | Futures scalper: MTF + scanner consensus + candle predictor + sentiment fusion | implemented | 2026-10-27 |

<!-- next-serial: 10 -->

## Status values

- `scaffolded` — folder + spec created, strategy not yet implemented/verified.
- `backtested` — has a completed backtest on real data.
- `trained` — walk-forward optimization done.
- `reviewed` — `REVIEW.md` generated.
- `paper` — running on a demo/testnet account (human-approved).
- `archived` — retired.