# T01 — Smart Binance Intelligence — Agent Profile

> **One line:** A self‑learning crypto trading agent with a live web dashboard that
> works on *any* Binance spot pair, practices with **paper trading** ($1,000
> virtual), tracks its own accuracy, and unlocks **real trading only after proving
> 70 %+ accuracy over 50+ trades.**

*This is a personal dossier for the trading agent that lives in
[`T01_Smart_Binance_Intelligence/`](T01_Smart_Binance_Intelligence/). It documents the system in
detail — architecture, decision logic, risk model, safety, current status, and the
research each component is built on, with sources. It complements the repo's own
[`README.md`](T01_Smart_Binance_Intelligence/README.md).*

---

## 1. Identity card

| Field | Value |
|---|---|
| **Name** | T01 — Smart Binance Intelligence |
| **Type** | Standalone autonomous trading bot + FastAPI web service |
| **Domain** | Cryptocurrency spot trading (technical‑analysis strategy) |
| **Location** | [`T01_Smart_Binance_Intelligence/`](T01_Smart_Binance_Intelligence/) |
| **Language** | Python 3 (async FastAPI backend); browser dashboard (HTML/JS) |
| **Exchange** | Binance spot, via [`ccxt`](https://github.com/ccxt/ccxt) |
| **Storage** | SQLite ([`data/trades.db`](T01_Smart_Binance_Intelligence/data)) |
| **Default market** | `BTC/USDT` @ `5m` (any USDT pair selectable) |
| **Modes** | **Paper** (default, no real money) · **Real** (locked behind an accuracy gate) |
| **Entry point** | `python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000` |
| **Status** | **Working — boots and runs.** Backend + `frontend/` both present; verified to boot and serve the dashboard (`/terminal`) and landing page (`/`). Spot paper‑trading is live; real trading stays gated. Planned v2 build tracked in §11. |

---

## 2. What it is (elevator pitch)

T01 continuously pulls live market data for a chosen Binance pair, computes a
panel of classic technical indicators, scores them into a single **net
bull/bear momentum** number, and paper‑trades when that score crosses a tunable
threshold. Every trade is journaled to SQLite; performance metrics (accuracy,
Sharpe, drawdown, profit factor, ROI) are computed live and streamed to a
dashboard over WebSocket. A lightweight **self‑tuning** loop nudges the strategy's
threshold based on recent accuracy. Real‑money trading is deliberately **gated**:
it stays locked until the paper track record proves ≥ 70 % win‑rate over ≥ 50
trades, *and* API keys are configured, *and* the operator explicitly enables it.

Design priorities, in order: **capital safety → measurable track record → only
then, real money.**

---

## 3. Architecture at a glance

```
backend/
  main.py            FastAPI app — REST + WebSocket + serves dashboard, security middleware
  bot.py             Async trading loop (analyze → trade → broadcast) + pub/sub
  config.py          All settings from .env (credentials, risk, gate, server)
  data/
    collector.py     Universal market data via ccxt (OHLCV, ticker, order book)
    database.py      SQLite schema + trades / equity_curve / key-value state
  analysis/
    indicators.py    RSI, MACD, EMA/SMA, Bollinger Bands (pure pandas)
    signals.py       Weighted net-momentum signal engine → buy/sell/hold
    risk.py          Position sizing, stop/target prices, concurrency cap
  strategy/
    engine.py        Decision wrapper + self-learning parameter tuner
  trading/
    paper_engine.py  Simulated wallet, real prices, SL/TP management
    real_engine.py   Guarded real connector — LOCKED until the gate opens
    performance.py   Metrics + the real-trading accuracy gate
  safety/
    circuit_breaker.py  Emergency STOP + daily loss-limit halt
frontend/            index.html, styles.css, app.js (canvas terminal) + landing/index.html
```

### The main loop ([`bot.py`](T01_Smart_Binance_Intelligence/backend/bot.py))

`TradingBot.run_forever()` cycles every **12 seconds** (README now matches). Each
`_cycle()`:

1. Fetches OHLCV (**250 candles**), ticker, and order book **off the event loop**
   via `asyncio.to_thread` (ccxt is blocking); skips the cycle on a non‑positive
   price so a bad tick can never liquidate the book at 0.
2. Routes to the active engine (real only when fully gated‑on, else paper) and
   checks `circuit_breaker.trading_allowed(mode)`.
3. **Manages open positions first** — `check_exits()` closes any that hit
   stop‑loss or take‑profit. It now marks **every held symbol** (not just the
   active one), so a position left open after switching symbols is still managed.
4. Computes all indicators and generates a signal.
5. Acts: on `buy`, opens a paper position (respecting caps/duplicates); on `sell`,
   closes the matching position; otherwise logs a scan line.
6. Calls `engine.self_tune()` to let the strategy learn.
7. Broadcasts a `tick` event (price, ticker, order book, signal, indicators,
   params, running/allowed flags, recent activity) to all WebSocket subscribers.

The loop is wrapped so transient ccxt/network errors are logged and the bot keeps
running rather than crashing.

---

## 4. The decision logic (how it decides to trade)

### 4.1 Indicators ([`analysis/indicators.py`](T01_Smart_Binance_Intelligence/backend/analysis/indicators.py))

Computed in pure pandas/numpy (no C‑extension TA libs), so it installs cleanly on
Windows:

- **RSI(14)** — Wilder‑style EWMA of gains/losses.
- **MACD(12, 26, 9)** — EMA(12) − EMA(26), signal EMA(9), histogram.
- **EMA 50 / 100 / 200** and **SMA 20**.
- **Bollinger Bands(20, 2σ)** — SMA(20) ± 2·rolling std.
- **Volume SMA(20)** for volume confirmation.
- **ATR(14)** — average true range, a volatility gauge driving adaptive stops/targets/sizing (§5).
- **ADX(14)** — trend *strength* (0–100); labels each entry's regime (**trend** ≥ `ADX_TREND_MIN`, else **chop**) for loss reflection (§4.4).
- **VWAP (rolling 24)** — a volume‑weighted fair‑value proxy feeding the VWAP confluence sub‑signal (§4.2).

### 4.2 Signal engine ([`analysis/signals.py`](T01_Smart_Binance_Intelligence/backend/analysis/signals.py))

Rather than requiring rare unanimous conditions, T01 uses a **weighted
net‑momentum score** — several sub‑signals each contribute a signed weight, and the
bot acts when the net crosses a threshold. This produces regular, explainable
trades. Weights (positive = bullish):

| Sub‑signal | Condition | Score |
|---|---|---|
| RSI oversold / low | `<30` / `<rsi_buy(45)` | +2.0 / +1.0 |
| RSI overbought / high | `>70` / `>rsi_sell(60)` | −2.0 / −1.0 |
| MACD position | histogram beyond a ±`macd_eps` dead‑band (~2 bps of price) | ±1.0 |
| MACD momentum turn | histogram crosses **out of** that dead‑band | ±1.0 |
| Trend | `EMA50`/`EMA200` separated beyond `trend_band` (~0.1%) | ±0.8 |
| Bollinger mean‑reversion | price ≤ lower / ≥ upper | +1.2 / −1.2 |
| Volume confirmation | volume > avg, in candle direction | ±0.6 |
| VWAP confluence | price above / below rolling VWAP | +0.7 / −0.7 |

`net = bull − bear`; `confidence = min(1, |net| / 7.3)` (7.3 = the max achievable
one‑sided score). If `net ≥ net_threshold` → **buy**; if `net ≤ −net_threshold` →
**sell**; else **hold**. Below **`_MIN_BARS` (30)** of history the engine returns
**hold** — too little data leaves indicators NaN and would otherwise fabricate a
phantom signal. The full factor breakdown and indicator snapshot are attached to
every signal for the dashboard.

### 4.3 Self‑learning tuner ([`strategy/engine.py`](T01_Smart_Binance_Intelligence/backend/strategy/engine.py))

`self_tune()` reads recent paper accuracy and adjusts `net_threshold`, clamped to
`[1.0, 3.0]`:

- accuracy `< 50 %` → raise threshold `+0.1` (fewer, higher‑quality trades)
- accuracy `< 65 %` → raise `+0.05`
- accuracy `> 75 %` → lower `−0.05` (trade a bit more)
- fewer than 10 trades → don't learn yet

This is a deliberately conservative, interpretable feedback controller — *not* a
black‑box ML model. Tuned params persist in the `state` table.

### 4.4 Loss reflection — attribute *why*, then fix the specific cause ([`strategy/reflection.py`](T01_Smart_Binance_Intelligence/backend/strategy/reflection.py))

`self_tune()` only knows the *aggregate* win‑rate and turns one dial
(`net_threshold`). Reflection answers a different question — **why** did the
recent losers lose — and corrects that specific cause. Every entry is tagged at
open time (stored on the `trades` row) with three pieces of context that are all
known at signal time:

- **`entry_factor`** — the dominant sub‑signal *family* that opened it (the
  largest‑magnitude weighted factor: rsi / macd / trend / bb / vol / vwap).
- **`entry_regime`** — **trend** or **chop**, from ADX vs `ADX_TREND_MIN`.
- **`entry_adx`** — the raw ADX reading; plus the exit type is already recorded
  (`stop_loss` / `take_profit` / `signal_sell`).

After each close, once there are `REFLECT_MIN_TRADES` recent trades and the recent
loss rate exceeds `REFLECT_LOSS_RATE`, `diagnose_and_correct()` groups the losers
by cause and applies a **targeted** fix (each a *different* knob than
`net_threshold`, so the two loops never fight):

| Dominant loss cause | Targeted correction |
|---|---|
| ≥50 % of losers opened in **chop** | raise `adx_min` → gate out low‑ADX entries |
| ≥50 % of losers opened by **one family** | down‑weight *that* family (`factor_weights`, floor 0.5) |
| ≥60 % of losers exited via **stop‑loss** | widen the ATR stop (`atr_stop_mult`, cap 3.0) |

All three knobs default to no‑op (`adx_min=0`, `factor_weights={}`,
`atr_stop_mult=0`), so behaviour is identical to before until a *diagnosed* losing
streak moves them — and every move only ever tightens (filter more, weight less,
stop wider), the conservative direction. This is the roadmap #16 idea built
properly: "diagnose, then fix the specific thing," not one blunt global average.

---

## 5. Risk & money management

### Position sizing ([`analysis/risk.py`](T01_Smart_Binance_Intelligence/backend/analysis/risk.py))

Fixed‑fractional, **risk‑based** sizing:

```
capital_at_risk = balance × RISK_PER_TRADE       (paper 2 %, real 1 %)
stop_distance   = ATR × ATR_STOP_MULT (1.5)       when ATR stops enabled + ATR known
                  else price × STOP_LOSS_PCT (2 %) # fixed-% fallback
qty_risk        = capital_at_risk / stop_distance
# affordability cap: split the FREE balance across the position slots still open,
# so all MAX_CONCURRENT_POSITIONS can fit in cash (replaced the old fixed 0.30 cap)
slots_left      = max(1, MAX_CONCURRENT_POSITIONS − open_count)
qty             = min(qty_risk, (balance / slots_left) / price)  # smaller wins
```

- **Adaptive (ATR) stops & targets** (`USE_ATR_STOPS`, default on): stop distance =
  `ATR × ATR_STOP_MULT` (1.5), target = `ATR × ATR_TP_MULT` (3.0) → a 2:1 target that
  scales with volatility. Both sizing and the actual stop read the *same*
  `_stop_distance`, so a wider volatility stop automatically shrinks the position.
  Falls back to fixed **−2 % / +4 %** whenever ATR is unavailable (thin history), so
  behaviour is never worse than the old fixed baseline.
- **Trailing stops** (`TRAIL_ENABLED`, default on): once a long is in profit, the
  stop ratchets up to `price × (1 − TRAIL_PCT)` (1.5 %) and never loosens — locking
  gains on a pullback instead of round‑tripping to the entry stop.
- **Max 3 concurrent positions**, one per symbol at a time.

### Circuit breaker ([`safety/circuit_breaker.py`](T01_Smart_Binance_Intelligence/backend/safety/circuit_breaker.py))

- **Emergency STOP** — a persisted flag; also stops the bot.
- **Daily loss limit** — halts trading for the day if realized PnL ≤ −3 % of the
  starting balance.
- `trading_allowed()` is checked at the top of every cycle.

### Performance & the accuracy gate ([`trading/performance.py`](T01_Smart_Binance_Intelligence/backend/trading/performance.py))

`compute_metrics()` produces: total trades, wins/losses, accuracy (%), total &
average PnL, average win/loss, **expectancy** (`avg_win·winrate − |avg_loss|·(1−winrate)`
— the average $ edge per trade, and a truer profitability proxy than win‑rate),
**profit factor** (gross profit / gross loss), **Sharpe ratio** (per‑trade mean/σ × √N),
**max drawdown** (peak‑to‑trough on the cumulative PnL curve), and **ROI %**. All paper
PnL is **net of round‑trip fees** (`PAPER_FEE_PCT`, 0.10 %). Real trading is `unlocked` only when
`accuracy ≥ 70 %` **and** `total_trades ≥ 50`. Synthetic `reset` closes (created
when the paper wallet is reset) are **excluded** from every metric, so a wallet
reset can never inflate the trade count or accuracy toward the gate.

---

## 6. Real‑trading gate & safety posture

[`trading/real_engine.py`](T01_Smart_Binance_Intelligence/backend/trading/real_engine.py) is a
**guarded real connector** — it places actual Binance market orders (sized by
risk, rounded to lot precision, checked against min‑notional), but every action
first passes `_guard()`, which raises `RealTradingLocked` unless **all three** hold:

1. `performance.is_real_trading_unlocked()` is true (the 70 % / 50‑trade gate), **and**
2. Binance API key + secret are configured, **and**
3. The operator has explicitly enabled real mode.

Additional safety from the repo's guidance:
- Paper mode uses **real prices but simulated fills** — no real money.
- Real trading requires the operator's **own** Binance API keys in `.env` (never
  committed), a **dedicated sub‑account** with **withdrawals disabled**, and
  starting on **Binance testnet** (`BINANCE_TESTNET=true`).
