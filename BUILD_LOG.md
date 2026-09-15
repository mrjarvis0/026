# BUILD_LOG.md â€” 026 Intelligence Engine OS

> Append-only history. **Never overwritten.** Current snapshot lives in
> `PROJECT_STATE.md`. Every session records: goal, audit findings, files touched
> (tagged), tests run, decisions with reasons, self-critique, open questions, and
> where the next session starts.

---

## Session 2026-09-04 â€” genesis (documentation system)

### Goal for this session

1. Establish 026's design and documentation system from a clean scaffold.
2. Put the continuity system in place â€” `AGENTS.md`, `PROJECT_STATE.md`,
   `BUILD_LOG.md` â€” plus a living handbook, `docs/MANUAL.md`.
3. Confirm the project's data-exposure surface (git / mail / other devices).

### Audit findings (delta from last session)

No previous session recorded â€” this is session zero for 026. Established by
reading the tree, not assuming:

- `F:\026` is a scaffold: 19 top-level directories, all empty; top-level doc
  files present at 0 bytes.
- **Not a git repository.** No `.git` directory, no remotes. `.github/workflows/`
  holds `ci.yml` and `deploy.yml`, both **0 bytes** â€” inert and unrunnable.
- The path is a plain drive location, not a cloud-sync folder. The only non-empty
  files in the project are the documents produced this session.

Conclusion for the operator's privacy question: **project data does not leave the
machine.** It is not on git, not emailed, not synced to another device. That
changes only if a git remote, deploy target, or connector is added later â€” none
exists today. Recorded in `PROJECT_STATE.md` â†’ *Data-exposure status*.

### The design decision â€” 026 as an OS for a fleet

026 is an operating system that hosts, schedules, and correlates a fleet of
intelligence agents, rather than a single pipeline. The value that justifies the
"OS" framing is **combination**: one agent's sourced finding becomes fuel for
another's, under one governance layer (the sentinel) that never lets a claim
outrun its evidence.

This makes 026's core capability concrete and testable: fuse a news-side rumor
(A002) with an on-chain anomaly (A001) into one correlated finding â€” while keeping
each half's provenance split, never averaging confidence, and never resolving a
disagreement by overwriting it.

The laws the whole system inherits (evidence standard, maturity gates, coverage
before absence, provenance, `no_trade_execution`, downward-only imports) are
written into `AGENTS.md` Â§0 and enforced, per the roadmap, in code the kernel
sessions will build.

### Files touched

| File | Tag | Note |
|---|---|---|
| `README.md` | **BUILD-NEW** | 026 vision, kernel+fleet+services architecture, directory map, honest genesis status |
| `AGENTS.md` | **BUILD-NEW** | Fleet contract â€” manifest schema, cross-agent correlation rules, trust/governance, the 10-step build discipline |
| `PROJECT_STATE.md` | **BUILD-NEW** | Living snapshot; honest "nothing runs yet" state + data-exposure status |
| `BUILD_LOG.md` | **BUILD-NEW** | This file â€” append-only history, genesis entry |
| `docs/MANUAL.md` | **BUILD-NEW** | The living handbook: structure, per-file catalog, security roles, data sources, how it works |

**No source code was written or modified.** There is none to modify at genesis.

### Tests run / passed / failed

| Command | Result |
|---|---|
| any suite | **none** â€” `tests/` is empty, by design at genesis |

No tests were run because none exist and no code was written. Recording this
rather than implying coverage: a green suite would be a lie here, and an empty one
is the truth.

### Decisions made and why

- **026 framed as an OS, not a single agent.** The differentiator is coordination
  and correlation across agents under one governance layer â€” that is what a folder
  of scripts cannot do.
- **Docs describe the target in present tense but the status sections say plainly
  it does not run.** Kept the aspirational architecture readable while refusing to
  let it read as shipped â€” the `Status` / `Honest status` sections carry that.
- **A living manual (`docs/MANUAL.md`) is a first-class artifact.** The operator
  wants a handbook that teaches the whole project â€” structure, every file, security
  roles, data sources â€” and grows as the project grows. The build discipline in
  `AGENTS.md` Â§9.7 now requires updating it whenever a file is created or moved.
- **Confirmed the data-exposure surface before answering it.** Checked for `.git`,
  remotes, workflow contents, and the path â€” did not assert "nothing leaks" from
  memory.

### Proposed improvements (not acted on)

- `PROPOSED`: fill `ARCHITECTURE.md` with the layer ranking and the cross-agent
  correlation contract, so `tests/test_architecture.py` has a spec to enforce.
- `PROPOSED`: write a real `Makefile` whose `doctor` target fails honestly before
  the kernel exists, then passes as each check becomes real.
- `PROPOSED`: seed `.gitignore` and `.env.example` before any secret or venv is
  created, so nothing sensitive is ever tracked even once git is initialised.

### Self-critique â€” what is fragile, assumed, untested

- **Assumed:** that the target directory is `F:\026`. Cheap to correct if wrong â€”
  these five files move; nothing else was created or destroyed.
- **Assumed:** Python 3.11+/pydantic-v2/async-first is the right base. Reasonable
  for this shape of system, but not yet a confirmed operator decision.
- **Untested â€” everything.** These are design and documentation artifacts. Not one
  claim about 026's behavior has been executed, because there is nothing to
  execute. The value is a trustworthy plan and an honest starting line.
- **Fragile:** the docs' credibility depends on future sessions keeping
  `PROJECT_STATE.md` and `docs/MANUAL.md` honest and current. The moment either
  claims something that was never run or built, the whole system is worth nothing.

### Open questions for the operator

1. Kernel-first, or one agent end-to-end first? (Recommend thin kernel + `make doctor`.)
2. Confirm the runtime stack: Python 3.11+ / pydantic-v2 / async-first?
3. Which provider keys will 026 hold, and in what `.env`?

### Next session should start at

**The kernel skeleton â€” see `PROJECT_STATE.md` â†’ "Next session should start at".**
Provision `.venv`, write `config/` (the dependency-free lowest layer), then a
`Makefile` whose `make doctor` verifies interpreter, config load, no-secrets, and
the `no_trade_execution` constant â€” made to fail honestly first. Add
`tests/test_architecture.py` before there is much to import. Record every new file
in `docs/MANUAL.md` as it lands.

Do **not** build an agent before `make doctor` is green.

---

## Session 2026-09-05 â€” stack decision + execution charter evolved

### Goal for this session

1. Choose and record the project's language/technology stack.
2. Resolve the direction question. 026 is confirmed as an **intelligence-driven
   trading system**: world-wide data â†’ real-time analysis â†’ market prediction â†’
   backtest / paper-trade â†’ (eventually) gated real-money execution.
3. Evolve the `no_trade_execution` law into an honest, gated model, since
   real-money execution is now an explicit goal â€” not a silent rewrite.

### Decisions made and why

- **Stack confirmed â€” deliberately minimal.** Python is the whole backend brain
  and fleet (ingestion, MCP connectors, real-time feeds, ML/prediction, analysis,
  backtesting, paper-trading, strategy, risk engine, the gated execution client,
  the API) + TypeScript/React/Next.js for the dashboard + SQL. PostgreSQL +
  TimescaleDB + pgvector as **one** database engine; Redis for cache/queue/bus.
  Rust is reserved for a *measured* hot path only (via PyO3), not adopted now.
  Full breakdown: `docs/STACK.md`. *Why:* two languages doing ~95% of the work
  keeps the evidence-grade discipline holdable for a small team; a polyglot
  backend is surface area, not capability.
- **Rejected: a separate Node runtime for feeds / API.** Python `asyncio` handles
  WebSocket ingestion without a second backend language; Next.js already carries
  the only Node the UI needs.
- **Charter evolved: `no_trade_execution` (never) â†’ gated execution (OFF by
  default).** The old absolute prohibition was honest for an intelligence-only
  platform but false for the operator's actual goal. New law: real-money orders
  fire **only** through the sentinel's gate â€” paper-validated, hard risk limits
  (max position, daily loss cap, kill-switch), human-approvable, default OFF.
  Data connectors stay strictly read-only; execution is an isolated, separate
  path. Every order traces to the evidence that licensed it; nothing fires
  silently.

### Files touched

| File | Tag | Note |
|---|---|---|
| `docs/STACK.md` | **BUILD-NEW** | The chosen language/tech stack and what each language does |
| `README.md` | **DOC-EDIT** | "One rule" bullet, sentinel ASCII label, directory map â†’ gated execution |
| `AGENTS.md` | **DOC-EDIT** | Â§0 law, manifest invariant, sentinel job, correlation flow, trust boundary, escalation list, architecture test, fleet rule 6, roadmap â†’ gated execution |
| `PROJECT_STATE.md` | **DOC-EDIT** | Invariant row + doctor check â†’ gated execution; date + phase bumped |
| `ROADMAP.md` | **DOC-EDIT** | Exchange-connector rule, financial non-negotiable, sentinel roadmap â†’ gated execution |
| `docs/manual/02-structure.md`, `docs/manual/README.md` | **DOC-EDIT** | `no-trade` â†’ `execution-gate` wording |

**No source code was written or modified.** Execution code does not exist; only
the charter now tells the truth about the target.

### Tests run / passed / failed

| Command | Result |
|---|---|
| any suite | **none** â€” `tests/` still empty; no code written this session |

### Self-critique â€” what is fragile, assumed, untested

- **The charter now promises a gate that does not exist.** "Gated execution, OFF
  by default" is a design commitment, not a running control. Until `security/`
  implements the gate and a test proves an order cannot fire without passing it,
  this is a claim, not a safeguard. The first execution-related code **must** be
  the gate and its test â€” never an order path first.
- **The stack is chosen, not validated.** No `.venv`, no `pyproject.toml`, no
  build. The next session must make `make doctor` real before trusting any of it.
- **Real-money execution carries real financial risk.** No prediction or backtest
  result licenses turning the gate on. That decision stays the operator's, per
  stage, after paper-trade evidence.

### Open questions for the operator

1. Which broker/exchange will execution eventually target (read-only data first)?
2. What are the initial hard risk limits (max position, daily loss cap)?
3. Phase 1 (source inventory) remains the current roadmap focus â€” confirm we
   start there next, before any kernel code.

### Next session should start at

**Phase 1 â€” Source & API Inventory** (`ROADMAP.md`). Begin cataloguing the
world-wide data sources (APIs, exchanges read-only, MCP servers) into
`docs/SOURCES.md`, one governed row each, before any connector code. The kernel
skeleton + an honest `make doctor` remains the first code milestone after that.

---

## Session 2026-09-05 (cont.) â€” source inventory seeded

### Goal

Start `ROADMAP.md` Phase 1: create `docs/SOURCES.md`, the master source inventory,
per the operator's intent â€” **all markets worldwide, all source types, free-tier
first, paid later.**

### Decisions made and why

- **Structure covers the whole world; seed covers it via aggregators.** "All
  sources in the world" is unbounded, so the catalog is organised by domain
  (crypto market + on-chain, global equities, forex, commodities/indices/rates,
  macro, news, sentiment, reference, MCP) â€” nothing excluded â€” and seeded with the
  strongest **free** sources per domain. Preferred high-coverage aggregators/
  libraries (CCXT = 100+ crypto exchanges; yfinance / Twelve Data / Alpha Vantage
  = global equities+fx+commodities; FRED / World Bank / IMF = global macro; GDELT =
  global news) so one connector covers a large slice of "the world."
- **Seed rows are `â¬œ planned` and explicitly unverified.** Rate limits, costs, and
  auth are best-known values, not confirmed. A row is promoted â¬œ â†’ ðŸ”œ (docs
  verified) â†’ âœ… (connector lands a raw, cited record). This keeps the catalog
  honest: nothing claims to be "real" on an unchecked value.
- **Free-tier now, paid shortlisted.** Paid/limited sources (Dune, Whale Alert,
  Trading Economics, X/Twitter, Polygon paid) are catalogued as `PAID-LATER`.
- **Proposed new agents A05 (Market Data) and A06 (Macro/Econ).** "All markets"
  needs consumers beyond the four agents in `AGENTS.md` Â§3. Flagged as proposals,
  not silently added to the fleet contract.

### Files touched

| File | Tag | Note |
|---|---|---|
| `docs/SOURCES.md` | **BUILD-NEW** | Master source inventory â€” ~55 free-tier global sources across 10 domains, seeded â¬œ unverified |
| `ROADMAP.md` | **DOC-EDIT** | Phase 1 `SOURCES.md` deliverable ticked (created; rows unverified) |
| `PROJECT_STATE.md` | **DOC-EDIT** | Added `docs/STACK.md` + `docs/SOURCES.md` to "what exists"; next-session points at source verification |

### Tests run / passed / failed

| Command | Result |
|---|---|
| any suite | **none** â€” still docs only; no code written |

### Self-critique

- **The inventory's values are unverified.** Every rate limit / cost / auth is a
  seed to check against provider docs, not a fact. If a connector is built off an
  unverified row, that violates the catalog's own rule â€” verify first.
- **A05 / A06 are not real agents.** Until confirmed and written into `AGENTS.md`,
  "Consumed by A05/A06" is a plan, not a wiring.
- **`docs/MANUAL.md` not yet updated** for `STACK.md` / `SOURCES.md` â€” pending, so
  the file catalog is momentarily behind reality.

### Next session should start at

Verify the highest-value free rows first (advance â¬œ â†’ ðŸ”œ): the aggregators that
buy the most coverage â€” CCXT, yfinance/Twelve Data, FRED, GDELT â€” then pick the
first sources to make âœ… real in Phase 2 (thin, typed connectors landing raw,
cited records). Also: confirm A05/A06 with the operator, and fold `STACK.md` /
`SOURCES.md` into `docs/MANUAL.md`.

---

## Session 2026-09-05 (cont. 2) â€” operator master list researched & organized

### Goal

The operator supplied a real 40-source master list (Crypto 17 Â· Stock 15 Â·
Blockchain & Sentiment 8). Research each, then rewrite `docs/SOURCES.md` around the
real list â€” replacing the earlier illustrative seed.

### Research findings (web-verified 2026-09-05) â€” the value-add

Seven sources were **not** what the list assumed; catching these prevents building
against dead or paid endpoints:

- **IEX Cloud â†’ DEAD.** Shut down 2024-08-31; all endpoints off. Removed from buildable set; migrate path noted (Alpha Vantage / Polygon / FMP).
- **CoinCap â†’ paid now.** Keyless `api.coincap.io/v2` is gone (NXDOMAIN); v3 needs key + prepaid credits. Re-tagged `PAID-LATER`.
- **Massive.com â†’ not a data source.** It is a residential-proxy / web-scrape infra vendor. Re-tagged `INFRA` (useful for scraping API-less sites, not a feed).
- **Glassnode â†’ API paid.** Free is web-only, Tier-1, 24h. `PAID-LATER`.
- **CryptoQuant â†’ free plan has no API.** `PAID-LATER`.
- **Dune â†’ free API gutted** (~Sept 2026, view-only / minimal credits). `PAID-LATER`.
- **Kaiko â†’ free = research charts only**; raw feeds enterprise. `PAID-LATER`.

### Decisions made and why

- **Introduced an `Access` taxonomy.** The list is not all live APIs â€” it mixes
  `live-api`, `onchain`, `bulk-dataset` (Kaggle/HF/AWS/GCP/Stooq/Binance-vision),
  `query-platform` (Dune/Glassnode/Kaiko), one `model` (FinBERT â€” not data), and
  `infra` (Massive proxy, OpenBB SDK). Each now has a distinct landing target, so a
  dataset loader and a model wrapper are not mistaken for API connectors.
- **`docs/SOURCES.md` rewritten** around the operator's real list; earlier seed
  retired. High-coverage free multipliers not on the list (CCXT, Frankfurter,
  Reddit, Fear&Greed) parked in a "recommended additions" section, not silently
  mixed in.
- **Status honesty:** rows I web-checked today are ðŸ”œ; rows I know but did not
  verify limits for are â¬œ (limits to confirm before a connector).

### Files touched

| File | Tag | Note |
|---|---|---|
| `docs/SOURCES.md` | **BUILD-REWRITE** | Operator's 40 sources, researched, organized by access type; 7 gotchas surfaced |
| `PROJECT_STATE.md` | **DOC-EDIT** | `docs/SOURCES.md` row updated to "built / researched" |

**No source code written.** Docs only.

### Tests run / passed / failed

| Command | Result |
|---|---|
| any suite | **none** â€” docs only |

### Self-critique

- **â¬œ rows are still unverified.** Rate limits/costs for the well-known APIs
  (CoinGecko, Alpha Vantage, Finnhub, Polygon, Twelve Data, Etherscan, FRED, â€¦) are
  from prior knowledge, not today's docs â€” confirm before building each.
- **Free tiers move.** Today's ðŸ”œ truth can change (CoinCap and Dune both changed
  recently). Re-verify at connector-build time, not just here.
- **Buildable-now set is smaller than 40.** After removing DEAD (IEX) and
  PAID-LATER (CoinCap, Glassnode, CryptoQuant, Dune, Kaiko) and non-feeds (Massive
  infra, FinBERT model), the free live/bulk set is what Phase 2 should start on.

