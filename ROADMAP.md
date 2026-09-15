# ROADMAP.md — 026 Intelligence Engine OS

> The **planned** path, in sequence. Present-tense "what *is*" lives in
> [`PROJECT_STATE.md`](PROJECT_STATE.md); proven history lives in
> [`BUILD_LOG.md`](BUILD_LOG.md). Everything here is a target until the log says
> otherwise.

**Sequencing principle:** *sources before code.* An agent is only as good as the
evidence it can honestly source. So the first real work is not a connector — it
is knowing **exactly where every piece of evidence comes from**, what it costs,
what it's rate-limited to, and which folder it lands in. Nothing gets a client
until it has a row in the source inventory.

**Status markers:** ✅ done · 🔜 current focus · ⬜ planned

---

## Phase 0 — Genesis · ✅ done

Documentation & continuity system in place (`README`, `AGENTS.md`,
`PROJECT_STATE.md`, `BUILD_LOG.md`, `docs/manual/`). No platform code yet — by
design. See `PROJECT_STATE.md`.

---

## Phase 1 — Source & API Inventory · 🔜 current focus

> **This is where we are now.** The operator is researching sources; each one
> gets catalogued here before any code is written.

**Goal:** a frozen, governed list of every external source 026 will draw on —
APIs, exchanges, websites, wikis, MCP servers, global-data providers — with
access method, auth, rate limits, cost, consuming agent, and a **landing folder**
for each. A source is not "real" until it has a complete row.

**Why first:** the platform's one rule is *provenance* — every conclusion traces
to a raw, sourced, timestamped record. That is impossible unless the sources are
enumerated and governed *before* the pipelines that consume them exist.

