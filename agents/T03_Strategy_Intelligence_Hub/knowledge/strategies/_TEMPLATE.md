---
slug: <trader-slug>
trader: <Full Name>
market_origin: <stocks|futures|forex|crypto|market-agnostic>
mechanical: <green|yellow|red>   # backtestability: green=mechanical, yellow=semi, red=discretionary
status: researching              # researching | documented | implemented
agent: null                      # e.g. $003-donchian once scaffolded
sources: []                      # list of [TAG] ids that resolve in ../sources/SOURCES.md
---

# <Full Name> — <strategy name>

## Who & why they matter
Short factual background. `[TAG]`

## The exact rules (cited)
- **Entry:** … `[TAG]`
- **Exit:** … `[TAG]`
- **Position sizing / risk:** … `[TAG]`
- **Universe / timeframe:** …

## How it becomes a signal
How the rules map to `position ∈ {-1, 0, +1}` in the hub's contract. Note any simplification
honestly (Constitution R-E.5).

## Parameters (with sensible search ranges)
| Param | Meaning | Default | Range |
|---|---|---|---|

## Open questions / caveats
What is uncertain, discretionary, or needs re-verification at build time (R-E.6).

## Sources
- `[TAG]` … (also add to ../sources/SOURCES.md)