### Next session should start at

Pick the **first free, high-value sources to make âœ…** in Phase 2 â€” likely the free
live APIs (Binance public, CoinGecko, yfinance, Finnhub, FRED, GDELT) and a couple
of bulk datasets â€” write one thin, typed connector each landing a raw, cited record.
Confirm A05/A06 with the operator; fold `STACK.md` / `SOURCES.md` into `docs/MANUAL.md`.

---

## Session 2026-09-05 (cont. 3) â€” source catalog moved to `sources/` folder

### Goal

Operator's call: keep the source catalog in a **dedicated folder, split by type**
(one file for APIs, one for links, one for MCP, etc.) rather than a single
`SOURCES.md`.

### Decision â€” organize by *access type*, tag domain per row

New top-level `sources/` folder, one file per access method:
`apis.md` Â· `datasets.md` Â· `links.md` (inbox + portals) Â· `mcp.md` Â· `models.md`
(FinBERT â€” not data) Â· `infra.md` (Massive proxy, OpenBB SDK â€” not feeds) Â· `README.md`.

*Why type, not market:* it maps 1:1 to how you connect and to `integrations/`
folders; the set of types is small and bounded (won't sprawl as "all the world" is
added). The market/domain (crypto/stock/macroâ€¦) is a **column** inside each file, so
"all crypto" is still filterable.

**The rule that future-proofs it** (operator asked "will this cause future
problems?"): every source has a **global stable ID** (`S0xx`) that never changes;
**one row = one source + one access method**; a hybrid source (Binance = API S002 +
bulk S001) gets a row per method, cross-linked by ID; new URLs land in `links.md`
(inbox) then get triaged. So moving a row between files later is painless â€” the ID
is the anchor, not the filename.

### Files touched

| File | Tag | Note |
|---|---|---|
| `sources/README.md` + `apis.md` `datasets.md` `links.md` `mcp.md` `models.md` `infra.md` | **BUILD-NEW** | The source registry, split by type; 40 sources distributed with global IDs |
| `docs/SOURCES.md` | **BUILD-REWRITE** | Now a pointer stub â†’ `sources/README.md` (no duplicated content â†’ no drift) |
| `README.md` | **DOC-EDIT** | Directory map: added `sources/` (Governance layer) |
| `ROADMAP.md` | **DOC-EDIT** | Phase 1 deliverable now points at the `sources/` folder |
| `PROJECT_STATE.md` | **DOC-EDIT** | "What exists" reflects the `sources/` folder + the pointer stub |

**No source code written.** Docs/catalog only.

### Self-critique

- **A new top-level folder was added** (`sources/`). It overlaps conceptually with
  `integrations/` (code) and `config/` (config) â€” mitigated by stating the split
  explicitly in `sources/README.md` ("what lives elsewhere"). If it ever confuses,
  it can fold under `docs/` with no ID changes.
- **`docs/MANUAL.md` still not updated** for `STACK.md`, the `sources/` folder, or
  the gated-execution charter â€” the handbook is now several changes behind. Pending.
- Same-day churn: `SOURCES.md` was created, filled, researched, then moved in one
  day. The moves are cheap (docs only, IDs stable) but the operator should confirm
  the `sources/` layout is what they want before more sources are poured in.

### Next session should start at

Await the operator's remaining source URLs (they land in `sources/links.md` inbox,
then get triaged into the type files). Then confirm A05/A06 and update
`docs/MANUAL.md` to catalog the new `sources/` folder + `STACK.md`.

---

## Session 2026-09-05 (cont. 4) â€” manual update + full consistency audit

### Goal

Update the manual for everything built this session, and audit all docs for drift /
organization â€” the operator wants everything finely organized.

### Audit findings & reconciliations

- **Naming reconciliation (important).** The genesis entry above records a file
  `docs/MANUAL.md` tagged BUILD-NEW. In reality the manual was created as the
  **`docs/manual/` folder** (`README.md` index + `01-overview.md` + `02-structure.md`);
  no `docs/MANUAL.md` file ever existed. Per the "reconcile explicitly, never
  silently" rule, that genesis line is left as history and corrected here. All live
  references to `docs/MANUAL.md` in `README.md`, `AGENTS.md`, and `PROJECT_STATE.md`
  were repointed to `docs/manual/` this session.
- **Stale hard-rule in the manual.** `docs/manual/01-overview.md` still said 026
  would "sign a transaction, place a trade, or move any funds" â€” contradicting the
  gated-execution charter adopted earlier today. Rewritten to the gated model, and a
  "will act via the gated layer" line added to what 026 *will* do. The now-false
  "never give financial advice" bullet was replaced with "never present a prediction
  as a certainty" (consistent with both the ethos and the trading purpose).
- **`sources/` folder was absent from the manual.** Added to `02-structure.md`
  (top-level table + a per-file sub-section) and given a full new section 05.

### Files touched

| File | Tag | Note |
|---|---|---|
| `docs/manual/05-data-sources.md` | **BUILD-NEW** | New manual section â€” governs the `sources/` registry, the 4 layers, non-negotiables |
| `docs/manual/README.md` | **DOC-EDIT** | Section 05 now written + linked |
| `docs/manual/01-overview.md` | **DOC-EDIT** | One-liner + will/never rules â†’ gated-execution honest |
| `docs/manual/02-structure.md` | **DOC-EDIT** | Added `sources/` (top-level + files) and the `docs/` top-level files note |
| `README.md`, `AGENTS.md`, `PROJECT_STATE.md` | **DOC-EDIT** | `docs/MANUAL.md` â†’ `docs/manual/` (8 references) |

**No source code written.** Docs only.

### Tests run / passed / failed

| Command | Result |
|---|---|
| grep sweep: `docs/MANUAL.md`, stale trade rules | **clean** in live docs â€” only append-only BUILD_LOG history retains the old names (by design) |
| any suite | **none** â€” docs only |

### Self-critique â€” what's still not organized

- **`ARCHITECTURE.md` and `CHANGELOG.md` are 0 bytes.** Present but empty. Honest at
  genesis (history lives in `BUILD_LOG.md`), but untidy â€” decide whether to fill them
  with pointers or delete them.
- **Manual sections 03 (Architecture), 04 (Security), 06 (Agents), 07 (Glossary),
  08 (Manual log) are still planned.** `01-overview.md` and `02-structure.md` link
  forward to `04-security.md`, which does not exist yet â€” a dangling link until that
  section is written (expected per the "one at a time" plan, but worth knowing).
- **`docs/manual/` sub-folders** (`architecture/`, `adr/`, `api/`, `agents/`,
  `runbooks/`) described in `02-structure.md` do not exist as folders yet â€” they are
  the documented target.

### Next session should start at

Await the operator's remaining source URLs (â†’ `sources/links.md` inbox â†’ triaged).
When ready, write manual section 04 (Security) so the forward links resolve, and
confirm the A05/A06 agents. Decide the fate of the empty `ARCHITECTURE.md` /
`CHANGELOG.md`.

---

## Session 2026-09-05 (cont. 5) â€” pointer stubs + fix all broken links

### Goal

Operator: give `ARCHITECTURE.md` / `CHANGELOG.md` pointer stubs, and fix all errors.

### What was done

- **`ARCHITECTURE.md`** â€” pointer stub â†’ README architecture, `docs/manual/`,
  `AGENTS.md`, `04-security.md`, `STACK.md`, `BUILD_LOG.md`. (Full write-up will be
  manual section 03.)
- **`CHANGELOG.md`** â€” pointer stub â†’ `BUILD_LOG.md` (history), `PROJECT_STATE.md`
  (current), `ROADMAP.md` (planned). A versioned changelog starts at first release.
- **Broken link fixed.** A repo-wide link scan found the only broken internal link:
  `04-security.md`, referenced from `01-overview.md`, `02-structure.md`, and
  `05-data-sources.md`, but the file did not exist. **Wrote `docs/manual/04-security.md`**
  (sentinel, trust levels, the execution gate, secrets, evidence guarantees â€”
  plain-language guide to `AGENTS.md` Â§0/Â§6) and linked it from the index.
- **PROJECT_STATE correction.** The "what exists" table listed `ROADMAP.md` as
  "â¬œ empty, 0 bytes" â€” but it has ~7 KB of content. Split that row: `ROADMAP.md`
  âœ… written; `ARCHITECTURE.md`/`CHANGELOG.md` âœ… pointer; only `Makefile` /
  `requirements.txt` remain â¬œ empty.

### Files touched

| File | Tag | Note |
|---|---|---|
| `ARCHITECTURE.md`, `CHANGELOG.md` | **BUILD-NEW** | Pointer stubs (were 0 bytes) |
| `docs/manual/04-security.md` | **BUILD-NEW** | New manual section â€” resolves 3 dangling links |
| `docs/manual/README.md` | **DOC-EDIT** | Section 04 written + linked |
| `PROJECT_STATE.md` | **DOC-EDIT** | Manual sections + fixed the ROADMAP "empty" error |

### Tests run / passed / failed

| Command | Result |
|---|---|
| repo-wide markdown link scan (resolve every `](*.md)` target) | **PASS â€” 0 broken links** |
| grep: stale `docs/MANUAL.md` / trade rules in live docs | **clean** (only BUILD_LOG history retains old names) |
| any suite | **none** â€” docs only |

### Still empty (planned placeholders, not errors)

`Makefile`, `requirements.txt` (+ `requirements/{base,dev,prod}.txt`),
`.env.example`, `.gitignore`, `.editorconfig` â€” 0 bytes, to be filled when the
build/deps and confirmed source keys arrive. `.env.example` waits on which source
keys 026 will hold; `.gitignore` should be seeded before any `git init`.

### Next session should start at

Await the operator's remaining source URLs (â†’ `sources/links.md` inbox). Open
items: confirm A05/A06 agents; seed `.gitignore` + `.env.example` when keys are
decided; write manual section 03 (Architecture) so `ARCHITECTURE.md` can point at a
real section.

---

## Session 2026-09-06 â€” Phase-1 docs hardening (audit â†’ repair â†’ improve)

### Goal

Operator's call: stay in **Phase 1, docs only, no code.** Audit the existing docs for
real defects/drift (evidence-grade â€” grep, don't assume), then repair and improve them
so the source registry follows its own provenance rules. Four approved workstreams:
registry integrity, schema alignment, A05/A06 resolution + missing sources, and new
doc sections (glossary + ADRs + Phase-1 exit criteria).

### Audit findings (grep-verified, the value-add)

- **Source registry lost its own provenance.** `grep -rhoE 'S0[0-9]{2}' sources/`
  showed 8 gap IDs (`S018, S019, S030, S035â€“S039`) with **no master index** to answer
  "where is S030?". The loose "40 sources" count didn't reconcile (39 distinct IDs incl.
  dead `S023`; ~38 rows).
- **Catalog didn't deliver its promised schema.** `ROADMAP.md`'s template requires
  Provenance-field / Landing-folder / Rate-limit / Cost columns; `apis.md`/`datasets.md`
  rows had none (all merged into a prose "Free reality" column). `mcp.md` had a
  provenance column â†’ internal inconsistency.
- **Registry â†” contract mismatch.** Half the `sources/` rows targeted `A05`/`A06`,
  which `AGENTS.md` Â§3 didn't define. Manual `02` said "A01â€¦A08" â€” A08 had no source.
- **Planned sections missing:** Glossary (manual 07), ADRs (`docs/adr/` empty), and no
  Phase-1 "done" definition.
- **Recommended free sources never landed:** CCXT, Frankfurter, Reddit, Fear&Greed
  were noted only in prose.

### Decisions made and why

