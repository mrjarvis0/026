# models.md — ML models (not data feeds)

> Pre-trained models 026 *uses* inside an agent's intelligence step. A model is
> **not a data source** — it consumes data (e.g. news text) and outputs a signal
> (e.g. sentiment). Tracked here so it is governed like everything else.
> Used from `brain/` or an agent's `skills/`, not fetched as raw data.
> Master ID index lives in [`README.md`](README.md#master-index).

**Schema.** A model has no rate limit or provenance-of-fetch (it is not a feed), so
those columns do not apply. It carries a license, a home (`Lands in`), and the
maturity rule below. Its **output** is a claim governed exactly like any other.

| ID | Model | Domain | What it does | License / Auth | Lands in | Tier | Used by | Status |
|----|-------|--------|--------------|----------------|----------|------|---------|--------|
| S046 | [FinBERT](https://huggingface.co/ProsusAI/finbert) (ProsusAI) | sentiment | Financial-text sentiment classification (positive/negative/neutral) | free weights (HF) | `brain/` or agent `skills/` | MODEL | A004 | 🔜 |

**Note:** a model's *output* is a claim like any other — under 026's rules it may
alert only at `VALIDATED` maturity (a measured error rate on a labelled window),
never on a plausible-looking score. See [glossary → maturity gate](../docs/manual/07-glossary.md).
