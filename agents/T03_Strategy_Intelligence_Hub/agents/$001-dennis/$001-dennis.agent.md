# `$001-dennis` — Richard Dennis, Turtle Trading

- **Serial:** $001
- **Owner (trader):** Richard Dennis (with William Eckhardt) — the "Turtles" experiment
- **Market:** crypto (start: BTC/USDT, daily)
- **Strategy:** Turtle Trading — Donchian channel breakout, trend following
- **Created:** 2026-08-28
- **Binding law:** inherits [`../../AGENT_CONSTITUTION.md`](../../../AGENT_CONSTITUTION.md) and the [hub spec](../../%24trategy-master.agent.md).

## 1. The trader & the strategy (research)

Richard Dennis and William Eckhardt ran the **Turtle Trading** experiment in the early 1980s to
test whether trading could be taught as a mechanical rule set. It could: the "Turtles" traded a
fully systematic **trend-following breakout** system. `[Turtle-Rules]` `[Curtis-Faith]`

The system is mechanical — ideal as this hub's first backtest — with two sub-systems:

**Entry (breakout):**
- **System 1:** enter on a breakout of the **20-day** high (long) / low (short). `[Turtle-Rules]`
- **System 2:** enter on a breakout of the **55-day** high / low. `[Turtle-Rules]`

**Exit (opposite breakout):**
- **System 1:** exit on a **10-day** opposite breakout. `[Turtle-Rules]`
- **System 2:** exit on a **20-day** opposite breakout. `[Turtle-Rules]`

**Position sizing & risk (original):** size positions by market volatility **"N" (a 20-day ATR)** in
"Units," risking a fixed fraction per Unit, with **pyramiding** (adding Units as the trend runs) and
an ATR-based stop. `[Turtle-Rules]` `[Curtis-Faith]`

## 2. How it maps to signals

`strategy.py` (`DennisStrategy`) emits `position ∈ {-1, 0, +1}` per bar:
- Long when close > highest high of the prior `entry_donchian` bars.
- Short when close < lowest low of that window (disable via `allow_short: false`).
- Exit when close crosses the opposite `exit_donchian` channel; may flip directly to the opposite
  side if that breakout also triggers.
- Channels use `.shift(1)` (prior-bar windows) and the backtester acts on the next bar — **no
  look-ahead**.

**Simplification (be honest, R-E.5):** the [-1, 0, +1] contract abstracts away ATR **position
sizing and pyramiding**; here every position is full size. This captures the *timing* edge of the
Turtle system but not its volatility-scaled risk management. A later revision can add ATR sizing via
the optional `size` column of the signal contract.

## 3. Parameters

| Param | Meaning | Default | Search range |
|---|---|---|---|
| `entry_donchian` | breakout entry window | 20 | [20, 55] |
| `exit_donchian` | opposite-breakout exit window | 10 | [10, 20] |
| `allow_short` | permit short entries | true | [true, false] |

## 4. Backtest & review

- Config: [`config.yaml`](config.yaml)
- Implementation: [`strategy.py`](strategy.py)
- Latest review: [`results/REVIEW.md`](results/REVIEW.md) (after `python scripts/review.py '$001-dennis'`)

## 5. Sources

- `[Turtle-Rules]` *The Original Turtle Trading Rules* — Curtis Faith / originalturtles.org (public PDF
  documenting Systems 1 & 2, Donchian entry/exit windows, N/ATR sizing, Units, pyramiding).
  https://www.metastocktools.com/downloads/turtlerules.pdf
- `[Curtis-Faith]` Curtis Faith, *Way of the Turtle* (McGraw-Hill, 2007) — first-hand account of the
  Turtle system and its risk rules.

> **Verify at build time (R-E.6):** confirm the exact window values and sizing rules against the
> source PDF before trusting live parameters; the values above are the commonly documented ones.
