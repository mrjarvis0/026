# `$008-tudorjones`

Algorithmic version of **tudorjones**'s strategy — *200-day MA rule (defensive trend/regime filter)* — on **crypto**.

- Spec (cited rules): [`$008-tudorjones.agent.md`]($008-tudorjones.agent.md)
- Signal logic: [`strategy.py`](strategy.py)
- Config: [`config.yaml`](config.yaml)
- Results: `results/` (`REVIEW.md` after review)

## Run (from the hub root)

```bash
python scripts/backtest.py '$008-tudorjones'
python scripts/train.py    '$008-tudorjones'
python scripts/review.py   '$008-tudorjones'
```

## Status

Scaffolded 2026-08-29. Replace the placeholder logic in `strategy.py` with tudorjones's real, cited
rules before trusting any result.
