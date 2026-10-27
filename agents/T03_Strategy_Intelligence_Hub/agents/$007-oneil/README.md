# `$007-oneil`

Algorithmic version of **oneil**'s strategy — *CANSLIM technical subset (new-high breakout + market filter + 8% stop)* — on **crypto**.

- Spec (cited rules): [`$007-oneil.agent.md`]($007-oneil.agent.md)
- Signal logic: [`strategy.py`](strategy.py)
- Config: [`config.yaml`](config.yaml)
- Results: `results/` (`REVIEW.md` after review)

## Run (from the hub root)

```bash
python scripts/backtest.py '$007-oneil'
python scripts/train.py    '$007-oneil'
python scripts/review.py   '$007-oneil'
```

## Status

Scaffolded 2026-08-29. Replace the placeholder logic in `strategy.py` with oneil's real, cited
rules before trusting any result.