- ⚠️ **Not financial advice.** Crypto trading carries real risk of loss.

### Web security ([`main.py`](T01_Smart_Binance_Intelligence/backend/main.py))

The service intentionally has **no auth** (single‑user localhost tool), so it
hardens the transport instead:
- **DNS‑rebinding protection** — a `Host` allowlist (`127.0.0.1`/`localhost` + any
  configured `TRUSTED_HOSTS`); unknown hosts get `403`.
- **CSRF protection** — state‑changing methods must be same‑origin.
- **WebSocket origin check** — cross‑origin `/ws` upgrades are rejected (`1008`).
- Result limits are capped (`MAX_LIMIT = 1000`) as basic DoS protection; internal
  errors are logged server‑side and returned generically.

---

## 7. Data model ([`data/database.py`](T01_Smart_Binance_Intelligence/backend/data/database.py))

Three SQLite tables:
- **`trades`** — mode, symbol, side, entry/exit price, qty, stop/target, status,
  realized `pnl`/`pnl_pct`, entry/exit reason, the loss‑attribution tags
  (`entry_factor`, `entry_regime`, `entry_adx` — see §4.4), and timestamps.
  New columns are added by an idempotent `ALTER TABLE` migration in `init_db()`,
  so existing databases upgrade in place.
- **`equity_curve`** — balance + equity snapshots over time.
- **`state`** — key/value store (active symbol/timeframe, `bot_running`,
  `paper_balance`, `strategy_params`, `emergency_stop`, `real_enabled`, …).

