# ADR-0004 — Source registry organized by access-type with stable IDs

- **Status:** accepted
- **Date:** 2026-09-05
- **Deciders:** operator, Claude
- **History:** [`BUILD_LOG.md`](../../BUILD_LOG.md) → sessions 2026-09-05 (cont. 2–4); registry lives in [`sources/`](../../sources/README.md)

## Context

026's one promise is provenance — every conclusion traces to a raw, sourced record.
That is impossible unless sources are enumerated and governed **before** the pipelines
that consume them (*sources before code*). The operator supplied a real ~40-source
master list mixing live APIs, bulk datasets, on-chain query platforms, one model, and
infra tools. Two organizing questions had to be settled so the catalog would not
sprawl or drift: **split by what?** and **how are rows identified?**

## Decision

Organize the registry **by access type** — one file per access method (`apis.md`,
`datasets.md`, `links.md`, `mcp.md`, `models.md`, `infra.md`) — because type maps 1:1
to how you connect and to the `integrations/` folders, and the set of types is small
and bounded. The market/domain (crypto/stock/macro…) is a **column inside** each
file, so "all crypto" stays filterable without splitting by market.

Identify every source with a **global, stable ID** (`S0xx`) that:
- never changes and is **never reused**, whatever file the row lives in;
- follows the rule **one row = one source + one access method** (a hybrid like Binance
  = API `S002` + bulk `S001`, cross-linked by ID);
- lets new URLs land in `links.md` (the inbox) first, then get triaged.

## Consequences

- **Easy:** moving a row between files is painless (the ID is the anchor, not the
  filename); a hybrid source is unambiguous; the registry maps cleanly onto code
  layout later.
- **Hard / cost accepted:** IDs assigned during research leave **gaps** when a
  candidate is dropped/merged/dead. Gaps must be *documented* (reserved / dropped),
  never silently skipped — enforced by the **master index** in
  [`sources/README.md`](../../sources/README.md#master-index).
- **Requires discipline:** every row must carry its provenance field, landing folder,
  rate limit, cost, and ToS (the canonical schema); a source is not "real" until its
  row is complete and its status reaches ✅.
- **Overlap noted:** `sources/` (catalog) sits beside `integrations/` (code) and
  `config/` (machine config); the boundary is stated in `sources/README.md` so it
  does not confuse.
