# `$002-donchian`

Algorithmic version of **donchian**'s strategy — *Donchian channel breakout (weekly/4-week rule, trend timing)* — on **crypto**.

- Spec (cited rules): [`$002-donchian.agent.md`]($002-donchian.agent.md)
- Signal logic: [`strategy.py`](strategy.py)
- Config: [`config.yaml`](config.yaml)
- Results: `results/` (`REVIEW.md` after review)

## Run (from the hub root)

```bash
python scripts/backtest.py '$002-donchian'
python scripts/train.py    '$002-donchian'
python scripts/review.py   '$002-donchian'
```

## Status

Scaffolded 2026-08-28. Replace the placeholder logic in `strategy.py` with donchian's real, cited
rules before trusting any result.
