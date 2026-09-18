# T01 — Smart Binance Intelligence

A self-learning crypto trading agent with a live web dashboard. It works on **any** Binance pair, practices with **paper trading** ($1,000 virtual), tracks its own accuracy, and only unlocks **real trading** once it proves **70%+ accuracy over 50+ trades**.

## Features
- 🌐 Universal — trade/analyze any Binance spot pair (pick from dashboard)
- 📊 Live web dashboard (candlestick chart, signals, P&L, accuracy meter)
- 🧠 Self-learning strategy tuner (adjusts parameters from results)
- 📝 Paper trading with full trade history & metrics (accuracy, expectancy, Sharpe, drawdown, ROI)
- 💸 **Fee-aware paper PnL** — round-trip trading fees applied so simulated results are realistic
- 🎯 **Volatility-adaptive (ATR) stops & targets** + risk-based position sizing that shrinks in choppy tape
- 📈 **VWAP confluence** sub-signal on top of RSI/MACD/EMA/Bollinger/volume scoring
- 🪜 **Trailing stops** — lock in profit as price runs, never loosen a stop
- 🌍 **Geo-block resilient** — auto-falls back to public Kraken data when Binance returns HTTP 451
- 🔒 Real trading locked behind the 70% accuracy gate
- 🛑 Emergency STOP + daily loss-limit circuit breaker

## Setup

```bash
cd T01_Smart_Binance_Intelligence
python -m venv venv
venv\Scripts\activate            # Windows
pip install -r requirements.txt
copy .env.example .env           # optional — only needed for real trading
```

## Run

```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000 in your browser (landing page → **Open Terminal**, or
go straight to the dashboard at http://127.0.0.1:8000/terminal).

## How it works

1. **Pick a coin** from the dropdown (any Binance USDT pair).
2. Click **▶ Start** — the bot analyzes the market every ~12s and paper-trades.
3. Watch the **Accuracy Gate** climb. Real trading stays locked until 70%.
4. Once unlocked (and you've added API keys + a sub-account), you can enable real mode.

## Safety
- Paper mode uses **no real money** — prices are real, trades are simulated.
- Real trading requires your own Binance API keys (in `.env`, never committed).
- Use a **dedicated sub-account** with **withdrawals disabled**.
- Start with Binance **testnet** (`BINANCE_TESTNET=true`) before going live.

⚠️ **Not financial advice.** Crypto trading carries real risk of loss.

## Project layout
```
backend/
  main.py          FastAPI app (REST + WebSocket + serves dashboard)
  bot.py           Background trading loop
  config.py        Settings from .env
  data/            collector (ccxt), database (SQLite)
  analysis/        indicators, signals, risk
  strategy/        decision engine + self-learning tuner
  trading/         paper_engine, real_engine (locked), performance
  safety/          circuit_breaker (emergency stop, loss limits)
frontend/          index.html, styles.css, app.js (canvas terminal)
  landing/         index.html (product landing page at /)
```

## Roadmap (v2)

The next build phase turns this spot paper-trader into a **scalping-first,
multi-market auto-trader**. Full plan (scalping-first, foundation-first)
lives in [`T01_Smart_Binance_Intelligence.agent.md`](../T01_Smart_Binance_Intelligence.agent.md) §11.

**✅ Recently shipped** (foundation for the scalping build):
- **Fees + expectancy** — round-trip paper fees + expectancy metric (roadmap #1)
- **Adaptive ATR stops/targets** + volatility-scaled position sizing (roadmap #2)
- **VWAP + ATR indicators** and a VWAP confluence sub-signal (part of roadmap #6)
- **Trailing stops** to protect open profit (part of roadmap #12)
- **Kraken fallback** for public data when Binance is geo-blocked (HTTP 451)

**Still planned:**
- Dedicated **scalping profile** (1m/5m/30m, maker orders), **real-time WebSocket** data
- **Multi-timeframe** confluence, **ADX/Stochastic**, **chart-pattern & market-structure** detection
- **Multi-symbol scanner**, **exchange-native OCO/stop-limit**, a **backtester**, order reconciliation
- **Multi-strategy** engine (scalping/swing/trend) and a **futures + shorting** module
- **Loss root-cause diagnosis** — tag *why* each trade lost and correct that specific cause, instead of one global threshold nudge