Paper balance and all learned state survive restarts.

---

## 8. Current status, strengths & known gaps

**Strengths**
- Clean separation of concerns (data / analysis / strategy / trading / safety /
  API) with small, readable modules.
- Genuinely safety‑first: paper‑by‑default, a hard accuracy gate before real
  money, an emergency stop, a daily loss circuit breaker, and a locked real
  connector.
- Pure‑pandas indicators — no fragile native TA dependency.
- Thoughtful localhost web hardening despite having no auth.

**New in this build (2026‑09‑18) — reconciled & merged from the Jules AI branches**
- **Repo‑health fix**: the blanket `data/` `.gitignore` rule was also hiding the
  *source* package `backend/data/` (collector + database), so a fresh clone of
  `main` could not import `backend.data` and T01 wouldn't boot. Source is now
  tracked; the runtime `trades.db` stays ignored.
- **Fees + expectancy** (roadmap #1) — round‑trip `PAPER_FEE_PCT` in the paper
  engine + an `expectancy` metric and dashboard tile.
- **Adaptive ATR stops/targets + volatility sizing** (roadmap #2).
- **ATR & VWAP indicators + a VWAP confluence sub‑signal** (part of roadmap #6).
- **Trailing stops** (part of roadmap #12).
- **Kraken fallback** for public market data when Binance returns HTTP 451.
- **ADX indicator + trend/chop regime labelling** (completes the indicator side of #6).
- **Per‑trade loss attribution + targeted self‑correction** (roadmap #16, §4.4) —
  the proper build: tag each entry's dominant factor / regime / ADX, then diagnose
  and fix the specific loss cause (regime filter / factor down‑weight / wider stop).
  This is the "does T01 know *why* a trade lost" capability, done right.
- **Non‑acting multi‑scenario predictions** — the bot broadcasts what a
  conservative / standard / aggressive threshold would each decide (dashboard
  foresight), while still trading only the standard signal.
- **T01 test suite**: `tests/test_t01_merge.py` (17) + `tests/test_t01_reflection.py`
  (13) = **30 cases**. Deliberately dropped from the Jules branches: the illusory
  multi‑scenario `decide()` that silently acted on the loosest threshold, a
  duplicate hardcoded fee path, an untested Sharpe/PF tuner rewrite, and the
  double‑nudge reflect loop — the reflection here is the corrected version.

**Recently fixed (2026‑09‑14)**
- **Signal crash / phantom trades on thin data** — `generate_signal()` raised
  `IndexError` on an empty frame and emitted a false BUY on 1–2 bars (defaulted
  Bollinger bounds made `price ≤ bb_lower` trivially true). Now guarded by
  `_MIN_BARS = 30` (returns *hold* until enough history).
- **Wallet reset polluted the accuracy gate** — synthetic `reset` closes counted
  as losing trades, inflating the count toward the 50‑trade gate and dragging
  accuracy. `compute_metrics()` now excludes them.
- **Stranded positions** — after switching symbols, an open position on the old
  symbol was never exit‑checked (no mark price). The loop now marks every held
  symbol before running `check_exits`.

**Gaps / caveats (honest) — these drive the v2 roadmap in §11**
- **Fees now modelled, slippage not yet.** Paper PnL is net of round‑trip fees
  (`PAPER_FEE_PCT`), which removes the single biggest correctness gap; a spread/
  slippage model is still pending, so very‑tight scalps remain slightly optimistic.
- **Spot‑only, long‑only, one symbol at a time.** No shorting, no futures, no
  leverage; positions open only on the active symbol. (Binance stock tokens were
  discontinued in 2021 — real equities need a different broker.)
- **Single strategy, single timeframe.** One net‑momentum model. Stops/targets are
  now **ATR‑adaptive** (no longer a flat 2 %/4 %), but there is still no dedicated
  scalping profile, no multi‑timeframe confluence, and no chart‑pattern /
  market‑structure detection.
- **Soft stops.** SL/TP (and the new trailing stop) fire only when the 12 s loop
  sees the level crossed; no exchange‑native OCO/stop‑limit, so a fast wick between
  polls (or a downed bot) is unprotected.
- **Strategy is unvalidated out‑of‑sample.** No backtester; the 70 % gate measures
  *paper* win‑rate. Expectancy is now reported alongside it, but is still
  in‑sample — an optimistic proxy until a walk‑forward backtester lands.
- **`requirements.txt` lists more than the code uses** (`aiosqlite`, `jinja2`,
  `httpx` aren't imported; storage is synchronous `sqlite3`). Harmless; worth trimming.

---

## 9. How to run

```bash
cd T01_Smart_Binance_Intelligence
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env        # optional — only needed for real trading
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Then open <http://127.0.0.1:8000>. Pick a coin, click ▶ Start, watch the accuracy
gate climb. Real mode stays locked until 70 % / 50 trades.

*(A `.claude/launch.json` is already configured to launch this via the
`T01` profile on port 8000.)*

---

## 10. Research foundations & sources

T01 is built from well‑established, textbook‑grade quantitative‑finance and
software components. Canonical primary sources for each, **verified 2026‑08‑28**:

### Technical indicators
- **RSI** — Wilder, J. W. (1978). *New Concepts in Technical Trading Systems*.
  Trend Research. (Origin of RSI and its 14‑period default.)
- **MACD** — Appel, G. (1979; expanded 2005, *Technical Analysis: Power Tools for
  Active Investors*). Origin of the 12/26/9 EMA construction.
- **Bollinger Bands** — Bollinger, J. (2001). *Bollinger on Bollinger Bands*.
  McGraw‑Hill. (20‑period SMA ± 2 standard deviations.) <https://www.bollingerbands.com/>
- **Moving averages / EMA** — standard technical‑analysis constructs; see Murphy,
  J. J. (1999). *Technical Analysis of the Financial Markets*. NYIF.

### Performance metrics
- **Sharpe ratio** — Sharpe, W. F. (1966). "Mutual Fund Performance." *Journal of
  Business*, 39(1), 119–138; and Sharpe, W. F. (1994). "The Sharpe Ratio."
  *Journal of Portfolio Management*, 21(1), 49–58. (Risk‑adjusted return; T01
  applies the per‑trade variant scaled by √N.)
- **Maximum drawdown / profit factor** — standard trading‑system evaluation
  metrics; see Pardo, R. (2008). *The Evaluation and Optimization of Trading
  Strategies*, 2nd ed., Wiley.

### Position sizing & risk
- **Fixed‑fractional / risk‑per‑trade sizing** — Vince, R. (1990). *Portfolio
  Management Formulas / The Mathematics of Money Management*, Wiley; and
  Tharp, V. K. (2007). *Trade Your Way to Financial Freedom*, 2nd ed.,
  McGraw‑Hill (position sizing & R‑multiples). T01's `capital_at_risk /
  stop_distance` sizing is the classic risk‑based formulation.

### Platform & libraries
- **ccxt** — CryptoCurrency eXchange Trading library (unified exchange API used for
  all Binance market data and, when unlocked, order placement).
  <https://github.com/ccxt/ccxt> · docs <https://docs.ccxt.com/>
- **FastAPI** — the async web framework serving REST + WebSocket.
  <https://fastapi.tiangolo.com/>
- **Binance API** — spot market data, testnet, and (real mode) order endpoints.
  <https://developers.binance.com/docs/binance-spot-api-docs>

### Security techniques
- **DNS‑rebinding & CSRF protection for localhost services** — OWASP guidance on
  CSRF and same‑origin enforcement, applied here via `Host`/`Origin` allowlists.
  <https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html>

---

## 11. Planned v2 build — roadmap (16 items)

The vision: trade **any Binance market**, run **multiple strategy types** (swing,
trend, futures) with **scalping first** on **1m / 5m / 30m**, analyze **every
timeframe** for **patterns & trend**, and **auto‑trade** the best setups. The 16
features below are ordered **scalping‑first + foundation‑first** (each builds on
the earlier ones). Status legend: **✅ done**, **🟡 partial**, **⬜ planned**.
The 2026‑09‑18 merge landed the Phase‑A/foundation pieces (#1, #2) plus parts of
#6 and #12; the rest remain the backlog.

**Phase A — make the edge real (do first)**
1. ✅ **Fees + expectancy** — round‑trip `PAPER_FEE_PCT` applied on both legs in the
   paper engine (net‑of‑fee PnL) and an **expectancy** metric + dashboard tile.
   *(Per‑symbol maker/taker tiers and a spread/slippage model still pending.)*
2. ✅ **Adaptive ATR/volatility‑based stops & targets** — `ATR × ATR_STOP_MULT`
   (1.5) / `ATR_TP_MULT` (3.0), with position sizing off the same distance and a
   safe fixed‑% fallback. Replaces the flat 2 %/4 %.
3. ⬜ **Scalping strategy profile** (1m/5m/30m presets: fast cadence, tight risk,
   **maker/limit entries** to avoid taker fees).

**Phase B — scalping brain**
4. **Real‑time WebSocket market stream** (ccxt.pro / Binance WS) to replace the
   12 s polling loop — sub‑second reaction for 1m scalping.
5. **Multi‑timeframe confluence** — higher‑TF trend bias (30m/1h) gates lower‑TF
   (1m/5m) entries.
6. 🟡 **More indicators for scalping** — **VWAP** ✅ (rolling; anchored VWAP still
   TODO), **ATR** ✅ and **ADX** ✅ are in and wired to signals/stops/regime;
   Stochastic and volume profile still pending.
7. **Chart‑pattern & market‑structure detection** — candlesticks (engulfing,
   hammer, doji, pin‑bar), support/resistance, breakouts, and structure
   (higher‑highs/lows, break‑of‑structure).

**Phase C — find & execute across the whole market**
8. **Multi‑symbol scanner** — scan *all* pairs in the background, rank setups, and
   auto‑pick the best (not one symbol at a time).
9. **Exchange‑native OCO / stop‑limit orders** — hard, server‑side stops instead
   of today's soft poll‑based stops.
10. **Backtester + walk‑forward validation** — test strategies on historical OHLCV
    (net of fees) before trusting the live gate.
11. **Order reconciliation & restart resilience** — poll order status, handle
    partial/rejected fills, and re‑sync exchange positions with the DB on restart.
12. 🟡 **Overtrading & drawdown guards** — per‑position **trailing stops** ✅ (config
    `TRAIL_*`, ratchets up only); max daily trades, loss‑streak cooldown and a
    max‑drawdown kill‑switch still pending.

**Phase D — expand markets & strategies**
13. **Multi‑strategy engine + selector** — switchable **scalping / swing /
    trend‑following** profiles, each with its own params and risk.
14. **Futures + shorting module** (`ccxt.binanceusdm`) — leverage, margin mode,
    liquidation price, funding‑rate awareness, and **bidirectional** (long *and*
    short) trading.
15. **Notifications & monitoring** — Telegram/email alerts on entries/exits/stops/
    errors; plus housekeeping (trim unused deps, an **expectancy‑based** unlock gate).

> Note: **Binance no longer offers stocks/equities** (stock tokens ended 2021), so
> "stocks" would require a separate broker integration (e.g. Alpaca) outside this
> Binance‑focused agent.

**Phase E — learn from *why*, not just *whether***

16. ✅ **Per‑trade loss attribution + targeted self‑correction** — *built
    2026‑09‑18* (see §4.4, [`strategy/reflection.py`](T01_Smart_Binance_Intelligence/backend/strategy/reflection.py)).
    Every entry is now tagged with its **dominant sub‑signal family**, its
    **trend/chop regime** (from ADX), and the raw ADX; the exit type is already
    recorded. After each close, `diagnose_and_correct()` groups recent losers by
    cause and fixes the *specific* thing:
    - losses clustering in a choppy/low‑ADX regime → raise `adx_min` (regime
      filter), not a blanket threshold nudge;
    - losses clustering on one sub‑signal family → down‑weight *that* family
      (`factor_weights`), others untouched;
    - losses mostly from stop‑outs → widen the ATR stop (`atr_stop_mult`).

    This is the "diagnose, then fix the specific thing" behaviour the spec called
    for — a different knob than `self_tune`'s global threshold, so the two loops
    don't fight. *Still open (a stretch of the original spec):* an explicit
    "stopped‑out‑then‑price‑reverses" pattern detector (needs post‑exit price
    tracking); today the stop‑out cluster is handled by the simpler "stops too
    tight → widen" rule.

---

*Compiled 2026‑08‑28; **revised 2026‑09‑14** (frontend now present & app verified
to boot; signal/reset/multi‑symbol bug‑fixes; v2 roadmap added); **revised
2026‑09‑16** (item 16 — per‑trade loss attribution + targeted self‑correction —
added to the roadmap, per the operator's question about whether T01 understands
*why* a trade lost, not just *that* it lost); **revised 2026‑09‑18** (merged the
Jules AI branches: fixed the `data/` gitignore that hid `backend/data/` source;
shipped fees+expectancy #1, ATR stops #2, VWAP/ATR/**ADX** indicators #6, trailing
stops #12, a Binance→Kraken geo‑block fallback, and **built #16 for real** —
per‑trade loss attribution + targeted self‑correction (§4.4) plus non‑acting
multi‑scenario predictions; 30‑case test suite).
Code references point at the repository as it stands in
[`T01_Smart_Binance_Intelligence/`](T01_Smart_Binance_Intelligence/); external citations were
verified against live sources on 2026‑08‑28. Nothing here is financial advice.*
