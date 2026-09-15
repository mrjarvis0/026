# T01 — Smart Binance Intelligence

A self-learning crypto trading agent with a live web dashboard. It works on **any** Binance pair, practices with **paper trading** ($1,000 virtual), tracks its own accuracy, and only unlocks **real trading** once it proves **70%+ accuracy over 50+ trades**.

## Features
- 🌐 Universal — trade/analyze any Binance spot pair (pick from dashboard)
- 📊 Live web dashboard (candlestick chart, signals, P&L, accuracy meter)
- 🧠 Self-learning strategy tuner (adjusts parameters from results)
- 📝 Paper trading with full trade history & metrics (accuracy, Sharpe, drawdown, ROI)
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
multi-market auto-trader**. Full 15-item plan (scalping-first, foundation-first)
lives in [`T01_Smart_Binance_Intelligence.agent.md`](../T01_Smart_Binance_Intelligence.agent.md) §11.
Highlights:

- **Fees + slippage model** and expectancy metrics (so scalping results are real)
- **Adaptive ATR stops** + a dedicated **scalping profile** (1m/5m/30m, maker orders)
- **Real-time WebSocket** data, **multi-timeframe** confluence, **VWAP/ATR/ADX**
- **Chart-pattern & market-structure** detection + a **multi-symbol scanner**
- **Exchange-native OCO/stop-limit**, a **backtester**, order reconciliation
- **Multi-strategy** engine (scalping/swing/trend) and a **futures + shorting** module
