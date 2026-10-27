# `$trategy-master` — Futures Scalper (design & honest scope)

The aggressive **24/7 futures scalper** the user asked for: long **and** short, low timeframes,
multi-timeframe confirmation, a next-candle probability estimate, per-candle profit management, and —
above all — **the account must never go to zero.** Runs on **Binance USD-M Futures Testnet** (fake
money). Real money is never traded by this tool.

## Honest scope (read this first — R-E.3/R-E.5)

- **"100x profit per day" is not achievable reliably.** No system predicts the future; one that made
  100x/day would own all the money on earth within weeks. Reviews here will show the **real** numbers,
  and I will not fake a backtest to "prove" 100x.
- **"Predict the next 3 candles" = a probability estimate only** (think 52–58% on a good day, often
  worse after fees on low timeframes). It is an edge to exploit with strict risk, not a crystal ball.
- **"Max leverage" vs "never zero" directly conflict.** Capital-preservation **wins**: leverage is
  *capped*, per-trade risk is tiny, and circuit breakers halt trading before ruin. (Even so, leveraged
  gaps/liquidations mean no system is 100% ruin-proof — bounded risk just makes ruin very unlikely.)

## Components

| # | Component | Status |
|---|---|---|
| 1 | **RiskEngine** — never-zero: risk-based sizing, leverage cap, daily-loss/drawdown/floor circuit breakers | ✅ `core/live/risk.py` (built + verified) |
| 2 | **Futures broker** — Binance USD-M Futures **Testnet** via ccxt (`binanceusdm`, sandbox); long/short/leverage, read position/equity | ⏳ `core/paper/binance_futures_testnet.py` |
| 3 | **Multi-timeframe analyzer** — fetch 1m/5m/15m/1h; per-TF trend (EMA/ADX slope); alignment score (all-up / all-down / mixed=chop) | ⏳ `core/futures/mtf.py` |
| 4 | **Next-candle probability** — features (multi-TF alignment, momentum, candle body/wick, volume surge, RSI) → simple calibrated model → P(next bar up). **OOS accuracy reported honestly.** | ⏳ `core/futures/predict.py` |
| 5 | **Signal fusion** — combine strategy-scanner consensus + MTF alignment + P(up) + optional news/on-chain → `(direction, confidence)` | ⏳ `core/futures/fuse.py` |
| 6 | **News / on-chain adapters** — Fear & Greed index (alternative.me, free), CoinGecko market metrics (free), optional news RSS → sentiment/flow features. **Experimental — honest low edge on short TF.** | ⏳ `core/research/sentiment.py` |
| 7 | **Execution loop** — 24/7, per-candle: fuse → `RiskEngine.can_trade` + `position_size` → open/adjust long/short on futures testnet → trailing stop / per-candle profit take → kill-switch. Dry-run default; `--arm` to send. | ⏳ `core/futures/scalper.py` + `scripts/run_scalper.py` |
| 8 | **Scalper agent** — `agents/$009-scalper/` (symbol, timeframe, leverage cap, risk %, TF set) + cited spec | ⏳ |

## Fusion logic (planned)

```
direction, confidence = fuse(
    scanner_consensus,      # how many of the 8 strategies agree (from core.scan)
    mtf_alignment,          # +1 all TFs up, -1 all down, 0 chop -> if chop: stand aside
    p_up,                   # next-candle probability (0..1)
    sentiment (optional),   # Fear&Greed / news, small weight
)
# trade only when: TFs align AND |p_up-0.5| > threshold AND confidence high
# size = RiskEngine.position_size(equity, price, stop_distance); check can_trade() first
```

## Safety (non-negotiable)

- Testnet only; dry-run by default; `--arm --confirm I-CONFIRM-PAPER-ORDER` to transmit.
- RiskEngine guards every entry (sizing + circuit breakers). Learning-agent guard (`core/learn`) warns
  before repeating a known losing setup.
- Kill-switch: halt on daily-loss / max-drawdown / equity-floor; user starts & stops (Ctrl+C / task).
- Short allowed (futures), so no "-1 → flat" mapping (unlike spot).

## Reality on "profit target"

The `profit_target_x` in config is a **goal knob**, not a promise. The scalper aims to compound many
small edges intraday; the review reports whatever actually happens. If a run shows a small gain or a
loss, that is the honest result — the RiskEngine's job is to make sure a bad run **can't** zero the account.
