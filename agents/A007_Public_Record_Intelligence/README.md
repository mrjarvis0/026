# A007 — Public-Record Intelligence (scaffold)

> **Status: scaffold** — manifest only, no code, no data pipeline, no tests.
> Not an active fleet member (`config/agents/registry.yaml`: `enabled: false`).
> Proposed 2026-09-15 from LuxAlgo MCP source research. See
> [`docs/manual/06-agents.md` §6](../../docs/manual/06-agents.md) for the full
> research trail and [`sources/mcp.md`](../../sources/mcp.md) (`S119`) for the
> source record.

## Why this agent exists

LuxAlgo's MCP server exposes 18 government/public-record datasets through its
`trackers_*` tools (Congress trades, insider Forms 3/4/5, 13F, lobbying,
patents, clinical trials, FDA approvals, campaign finance, PAC contributions,
congressional hearings, COT, Fed communications, legislation, Wikipedia
pageviews...). Forcing all 18 into `A006` (Macro/Econ) would blur that agent's
domain — insider trading and patent filings are not macro indicators. `A007`
is the dedicated home for the **insider / "smart-money" / public-record**
subset specifically.

This was a real fork, not an obvious call — the alternative (split everything
across `A004`/`A006`, no new agent) is recorded in `docs/manual/06-agents.md` §6
in case a future session wants to revisit it.

## Scope

**In scope (this agent):**
- Congressional trades (Senate eFD + House Clerk)
- Insider transactions — Forms 3/4/5 (SEC EDGAR)
- 13F institutional holdings (EDGAR 13F-HR)
- Lobbying filings (Senate LDA API)
- Campaign finance + PAC contributions (FEC bulk)
- Patents (PatentsView / USPTO — needs a free USPTO key)
- Clinical trials (ClinicalTrials.gov)
- FDA drug approvals (openFDA Drugs@FDA)
- Congressional hearings (GovInfo CHRG)

**Explicitly out of scope (routed elsewhere — do not duplicate):**
- Futures positioning (COT, CFTC) → `A006` Macro/Econ
- Fed communications (Federal Reserve Board) → `A006` Macro/Econ
- Federal legislation (GovInfo BILLSTATUS) → `A006` Macro/Econ
- Wikipedia pageviews → `A004` Sentiment (attention/interest proxy, not a filing)

## Data source

[`sources/mcp.md`](../../sources/mcp.md) `S119` — LuxAlgo MCP
(`mcp.luxalgo.com/mcp`), `trackers_*` tool family. Free, keyless, CC0-licensed
government data (patents need a free USPTO key). Also available as daily
JSON/Parquet dumps on GitHub without going through MCP at all.

## Build starting point

Follow `AGENTS.md` §5 ("Adding a new agent — quick reference") once the
operator green-lights Phase 4 fleet work (per `ROADMAP.md`, connector/kernel
code doesn't start until Phase 1 — source inventory — is signed off):

1. Flesh out `evidence.detectors` in `agent.yaml` — e.g. a cluster detector for
   correlated Congress-trade + insider-Form-4 activity on the same ticker in a
   short window.
2. Vertical slice first: **one** `trackers_*` tool → ingestion → normalization
   → store → **one** skill, before expanding to the full dataset list (same
   build order A001 and A002 used).
3. Register in `config/agents/registry.yaml` with `enabled: true` only once
   tests exist — an agent with no `evidence.detectors` and no tests is capped
   at trust level 1 (`AGENTS.md` §2), same as it is today.
