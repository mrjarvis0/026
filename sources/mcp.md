# mcp.md — MCP servers

> MCP (Model Context Protocol) servers that provide real-time data or tools,
> surfaced through 026's tool registry. Operator's intent: **connect all useful
> MCP servers.** Each server needs its auth + tool list catalogued before use.
> Code lands in `integrations/mcp_servers/`. Master ID index: [`README.md`](README.md#master-index).

**Schema.** Aligned with the rest of the registry: an MCP server's "rate limit" is
usually per-server (`TBV`), its provenance is the call itself (`server`, `tool`,
`call_id`). `ToS` = the server's usage terms (`check` until reviewed).

| ID | Server | Domain | Tools / data it provides | Auth | Rate/Cost | Lands in | Provenance field | ToS | Consumed by | Status |
|----|--------|--------|--------------------------|------|-----------|----------|------------------|-----|-------------|--------|
| S119 | [LuxAlgo MCP](https://mcp.luxalgo.com/mcp) (hosted) | mixed (stock/crypto/forex/macro/alt-data) | `library_*` (850+ trading concepts + Pine source), `edge_*` (historical stats, N + CI), `trackers_*` (18 govt/public-record datasets), `propfirms_*` (Monte Carlo sim), `journal_*` (personal trade log, needs OAuth) | none for public tools; LuxAlgo OAuth for `journal_*` | TBV | `integrations/mcp_servers/` | `server`, `tool`, `call_id` | check | A007, A004, A005, A006, T01, librarian — split by tool family, see `docs/manual/06-agents.md` §6 | ⬜ |
| S120 | LuxAlgo Whale Options (local-only MCP, self-hosted, separate from S119) | mixed (options flow — stocks/crypto/forex/futures/commodities) | 16 tools — real-time options prints (sweeps/blocks/splits), net GEX per strike/expiry; synthetic demo tape works without a feed key | none for demo; data-vendor key for a real feed | TBV | `integrations/mcp_servers/` | `server`, `tool`, `call_id` | check | A005 | ⬜ |

**When adding an MCP server, record:** name, endpoint/command, auth method, the
exact tools it exposes, rate/cost, which agent consumes it, and the provenance
fields (`server`, `tool`, `call_id`) so every MCP-sourced record can be traced.
Then register the new ID in the master index ([`README.md`](README.md#master-index)).

**`S119` connected 2026-09-15** — registered as a project MCP server in
[`../.mcp.json`](../.mcp.json) (`http`, `https://mcp.luxalgo.com/mcp`, no key),
so it's callable ad-hoc from a Claude Code session on this repo (after a
restart + the usual "trust this project's MCP server?" prompt). **This is not**
`026`'s own Phase-2 connector (`integrations/mcp_servers/`, writing to
`data/raw/` with provenance) — that hasn't started, per `ROADMAP.md`'s Phase 1
gate. Status stays `⬜` until rate limits etc. are actually verified.
`S120` (Whale Options) and `S121` (Broker SDK) are **not** connected — both are
described as local-only/self-hosted in the operator's research, and neither an
install command nor a repo URL was given, so nothing was guessed. Operator: if
you have LuxAlgo's setup docs for either, share them and I'll wire it up the
same way.