- **Master index lives in `sources/README.md`** (operator's call in the plan, over a
  separate `INDEX.md`) â€” one discoverable entry point. Gap IDs recorded as
  **reserved/dropped, never reused** (rule #1), so gaps are accounted-for, not silent.
- **Canonical row schema defined once in `sources/README.md`; type-files cite it.**
  `apis.md`/`datasets.md` now carry Rate-limit, Cost, Lands-in, Provenance-field, ToS.
  Unverified values marked `TBV`/`check` â€” **no fabrication**; existing â¬œ/ðŸ”œ status
  semantics preserved (â¬œ still means limits unverified).
- **A05/A06 promoted to `planned` fleet agents** in `AGENTS.md` Â§3 + Â§12 (not
  reassigned â€” half the catalog genuinely feeds them). Formalized in `ADR-0004`.
- **4 new sources landed** with fresh IDs S048 (CCXT), S049 (Frankfurter), S050
  (Reddit), S051 (Fear&Greed) â€” gap IDs deliberately left unallocated for clean history.
- **ADRs formalize existing decisions** (OS-for-a-fleet, gated execution, minimal
  stack, sources-by-type) â€” no new decisions; just findable/durable versions of
  `BUILD_LOG` history.

### Files touched

| File | Tag | Note |
|---|---|---|
| `sources/apis.md` | **BUILD-REWRITE** | New 13-col schema; + S049/S050/S051 |
| `sources/datasets.md` | **BUILD-REWRITE** | Schema-aligned (Access instead of rate limit) |
| `sources/infra.md` | **DOC-EDIT** | Schema + CCXT (S048) |
| `sources/mcp.md`, `sources/models.md` | **DOC-EDIT** | Schema-aligned subset |
| `sources/README.md` | **BUILD-REWRITE** | Master index + canonical schema + count reconcile; A05/A06 caveat removed |
| `AGENTS.md` | **DOC-EDIT** | Â§3 A05/A06 rows (+ dedup of a concurrent-edit collision), Â§12 roadmap |
| `docs/manual/02-structure.md` | **DOC-EDIT** | A08â†’A06 fix (concurrent), Files section populated, adr note |
| `docs/manual/README.md` | **DOC-EDIT** | Section 07 â†’ written + linked |
| `docs/manual/07-glossary.md` | **BUILD-NEW** | The glossary â€” all 026 terms |
| `docs/adr/README.md` + `ADR-0001â€¦0004` | **BUILD-NEW** | ADR index + 4 records |
| `ROADMAP.md` | **DOC-EDIT** | Deliverables ticked + Phase-1 "definition of done"; template â†’ points at canonical schema |
| `PROJECT_STATE.md` | **DOC-OVERWRITE** | New snapshot: counts, new files, A01â€“A06 |

**No source code written.** Docs only, per the operator's constraint.

### Tests run / passed / failed

| Command | Result |
|---|---|
| `grep -rhoE 'S0[0-9]{2}' sources/` â†’ reconcile against master index | see verification below |
| repo-wide markdown link scan | see verification below |
| any code suite | **none** â€” docs only |

### Concurrency note (reconcile explicitly, not silently)

Mid-session, a **concurrent editor** (a parallel session applying the same plan)
touched `AGENTS.md` and `docs/manual/02-structure.md` â€” A05/A06 and the A08â†’A06 fix
landed twice, briefly producing a duplicated/broken fleet table. Caught it, merged to a
single clean version (kept the "Intelligence"-suffixed naming + ADR-0004 reference),
and the operator confirmed **single-writer** for the rest of the session. Recording
here per the "reconcile explicitly" rule.

### Self-critique â€” fragile / assumed / untested

- **Rate-limit/cost values are still mostly unverified.** The schema now has the
  columns, but â¬œ rows carry prior-knowledge numbers, not today's provider docs. `TBV`
  marks the genuinely-unknown; the â¬œ status still means "verify before building."
- **The 8 reserved IDs are assumed droppable.** Their original candidates aren't in the
  repo, so "reserved/dropped" is the honest label â€” but if the operator recalls a real
  source for one, that history is lost to us. Flagged as an open question.
- **New-source rows (S048â€“S051) are â¬œ unverified** â€” landed as governed rows, not yet
  web-checked. Same rule as any â¬œ.
- **A05/A06 scope is thin.** They're rostered as `planned` with one-line domains; their
  detectors, coverage, and per-agent specs don't exist (manual Â§06 still planned).

### Open questions for the operator

1. The 8 reserved IDs â€” any real source you meant for them, or leave reserved?
2. Next: keep verifying â¬œ source rows, or start the deferred docs-only **Tier-1 design
   specs** (schemas / correlation / validation / coverage / execution-gate)?
3. Seed `.env.example` key-*names* now, or defer to connector time?

### Next session should start at

Phase 1 is near its "definition of done" (`ROADMAP.md`). Docs-only remaining: verify
top free rows â¬œ â†’ ðŸ”œ, list the buildable-now set, decide `.env.example`. Or, on the
operator's word, begin the **Tier-1 design specs** (still docs, no code). Do not start
connector/kernel code until the operator green-lights it.

---

## Session 2026-09-06 — CIE-OS migration + SP-1 fleet conformance

### Goal for this session

Bring the CIE-OS project's full code/data into 026 without losing the source, then
begin adapting it into 026's architecture. Operator directive: copy everything,
keep `F:\CIE-OS` intact, verify code, fix errors, and ask before anything risky.

### Audit findings (delta from last session)

- `F:\CIE-OS` is a separate git project (~1 GB / ~11k files) whose *real* content is
  two agents: `A001_Blockchain_Intelligence` (large, ~700 MB of it SQLite `.db` data)
  and `A002_News_Intelligence`. Its `src/`, `config/`, `docs/`, `scripts/` are empty.
- Both agents already match 026's design closely: A001/A002 IDs + domains match
  `AGENTS.md` §3; both are self-contained vertical pipelines (§1); both already obey
  the §0 laws (evidence ceiling, maturity gate, coverage-before-absence, split
  provenance, downward-only imports).
- **Gated-execution law verified by evidence, not trust:** A001 declares
  `NO_TRADE_EXECUTION = True` once in `config/constants.py` (not env-readable) and
  `tests/test_security.py` bans every signing primitive + asserts no write/REST path.
  A002 has no wallet/order path (news → prediction only).

### Decisions (with reasons)

Operator chose (asked via structured questions):
1. **Copy-as-is first, adapt later** — staged, lowest risk.
2. **Copy all data incl. the big `.db` files** — "jitna bhi data hai".
3. **Copy secrets but git-ignore them** — practical + safe.
4. **Merge same-named docs** — nothing lost.
5. Adapt phase starts with **SP-1 (fleet conformance) + SP-2 (laws audit)**, kernel
   (SP-3/SP-4) and deep-verify (SP-5) deferred.
6. Fleet status label = **substantial** (code + tests present; runtime-verify pending).

### Files touched (tagged)

- `agents/A001_Blockchain_Intelligence/**`, `agents/A002_News_Intelligence/**` —
  `data correction` (migrated as-is from CIE-OS; junk `.venv/.git/__pycache__/*.pyc/
  caches` excluded; 1221 + 59 real files, verified lossless).
- `integrations/CIE-OS/**` — `BUILD-NEW` (lossless mirror of CIE-OS's non-agent
  supporting files for provenance; CIE-OS `.claude` kept as reference, NOT activated).
- `agents/A001_.../agent.yaml`, `agents/A002_.../agent.yaml` — `BUILD-NEW` (026 §2 manifests).
- `config/agents/registry.yaml` — `BUILD-NEW` (fleet registry; was 0 bytes).
- `AGENTS.md` — `MINOR-FIX` (§3 A001/A002 planned→substantial + migration note; also
  CIE-OS's AGENTS.md merged below a marker).
- `docs/manual/02-structure.md` — `MINOR-FIX` (`agents/` section: empty→A001/A002 landed).
- `PROJECT_STATE.md` — `MINOR-FIX` (honest-status updated: kernel still empty, two
  agents migrated in; CIE-OS's PROJECT_STATE merged below a marker).
- `requirements.txt`, `.gitignore` — `MINOR-FIX` (merged CIE-OS deps; secrets +
  Python junk added to `.gitignore`).

### Tests / verification run

- Copy integrity: source real-files == dest real-files for both agents (junk excluded).
- **Syntax compile:** `py_compile` over all 841 `.py` files → **841 OK, 0 failures**
  (Python 3.14.7). This is syntax only; imports/tests not yet run (SP-5).

### Self-critique — fragile / assumed / untested

- **Untested:** nothing has been *run*. 841-file syntax pass ≠ working. A001 targets
  `python >= 3.11`; system is 3.14 — heavy optional deps (chromadb/grpcio/asyncpg)
  may lack 3.14 wheels. Deferred to SP-5.
- **Assumed:** manifest `memory` namespaces + `tools` are the *target* 026 contract;
  the agents are NOT wired to a shared brain/bus/tool-registry (those don't exist).
  `status: substantial` reflects source, not runtime.
- **Assumed:** A001 detector list in the manifest = the four wired to
  `evaluation/labelled.py`; the fuller catalog (`docs/intelligence/detection-catalog.md`)
  has more whose per-detector build state was not individually re-verified.
- **Fragile:** `__pycache__/*.pyc` generated by the syntax check now sit in the
  agent trees (git-ignored). Harmless; can be swept.

### Open questions for the operator

- Big `.db` files (~700 MB) are copied and kept on disk but git-ignored — confirm
  that's the intended long-term home (vs `data/` conventions in §2 structure).
- SP-3/SP-4 (build the kernel + wire the agents to it) is the large next effort and
  changes interfaces the agents depend on — needs its own design pass before code.

### Where the next session starts

SP-2 laws audit is done (recorded above). Next: either **SP-5 deep-verify** (venv +
deps + run each agent's tests, fix failures) or **SP-3 kernel design**. Operator to
choose. No kernel/connector code until then.

### Addendum — SP-5 deep-verify (2026-09-07)

Operator chose SP-5. Provisioned `F:\026\.venv` on **Python 3.14.7** (only version on
the machine; agents target `>=3.11`). Installed lean core+dev deps only —
`pydantic 2.13.5` / `pydantic-core 2.46.5` (3.14 wheel exists, no source build) /
`pydantic-settings` / `aiosqlite` / `pytest 9.1.1` / `pytest-asyncio` / `pytest-timeout`.

Results (verified by execution):
- **A001** — `python -m pytest -q` in the agent dir → **1831 passed, 1 skipped, 0 failed**
  in 61s. (README claimed 782; the suite is larger.)
- **A002** — 7 standalone offline suites run as scripts → **212 checks passed, 0 failed**
  (core 38, narrative 33, verification 28, impact 34, learning 35, phase6 31, phase7 13).

**Self-critique:** A002 passed *without* numpy/pandas/sklearn/transformers installed —
its ML paths (sklearn training, HF transformer detector, pandas correlation) took the
documented rule fallback and were **not exercised**. Installing those (esp. torch via
transformers) is a separate, heavier step with 3.14-wheel risk; deferred. A001's
detectors remain unvalidated (no measured error rate; archive key needed) — verification
here proves the code runs and its tests pass, not that any detector may alert.

Records updated: `config/agents/registry.yaml` (`runtime_verified: true`),
`PROJECT_STATE.md` (honest status). Next open work: SP-3 kernel design → SP-4 wiring.

---

## Session 2026-09-07 — SP-3 slice 1: the sentinel (conformance enforcer)

### Goal for this session

Build the first kernel slice the operator chose: a static, read-only **sentinel**
that reads the fleet and proves each agent's real code matches its declared manifest
(trust, execution-gate, secrets, registry agreement, deviation-only). Spec:
`docs/architecture/sentinel-conformance-design.md`; plan:
`docs/superpowers/plans/2026-09-07-sentinel-conformance.md`.

### Audit findings (delta)

- 026's `security/` was an empty scaffold; no platform code existed there.
- A001 already enforces its own read-only boundary in `tests/test_security.py`; the
  sentinel generalizes that idea to the whole fleet as declared policy.

### Files touched (tagged) — all `BUILD-NEW` unless noted

- `security/__init__.py`, `security/sentinel/__init__.py`, `security/sentinel/tests/__init__.py`
- `security/policies/sentinel.yaml` — policy-as-data (banned primitives, secret patterns,
  advice terms, trust rule, registry paths).
- `security/sentinel/policy.py`, `report.py`, `scan.py`, `fleet.py`, `sentinel.py`, `__main__.py`
- `security/sentinel/checks/`: `base.py`, `manifest.py` (C1), `trust.py` (C2),
  `execution.py` (C3), `secrets.py` (C4), `registry.py` (C5), `deviation.py` (C6)
- `security/sentinel/tests/`: `test_policy.py`, `test_report.py`, `test_scan.py`,
  `test_fleet.py`, `test_checks_manifest_trust.py`, `test_checks_exec_secrets.py`,
  `test_checks_registry_deviation.py`, `test_sentinel_integration.py`
- `requirements/base.txt` — `MINOR-FIX`, added `PyYAML` (sentinel + agents parse YAML).
- `scripts/sentinel.bat` — Windows one-click entry.
- `PROJECT_STATE.md`, `docs/manual/02-structure.md` — `MINOR-FIX` (record the sentinel).

### Tests run (verify by execution)

- `python -m pytest security/sentinel/tests -q` → **28 passed** (Python 3.14.7 venv).
- `python -m security.sentinel scan` → fleet verdict **HOLD** (exit 1): **A002 PASS**;
  **A001 HOLD** on one best-effort deviation flag (`decision/recommendations.py:10:
  'should buy'`), reviewed as **benign** — the docstring says the module emits
  "nothing about what anyone should buy or sell" (it declines advice). No `FAIL`.

### Decisions & a real fix surfaced by running against real code

- Operator decisions (2026-09-07): C6 = flag **and** best-effort check; `HOLD` = exit 1
  (warning); include C5 registry↔§3 cross-check.
- **Secrets false-positive fixed:** the initial `0x[0-9a-fA-F]{64}` private-key pattern
  flagged A001's public **event-topic hashes** (`contracts/signatures.py` TRANSFER_TOPIC
  etc.). Replaced with a **context-gated** pattern (only a 0x/hex value assigned to a
  `private_key`/`mnemonic`/`secret_key`-named var). Locked with two regression tests
  (hash → PASS, `PRIVATE_KEY = "0x…"` → FAIL). Also refined C6 advice terms to
  advice-*shaped* phrases and excluded `tests/`/`fixtures/` — cut A001 deviation noise
  from 10 hits to 1.

### Self-critique — fragile / assumed / untested

- **C6 is best-effort** and text-based: it still flags an advice-shaped phrase inside a
  docstring (the one remaining A001 HOLD). Properly distinguishing an *emitted* string
  from a docstring needs AST work — a slice-2 improvement, named not hidden.
- **Deferred (out of slice-1 scope):** the runtime gate interface (`sentinel.check`),
  the money execution-gate state machine, and architecture-law (downward-only import)
  checks. These are named in the spec §2 as future slices.
- The sentinel scans source as text; it does not import agents (downward-only imports
  preserved).

### Open questions for the operator

- Should slice 2 add AST-based C6 (distinguish docstrings from emitted output) so A001
  reaches `PASS`, or is the current best-effort HOLD-for-review acceptable?
- Next kernel piece: SP-3 slice 2 (runtime gate seam) or the message bus (SP-4)?

### Where the next session starts

Sentinel slice 1 is built, tested (28 passed), and runs over the real fleet. Next:
operator picks slice 2 (runtime gate / bus). No bus/connector code until then.

---

## Session 2026-09-07 (cont.) — C6 AST upgrade + runtime gate + message bus

Operator: "1,2,3 complete karo" — do all three of the offered next steps. Done in
order smallest→largest, each test-first.

### 3 · C6 deviation AST upgrade  (`BUILD-NEW` scan helper, `MINOR-FIX` deviation)

- Added `security/sentinel/scan.py::python_string_literals` — AST-based; yields only
  **non-docstring** string literals (a docstring that declines advice must not itself
  read as advice). `deviation.py` now scans those, with a raw-text fallback on parse error.
- Result: A001's remaining benign HOLD (`recommendations.py` docstring "should buy") is
  gone. **Fleet verdict is now PASS** (`python -m security.sentinel scan` → A001 PASS,
  A002 PASS, exit 0). Genuine emitted advice is still caught (tests prove it).

### 2 · Runtime gate seam — `security/sentinel/gate.py`  (`BUILD-NEW`)

- `check_action(action, agent_manifest) -> GateResult(Decision.{ALLOW,HOLD,DENY})`.
  Deny-by-default: execution/trade/transfer/sign kinds → **DENY** (ADR-0002: no order
  without a gate that does not exist); `requires_approval` tool → **HOLD**; trust above
  the agent's level → DENY; tool outside declared surface → DENY; else ALLOW.
- The seam the bus calls; nothing else calls it yet. 5 tests.

### 1 · Message bus — `orchestrator/event_bus/`  (`BUILD-NEW`)

- `message.py` (Message + Budget + Response, wire dict with `from`), `trace.py`
  (append-only, replayable TraceLog), `bus.py` (MessageBus: register handler + send).
- `send` order: trace → no-handler refuse → **sentinel gate** on any declared action
  (DENY/HOLD short-circuit) → budget (exhausted → degrade, not go dark) → route to
  handler → Response. Handler crash is caught, never takes the bus down.
- Slice-1 proves the path with a stub/echo handler; wiring A001/A002's real pipelines
  (their runtime/DBs) is the next SP-4 slice. 6 tests.
- Platform-internal dependency: `orchestrator` imports `security.sentinel.gate` (a
  platform service). Agents import neither — downward-only imports still hold.

### Tests run

`python -m pytest security/sentinel/tests orchestrator/event_bus/tests -q` →
**42 passed** (Python 3.14.7). Fleet scan → PASS.

### Self-critique

- Bus handlers are stubs; no real agent is wired yet (SP-4 next slice). The gate is
  consulted only when a message carries an `action` — task messages without a declared
  action are not gated (by design; they carry no boundary-crossing act).
- Architecture-law enforcement (downward-only imports as a *test*) still deferred; the
  orchestrator→security dependency is asserted safe by reasoning, not yet by a test.

### Where next

Real-agent bus adapters (thin wrappers over A001's IntelligenceService / A002's cli), then
cross-agent correlation (§4). Or the brain (namespaced memory). Operator to choose.

---

## Session 2026-09-07 (cont.) — real agent↔bus adapters (`bootstrap/`)

Operator chose "Real agent↔bus adapters". The bus now routes to the agents' **actual**
read-only code, not stubs.

### Files (`BUILD-NEW`)

- `bootstrap/__init__.py`, `bootstrap/adapters.py`, `bootstrap/wire.py`,
  `bootstrap/tests/test_adapters.py`
- `bootstrap/` is the **composition root** — the only layer allowed to import both the
  kernel and the fleet (ADR-0001: the kernel itself still imports no agent). `wire.build_bus()`
  loads manifests via the sentinel fleet loader, creates a `MessageBus`, and registers the
  adapters.
- Adapters are **duck-typed** over the bus `Message` (read `.payload` only) so the agents
  never import the kernel. Both are strictly **read-only**:
  - `a001_handler`: puts A001's dir on `sys.path` just-in-time (A001 uses bare imports), then
    `IntelligenceService().detectors()/.skills()/.chains()` — catalogue ops that work with
    no DB, no network, no keys.
  - `a002_handler`: `agents.A002_News_Intelligence.config` — `SOURCES` / `sources_by_kind` /
    `get_settings()` (static registry + settings; no network).

### Tests run (verify by execution)

- `python -m pytest security/sentinel/tests orchestrator/event_bus/tests bootstrap/tests -q`
  → **46 passed** (Python 3.14.7). Fleet scan → PASS.
- The bootstrap tests prove a real query round-trips through the bus (A001 detectors
  catalogue; A002 sources/settings) AND that the gate still **denies** a trade action to
  the real A001.

### Self-critique — fragile / assumed

- **Import-hygiene wart (named, not hidden):** A001 uses bare top-level imports, so its
  adapter prepends A001's dir to `sys.path`. It works because `security`/`orchestrator`
  are imported (from the repo root) before that insertion and cached, so A001's own
  `security/`, `config/` etc. do not shadow the platform's. This is fragile under a
  different import order; the durable fix is to package A001 (a `pyproject`/namespace so it
  imports as `agents.A001_....*` like A002). Deferred.
- Adapters expose only read-only catalogue/registry ops. Real investigative queries
  (which need A001's DB / A002's live sources) are a later slice.
- Cross-agent correlation (§4) — the actual payoff — is still ahead; the plumbing (bus +
  gate + real handlers) is now in place for it.

### Where next

Cross-agent correlation over the bus (fuse an A001 finding with an A002 finding under §4
rules), or the shared brain (namespaced memory) that correlation reads/writes.

---

## Session 2026-09-07 (cont.) — architecture-law test + the brain

Operator chose "the brain and architecture law test". Done smaller-first.

### Architecture-law test — `tests/test_architecture.py`  (`BUILD-NEW`)

- Mechanically enforces downward-only imports (AGENTS.md §0/§10, ADR-0001) over *absolute*
  imports: `security` must not import up (orchestrator/bootstrap) or into the fleet;
  `orchestrator` must not import `agents`/`bootstrap` (importing lower `security` is fine);
  agents must not import `orchestrator`/`bootstrap`/`brain`; `brain` must not import up or
  into the fleet.
- Handles the migrated-agent name collision honestly: agent checks forbid only names no
  agent defines internally (`orchestrator`, `bootstrap`, `brain`) — so a hit is a genuine
  violation, not A001's own bare `import security`/`config`. 4 tests, all pass.

### The brain — `brain/`  (`BUILD-NEW`)

- `brain/store.py::Brain` — namespaced memory on stdlib sqlite3 (no new dep). Writes are
  **versioned** (append, never overwrite); reads are **logged**; nothing silent (§7).
  Namespaces validated: bare tokens (`global`, `entities`, `chain`, `news`) or scoped
  `projects/<id>` / `private/<agent>`.
- `brain/access.py::AgentBrainView` — scopes read/write to the agent's manifest
  `memory.reads`/`memory.writes`, with `projects.*` wildcard matching. A001 may write
  `chain`, A002 may write `news`, both cite shared `entities` (the correlation fuel); an
  undeclared namespace raises `NamespaceDenied`.
- 5 tests: versioning, read-logging, namespace validation, write-scope, and the
  cross-agent `entities` read (A001 writes, A002 reads) with A002 denied A001's `chain`.

### Tests run

`python -m pytest security/sentinel/tests orchestrator/event_bus/tests bootstrap/tests
brain/tests tests/test_architecture.py -q` → **55 passed** (Python 3.14.7). Fleet scan → PASS.

### Self-critique

- Brain is sync sqlite3, single-process, in-file; fine for slice-1. No embeddings / RAG /
  knowledge-graph yet (brain/ subdirs still empty) — those are later.
- Nothing wires the brain into the bus/agents yet: `AgentBrainView` is ready, but the
  adapters do not read/write the brain during a task. That join is what cross-agent
  correlation (§4) will use next.

### Where next

Cross-agent correlation (§4): an orchestrator flow that has A001 and A002 write findings to
the brain (own namespace + shared `entities`), then fuses them — weakest-confidence, split
provenance, conflicts recorded. Or deeper real adapters. Operator to choose.

---

## Session 2026-09-07 (cont.) — deeper real adapters (DB-backed reads)

Operator chose "Deeper real adapters". Expanded `bootstrap/adapters.py` beyond
catalogue/registry to **real DB-backed read queries** over the migrated databases.

### Changes (`MINOR-FIX` adapters, `BUILD-NEW` tests)

- A001 adapter ops now: catalogue (`detectors/skills/chains`, no DB) **+ DB reads**
  `metrics`, `coverage(chain)`, `flows(chain)`, `labels(chain)`, `health` — served by
  `IntelligenceService(database_path=agents/A001_.../data/a001.db)`, which is read-only by
  construction (no ingestion/write path on the facade).
- A002 adapter op `stats` — `Storage(a002.db)` → `count_items()` + `count_entities()`
  (async, run via `asyncio.run`; `init()` is idempotent schema-ensure, no data mutation,
  exactly as A002's own doctor does).

### Verify by execution (real data — this is the proof migration + kernel work together)

`python -m pytest ... -q` → **58 passed**. Live demo through the bus:
- A001 `metrics` → real gauges from a001.db (`storage_available`, detector states, uptime).
- A001 `coverage ethereum` → real window: heights 25723714→25723795, 82 blocks (45 complete,
  37 incomplete, 5 selective).
- A002 `stats` → **447 items, 107 entities** (real migrated news data in a002.db).
- A001 `trade` action → **denied** by the gate ("no execution gate exists") — on the real agent.

### Self-critique

- Reads only. No investigative op that would need live RPC (A001) or a live price fetch
  (A002) is exposed — those cross into network and are deliberately out.
- The import-hygiene wart (A001 dir on `sys.path`) is unchanged; still the durable fix is
  packaging A001.
- Agents still don't read/write the **brain** during a task; that join + cross-agent
  correlation (§4) remain the next real milestone.

### Where next

Cross-agent correlation (§4), or the brain↔task join. Operator to choose.

---

## Session 2026-09-07 (cont.) — +67 blockchain data sources for A001 (registry + A001 config)

Operator dropped `F:\blockchain-data-sources-notes.md` (85 blockchain sources) and chose
"Dono (central + A001)". Catalogued into the registry with stable IDs and added a safe
A001 machine-config — **A001's tested `config/rpc/` Python untouched**.

### Files touched (tagged)

- `sources/apis.md` — `BUILD-NEW` rows: **56** APIs (S052–S066, S075–S114, S116).
- `sources/infra.md` — `BUILD-NEW` rows: **9** RPC/node providers (S067–S074, S115) +
  a documented "not catalogued" note (embedded-wallet & tax tooling — not data feeds).
- `sources/links.md` — `BUILD-NEW` rows: **2** trusted awesome-list discovery portals
  (S117 igorbarinov/awesome-bitcoin, S118 best-of-crypto).
- `sources/README.md` — `MINOR-FIX` master index (67 new rows), counts
  (42→**109** catalogued, highest ID **S118**), ledger note (fresh IDs from S119).
- `config/sources/a001.yaml` — `BUILD-NEW` A001 machine-config: sources grouped by role,
  each referencing its stable ID + key-NAME env var (never a secret), free-first priority
  tiers. Does not replace/modify `agents/A001_.../config/rpc/`.

### Dedup & scope decisions

- ~9 already catalogued, mapped to existing IDs (Etherscan S010, Blockchain.com S009,
  CoinGecko S004, CoinMarketCap S007, Binance S002, Glassnode S013, CryptoQuant S014,
  Dune S017, Kaiko S012). Etherscan-family (BscScan/PolygonScan/…) noted as one Etherscan
  V2 key. Pump.fun/Coinpath fronted via BitQuery (S090). Etherscan Gas Tracker = S010 sub.
- **Deliberately not catalogued:** embedded-wallet/AA infra (Privy/Dynamic/Pimlico/
  Coinbase WaaS) and crypto-tax tooling (CoinLedger/TaxBit) — not intelligence data feeds,
  and (wallets) outside A001's read-only, no-keys trust surface.

### Verify by execution

`python scratchpad/verify_sources.py` → a001.yaml parses; master index **118 rows, 0
duplicates**, highest S118; a001.yaml's 70 referenced IDs all exist; apis(82)/infra(12)/
links(6) rows all present in the master index (files ↔ index in sync).

### Self-critique — honesty

- All 67 new rows are `⬜` (known, limits unverified) with `TBV` rate limits — **not**
  web-verified this session. A real check (auth/rate/cost/ToS per source) moves them to
  `🔜`/`✅` and gets recorded here. Nothing is marked verified that was not.
- `config/sources/a001.yaml` key-env names are best-effort; uncertain ones are `TBV`. No
  real keys anywhere (they belong in `.env`).
- Registry ≠ connectors: cataloguing a source does not fetch from it. Connectors land in
  `integrations/` later (Phase 2), and only then does a source reach `✅ live`.

### Where next

Per-source verification pass (move ⬜→🔜), or connectors for the Tier-1 keyless free
sources (DeFiLlama, Blockscout, Mempool.space, DexScreener, GeckoTerminal, PublicNode).
Or back to the kernel: cross-agent correlation (§4). Operator to choose.

---

## Session 2026-09-07 (cont.) — A001 bug-hunt (systematic-debugging)

Operator asked to find/fix bugs in A001 and confirm it works. Followed
systematic-debugging: gather evidence first, root-cause before any fix.

### Evidence gathered (Phase 1)

- `python -m cli doctor` → **14/14 OK** (chain registry, sensors 13/13, storage schema v8,
  decision gate 5 detectors/4 may-alert, credentials 1 keyed provider from `.env.local`,
  trade execution disabled/read-only, smoke investigation 0 failures).
- `python -m pytest -q` → **1831 passed, 1 skipped**.
- `ruff check` (installed ruff 0.16.6; mypy skipped — no 3.14 wheel, was source-building)
  → 494 F/B findings, but triaged: 410 F401 unused-import + B905/B007/F541/B904 = lint-debt
  (not functional bugs). Sharp bug-class: 1 F821, 1 B023, 3 F811, 1 F402, 3 B018, 21 F841.

### Root-cause of the "scary" findings (investigated, not guessed)

- **F821 `ssl` undefined (`tools/adapters/rest.py:134`)** — NOT a bug. It's a *string*
  return annotation with `ssl` deliberately lazy-imported inside the method (documented:
  read-only paths must not die if the `_ssl` DLL is unavailable). No runtime NameError.
- **B023 loop-closure (`tools/web/parser.py:126`)** — NOT a bug. The lambda is handed to
  `re.sub`, invoked synchronously in the same iteration, so `level` is correct.
- **F811 `Verdict` (`pipeline/__init__.py`)** — a latent hazard (not a crash). budget.py and
  materiality.py both define `Verdict`; the package imported both, the second (materiality)
  shadowed the first. Tests expect `pipeline.Verdict` = materiality's, and get it — so
  behavior is correct, but a future import re-order could silently flip it.

### Fix (Phase 4) — one targeted change

- `pipeline/__init__.py` — `MINOR-FIX`: removed the dead/shadowed `Verdict` from the
  `from .budget import …` line (+ a note). `pipeline.Verdict` is now unambiguously
  materiality's; budget's stays reachable as `pipeline.budget.Verdict`.
- **Verified:** ruff F811 on the file → clean; `pipeline.Verdict is materiality.Verdict`
  == True and `budget.Verdict` distinct; **full suite still 1831 passed, 1 skipped** (no
  regression).

### Verdict

**A001 works.** No functional/crash bugs found — the alarming ruff hits were an intentional
pattern, a false positive, and a latent (now-closed) hazard. What remains is **lint-debt**
(410 unused imports incl. likely intentional `__init__` re-exports, plus F841/B905/B004/…)
— harmless to runtime; a mass `--fix` is deliberately NOT applied (risky on `__init__`
re-exports; needs review). Offered to the operator as optional cleanup.

---

## Session 2026-09-08 — SP-1 price wiring (whale USD), TDD

Roadmap SP-1 (of the 12-SP A001→trading decomposition). Brainstormed → bounded →
TDD build. **Key find:** the DeFiLlama price *connector* already existed
(`sensors/market/price_sensor.py`, keyless, 33 tests) but was **unwired** — no consumer
used it. So SP-1 = wire it, not build it.

### Changes (TDD, red→green each)

- `sensors/market/price_sensor.py` — `BUILD-NEW` methods `historical_native_price(chain, at)`
  + `historical_token_price(chain, contract, at)` (DeFiLlama `/prices/historical/{ts}`),
  per-timestamp cache, positive-timestamp guard. Tests: `sensors/tests/test_price_historical.py`
  (5).
- `skills/whale_detection/transfers.py` — `MINOR-FIX`: `WhaleTransferSkill.__init__(price=None)`
  + `_native_usd(chain, value_raw)` (native decimals map: BTC 8, SOL 9, EVM 18); `_entry`
  made an instance method that now emits real `usd_value` + `usd_basis` when a price
  provider is wired, honest `0.0`/`"unpriced"` when not. Tests: `skills/tests/test_whale_usd.py` (4).
- `skills/registry.py` — `MINOR-FIX`: whale entry now `WhaleTransferSkill(price=PriceFeedSensor())`;
  `bounded_by` updated (native USD priced; token USD pending decimals; labels thin).

### Verify by execution

- `python -m pytest -q` → **1840 passed, 1 skipped** (was 1831; +9). No regression.
- `cli skills` → whale line no longer says "no price feed"; now "native transfers priced
  in USD (DeFiLlama)".
- **Live smoke** (real DeFiLlama, keyless): ETH current **$2496.89**, historical 24h-ago
  **$2505.78** — current + historical both real, end-to-end.

### Honest boundary (unchanged from design)

- **Native USD is live**; **token USD** is plumbed but stays undetermined until token
  decimals arrive (SP-4) — no fabrication.
- Whale skill uses **current** price for `usd_value` (transfers carry `height`, not a
  timestamp, in this skill); the **historical** method is ready for timestamp-aware
  consumers (backtest/pipeline). smart_money P&L wiring is SP-1's remaining half (next).
- `MaterialityGate` keep/drop logic untouched (protects the core path); a USD-floor in the
  gate is a later small step.

### Where next

SP-1 part 2: wire price into `smart_money` for a real (native) P&L signal. Then SP-2
(balances) / SP-3 (labels) / SP-4 (decimals+decoding) per the roadmap.

### SP-1 part 2 — smart_money price wiring (2026-09-08, TDD) — SP-1 COMPLETE

- `skills/smart_money/tracker.py` — `MINOR-FIX`: `__init__(price=None)` + `_native_flow_usd(chain, transfers, address)` (values an address's native in/out flows in USD; honest: flow value, NOT realized P&L — needs cost-basis + token prices). Added `native_flow_usd` to the profile; `_bounds` is now price-aware. Tests: `skills/tests/test_smart_money_pnl.py` (3).
- `skills/registry.py` — smart_money now `SmartMoneySkill(price=PriceFeedSensor())`; bounded_by updated.
- `intelligence/engines/tests/test_composition.py` — `MINOR-FIX`: the "price feed" limitation assertion updated to the token-side limitation ("token USD" / "token prices"), since native USD is now priced (limitations are collected from registry `bounded_by`, per `composition.py:188`).
- Verify: **1843 passed, 1 skipped** (+3); `cli skills` — both whale and smart_money bounds now say "native ... priced in USD (DeFiLlama)"; sentinel scan → A001 PASS (conformance intact). SP-1 (price wiring) done. Next: SP-2 balances.

---

## Session 2026-09-13 — SP-2 balances (wallet_profile), TDD

Same shape as SP-1: the balance *sensor* already existed
(`sensors/evm/rpc_sensor.py` `balance()`/`token_balance()`, tested) — wallet_profile
just did not use it. So SP-2 = wire it.

### Changes (TDD)

- `skills/wallet_lookup/profile.py` — `MINOR-FIX`: `WalletProfileSkill.__init__(balances=None, **kwargs)`
  + `_balance_wei(chain, address)`; `run()` now emits `native_balance_wei` (live current
  balance when a provider is wired) + `balance_basis`. Honest: None/"unavailable" without a
  provider — a partial-window sum is not a balance. Tests: `skills/tests/test_wallet_balance.py` (3).
- `skills/wallet_lookup/balances.py` — `BUILD-NEW`: `SensorBalances` adapts `SensorRegistry`
  to `native_balance(chain, address)`; unsupported (non-EVM) chain → None (degrade, not raise).
- `skills/registry.py` — wallet_profile now `WalletProfileSkill(balances=SensorBalances())`;
  bounded_by updated.
- `intelligence/engines/tests/test_composition.py` — `MINOR-FIX`: "balance sensor" limitation
  assertion → token/historical (native balance is now live).

### Regression fixed mid-build (systematic-debugging)

My first `__init__(self, balances=None)` dropped the base Skill's `absence_threshold` kwarg
→ 12 window/floor tests failed with `unexpected keyword 'absence_threshold'`. Root cause:
base `Skill.__init__` takes config kwargs. Fix: forward `**kwargs` to `super().__init__` in
all three wired skills (wallet_profile, whale, smart_money). Backward-compatible again.

### Verify by execution

- `python -m pytest -q` → **1846 passed, 1 skipped** (+3). No regression.
- `cli skills` → wallet_profile no longer "no balance sensor"; now "native balance read live
  (RPC eth_getBalance)".
- **Live smoke:** `SensorBalances().native_balance("ethereum", <vitalik>)` → **6.71 ETH** (real,
  via configured RPC provider). sentinel scan → A001 PASS.

### Honest boundary

Native **current** balance is live. **Token balances** (balanceOf over an address's
touched tokens) and **historical** (block-time / archive) balance are follow-ups. Non-EVM
chains have no balance sensor yet → None.

### Where next

SP-3 (labels) or SP-4 (token decimals — unblocks token USD + token balances). Then SP-5
(skills full) etc.

---

<!-- ============================================================ -->
<!-- MERGED FROM CIE-OS: F:\CIE-OS\BUILD_LOG.md on 2026-09-06 -->
<!-- 026's original content is ABOVE. CIE-OS original also preserved at integrations\CIE-OS\ -->
<!-- ============================================================ -->

# BUILD_LOG.md â€” CIE-OS A001 Blockchain Intelligence Agent

> Append-only history. Never overwritten. Current snapshot lives in
> `PROJECT_STATE.md`.

---

## Session 2026-08-11

### Goal for this session

1. Establish the Section 4 continuity system, which did not exist.
2. Run the mandatory Section 3 codebase audit and produce a Reuse Map backed by
   executed commands rather than assumption.
3. Migrate `F:\Agents\.env.local` into the CIE-OS tree.

### Audit findings (delta from last session)

No previous session recorded â€” `PROJECT_STATE.md` and `BUILD_LOG.md` were both
absent. This is session zero **for the continuity system only**; the codebase
itself is substantial and largely working (692 Python files, ~128,614 LOC).

Findings established by execution:

- `python -m pytest -q` at the agent root: **831 passed, 0 failed**, 45.28s.
  Two `ResourceWarning`s from `aiosqlite` in `memory/storage/tests/test_storage.py`
  (connections deleted before close). Not failures; not fixed this session.
- `python -m cli doctor`: 13/13 checks `ok`, exit 0.
- `python -m cli metrics`: ethereum has 45 blocks and 14,457 transactions
  stored, 0 withdrawn by reorg.
- `python -m cli providers`: 21 endpoints configured, 8 usable, 13 dormant.
  **0 keyed providers active.**

Priority Stack position: **Tier 0 is `DONE` for ethereum** (verified, not
assumed). **Tier 1 is `PARTIAL`** â€” the code exists and its unit tests pass,
but it has never run against a data window wide enough to emit anything.
`a001_coverage_supports_absence{chain="ethereum"} 0` and
`a001_detectors_alerting 0` are the system correctly declining to speak, not a
defect.

Two Section 6 invariant problems found and **not** silently absorbed:

1. **`no_trade_execution=True` does not exist in the codebase.**
   `grep -rni "trade" --include=*.py` returns only incidental matches â€” a
   durability comment in `database/connection.py:64`, prose in
   `intelligence/analysis/`, a BIP-39 wordlist in `tools/blockchain/wallet.py`,
   and an intent-router keyword list. The actual behaviour is correct (the CLI
   help states A001 holds no keys, signs nothing, and never submits a
   transaction; there is no signing or exchange-write path), but the hardcoded
   flag the invariant names is unimplemented. The guarantee is implicit rather
   than enforced. Recorded as VIOLATED-AS-SPECIFIED.
2. **Import direction is `UNVERIFIED`.** No mechanical enforcement of the
   downward-only rule was found. Not claimed as holding.

One Section 14 concern: `except Exception: pass` at
`memory/base/conversation.py:1523` and `:1538`. Off the A001 data path, but
unclassified suppression. Not fixed this session.

### Files touched

| File | Tag | Note |
|---|---|---|
| `agents/A001_Blockchain_Intelligence/.env.local` | **BUILD-NEW** | Migration target. Did not exist |
| `PROJECT_STATE.md` | **BUILD-NEW** | Section 4 continuity |
| `BUILD_LOG.md` | **BUILD-NEW** | Section 4 continuity |

**No source code was modified.** 831 tests passed before the session's changes
and nothing on a code path was altered, so the suite's meaning is unchanged.

### The `.env.local` migration

Source `F:\Agents\.env.local` (445 bytes) contained:

- `A001_PYTHON=F:\CIE-OS (crypto intelligence engine-opreting system\.venv\Scripts\python.exe`
- three commented, empty provider keys (`ALCHEMY_API_KEY`, `ETHERSCAN_API_KEY`,
  `INFURA_API_KEY`)

**No live credentials were present**, so this migration did not handle any
secret and the Section 18 escalation trigger did not fire.

Three decisions, with reasons:

1. **Target = agent root, not repo root.** `config/dotenv.py` searches
   `.env.local` then `.env` across four directories, nearest first, and returns
   on the **first file found**. The repo root already holds an empty `F:\CIE-OS\.env`,
   which was being found and yielding zero variables â€” the exact silent failure
   `config/dotenv.py`'s own module docstring was written to prevent. Placing the
   file at the agent root shadows it. It also keeps the file agent-scoped, so
   A002 does not inherit A001's configuration (Section 0: no shared state).

2. **`A001_PYTHON` corrected â€” MINOR-FIX.** The migrated path pointed at
   `F:\CIE-OS (crypto intelligence engine-opreting system\...`, which **does not
   exist on this machine** (`ls` confirms). Migrating it verbatim would have
   carried a dead path forward. `a001.bat` checks `if exist` before using it, so
   a dead value falls through to the upward `.venv` search and then to system
   Python â€” which lacks `pydantic-settings` and `aiosqlite`, and makes a working
   agent look broken. Corrected to `F:\CIE-OS\.venv\Scripts\python.exe`,
   verified present.

3. **File written ASCII-only, no BOM â€” deliberate.** It is parsed by two
   fragile readers. `config/dotenv.py:137` skips any name that is not
   alphanumeric-plus-underscore, so a UTF-8 BOM would turn `A001_PYTHON` into
   `\ufeffA001_PYTHON` and **silently drop the first variable**. `scripts/a001.bat`
   reads the same file with `for /f delims==` under the console codepage.
   Verified: first bytes are `# C I E - O S` (no BOM) and
   `grep '[^ -~]'` finds nothing.

The commented key list was expanded from 3 names to the 9 the provider catalog
actually reports, so the file matches what `python -m cli providers` tells the
operator to set. All remain commented and empty â€” no behaviour changed, no
false activation.

### Tests run / passed / failed

| Command | Result |
|---|---|
| `python -m pytest -q --timeout=300` | **error** â€” `unrecognized arguments: --timeout=300`; `pytest-timeout` is not installed. Re-run without it |
| `python -m pytest -q` | **831 passed**, 0 failed, 2 warnings, 45.28s |
| `python -m cli doctor` | 13/13 `ok`, exit 0 |
| `python -m cli metrics --db data/a001.db` | ethereum 45 blocks / 14,457 tx |
| `python -m cli providers` | 21 endpoints, 8 usable, 13 dormant |

Post-migration verification:

| Check | Result |
|---|---|
| `dotenv.parse()` on the new file | `{'A001_PYTHON': 'F:\\CIE-OS\\.venv\\Scripts\\python.exe'}` â€” exactly one variable |
| BOM / non-ASCII scan | Clean |
| `cli doctor` credentials line | `ok â€” 0 keyed provider(s) active; 1 variable(s) from F:\CIE-OS\agents\A001_Blockchain_Intelligence\.env.local` |
| `cli providers` env line | `1 variable(s) from F:\CIE-OS\agents\A001_Blockchain_Intelligence\.env.local` |
| `a001.bat` resolution block, replicated in a scratch `.bat` | `RESOLVED: F:\CIE-OS\.venv\Scripts\python.exe` |

Before the migration both commands reported `0 variable(s) from F:\CIE-OS\.env`.
The batch block was replicated rather than running `scripts/a001.bat` directly,
because that script performs a live 25-block ingest and ends in `pause`.

### Decisions made and why

- **Everything got `REUSE`.** Nothing was replaced. Section 3.2 requires failing
  tests, an invariant violation risking correctness, or a structural block â€” and
  the suite is fully green. The two invariant problems found are *missing
  enforcement*, which is a gap to close, not grounds to replace working code.
- **The nine empty top-level directories were left alone.** They contradict
  Section 8's vertical-slice discipline, but they are inert and removing them is
  a preference, not a justification. Logged below instead.
- **`no_trade_execution` was not added this session.** Section 18 requires
  stopping and asking before touching a trade-execution boundary. Reported to
  the operator rather than implemented unilaterally.

### Proposed improvements (not acted on)

- `PROPOSED-IMPROVEMENT`: add `no_trade_execution=True` as a real constant in
  `config/constants.py`, asserted at agent startup and surfaced by
  `cli doctor`, turning the read-only guarantee from implicit into enforced.
- `PROPOSED-IMPROVEMENT`: add mechanical enforcement of the downward-only
  import rule (e.g. `import-linter`), so that invariant can move from
  `UNVERIFIED` to `HOLDS`.
- `PROPOSED-IMPROVEMENT`: classify or narrow the two `except Exception: pass`
  sites in `memory/base/conversation.py`.
- `PROPOSED-IMPROVEMENT`: close the two `aiosqlite` connections in
  `memory/storage/tests/test_storage.py` with `async with` to clear the
  `ResourceWarning`s.
- `PROPOSED-IMPROVEMENT`: add `pytest-timeout` to the dev requirements so a
  hung test cannot stall a suite run.
- `PROPOSED-IMPROVEMENT`: delete the nine empty top-level directories, or add a
  one-line README to each stating the owning module, so an audit is not
  misled by them.
- `PROPOSED-IMPROVEMENT`: remove the now-redundant empty `F:\CIE-OS\.env`, which
  exists only to be shadowed.

### Self-critique â€” what is fragile, assumed, untested

- **Fragile:** the migrated file's usefulness depends on `F:\CIE-OS\.venv`
  staying put. If the venv moves, `A001_PYTHON` is dead again and the failure is
  a silent fallback to system Python, not an error.
- **Fragile:** `config/dotenv.py` returns on the **first** file found, so
  creating a `.env` in the agent directory later would shadow this `.env.local`
  and quietly drop `A001_PYTHON`.
- **Assumed:** that `memory/`, `planning/` and `tools/` are healthy. Their tests
  pass, but they were not read â€” 74,702 LOC across 330 files was assessed by
  test result and structure only. Their invariant column is `UNVERIFIED` and
  should stay that way until someone reads them.
- **Assumed:** that `Tier 0 = DONE` generalises beyond ethereum. It does not.
  Only ethereum has ingested data; the other eight chains are registry entries
  with readable sensors and nothing more.
- **Untested this session:** ingestion against a live chain, the REST interface,
  the visualize/dashboard path, backup/restore, and every Tier 1 intelligence
  module against real data rather than fixtures.
- **Not verified:** whether `F:\A001_Blockchain_Intelligence\` at the drive root
  is a stale duplicate of the agent. It was noticed and not investigated.

### Open questions for the operator

1. Delete the source `F:\Agents\.env.local` now that its contents are migrated
   and verified? It was left in place â€” the contents are copied and the one real
   value was corrected, so nothing is lost either way.
2. Add `no_trade_execution=True` as a real enforced constant? Section 18 says a
   trade-execution boundary is an escalation, so this is the operator's call.
3. Is `F:\A001_Blockchain_Intelligence\` (drive root) a stale duplicate that
   should be removed, or a deliberate second checkout?
4. Should provider keys be obtained? 13 of 21 endpoints are dormant. Not
   required for correctness, but it bounds throughput and historical depth.

### Next session should start at

**Tier 1, the first real vertical slice.** Widen the ethereum coverage window
(`python -m cli ingest --chain ethereum --blocks N --tokens`) until
`a001_coverage_supports_absence{chain="ethereum"}` reads 1 and at least one
detector is licensed to alert, then trace a single intelligence output from
terminal alert back to raw ingestion with its provenance intact â€” the Section 19
end-to-end scenario, on one chain.

Do **not** start Tier 2 (additional chains) before that passes.

> **Correction, appended 2026-08-11 (session 2):** the clause "and at least one
> detector is licensed to alert" was wrong. Alerting is gated on `VALIDATED`
> maturity, which requires a measured error rate from `evaluation/` against a
> labelled window â€” not on data volume. No amount of ingestion moves it. See
> session 2 below.

---

## Session 2026-08-11 (second session)

### Goal for this session

Operator chose: close the two Section 6 invariant gaps first, then attempt the
Tier 1 vertical slice. Also approved adding the `no_trade_execution` constant
(Section 18 escalation) and deleting the migrated source env file.

### Audit findings (delta from session 1)

**Correction to session 1.** Session 1 recorded the read-only guarantee as
"implicit, not enforced". That was too strong, and reading
`tests/test_security.py` disproved it: `test_no_signing_primitive_exists_in_the_source`,
`test_every_rest_route_is_read_only` and `test_the_service_exposes_no_write_operation`
already enforce it by scanning the source and the public surface. What was
genuinely missing was only the *named constant* Section 6 specifies. Step 1
shrank accordingly.

**Correction to session 1.** Session 1 said alerting was blocked by a narrow
coverage window. Wrong. `decision/maturity.py` gates alerting on `VALIDATED`
maturity via a measured error rate; coverage is a separate gate governing
*negative* claims. The two are independent and were conflated.

**Import direction, previously `UNVERIFIED`, is now measured:** exactly **2**
upward imports across the 11 ranked layers, plus **1** resulting cycle. Far
better than feared for a 128k-LOC codebase.

### ACTIVE BLOCKER discovered â€” log completeness is not recorded

Found while running the Step 3a backfill. A 25-block ingest with `--tokens`
reported `tokens: 0 transfer(s)` â€” impossible on ethereum mainnet, where the
same run stored 8,623 transactions.

Root cause, verified by direct call rather than inference:

```
sensor.logs(from_height=25723761, to_height=25723761)
  -> determined: False, reason: "3 endpoint(s) tried, none answered"
```

The open endpoints refuse `eth_getLogs`. The poller's handling is correct and
deliberate â€” it counts `logs_undetermined` and keeps the block. But the
shortfall never reached the stored row (`complete` is set from the block's own
quality, `database/writer.py:177`), `supports_absence` never consults
completeness (`skills/base.py:85`), and nothing was printed.

This **blocks Step 3**: backfilling 3,600 blocks this way would flip
`supports_absence` to 1 and license negative claims over a window whose
transfers were never fetched. The backfill was therefore **not run** â€” at the
measured 7.6 s/block it would have cost ~7.5 hours to produce a poisoned window.

### Files touched

| File | Tag | Note |
|---|---|---|
| `config/constants.py` | **MINOR-FIX** | Added `NO_TRADE_EXECUTION` + `__all__` entry |
| `cli/main.py` | **MINOR-FIX** | Added `trade execution` doctor check; added `logs` line + shortfall warning to `ingest` |
| `tests/test_security.py` | **MINOR-FIX** | Added `test_trade_execution_is_disabled_and_cannot_be_switched_off` |
| `tests/test_architecture.py` | **BUILD-NEW** | Layer direction + cycle ratchet, 7 tests |
| `F:\Agents\.env.local` | **deleted** | Migration source, approved by operator |
| `PROJECT_STATE.md` | overwritten | |
| `BUILD_LOG.md` | appended | |

### Tests run / passed / failed

| Command | Result |
|---|---|
| `python -m pytest -q tests/test_security.py` | 17 passed |
| `python -m pytest -q tests/test_architecture.py` | **1 failed, 5 passed** â€” the cycle test found `intelligence <-> skills` |
| `python -m pytest -q tests/test_architecture.py` (after ratchet) | 7 passed |
| `python -m pytest -q` (full) | **839 passed, 0 failed**, 42.51s â€” up from 831 |
| `python -m cli doctor` | **14/14 ok**, exit 0; new line `trade execution ok â€” disabled; 6 route(s) read-only` |
| `python -m cli ingest --blocks 3 --tokens` | Now prints `logs: 0 captured, 3 undetermined, 0 dropped` + WARNING |

The architecture cycle test failing on first run is recorded deliberately: it
was written before the violation was known to exist, and it found one.

### Decisions made and why

- **`NO_TRADE_EXECUTION` is not configurable and not read from the
  environment.** A boundary a deployment can switch off is a default, not a
  boundary â€” the same reasoning `decision.maturity` applies to
  `ALERT_MATURITY`. The doctor check pairs the constant with a live surface
  scan, because a flag reporting "ok" beside an exposed write route would be
  exactly the reassuring lie the check exists to prevent.
- **Enforced 2 of the 3 documented layer rules.** `layered-architecture.md` Â§5
  also says "no skipped layers"; that is stricter than the Section 6 invariant,
  the codebase has never met it, and asserting it would produce a test that
  fails on arrival and gets deleted. Only downward-direction and no-cycles are
  asserted. The omission is documented in the test module itself.
- **The 2 upward imports and 1 cycle were allowlisted, not fixed.** Both fixes
  mean relocating a shared name to a lower layer, which changes a package's
  public surface â€” scoped work, not a side effect of adding a test. The
  allowlist is a two-way ratchet: a new violation fails, and so does an entry
  that has been fixed but left behind.
- **The `ingest` visibility fix was made; the deeper completeness fix was
  not.** Printing the shortfall is unambiguously right and touches nothing.
  Making `complete` reflect log completeness, and `supports_absence` require
  it, changes stored-data semantics and the meaning of an existing column â€”
  that needs the operator.
- **The backfill was not run.** Building a 7.5-hour window on a known-poisoned
  path would have been the expensive way to produce a wrong answer.
- **The 28 tainted blocks were left in place.** Deleting stored observations is
  irreversible; the operator decides.

### Proposed improvements (not acted on)

- `PROPOSED-IMPROVEMENT`: record log completeness on the block row â€” either a
  `logs_complete` column or by folding the log shortfall into `complete` â€” and
  make `Coverage.supports_absence` require it. This is the blocker's real fix.
- `PROPOSED-IMPROVEMENT`: have `cli ingest` exit `EXIT_DEGRADED` when logs are
  undetermined, as it already does for rejections. Not done unilaterally: it
  changes an exit-code contract the scheduled task reads.
- `PROPOSED-IMPROVEMENT`: relocate `DEFAULT_PERCENTILE` and `Stance` downward to
  clear the allowlist and break the cycle.
- Carried forward, unchanged: `pytest-timeout` missing; two
  `except Exception: pass` sites in `memory/base/conversation.py`; two
  `aiosqlite` `ResourceWarning`s; nine empty top-level directories; the
  redundant empty `F:\CIE-OS\.env`.

### Self-critique â€” what is fragile, assumed, untested

- **Fragile:** the architecture test ranks only the 11 packages the doc names.
  Twelve others are explicitly `UNRANKED` and therefore unchecked â€” including
  `tools/`, `planning/` and `blockchain/`. Coverage of the invariant is real
  but partial, and the module says so.
- **Fragile:** the cycle check is package-level. A cycle *within* one package
  passes it.
- **Assumed:** that `eth_getLogs` failure is provider-side and not a bug in
  A001's log request. Evidence points at the provider â€” the identical code path
  captured 26,987 transfers on 2026-08-10 â€” but no keyed endpoint was tried, so
  this is `PROBABLE`, not `VERIFIED`.
- **Untested:** whether the 45 older blocks are themselves fully log-complete,
  or merely got more logs than the newer ones. They were not audited per-block
  against an independent source.
- **Untested this session:** the REST interface, `visualize`, backup/restore,
  and every Tier 1 module against real data. Unchanged from session 1.
- **Not verified:** `F:\A001_Blockchain_Intelligence\` at the drive root. Noticed
  in session 1, still not investigated.

### Open questions for the operator

1. **The blocker fix.** Add a `logs_complete` column, or fold the log shortfall
   into the existing `complete` flag? The second is less schema churn but
   overloads a column whose current meaning is "the block record was complete".
2. **The 28 tainted blocks** (25723761â€“25723788) â€” delete and rewind the
   checkpoint to 25723760, or keep and let the completeness fix reclassify them?
3. **Provider keys.** This has stopped being only a throughput question: a keyed
   endpoint that serves `eth_getLogs` is the difference between a usable Tier 1
   window and none. 7.5 hours for 3,600 blocks on open endpoints is also
   impractical on its own.
4. Still open from session 1: is `F:\A001_Blockchain_Intelligence\` a stale
   duplicate?

### Next session should start at

**The blocker, not the slice.** Decide question 1, implement it with a
regression test that a log-incomplete block cannot license a negative claim,
then re-attempt the Tier 1 slice. The slice's success criterion remains
`supports_absence 1` plus one traced end-to-end output â€” **not** an alert, which
is gated on evidence that does not exist yet.

---

## Session 2026-08-11 (third session)

### Goal for this session

Fix the blocker recorded above. The operator delegated open question 1 (new
column vs. reuse the existing flag) rather than answering it, so the choice is
made and justified below.

### Decision on the blocker's shape

**Reuse `blocks.complete`. No schema migration.**

Reading `normalization/quality.py` settled it. That module already describes the
exact failure, in its own docstring, as the reason it exists:

> "a thin record reaching a detector unlabelled is read as complete, and 'no
> large transfers in this block' is then asserted from a record that never
> contained transfers at all."

And `Severity.INCOMPLETE` is already defined as *"Usable, but narrower than it
looks. A consumer must not infer absence."* That is precisely the claim a
log-refused block needs to carry. A `logs_complete` column would have added a
second, parallel vocabulary for a distinction the codebase had already drawn â€”
and left `complete` still lying.

The bug was never a missing concept. It was that the shortfall had no route from
the poller, which knew, to the row, which reported.

### Files touched

| File | Tag | Change |
|---|---|---|
| `sensors/envelope.py` | **MINOR-FIX** | New `CaptureGap` enum; `RawRecord.capture_gaps` |
| `sensors/__init__.py` | **MINOR-FIX** | Export `CaptureGap` |
| `ingestion/poller.py` | **REFACTOR** | `_queue_logs` â†’ `_read_logs`; logs read before the block is queued, queued after it |
| `normalization/quality.py` | **MINOR-FIX** | `assess_block(..., capture_gaps=)` + `logs_captured` finding |
| `normalization/normalizer.py` | **MINOR-FIX** | Pass `record.capture_gaps` through |
| `database/analytics.py` | **MINOR-FIX** | `HeightWindow.complete_blocks/.incomplete_blocks/.all_complete`; window query counts complete rows |
| `skills/base.py` | **MINOR-FIX** | `supports_absence` requires completeness; `limitation` explains |
| `ingestion/backfill.py` | **REFACTOR** | Gained `include_logs` and log counters; had **no log handling at all** |
| `cli/main.py` | **MINOR-FIX** | Backfill branch passes `include_logs`; log reporting shared by both capture paths |
| `ingestion/tests/test_ingestion.py` | **MINOR-FIX** | `FakeChain.logs()` + `serves_logs`; 7 new tests |
| `normalization/tests/test_normalization.py` | **MINOR-FIX** | 2 new tests |
| `skills/tests/test_skills.py` | **MINOR-FIX** | 1 new test |
| `data/a001.db` | **data correction** | 28 rows `complete=1` â†’ `0` |

### The second half of the blocker, found by the self-critique

The first pass fixed only the poller. Writing the self-critique surfaced the
obvious question â€” *what about the other capture path?* â€” and checking it found
the same defect, worse:

`ingestion/backfill.py` had **no log handling whatsoever**. No `include_logs`
parameter, not one mention of logs in the file. `cmd_ingest` accepted `--tokens`
in backfill mode, configured a token repository, printed `tokens: 0 transfer(s)`
â€” and never asked for a log anywhere. Every block a backfill captured was stored
looking whole.

This was the more dangerous of the two, because a historical range is precisely
what a deep coverage window gets built from. Fixed by mirroring the poller:
`_read_logs`, read-before-queue, gap on failure, counters on `BackfillProgress`.

Two smaller corrections came with it, both in the backfill branch of
`cmd_ingest`: `job.run()` used the default batch of 50 regardless of `--blocks`,
so `--backfill --blocks 500` silently fetched 50; and `writer.drain` was sized
for blocks alone, which is half of what a run now produces.

### The ordering change in the poller

The one subtle piece. Logs must be **queued after** the block (token transfers
reference their block by foreign key), but the outcome must be known **before**
the block is queued (so it can be stamped on it). Those are not in conflict â€”
read and queue are separate steps â€” but the original code fused them.

One edge case had to be handled explicitly: logs fetched successfully but no
room left in the queue for them. Queueing the block anyway would store it
claiming completeness while discarding logs already in hand. The poller now
checks for room for **both** records before committing, and marks the gap if it
cannot have both. That failure is recoverable; the silent one was not.

### Tests run / passed / failed

| Command | Result |
|---|---|
| `python -m pytest -q` (after the source change, before new tests) | 839 passed â€” **nothing broke, and nothing covered the new behaviour** |
| `python -m cli ingest --blocks 2 --tokens` (live) | `logs: 0 captured, 2 undetermined`; blocks 25723789/90 stored **`complete=0`** where the same path produced `complete=1` before |
| `Coverage` over the live window | `supports_absence: False`, limitation names the incomplete count |
| `python -m pytest -q ingestion/ normalization/ skills/ tests` | 118 passed |
| `python -m cli ingest --backfill --start 25723714 --blocks 2 --tokens` (live) | `logs: 0 captured, 2 undetermined`; both blocks stored **`complete=0`** |
| `python -m pytest -q` (full, final) | **849 passed, 0 failed** |
| `python -m cli doctor` | 14/14 ok, exit 0 |

The 839-pass run after the source change is recorded deliberately: a green suite
that proves nothing is the reason Section 14 requires the regression test, not
the fix.

### The data correction

28 blocks (25723761â€“25723788) were stored `complete=1` with zero transfers by
the pre-fix code. The fix does not reach existing rows, so the window would have
kept counting them as whole.

Corrected with a scoped `UPDATE`: ethereum, canonical, `complete = 1`, zero
token transfers, and inside the range where log refusal was directly verified.
The 45 blocks holding real transfers were untouched. A verified snapshot was
taken first via the existing `cli backup`:
`data/a001-ethereum-20260811T102050Z.db`.

This is a correction, not a deletion, and it fails safe: if the judgement were
wrong, the effect is a window that refuses to license an absence it could have
supported. The opposite error is the one that produces confident falsehoods.

### Decisions made and why

- **Reused the existing flag** rather than adding a column â€” see above.
- **`capture_gaps` excluded from `record_id`.** Two captures of one block are
  the same observation whether or not one also obtained that block's logs.
  Folding the gap into the identity would break the dedup the record exists to
  provide. Asserted by a test.
- **`assess_block` takes the gaps as a parameter** rather than reading them off
  a new `CanonicalBlock` field. Everything else it checks is derivable from the
  block; log capture is not, and is not a property of the block at all. The
  function stays pure, which its own design goals require.
- **The correction was applied rather than escalated.** Section 18 reserves
  escalation for weak-justification replacements, architecture-level source
  conflicts, and trade/secrets boundaries. This was none of those, the evidence
  was direct, a backup existed, and the error direction is conservative.

### Proposed improvements (not acted on)

- `PROPOSED-IMPROVEMENT`: `cli ingest` should exit `EXIT_DEGRADED` when logs are
  undetermined, as it already does for rejections. Still not done: it changes an
  exit-code contract the scheduled task reads.
- `PROPOSED-IMPROVEMENT`: a `cli` repair path for retro-correcting completeness,
  so the next occurrence does not need a hand-written `UPDATE`.
- `PROPOSED-IMPROVEMENT`: relocate `DEFAULT_PERCENTILE` and `Stance` downward to
  clear the architecture allowlist and break the `intelligence <-> skills` cycle.
- Carried forward: `pytest-timeout` missing; two `except Exception: pass` sites
  in `memory/base/conversation.py`; two `aiosqlite` `ResourceWarning`s; nine
  empty top-level directories; the redundant empty `F:\CIE-OS\.env`.

### Self-critique â€” what is fragile, assumed, untested

- **Assumed, and this is the weakest link:** that all 28 corrected blocks were
  log-refused rather than genuinely transfer-free. The evidence is strong â€”
  ethereum blocks with 95â€“711 transactions each, ingested with `--tokens`, in a
  range where `sensor.logs()` was directly observed returning `determined:
  False` â€” but it is inference over a range, not a per-block observation. Rated
  `PROBABLE`, not `VERIFIED`. The error direction is conservative.
- **Both capture paths are now covered**, but only because the self-critique
  asked where else the bug could live. The first pass fixed the poller and
  declared the blocker resolved; it was resolved on one of two paths, and the
  unfixed one was the more important. Worth remembering as a process note: the
  fix felt finished before it was.
- **Untested:** the queue-full branch that drops fetched logs and marks the gap.
  It is guarded by a capacity check and marked `pragma: no cover`, so it is
  reasoned-about, not exercised.
- **Untested:** whether the 45 "complete" blocks are genuinely log-complete.
  They hold 26,987 transfers, which is strong evidence they were served â€” but no
  per-block reconciliation against an independent source was done.
- **Unchanged from earlier sessions:** REST interface, `visualize`,
  backup/restore round-trip, and every Tier 1 module against real data remain
  untested. `memory/`, `planning/`, `tools/` remain unread.

### Open questions for the operator

1. **A provider key is now the critical path.** Not a throughput question any
   more: without an endpoint that serves `eth_getLogs`, no window can ever
   support a negative claim, so Tier 1 cannot be validated at all. Which
   provider?
2. The 45 blocks captured on 2026-08-10 are still marked complete on the
   strength of holding 26,987 transfers. Should they be reconciled against an
   independent source before a window is built on them?
3. Still open: is `F:\A001_Blockchain_Intelligence\` (drive root) a stale
   duplicate?

### Late additions â€” the Tier 1 slice actually ran, and a claim was wrong

Two things were established after the blocker fix was written up.

**1. The Tier 1 vertical slice works end to end, today.** The absence gate needs
logs; *positive* claims do not â€” the whale and wallet skills read native value
transfers from the `transactions` table. Run against a real stored address:

```
cli investigate --db data/a001.db --address 0x5fa36dfe10ce3ee46479790076afe328bef7e2e2
  Signal 40.0/100   Confidence 0.60 (moderate)
  [affirmed]     likely: whale-scale transfer activity observed
                 retracted by: the transfer resolving to an internal rebalance ...
                 caveat: alerting requires validated maturity; never backtested
  [undetermined] cannot be determined: whether a dormant wallet reactivated
                 caveat: 32 of 77 stored blocks are incomplete ...
```

The Section 9 provenance chain was then closed by hand, all the way down:
conclusion â†’ evidence artifact â†’ `tx_hash 0xc8093c1e...` â†’ stored transaction
(668.56 ETH) â†’ block 25723775 â†’ `parent_hash` linkage â†’ `source_provider
publicnode` â†’ `source_record_id block-068f054f...` â†’ `observed_at`. That is the
Section 19 end-to-end scenario, minus the alert â€” which is correctly withheld.

Worth noting: **this session's own fix appears in that output**, and on the right
conclusion. The incomplete-window caveat attached to the *undetermined* dormancy
finding â€” a negative claim â€” and not to the affirmed whale finding.

Also verified: `cli visualize` renders a dashboard, and `cli serve` answers on
`/coverage`, `/investigate`, `/detectors`, `/skills`, `/health`, `/metrics`, with
the new completeness fields exposed over the API.

**2. "A provider key is the critical path" was wrong.** It was concluded from
ethereum alone. Base's open endpoints *do* serve `eth_getLogs`:

```
cli ingest --db data/base.db --chain base --blocks 10 --tokens
  logs   : 10 captured, 0 undetermined, 0 dropped
  tokens : 740 transfer(s), 133 NFT transfer(s)
  window : 15 blocks, 15 complete, contiguous True, all_complete True
```

The base window's only limitation is now depth â€” "only 15 blocks stored, 3600
needed" â€” which is the failure mode that ingestion alone fixes. Measured:
**base ~3.2 s/block** against **ethereum ~7.6 s/block**, so a 3,600-block base
window is ~3.2 hours, resumable, no key required.

A generalisation from one chain, in a codebase whose Section 10 exists
specifically to forbid that. Recorded rather than quietly edited.

### Next session should start at

**Build the 3,600-block base window.** Nothing blocks it:

```
python -m cli ingest --db data/base.db --chain base --blocks 500 --tokens
```

Repeated, or scheduled via `scripts/install-task.ps1`; the checkpoint makes it
resumable. Confirm `supports_absence` reads 1 *and* `all_complete` stays true,
then re-run the investigate â†’ provenance trace on base with a licensed negative
claim included. That closes the Tier 1 gate.

Detector promotion to `VALIDATED` remains out of scope â€” it needs a labelled
window and `evaluation/backtest.py`, which is its own project.

---

## Session 2026-08-11 (fourth session)

### Goal

Continue building. Verify the Section 11 multi-agent claim left `UNVERIFIED`,
then build the anomaly engine â€” the one Tier 1 module Section 19 requires that
did not exist.

### Section 11 â€” verified, and it holds

Checked rather than assumed:

- `intelligence/engines/composition.py:194-203` records conflicting fields
  instead of overwriting them, with the reason stated in the code: *"Overwriting
  would hide a genuine disagreement behind a plausible value."* Covered by
  `test_conflicts_are_recorded_not_resolved`.
- `_weakest(coverages)` takes the weakest coverage, not the mean.
- `FinalScoreEngine` weights score *values* but sets
  `confidence = min(...)` and preserves the component breakdown. Section 11's
  prohibition is on averaging child conclusions; a numeric aggregate that keeps
  its components visible and takes worst-case confidence is not that.
- `EvidenceValidator` recomputes the content hash for chain-of-custody and
  enforces the tier ceiling.

Status moves from `UNVERIFIED` to `HOLDS`. No gap found.

### A serious bug found while building â€” `consume()` dropped records silently

Caught by watching the base window build, not by a test.

`cli ingest --blocks 100 --tokens` reported `logs: 100 captured` but
`stored: 32 block(s)`, and the window went non-contiguous. Cause:
`RecordWriter.consume()` drained **one** batch of `DEFAULT_BATCH = 64` records
and returned. A 100-block run with tokens queues 200 records, 64 of them were
written â€” 32 blocks â€” and the remaining 136 died with the process.

The checkpoint had already advanced to height 100, because the poller commits
the position when a record is *queued*, not when it is written. Heights 33-100
were therefore recorded as done and never fetched again.

Confirmed in the data before fixing: two gaps in `data/base.db`, of **68 heights
each** â€” exactly 100 âˆ’ 32.

This never showed earlier because every previous run was under 32 blocks.

Fixed in `database/writer.py`: `consume` now drains until the queue is empty,
using `batch` as the commit size it was always documented to be. Regression test
`test_consume_drains_the_whole_queue_not_one_batch` fails on the old behaviour.

### The anomaly engine

Audited before building, per Section 3. `intelligence/scoring/anomaly.py`
already existed but consumed `subject["anomalies"]`, and **nothing produced it** â€”
an orphaned scorer. What was missing was the analyzer.

Built `intelligence/analysis/anomaly.py` (DET-ANOMALY-01), wired into
`DEFAULT_ANALYZERS`, the `score` stage, `_CLAIM_SPECS`, and the maturity
registry at `IMPLEMENTED` with the same `blocked_by` as its peers.

Design constraints taken from Section 12 and Section 13:

- Reports **deviation only**. Never bullish, bearish, manipulation, wash
  trading, or smart money â€” asserted by a test that scans the rendered output.
- Grades on the evidence standard's vocabulary: `NORMAL / UNUSUAL / SUSPICIOUS
  / HIGH_RISK_PATTERN / INSUFFICIENT_EVIDENCE`.
- `NORMAL` is a negative claim, so it requires `absence_meaningful`. Without
  coverage the verdict is `INSUFFICIENT_EVIDENCE`, not `NORMAL`.
- Under 20 observations, or a population with no spread, is
  `INSUFFICIENT_EVIDENCE` rather than a verdict.

### A bug I introduced, and caught before it shipped

The first version computed the modified z-score on **raw** transfer values. Run
against real data it produced:

```
HIGH_RISK_PATTERN â€” 1581 outlier(s) in a population of 5000 (max z=88104.08)
```

31.6% of ordinary ethereum traffic flagged as anomalous, and it had already
added 30 points to the signal score of a live investigation.

Measured both ways on the same 5,000 transfers:

| scale | outliers | share | max z |
|---|---|---|---|
| raw | 1,581 | 31.6% | 88,104 |
| log10 | 0 | 0.0% | 2.5 |

The estimator assumes approximate normality around the centre. Transfer values
are log-normal across eight orders of magnitude, so on the raw scale the MAD is
negligible against the spread and nearly everything clears the cutoff. A robust
estimator on the wrong scale is still wrong.

Fixed by transforming to log10 first, and the `SUSPICIOUS`/`HIGH_RISK` bands
retuned from 10/50 to 5/8, which were meaningless on the raw scale.

Regression test `test_a_log_normal_population_is_not_flagged_wholesale` was
verified to actually catch it: **40% flagged without the transform, 0% with**,
against an asserted ceiling of 2%.

Note for the record: this does not contradict the whale detector flagging the
largest of those transfers. Percentile rank and distributional outlier are
different questions â€” the largest sample from a log-normal population is
expected to be the largest, and being so is not a departure from the
distribution.

### One more wiring gap, found by reading the live output

The report stage listed findings from a hardcoded `("whale", "dormant")` tuple.
The new detector was therefore scoring and reaching the decision gate while
never appearing in the findings a reader sees. Now derived from whichever
analyzer findings carry a summary.

### Files touched

| File | Tag | Change |
|---|---|---|
| `database/writer.py` | **MINOR-FIX** | `consume` drains the whole queue |
| `intelligence/analysis/anomaly.py` | **BUILD-NEW** | DET-ANOMALY-01 |
| `intelligence/analysis/__init__.py` | **MINOR-FIX** | Export |
| `intelligence/core/stages.py` | **MINOR-FIX** | Register analyzer, score contribution, derive the findings list |
| `decision/conclusions.py` | **MINOR-FIX** | `_CLAIM_SPECS["anomaly"]` |
| `decision/maturity.py` | **MINOR-FIX** | DET-ANOMALY-01 at `IMPLEMENTED` |
| `database/tests/test_database.py` | **MINOR-FIX** | 1 regression test |
| `intelligence/analysis/tests/test_analyzers.py` | **MINOR-FIX** | 12 new tests |

### Tests run / passed / failed

| Command | Result |
|---|---|
| `python -m pytest -q database/tests/test_database.py` | 29 passed |
| `python -m pytest -q intelligence/analysis/tests/test_analyzers.py` | 33 passed |
| `python -m pytest -q` (full) | **862 passed, 0 failed** (was 850) |
| `python -m cli detectors` | 3 detectors, all `implemented`, **0 may alert** |
| Live `cli investigate` after the log fix | `anomaly not determinable (no deviation found, but the window cannot license an absence)` |
| Base window build, chunk 2 | `200 blocks, 200 complete, contiguous=True` â€” was 32/100 before the `consume` fix |

The full-suite run took 205s rather than the usual ~50s; the base window build
was competing for disk and network at the time. Not a code regression.

### Self-critique

- **Two of this session's three bugs were found by watching real output, not by
  the suite.** The `consume` truncation and the raw-scale anomaly both passed
  every test that existed. Unit tests confirm what a component does with data
  you thought to give it; neither would have surfaced without running the thing
  against a real chain.
- **The anomaly detector has never been validated against labelled data.** Its
  thresholds (3.5 / 5 / 8, min population 20) are principled and sourced, but
  unmeasured. It sits at `IMPLEMENTED` for exactly that reason.
- **Untested:** the `HIGH_RISK_PATTERN` and `SUSPICIOUS` bands have unit
  coverage but have never fired on real chain data, because the one real
  population tested had no genuine outlier.
- **Assumed:** that log10 is the right transform for every chain's value
  distribution. Verified on ethereum only. Base may differ, and no test asserts
  the assumption holds per-chain.
- **Base window still building** â€” 200 of 3,600 blocks at the time of writing.

### Next session should start at

Finish the base window, then re-run the investigate trace on base where
`supports_absence` will be true â€” the first time A001 will be able to issue a
licensed *negative* claim, and the first real exercise of the anomaly detector's
`NORMAL` verdict.

Then: exchange flow intelligence (needs an address label source) and terminal
depth. Detector promotion to `VALIDATED` remains its own project.

---

## Session 2026-08-11 (fifth session) â€” selective capture

### Goal

The operator reported that a previous project mirrored every blockchain
transaction locally and computed over the copy, which became heavy and buggy.
**That anti-pattern was in A001**, and the first job was to measure it rather
than accept or dismiss the report.

### Measured, before changing anything

| chain | blocks | size | per block |
|---|---|---|---|
| ethereum | 77 | 54.2 MB | **0.70 MB** |
| base | 437 | 175 MB | **0.40 MB** |

Ethereum at 7,200 blocks/day â†’ **~5 GB/day, ~150 GB/month, one chain**. Across
fifteen chains, 30â€“50 GB/day. The operator's diagnosis was correct.

334 transactions per ethereum block were being stored so that a handful could
later be counted. The counting can happen once, at capture.

### What was built

**Schema v3** (`database/migrations.py`, forward-only, verified against an
existing v2 database with data preserved):
`block_aggregates`, `hourly_aggregates`, `entities`, `labels`.

**`tiers/`** â€” where data lives and for how long:

| Tier | Window | Holds |
|---|---|---|
| CACHE | seconds | raw provider responses, in memory only |
| HOT | 7 days | per-block aggregates + material transactions |
| WARM | 90 days | hourly aggregates â€” the anomaly baseline |
| LEDGER | forever | entities, track records, labels |

`tiers/retention.py` states the policy as data, not behaviour, so it can be
reported rather than inferred. 90 days for WARM because institutional and
smart-money patterns are measured in months.

**`pipeline/`** â€” `materiality.py` (percentile-based gate, never a fixed
currency amount) and `aggregate.py` (the counters that make dropping honest).

### Correction to the approved plan

The plan said to reuse `memory/storage/cache.py` for the cache tier. **Reading
it showed that was wrong** â€” it is async and `MemoryEntry`-shaped, built for
conversational agent memory, and the ingestion path is synchronous.

The correct reuse was already in the codebase: `blockchain/rpc/clients/cache.py`
(`ResponseCache`), which is sync, bounded, never caches failures, and derives
lifetimes from finality rather than a fixed clock â€” an immutable block is held
indefinitely while a head-dependent read is barely held at all. It is already
wired through `ChainDispatcher` into every sensor read. **Tier C needed no work.**

### A bug in my own code, caught before it shipped

`BlockAggregateRepository.totals_between` first summed value columns with
`SUM(CAST(value AS INTEGER))`. Amount columns are zero-padded TEXT precisely
because SQLite's INTEGER is signed 64-bit, ceiling ~9.22e18 â€” about nine ether
in wei.

Verified rather than reasoned about: SQLite does not truncate here, it **raises
`integer overflow`**. Any window summing more than ~9.2 ETH â€” which is nearly
every window â€” would have failed outright. Counts are now summed in SQL; values
are summed in Python, whose integers are unbounded.

Regression test `test_large_totals_are_exact` uses 150 ETH deliberately.

### Result â€” measured on real ethereum data

Filter, over the 77 stored blocks (25,743 real transactions):

```
derived floor    : 13.03 ETH  (99.5th percentile of the chain's own distribution)
transactions seen: 25,743
kept (material)  : 66   (0.26%)
dropped          : 25,677
```

Disk, same blocks written the new way:

| | old | new |
|---|---|---|
| per block | 720.8 KB | **2,926 bytes** |
| ethereum/day | ~5 GB | **20.1 MB** |
| 90 days | ~450 GB | **1.77 GB** |

**252Ã— reduction.** The plan's target was under 5 KB/block.

Caveat stated: this figure covers aggregates only. The 66 material transactions
add roughly 0.3 KB/block at typical row size â€” still inside the target, but not
included in the 2,926.

### Tests

| Command | Result |
|---|---|
| `pytest -q database/` | 50 passed (v2â†’v3 migration preserves data) |
| `pytest -q tiers/ tests/test_architecture.py` | 18 passed |
| `pytest -q pipeline/ tiers/ tests/test_architecture.py` | 35 passed |
| `pytest -q` (full) | **890 passed, 0 failed** (was 862) |
| `cli doctor` | 14/14 ok, exit 0 |

`tiers` and `pipeline` added to the architecture test's layer order and to
`pytest.ini` testpaths â€” without the second, the new tests would have been
written and never run.

### Self-critique

- **The 252Ã— figure is a replay, not a live run.** Real transactions, real
  values, but read from the existing store rather than streamed from a live
  block. The live path is not yet wired to the new pipeline.
- **The materiality gate's label rule is inert.** No label source is
  configured, so exchange and bridge flows below the value floor are invisible.
  The gate reports this through `limitation()` rather than failing quietly, but
  it is a real coverage hole and it is the operator's stated Tier-1 signal.
- **Tier W and Tier L have schema but no repositories yet.** The baseline
  rollup and entity ledger are designed and migrated, not implemented.
- **Untested:** the floor rising under budget pressure. The mechanism exists
  (`with_floor`) and nothing exercises it.
- **The old full-copy path is still the one `cli ingest` uses.** Nothing has
  been switched over; both exist side by side.

### Next session should start at

Wire the live capture path to the new pipeline and re-measure against a real
ingest rather than a replay. Then Tier W rollup and Tier L entity ledger, which
is what smart-money detection needs to start accumulating at all.


---

## Session 2026-08-11 (fifth) â€” selective pipeline wired to live capture

### Goal

Wire the new selective pipeline into the real capture path and measure it
against live chain data, not a replay.

### Result â€” the duplication anti-pattern is fixed and measured

| | old (full copy) | new (selective) |
|---|---|---|
| marginal cost | 536,986 B/block | **1,502 B/block** |
| base @2s | 21.60 GB/day | **61.9 MB/day** |
| ethereum @12s | 3.60 GB/day | **10.3 MB/day** |
| 15 chains Ã— 90 days | ~28 TB | **~82 GB** |

**358Ã— reduction.** The plan's target was <5 KB/block; actual is 1.5 KB.

The plan text said "roughly 700Ã—" â€” that was an estimate written before
measurement. The measured figure is 358Ã—, and the plan should be corrected
rather than left to look achieved.

Live run, base chain, 30 blocks: `5,003 transactions seen, 6 stored (0.12%)`.
The 168 KB of fixed schema is paid once and excluded from the marginal figure;
an earlier 30-block sample reported 6.67 KB/block because that overhead was
still being amortised, which overstated the cost.

### Files touched

| File | Tag | Change |
|---|---|---|
| `pipeline/writer.py` | **BUILD-NEW** | `SelectiveWriter` â€” wraps `RecordWriter`, filters `block.transactions` before storage |
| `normalization/quality.py` | **MINOR-FIX** | `capture_floor` param + `selective_capture` finding |
| `cli/main.py` | **MINOR-FIX** | `--selective` / `--floor` flags, both capture paths, backfill head fix |

### Two bugs found by running it, not by reading it

1. **Backfill demanded a head read it never used.** `cmd_ingest` called
   `sensor.head()` before checking `--start`, and returned `EXIT_DEGRADED` when
   it failed. When base's endpoints stopped answering head reads, a backfill
   over a fixed historical range â€” every height settled and fetchable â€” refused
   to run. This is why the overnight 3,600-block job stalled at 700 contiguous
   blocks and then burned every remaining chunk doing nothing. Fixed: the head
   is read only when the caller did not supply a start.

2. **`--selective` was ignored by the backfill path.** Only the poller branch
   used it, so `--selective --backfill` would have stored every transaction of a
   historical range while reporting itself selective â€” and a historical range is
   exactly where the volume is. Both paths now honour it.

### Design note: selective capture vs "incomplete"

Writing only material transactions makes `len(block.transactions) <
block.transaction_count`, which fired the existing `transactions_complete`
finding: *"N of M transactions could not be normalized"*. That is factually
wrong â€” they normalized fine and were dropped on purpose â€” and would have sent
someone hunting a parser bug that does not exist.

`assess_block` now takes `capture_floor` and emits `selective_capture` instead,
with an exact boundary: *"do not infer that no transfer below <floor> occurred;
transfers at or above it were all captured."* Still INCOMPLETE, correctly â€” but
a consumer can now tell which side of the floor its question falls on.

`transaction_count` is deliberately left at the chain's own figure. Lowering it
to the material count would make a busy block read as a quiet one â€” the exact
misreading the aggregate exists to prevent.

### Tests

| Command | Result |
|---|---|
| `pytest -q` | **893 passed, 0 failed** |
| `cli doctor` | 14/14 ok, exit 0 |
| live `--selective` (poller) | 30 blocks, 5,003 seen, 6 kept (0.12%) |
| live `--selective --backfill --start` | 20 blocks, 3,085 seen, 4 kept â€” head never read |

### Open

- **Rate limits are now the binding constraint, not code.** Base's free
  endpoints stopped answering head reads under sustained load. This is exactly
  what the per-day/month budget ledger is for; it is the next task and is no
  longer optional.
- The 3,600-block absence window still has not been built. Two attempts failed
  for two different reasons, both now fixed.
- `supports_absence` should become floor-aware: a selectively captured window
  can license absence claims *above* the floor and not below. Currently any
  selective block counts as incomplete, so the gate stays shut.

### Next session should start at

The call-budget ledger (`pipeline/budget.py`), then rebuild the 3,600-block base
window with both fixes in place.

---

## Session 2026-08-11 (sixth) â€” persistent call-budget ledger

### Goal

Build the per-day / per-month call budget the free tiers actually meter on.
Rate limits became the binding constraint last session: base's endpoints stopped
answering head reads under sustained load, which is what stalled the 3,600-block
window.

### What was built

`pipeline/budget.py` + schema **v4** (`call_ledger` table).

`blockchain/rpc/rate_limit/bucket.py` already handles the per-minute dimension
and stays untouched. What it cannot do is remember: its state is a dict in
memory, so every restart hands the process a fresh minute. That is fine for a
minute and useless for a month, and the scheduled task runs every ten minutes
as a new process.

Design decisions, each with a reason:

- **Attempts are counted, not successes.** A provider counts the request when
  it arrives. Recording only successful calls undercounts precisely during
  retries, timeouts and 429 storms â€” the periods that burn the most allowance.
  So the ledger is written before the call goes out, and a failed call costs.
- **Day and month tracked separately; the worse one binds.** A provider can be
  comfortable today and out of allowance for the month. Tracking only the day
  walks into a wall it could have seen coming.
- **UTC windows.** A ledger on local time double-counts or skips an hour twice
  a year, and the provider is not resetting on the operator's timezone.
- **A ceiling is a belief, not a fact.** A 429 observed while the ledger still
  shows headroom is the provider stating its real limit;
  `observe_rejection()` records it and every later decision uses the lower
  figure. **The spend is never rewritten** â€” what was used is history, what is
  allowed is an estimate, and conflating them destroys the evidence that the
  estimate was wrong.
- **A provider with no known ceiling is never throttled.** Unmetered and
  undocumented providers are real; inventing a number produces confident
  throttling with no basis.
- **Conserve at 85%, do not stop at 100%.** A chain that goes dark at 23:00
  every day is worse than one that stays coarse from 20:00. `TIGHT` recommends
  degradation; it never applies it silently.

### Tests

| Command | Result |
|---|---|
| `pytest -q pipeline/tests/test_budget.py` | 15 passed |
| `pytest -q` (full) | **908 passed, 0 failed** |
| `cli doctor` | 14/14 ok, `storage ok â€” schema v4`, exit 0 |

Verified by execution, not reasoning: day resets while month carries; the worse
window binds; a 429 drops a believed ceiling from 5,000 to the 300 actually
spent and flips pressure to `EXHAUSTED`; an unmetered provider stays `UNKNOWN`
after 50,000 calls.

### Stopped deliberately short of wiring

The ledger is built and tested but **nothing writes to it yet on the real call
path**. That was a choice, not an omission.

Wiring it properly means aggregating `CallResult.attempts` per provider inside
`blockchain/rpc/clients/dispatch.py`, which is where the calls actually happen.
The approximation available at the CLI level â€” the poller's step count â€” is a
*lower bound* on calls made, and a budget that quietly undercounts is worse than
no budget: it reports headroom that does not exist. That is the same class of
false confidence this project keeps finding and fixing, and it was not worth
introducing to close a task.

Also noted: the transport layer should not grow a storage dependency. The
budget belongs to the caller, consulted around the call, not inside the
dispatcher.

### Next session should start at

1. Aggregate `CallResult.attempts` per provider and record spends through
   `CallBudget.spend()` â€” the seam is `ChainDispatcher.call`'s return path.
2. Then rebuild the 3,600-block base window with all three fixes in place
   (`consume` drain, backfill head, budget).

---

## Session 2026-08-12 â€” coverage learns *why* a block is incomplete

### Goal

Fix the incompleteness reason. Selective capture had shut the absence gate on
itself: every block it writes is incomplete, `complete` is one bit, and one bit
cannot separate a block that was filtered from a block that was never fetched.

### The bug, stated exactly

Two failures were stored identically and read as the worse one.

| | logs refused | filtered at a floor |
|---|---|---|
| what is missing | transfers nobody can describe | everything below a written-down number |
| what it licenses | no negative claim at all | "nothing at or above the floor happened" |
| what was stored | `complete = 0` | `complete = 0` |

So `Coverage.limitation` told an operator that selectively captured blocks
*"are incomplete; their transfers were never fetched"* â€” false, and false in the
direction that sends someone hunting a transport bug that does not exist. And
`supports_absence` stayed shut forever on any selective window, which threw away
the entire point of capturing selectively: the drop is bounded and the bound was
known at capture time.

### What changed

| File | Tag | Change |
|---|---|---|
| `normalization/quality.py` | **MINOR-FIX** | `QualityReport.incomplete_reason` + `.bounded`; `BOUNDED_CHECKS` |
| `database/migrations.py` | **BUILD-NEW** | schema **v5** â€” `blocks.incomplete_reason`, `blocks.capture_floor` |
| `database/repositories.py` | **MINOR-FIX** | `save()` takes and stores both |
| `database/writer.py`, `pipeline/writer.py` | **MINOR-FIX** | both capture paths pass the reason; selective passes the floor |
| `database/analytics.py` | **MINOR-FIX** | `HeightWindow.selective_blocks` / `unfetched_blocks` / `capture_floor` / `all_captured` |
| `skills/base.py` | **MINOR-FIX** | `supports_bounded_absence`, `absence_floor`, `supports_absence_above()`; corrected `limitation` |

### Decisions, each with its reason

- **The reason is stored, not derived.** A block whose transactions were all
  dropped at a floor is indistinguishable, by inspection, from one fetched
  without expansion. Only the capture knows, so if it does not say, nothing
  later can.
- **Stored as the check names themselves**, comma-separated
  (`"logs_captured,selective_capture"`). A second vocabulary for the same facts
  is a translation layer that drifts, and the names are already stable
  identifiers.
- **`BOUNDED_CHECKS` is deliberately narrow** â€” `selective_capture` alone.
  Being wrong in that direction licenses a claim the data cannot carry.
  `provenance` was left out: a block that cannot be cited is a weaker record
  whatever else it contains.
- **An empty reason on an incomplete block is *not* bounded.** That is every row
  written before v5, and the truthful reading is "incomplete, and nobody
  recorded why" â€” exactly the case a negative claim must not rest on. Old data
  therefore gains nothing, which is correct.
- **The floor is padded text and the window takes `MAX()`.** Unpadded, `MAX()`
  returns the longest string, so a floor of 9 wei would outrank one of 10 ether
  and the window would claim a *stronger* absence than it holds. Highest, not
  mean or latest: one hour of raised floor under budget pressure bounds the
  whole window.
- **An empty block is never stamped with a floor.** Nothing was filtered, so
  nothing was dropped. Stamping it would let an empty block raise a window's
  floor and narrow every claim drawn from it.
- **`supports_absence` stays strict and stays the default.** The bounded form
  needs a value named to use it. A bounded claim read as unbounded is the
  failure; the reverse costs only a claim that could have been made.
- **Classification is in Python, not SQL.** `window()` groups by reason â€” a
  handful of rows whatever the chain's height â€” and buckets them against
  `BOUNDED_CHECKS`. Policy written into a `CASE` expression is policy nobody
  can find.

### One existing test had to change

`test_a_v1_database_upgrades_without_losing_blocks` staged its "old" database by
writing through today's `RecordWriter`, which now names v5 columns against a v1
schema. The staging insert is now v1's own column list. The test's subject is
the migration, and it was breaking on the wrong thing.

### Verified by execution

| Check | Result |
|---|---|
| `pytest -q` | **924 passed, 0 failed** (was 908; 16 new) |
| `cli doctor` | 14/14 ok, `storage ok â€” schema v5`, exit 0 |
| live `ingest --selective`, base, 12 blocks | 1,700 tx seen, 1 kept (0.06%) |
| migration on a copy of `a001.db` (v2, 77 eth blocks) | â†’ v5, 45/32 split intact |
| migration on a copy of `live_selective.db` (v3, 230 base blocks) | â†’ v5, no data lost |

The live 12-block window, read back through `Coverage`:

```
selective_blocks         : 12      unfetched_blocks: 0
supports_absence         : False   <- unchanged, and correct
supports_bounded_absence : True    <- new
absence_floor            : 1000000000000000000
limitation: 12 of 12 blocks were captured selectively at a floor of
            1000000000000000000; an absence is evidence at or above that
            floor, not below it
```

Before this change the same window reported *"12 of 12 stored blocks are
incomplete; their transfers were never fetched"* and licensed nothing.

### Self-critique

- **No consumer reads the bounded form yet.** `wallet_lookup/profile.py`,
  `SubjectComposer`, `decision/recommendations.py`, the dashboard card and
  `telemetry/metrics.py` all still ask `supports_absence` and still get False.
  They inherit the corrected *message* immediately and the corrected *gate* not
  at all. That was scoped deliberately â€” the gate change is one decision per
  consumer about what a floor means for its own question â€” but until it lands,
  the practical win is honesty in the limitation line, not a detector that
  answers more.
- **Only new captures benefit.** The 230 selectively captured blocks already in
  `live_selective.db` carry no reason and stay classified as unfetched. That
  window also fails contiguity (230 blocks across a span of 18,578), so nothing
  is lost today, but the general point stands: this is a forward fix.
- **`logs_captured` is treated as unbounded, which is stricter than the truth.**
  A refused log read costs token and NFT transfers; the native transfers in that
  block were still captured whole. A finer model would bound the claim per
  record kind rather than per block. Erring strict here is the safe direction,
  but it is an approximation and it is now the reason a `--tokens` run with one
  refused fetch closes a window that could still answer for native value.

### Next session should start at

1. Decide, per consumer, what a bounded absence means for its question â€” the
   dormancy skill is the clear first one ("no material movement above X"), and
   it is where the corrected gate actually changes an answer.
2. Then the original queue: aggregate `CallResult.attempts` into
   `CallBudget.spend()` at `ChainDispatcher.call`'s return path, and rebuild the
   3,600-block base window.

---

## Session 2026-08-12 (later) â€” the call ledger gets a writer

### Goal

Step 2 of the queue above, first half: wire `CallBudget` to the real call path.
The ledger has been built, tested and unwritten-to since the sixth session. A
budget nothing writes to is a table, not a budget.

### The seam

The two constraints were already recorded and they point in opposite
directions. The count only exists in `blockchain/rpc/clients/dispatch.py` â€”
that is where requests actually leave the process. The ledger only exists in
`pipeline/budget.py` â€” that is storage, and the transport must not grow a
storage dependency to reach it.

So the transport now *reports* rather than records:

```
SpendSink = Callable[[str, str, int], None]     # (chain, provider, calls)
```

Three primitives, deliberately. The type is what keeps the layers apart, and a
signature made of strings and an int cannot quietly acquire an import later.
`CallBudget.recorder()` builds the other end.

### What changed

| File | Tag | Change |
|---|---|---|
| `blockchain/rpc/clients/dispatch.py` | **BUILD-NEW** | `SpendSink`; `ChainDispatcher(on_spend=...)`; `_report_spend()` |
| `blockchain/rpc/clients/dispatch.py` | **MINOR-FIX** | `CallResult.provider_attempts` â€” requests that actually went out, per provider |
| `blockchain/rpc/clients/__init__.py`, `rpc/__init__.py` | **MINOR-FIX** | export `SpendSink` |
| `pipeline/budget.py` | **BUILD-NEW** | `CallBudget.recorder()` |
| `pipeline/budget.py` | **MINOR-FIX** | `spend()` docstring now states where it is actually called from |
| `cli/main.py` | **MINOR-FIX** | `ingest` opens the database first, builds the dispatcher with the sink, prints the ledger |

### Decisions, each with its reason

- **`provider_attempts` is a new field, not a read of `failures`.** `failures`
  also holds candidates the local limiter refused, and a request that never
  left the process cost the provider nothing. Charging for those would make
  throttling look like usage and close a budget on a chain that was never read.
  `BUDGET_EXHAUSTED` is therefore the one outcome that reports an empty tuple.
- **Counted before the response, reported after the read.** The increment sits
  immediately before `_execute`, so a call that then times out is still spent â€”
  the sixth session's "attempts, not successes" survives intact. The *report*
  happens once per provider on `call`'s return path, so one logical read is one
  ledger write instead of one per retry. What that costs is a process killed
  mid-read: those requests reached the provider and go uncounted. The
  alternative costs a database write on the hot path of every retry, in exactly
  the 429 storms this ledger exists to survive. The undercount is bounded by
  one read; the alternative's cost is not bounded at all.
- **A sink that raises does not lose the answer.** The chain read is already in
  hand when the sink runs. It is logged at `exception` level rather than
  swallowed, because a ledger that silently stops recording reports headroom
  that does not exist â€” which is the failure mode the whole module is built
  against.
- **The database opens before the transport in `cli ingest`.** It has to: the
  ledger lives in the capture database and the dispatcher takes its sink at
  construction. A sink installed after the first call is a sink that missed a
  call, and the first call of a run is the head read â€” the one most likely to
  be the call that runs a free tier out.
- **No ceilings were configured.** Nothing in the provider catalog carries a
  per-day or per-month figure, and alchemy's free tier meters compute units,
  not calls. Inventing a number here would produce confident throttling with no
  basis â€” the sixth session's own decision. So every provider reads `UNKNOWN`
  and none is throttled. What the wiring buys today is the *measurement*, which
  is the thing that has to exist before any ceiling can be believed.
- **`check()` is still not consulted before a call.** With no ceiling known,
  every verdict is `allowed`, so consulting it would add a code path that
  cannot fail and cannot be tested against a real refusal.

### Verified by execution

| Check | Result |
|---|---|
| `pytest -q` | **937 passed, 0 failed** (was 924; 13 new) |
| `cli doctor` | 14/14 ok, schema v5, exit 0 |
| live `ingest --selective`, base, 5 blocks | 7 calls each to alchemy and base-official, ledgered |
| the same command again, 3 blocks, new process | 7 â†’ **12** each; the ledger survived the process |

```
budget     : alchemy 12 call(s) today, 12 this month (no ceiling known)
budget     : base-official 12 call(s) today, 12 this month (no ceiling known)
```

Fourteen calls for five blocks, split across two providers â€” which is also the
first time the per-block call cost of selective capture has been visible at all.

### Self-critique

- **Only `cli ingest` is wired.** Every other entry point â€” the API routes, the
  skills, `cli investigate`, `cli wallet` â€” builds its dispatcher through
  `SensorRegistry()` with no sink and spends silently. The ledger therefore
  undercounts A001's real usage by however much those paths read. `ingest` is
  the path that spends at volume, so this is the right first one, but the
  budget's own honesty rule says an undercount must be named: it is named here.
- **The 429 signal is still not connected.** `_dispatch` already detects a
  provider's 429 and penalises the local limiter, and `observe_rejection()`
  exists to turn that same event into a lowered ceiling. They are not joined,
  because a 429 from a per-second burst and a 429 from an exhausted daily quota
  are indistinguishable at this seam, and reading the first as the second would
  permanently cripple a believed daily ceiling on a burst that the limiter
  already handled. Joining them needs a discriminator that does not exist yet.
- **Nothing reads the ledger except a print.** It accumulates and it is
  displayed. No capture decision consults it, which is the correct state while
  every ceiling is unknown, and the wrong state the moment one is not.

### Next session should start at

1. The bounded-absence consumer decision, still item 1 from the previous
   session â€” the dormancy skill first.
2. Rebuild the 3,600-block base window. Not an implementation task: it is a
   sustained live capture, and rate limits, not code, are what stopped the last
   two attempts. The ledger now measures what it costs while it runs.

---

## Session 2026-08-14 â€” 15-chain restructure + terminal depth (Step 5)

### Goal for this session

Complete Step 5 of the handoff plan: create a `chains/` directory structure with
one numbered directory per chain (01â€“15), each containing `README.md`,
`endpoints.yaml`, `limits.yaml`, and `adapter.py`. Bitcoin gets its own UTXO
adapter shape. This is the final implementation step; Steps 1â€“4 were already
DONE.

### What was built

**Base adapter module** (`chains/__init__.py`, `chains/base.py`):

- `ChainAdapter` (abstract base) with properties: `chain`, `chain_type`,
  `sensor_family`, `is_account_based`, `is_utxo`, `has_sensor`.
- `EvmAdapter(ChainAdapter)` â€” for 13 EVM chains. `is_account_based=True`,
  `has_sensor=True`, `sensor_family="evm"`.
- `UtxoAdapter(ChainAdapter)` â€” for Bitcoin. `is_account_based=False`,
  `is_utxo=True`, `has_sensor=False`, `sensor_family="utxo"`. Docstring
  explains five concrete reasons the EVM account model produces wrong output
  on UTXO chains.
- `SolanaAdapter(ChainAdapter)` â€” for Solana. `has_sensor=False`,
  `sensor_family="solana"`. Notes slots-vs-blocks difference.

**15 numbered directories** (`chains/01_ethereum/` through `chains/15_bitcoin/`),
each containing:

| File | Contents |
|---|---|
| `__init__.py` | empty (package marker) |
| `adapter.py` | imports from `chains.base`, creates adapter instance |
| `endpoints.yaml` | all providers from catalog; access level, archive, logs, rate_limit; API key fields **empty** with `env_var` naming convention |
| `limits.yaml` | chain_type, has_sensor, finality, reorg_depth, block_time, constraints list â€” sourced from `knowledge/chains.py` |
| `README.md` | chain properties table, what A001 can do on this chain, provider count, known limits |

60 files in chain directories + 2 in `chains/` root = 62 new files.

**Terminal depth** â€” `cli chains` updated to reference the per-chain directory
structure: `"Per-chain details: chains/<number>_<chain>/ (README.md,
endpoints.yaml, limits.yaml, adapter.py)"`.

**17 new tests** (`chains/tests/test_chains.py`):

- All 15 directories exist with the four required files
- Chain order matches `ChainName` registry
- Endpoints/limits YAML have required fields and providers
- All adapters importable as `ChainAdapter` instances
- EVM chains use `EvmAdapter` with correct properties
- Solana uses `SolanaAdapter`, `has_sensor=False`
- Bitcoin uses `UtxoAdapter`, `is_utxo=True`, `is_account_based=False`,
  `has_sensor=False`
- Chain names match between YAML, adapters, and directories
- No API keys in endpoint files
- READMEs exist and mention observability

`pytest.ini` updated to include `chains` in testpaths.
`test_architecture.py` updated to include `"chains"` in the `UNRANKED` set.

### Design decisions

1. **The 15 chains are the existing 15 in the registry.** TRON, Sui, TON,
   Aptos, NEAR, Cosmos are not in the registry â€” they are aspirational, not
   part of Step 5.
2. **Thin per-chain adapters that import from the base.** The existing sensor
   registry and dispatcher handle actual chain interaction; adapters are the
   structured metadata and type-safety layer.
3. **Bitcoin gets `UtxoAdapter`, not `EvmAdapter`.** No accounts with balances,
   no event logs, common-input-ownership is probabilistic. The adapter and
   README document why EVM assumptions produce wrong output.
4. **Solana gets `SolanaAdapter`.** Slots differ from blocks, RPC dialect is
   different. No sensor exists yet â€” `has_sensor=False`.
5. **endpoints.yaml uses `env_var` references.** No credential appears in any
   tracked file. `.env.local` remains the only place for keys.

### Bugs found and fixed

1. **PyYAML not installed.** `ModuleNotFoundError: No module named 'yaml'`
   when running tests. Fixed by rewriting `test_chains.py` to use regex-based
   YAML parsing (`_read_yaml_field`, `_yaml_has_field`, `_count_providers`)
   instead of `yaml.safe_load`. Zero new dependencies.
2. **YAML comment in parsed value.** `_read_yaml_field` returned
   `"bitcoin_like  # UTXO, NOT account-based"` instead of `"bitcoin_like"`.
   Fixed by stripping inline comments: `if "#" in val: val = val[:val.index("#")].strip()`.

### Verified by execution

| Check | Result |
|---|---|
| `pytest -q` | **1,101 passed, 0 failed** (was 937; 164 new across Steps 3â€“5) |
| `cli doctor` | **14/14 ok**, schema **v7**, exit 0 |
| `cli chains` | **15** chains registered, 13 observable, 13 token-capable |

### Self-critique

- **Adapters carry no runtime behaviour.** They are structured metadata â€” the
  sensor registry and dispatcher still do the actual RPC work. This is correct
  for now (a `UtxoAdapter.fetch_utxos()` with no Bitcoin sensor to back it would
  be dishonest), but it means `adapter.py` adds type safety and documentation,
  not functionality.
- **`has_sensor=False` for Solana and Bitcoin is stated, not enforced.** If
  someone later writes a Solana sensor and forgets to update the adapter, the
  adapter's claim that no sensor exists becomes a lie. No test guards against
  this because the sensor registry is dynamic and chain-sensor mapping is
  convention, not registration.
- **The YAML files are not machine-validated beyond regex.** Without PyYAML in
  the dependency tree, the tests check field presence and basic structure but
  cannot validate full YAML schema. A malformed YAML file that happens to match
  the regexes would pass.

### Next session should start at

1. Run PROMPT 2 (final audit) â€” 7 checks with evidence, plus Section 19
   criteria assessment.
2. Three decisions left on purpose: wire labels to whale skill, attribute
   token transfers, connect exchange flow to a detector.
