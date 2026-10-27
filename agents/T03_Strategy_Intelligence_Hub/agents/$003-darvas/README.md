# `$003-darvas`

Algorithmic version of **darvas**'s strategy — *Darvas Box breakout on volume (long-only, trailing stop)* — on **crypto**.

- Spec (cited rules): [`$003-darvas.agent.md`]($003-darvas.agent.md)
- Signal logic: [`strategy.py`](strategy.py)
- Config: [`config.yaml`](config.yaml)
- Results: `results/` (`REVIEW.md` after review)

## Run (from the hub root)

```bash
python scripts/backtest.py '$003-darvas'
python scripts/train.py    '$003-darvas'
python scripts/review.py   '$003-darvas'
```

## Status

Scaffolded 2026-08-29. Replace the placeholder logic in `strategy.py` with darvas's real, cited
rules before trusting any result.
