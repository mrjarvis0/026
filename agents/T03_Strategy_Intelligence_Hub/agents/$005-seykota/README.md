# `$005-seykota`

Algorithmic version of **seykota**'s strategy — *EMA trend-following (dual-EMA crossover)* — on **crypto**.

- Spec (cited rules): [`$005-seykota.agent.md`]($005-seykota.agent.md)
- Signal logic: [`strategy.py`](strategy.py)
- Config: [`config.yaml`](config.yaml)
- Results: `results/` (`REVIEW.md` after review)

## Run (from the hub root)

```bash
python scripts/backtest.py '$005-seykota'
python scripts/train.py    '$005-seykota'
python scripts/review.py   '$005-seykota'
```

## Status

Scaffolded 2026-08-29. Replace the placeholder logic in `strategy.py` with seykota's real, cited
rules before trusting any result.
