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
| — | *(none yet — add as identified)* | — | — | per-server | TBV | `integrations/mcp_servers/` | `server`, `tool`, `call_id` | check | orchestrator | ⬜ |

**When adding an MCP server, record:** name, endpoint/command, auth method, the
exact tools it exposes, rate/cost, which agent consumes it, and the provenance
fields (`server`, `tool`, `call_id`) so every MCP-sourced record can be traced.
Then register the new ID in the master index ([`README.md`](README.md#master-index)).
