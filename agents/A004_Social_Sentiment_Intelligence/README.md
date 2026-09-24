# A004 — Social Sentiment Intelligence (empty scaffold)

> **Status: empty scaffold** — folder + this note only. No code, no `agent.yaml`
> manifest, no registry entry yet. Naming per `AGENTS.md` §3 (A-series =
> read-only intelligence). Build & kernel wiring deferred ("baaki kaam baad me").

**Layer:** Data / Ingestion · **Markets:** crypto · stocks · forex

## What it will do
Pulls sentiment from social sources (X/Twitter, Reddit, Telegram) and turns it
into measurable signals: bullish/bearish ratio, mention-volume spikes, and
abnormal-attention flags. Sentiment ≠ truth — it is an attention/crowd proxy,
scored on its own, never merged into a verdict.

## Reserved slot
A004 was already reserved in `AGENTS.md` §3 as *"Sentiment — Social/market
sentiment fusion."* This scaffold gives that reserved ID a home.

**Maps to:** operator research #2 (SocialSentimentAgent).
**Note:** A002 already has a *partial* Reddit connector; A004 is the dedicated,
multi-source sentiment owner — don't duplicate A002's internal news scoring here.
