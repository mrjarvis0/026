# `$006-raschke`

Algorithmic version of **raschke**'s strategy — *Turtle Soup false-breakout reversal (short-term mean-reversion)* — on **crypto**.

- Spec (cited rules): [`$006-raschke.agent.md`]($006-raschke.agent.md)
- Signal logic: [`strategy.py`](strategy.py)
- Config: [`config.yaml`](config.yaml)
- Results: `results/` (`REVIEW.md` after review)

## Run (from the hub root)

```bash
python scripts/backtest.py '$006-raschke'
python scripts/train.py    '$006-raschke'
python scripts/review.py   '$006-raschke'
```

## Status

Scaffolded 2026-08-29. Replace the placeholder logic in `strategy.py` with raschke's real, cited
rules before trusting any result.
