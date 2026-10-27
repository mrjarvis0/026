# `$004-williams`

Algorithmic version of **williams**'s strategy — *Volatility breakout (Open + k x prior range, short-term)* — on **crypto**.

- Spec (cited rules): [`$004-williams.agent.md`]($004-williams.agent.md)
- Signal logic: [`strategy.py`](strategy.py)
- Config: [`config.yaml`](config.yaml)
- Results: `results/` (`REVIEW.md` after review)

## Run (from the hub root)

```bash
python scripts/backtest.py '$004-williams'
python scripts/train.py    '$004-williams'
python scripts/review.py   '$004-williams'
```

## Status

Scaffolded 2026-08-29. Replace the placeholder logic in `strategy.py` with williams's real, cited
rules before trusting any result.
