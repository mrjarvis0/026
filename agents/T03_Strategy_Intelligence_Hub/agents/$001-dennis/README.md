# `$001-dennis`

Algorithmic version of **Richard Dennis**'s **Turtle Trading** system (Donchian channel breakout,
trend following) on **crypto** (BTC/USDT, daily).

- Spec (cited rules): [`$001-dennis.agent.md`](./%24001-dennis.agent.md)
- Signal logic: [`strategy.py`](strategy.py)
- Config: [`config.yaml`](config.yaml)
- Results: `results/` (`REVIEW.md` after review)

## Run (from the hub root)

```bash
python scripts/backtest.py '$001-dennis'
python scripts/train.py    '$001-dennis'
python scripts/review.py   '$001-dennis'
```

## Notes

- Backtesting crypto needs **no API keys** (public Binance data via ccxt).
- Position is full-size; ATR sizing/pyramiding from the original Turtle rules is intentionally not
  modeled yet (see the spec §2). Treat results as a timing test, not the full risk-managed system.
- Not financial advice; historical simulation only.
