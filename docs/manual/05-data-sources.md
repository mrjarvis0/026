# 05 · Data sources

[← Structure](02-structure.md) · [Index](README.md) · *Next: Agents (planned)*

> Where 026's information comes from, and how it is governed **before** any code
> touches it. The live catalog is the [`sources/`](../../sources/README.md) folder;
> this section explains how it works.

---

## The rule: sources before code

026's one promise is **provenance** — every conclusion traces back to a raw,
sourced, timestamped record. That is only possible if every source is **catalogued
and governed before** the pipeline that consumes it exists. So the first real work
is not a connector — it is knowing exactly where each piece of evidence comes from,
what it costs, and what it is rate-limited to.

> **A source is not "real" until it has a complete, verified row.** Until then, no
> connector is built against it.

## Where the catalog lives — the `sources/` registry

The catalog is organized **by access type** — one file per kind of source. The
market/domain (crypto, stock, macro…) is a *column* inside each file, so "all
crypto" is still filterable without splitting by market.

| File | Holds |
|---|---|
| [`sources/apis.md`](../../sources/apis.md) | Live / queryable APIs (REST, WebSocket) |
| [`sources/datasets.md`](../../sources/datasets.md) | Bulk / downloadable historical datasets |
| [`sources/links.md`](../../sources/links.md) | Inbox for new URLs + portals/registries to browse |
| [`sources/mcp.md`](../../sources/mcp.md) | MCP servers |
| [`sources/models.md`](../../sources/models.md) | ML models — *not* data feeds (e.g. FinBERT) |
| [`sources/infra.md`](../../sources/infra.md) | Tooling (proxy, SDKs) — *not* feeds |

Full legend, rules, and the research findings are in
[`sources/README.md`](../../sources/README.md).

## How a source is kept honest

- **Global stable ID.** Every source has an ID (`S001`, `S002`, …) that never
  changes, whatever file it lives in — so re-organizing later is painless.
- **One row = one source + one access method.** A hybrid source (e.g. Binance =
  API *and* bulk download) gets one row per method, cross-linked by ID.
- **Status marks reality:** ⬜ known (limits unverified) · 🔜 verified against the
  provider's docs · ✅ live (a connector lands a raw, cited record).
- **Tier marks cost:** `FREE` · `FREE*` (limited) · `PAID-LATER` · `DEAD` ·
  `INFRA`/`MODEL` (not a feed).

## The four layers a source passes through

| Layer | Where | Role |
|---|---|---|
| **Catalog** | [`sources/`](../../sources/README.md) | *This.* What exists, links, notes — for humans |
| **Config** | `config/sources/` | URLs, rate limits, key-names — for code *(later)* |
| **Connector** | `integrations/` | The client that fetches → lands raw in `data/raw/` *(later)* |
| **Secret** | `.env` | The real key — never in tracked source |

## Non-negotiables (from [`AGENTS.md`](../../AGENTS.md))

- 🔒 **Secrets → `.env` only.** `.env.example` holds the key *name*, blank value.
- 🔒 **Raw first.** Fetched bytes land in `data/raw/` untouched, tagged with the
  source's provenance field, before any cleaning.
- 🔒 **Data connectors are read-only.** A connector observes; it never places an
  order. Execution is a separate, gated path (see [04 · Security](04-security.md)).

---

[← Structure](02-structure.md) · [Index](README.md) · *Next: Agents (planned)*