### Deliverables
- [x] **`sources/` folder** — the source registry, split by type (`apis`, `datasets`, `links`, `mcp`, `models`, `infra`). Operator's master list catalogued + researched. Rows advance ⬜ → 🔜 → ✅ as verified. (`docs/SOURCES.md` is now a pointer to it.)
- [x] **Master index + stable-ID reconciliation** — every `S0xx` resolves in [`sources/README.md`](sources/README.md#master-index); gaps documented as reserved/dropped *(2026-09-06)*.
- [x] Landing folder decided per source — now a `Lands in` column on every row *(2026-09-06)*.
- [x] Provenance fields fixed per source — now a `Provenance field` column on every row, so each `data/raw/` record can cite its origin *(2026-09-06)*.
- [x] Cost & rate-limit noted per source — split into structured `Rate limit` + `Cost` columns (`TBV` where unverified) *(2026-09-06)*.
- [ ] `.env.example` seeded with the **key names** each source needs (names only — never a real secret)
- [ ] `config/` entries for non-secret config (base URLs, rate limits, model names) under `config/environments/` and `config/models/`
- [ ] Verify remaining ⬜ rows against provider docs (advance ⬜ → 🔜) — most rows still carry unverified limits.

### Definition of done — when Phase 1 is complete

Phase 1 ends (and Phase 2 may begin) when **all** of the following hold:

1. **Every source row is schema-complete** — ID, provenance field, landing folder,
   rate limit, cost, ToS all present (`TBV`/`check` allowed only where genuinely
   unverified, never blank).
2. **Master index reconciles** — every allocated `S0xx` resolves to a file+row; every
   gap ID is accounted for; the count matches the tree.
3. **The buildable-now set is chosen** — the free, live/bulk sources Phase 2 starts
   on are explicitly listed (after removing DEAD + PAID-LATER + non-feeds).
4. **`.env.example` seeded** with the key *names* those first sources need (names
   only), or the decision to defer is recorded.
5. **Fleet/registry agree** — no source points at an agent the contract doesn't
   define *(A05/A06 resolved 2026-09-06)*.

Nothing in Phase 1 requires code — it is the governed, provenance-clean catalog that
Phase 2's connectors are built against.

### Source Inventory — catalog template

> **Canonical schema now lives in [`sources/README.md`](sources/README.md#canonical-row-schema)**
> (the type-file split superseded a single table). The template below is the
> historical origin of that schema — kept for context; the registry is authoritative.

Fill **one row per source** as research completes. `EXAMPLE` rows below are
placeholders — they show the shape, not real sources.

| ID   | Source            | Type          | Access            | Auth        | Rate limit / quota | Cost    | Consumed by | Lands in                 | Provenance field         | Status |
|------|-------------------|---------------|-------------------|-------------|--------------------|---------|-------------|--------------------------|--------------------------|--------|
| S001 | *EXAMPLE provider* | `api`         | REST (JSON)       | API key     | 60 req/min         | free    | A002         | `integrations/apis/`     | `source_id`, `fetched_at`| ⬜ planned |
| S002 | *EXAMPLE exchange* | `exchange`    | REST + WebSocket  | key+secret  | 1200 req/min       | free    | A001         | `integrations/exchanges/`| `source_id`, `fetched_at`| ⬜ planned |
| S003 | *EXAMPLE wiki*     | `wiki`        | MediaWiki API     | none        | be polite          | free    | A002         | `integrations/apis/`     | `page`, `revision_id`    | ⬜ planned |
| S004 | *EXAMPLE MCP*      | `mcp`         | MCP server        | per-server  | n/a                | varies  | orchestrator| `integrations/mcp_servers/`| `server`, `tool`, `call_id`| ⬜ planned |

**Type values:** `api` · `exchange` · `website` (scrape) · `wiki` · `mcp` ·
`global-data` · `messaging` · `webhook`.

### Landing-folder legend — *type → where the connector code goes*

| Type          | Folder                      | Notes |
|---------------|-----------------------------|-------|
| `api`         | `integrations/apis/`        | Third-party REST/GraphQL clients (news, on-chain data, global data). |
| `exchange`    | `integrations/exchanges/`   | Market/exchange **data** connectors — read-only. Order execution is a separate, gated path, never mixed into a data connector. |
| `website`     | `integrations/apis/`        | Scrapers/readers. Respect `robots.txt` + ToS; note that in the row. |
| `wiki`        | `integrations/apis/`        | MediaWiki/wiki APIs — cite `revision_id` for provenance. |
| `mcp`         | `integrations/mcp_servers/` | MCP server integrations, surfaced through the tool registry. |
| `global-data` | `integrations/apis/`        | Public/global datasets exposed as APIs (e.g. reference stats). |
| `messaging`   | `integrations/messaging/`   | Chat/messaging channels (in and out). |
| `webhook`     | `integrations/webhooks/`    | Inbound/outbound webhook endpoints. |

**Non-negotiables for every source (from `AGENTS.md`):**
1. **Secrets → `.env` only.** Never hardcode a key inside `integrations/`.
   `.env.example` holds the key *name* with a blank value.
2. **Raw first.** Fetched bytes land in `data/raw/` untouched, tagged with the
   source's provenance field, *before* any cleaning.
3. **Data connectors are read-only.** A connector observes; it never places an
   order. Execution lives in its own gated path (OFF by default), isolated from
   every data connector.
4. **Cost & limits recorded**, so the orchestrator can budget against them later.

---

## Phase 2 — Connector skeletons · ⬜ planned

Once the inventory is frozen: one thin, typed client per source under
`integrations/`, each registered in `tools/registry/`, each writing to
`data/raw/` with its provenance field. **No agent logic yet** — just proven,
governed access to each source (a fetch that lands a raw, cited record).

---

## Phase 3 — Datasets · ⬜ planned *(the "talk after some work" phase)*

Defer per the operator's plan. When we get here: `data/processed/` schemas, the
`data/vector_store/` layout, `data/backups/` policy, and how raw records become
retrievable knowledge in `brain/`. Nothing is designed here until Phase 1–2 have
landed real sources to shape it.

---

## Phase 4+ — Kernel & Fleet · ⬜ planned

From here the plan dovetails into the fleet roadmap already in
[`AGENTS.md` §12](AGENTS.md) — not duplicated here:

- Kernel: `config → core runtime → shared brain → message bus` (first real `make doctor`)
- A001 / A002 built behind the kernel socket, tests green
- Orchestrator: plan → route → fuse, with budgets (fed by Phase 1 cost data)
- Cross-agent correlation + entity ledger
- Sentinel: trust enforcement + live execution-gate surface scan
- Dashboard: chat, traces, coverage, cost, health

---

<sub>Sources before code. A connector without a catalogued, governed source is a
claim without provenance — and 026 would rather say "cannot be determined."</sub>
