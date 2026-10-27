# Traders roster — suggestions for the next agents

Curated shortlist of famous traders whose strategies are worth turning into agents. **You pick who
and which; this is only a suggestion list.**

**Backtestability legend** (this hub judges strategies on real OHLCV data, so mechanical rules fit best):
- 🟢 **Mechanical** — clear price-based rules, cleanly backtestable from OHLCV.
- 🟡 **Semi-mechanical** — mostly rules + some discretion/extra data; backtestable with assumptions.
- 🔴 **Discretionary / fundamental** — needs judgment, macro, or fundamentals; hard to backtest honestly from price alone (be upfront if we attempt it).

> Priority order you set: **crypto → forex → stocks.** Many classic systems below were built for
> stocks/futures but are **market-agnostic** and apply directly to crypto (trend/breakout systems
> especially). That's the fastest path to crypto agents.

## Trend / breakout systems (🟢 best fit — market-agnostic, great on crypto)

| Suggested slug | Trader | Signature strategy | Fit |
|---|---|---|---|
| `$001-dennis` ✅ | Richard Dennis | Turtle Trading — Donchian breakout + ATR sizing | 🟢 (built) |
| `donchian` | Richard Donchian | "Father of trend following" — 4-week rule, moving-average channels | 🟢 |
| `darvas` | Nicolas Darvas | Darvas Box — breakout from consolidation boxes on new highs | 🟢 |
| `seykota` | Ed Seykota | Systematic trend following (exponential moving averages, risk control) | 🟢 |
| `oneil` | William O'Neil | CANSLIM — breakout from bases; the price/volume part is 🟢, fundamentals 🔴 | 🟡 |
| `williams` | Larry Williams | Volatility breakout, %R oscillator, short-term momentum | 🟢 |

## Momentum / short-term (🟢–🟡)

| Suggested slug | Trader | Signature strategy | Fit |
|---|---|---|---|
| `livermore` | Jesse Livermore | Trend + pivotal points + pyramiding (tape reading is 🔴, the pivot rules 🟡) | 🟡 |
| `schwartz` | Marty Schwartz | Momentum with moving averages + oscillators (RSI/stochastics) | 🟡 |
| `raschke` | Linda Raschke | Short-term momentum patterns (e.g. "80-20", Turtle Soup) | 🟡 |

## Macro / discretionary (🔴 — famous but hard to backtest faithfully)

| Suggested slug | Trader | Signature strategy | Fit |
|---|---|---|---|
| `tudorjones` | Paul Tudor Jones | Global macro; the **200-day MA rule** is 🟢, the macro calls 🔴 | 🟡 |
| `druckenmiller` | Stanley Druckenmiller | Concentrated macro bets | 🔴 |
| `soros` | George Soros | Reflexivity, macro | 🔴 |
| `buffett` | Warren Buffett | Value investing (fundamentals, not price rules) | 🔴 |

## Forex-focused

| Suggested slug | Trader | Signature strategy | Fit |
|---|---|---|---|
| `lipschutz` | Bill Lipschutz | FX position trading, risk-first | 🔴 |
| `lien` | Kathy Lien | FX technical + macro/interest-rate driven | 🟡 |
| (system) `london-breakout` | — classic FX system | breakout of the London-session opening range | 🟢 |
| (system) `carry-trade` | — classic FX system | long high-yield / short low-yield currency (needs rate data) | 🟡 |

## Not recommended to clone

- **Renaissance / Jim Simons, Citadel, etc.** — their rules are **not public**. We cannot honestly
  reproduce them; anything labeled "Medallion strategy" online is speculation (Constitution R-E.3: no
  fabrication). Skip, or build a *generic* quant system without claiming it's theirs.

---

### My top picks for the next few serials (crypto-first)

1. **`donchian`** — Richard Donchian's channel/4-week rule. Cleanest possible follow-up to the
   Turtles, trivially runs on crypto, fully documented. 🟢
2. **`darvas`** — Darvas Box breakout. Mechanical, iconic, works on trending crypto. 🟢
3. **`williams`** — Larry Williams volatility breakout. Short-term, active, good crypto behavior. 🟢

Tell me a name and market, and I'll (a) research + write its cited dossier here, then (b) scaffold the
agent.
