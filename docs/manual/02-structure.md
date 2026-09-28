# 02 · Structure

[← Overview](01-overview.md) · [Index](README.md) · *Next: Architecture (planned)*

> Folders only, for now. Each line says what that part of the project holds.
> File-by-file descriptions get added underneath each folder as the project is built.

---

## Top-level folders

| Folder | What it holds |
|--------|---------------|
| `agents/` | The fleet — one folder per agent (`A001_…` through `A06_…` are defined in [`AGENTS.md`](../../AGENTS.md) §3; higher numbers are reserved, not yet assigned), plus a `_template/` to copy from. Each agent is a self-contained pipeline. |
| `bootstrap/` | **Added 2026-09-07** — the composition root. Wires the fleet's read-only bus adapters into the orchestrator bus (`wire.build_bus()`). The only layer that imports *both* the kernel and the agents; ADR-0001 keeps the kernel itself agent-free, so this wiring lives here. |
| `brain/` | Shared memory: embeddings, knowledge graph, RAG, reasoning, LLM access, and shared prompts. |
| `config/` | All configuration: agent registry, environments (dev/prod), feature flags, model routing. |
| `dashboard/` | The web UI — frontend, backend, and assets. The one face for the whole fleet. |
| `data/` | Where data lives: raw, processed, cache, vector store, and backups. |
| `docs/` | All documentation — including this manual, architecture, ADRs, API docs, runbooks. |
| `infra/` | Deployment: Docker, Kubernetes, Terraform. |
| `integrations/` | Connections to the outside world: APIs, exchanges, MCP servers, messaging, webhooks. |
| `logs/` | Runtime logs, split into agent logs, system logs, and the audit trail. |
| `observability/` | Monitoring: metrics, traces, alerts, dashboards, and observability logs. |
| `orchestrator/` | The manager: core runtime, event bus, router, scheduler, workflows, and its memory. |
| `plugins/` | Drop-in capability packs — `available/` (installed) and `enabled/` (active). |
| `requirements/` | Python dependency lists, layered: base, dev, prod. |
| `sandbox/` | Isolated, guarded execution — containers and exec environments. |
| `scripts/` | Automation scripts: setup, dev, deploy, maintenance. |
| `security/` | The guard rails: policies, auth, secrets handling, and the security audit. |
| `sources/` | The source registry — the catalog of what data 026 draws on: APIs, datasets, links, MCP, models, infra. See [05 · Data sources](05-data-sources.md). |
| `src/` | Core platform source: api, core, models, schemas, services, pipelines, utils. |
| `tests/` | All tests: unit, integration, e2e, load, and shared fixtures. |
| `tools/` | The typed tool registry — the actions agents may take (`builtin/`, `custom/`, `registry/`). |

---

## Sub-folders (short notes)

### `agents/`
**Two agents landed 2026-09-06** — migrated in from the CIE-OS project (source kept
intact at `F:\CIE-OS`), copied as-is and then declared as fleet members:

| Folder | Agent | Manifest |
|--------|-------|----------|
| `A001_Blockchain_Intelligence/` | A001 · Blockchain Intelligence — on-chain whales/flows/anomaly, read-only (`NO_TRADE_EXECUTION`) | `agents/A001_Blockchain_Intelligence/agent.yaml` |
| `A002_News_Intelligence/` | A002 · News Intelligence — fake-news/rumor/market-impact, graded verdicts | `agents/A002_News_Intelligence/agent.yaml` |

Each agent is a self-contained vertical pipeline (per [`AGENTS.md`](../../AGENTS.md) §1)
and is registered in `config/agents/registry.yaml`. Their internal structure is
unchanged from CIE-OS; wiring to the shared kernel (bus / brain / sentinel) and
runtime verification are still open (see `BUILD_LOG.md` 2026-09-06 · CIE-OS migration).
A `_template/` to copy from is not yet extracted. The full contract lives in
[`AGENTS.md`](../../AGENTS.md).

### `brain/`
| Folder | What it holds |
|--------|---------------|
| `embeddings` | Vector embeddings of stored knowledge. |
| `knowledge_graph` | Entities and the relationships between them. |
| `rag` | Retrieval-augmented generation over the brain. |
| `reasoning` | Shared reasoning routines. |
| `llm` | LLM client access for the brain. |
| `prompts` | Shared prompts (e.g. the system prompt). |

**Built 2026-09-07 (slice 1):** `brain/store.py` (`Brain` — namespaced memory on stdlib
sqlite3; **versioned** writes, **logged** reads, nothing silent) and `brain/access.py`
(`AgentBrainView` — read/write scoped to the agent manifest's `memory.reads`/`writes`,
with `projects.*` wildcards). The subfolders above (embeddings/RAG/knowledge-graph/…)
are still empty — later slices.

### `config/`
| Folder | What it holds |
|--------|---------------|
| `agents` | The agent registry — which agents exist and are enabled. |
| `environments` | Per-environment settings (dev, prod). |
| `feature_flags` | On/off switches for features. |
| `models` | Model routing — which model each tier uses. |
| `sources` | Machine-config for source access (endpoints + key-NAMES code reads; never secrets). **Built 2026-09-07:** `sources/a001.yaml` — A001's sources by role, each referencing a `sources/` stable ID; free-first priority tiers. A001's live RPC resolution still lives in the agent's own `config/rpc/`. |

### `dashboard/`
| Folder | What it holds |
|--------|---------------|
| `frontend` | The operator console — Next.js 16 (App Router) + Tailwind v4 + react-three-fiber + motion. `app/` = pages (`/` = the **026** home, `/narratives` = A002 news by topic × verdict, `/agents?id=…` = every agent's manifest contract, `/sentinel` = scan matrix + gate simulator; route handlers `sentinel/scan` and `sentinel/gate` run the sentinel's own Python read-only; `/trace` = bus round composer + trace log, route handler `trace/run`; `/orchestrator` = command console + build status + module anatomy; `/brain` = memory-contract map + access checker, route handler `brain/check`; `/onchain` = A001's chain, coverage, flows, detectors; `/desk` = T01 trading desk via the `desk/t01` proxy route — T01 must be running on 127.0.0.1:8000), `components/` = UI (Hero + WebGL `HeroScene`, sticky-scroll `Pipeline`, CSS-3D `Voxel` icons, `NarrativeCity` 3D towers, `NarrativesView` filters/cards, `AgentModel` mouse-controlled 3D agent, `AgentsView` roster + contract, `SentinelDome` 3D gate, `SentinelView`, `Spin` = shared drag/zoom controls), `lib/sentinel.ts` = bridge to `security/sentinel` (scan CLI + `check_action`, cached, one scan at a time), `lib/fleet.ts` = server-only loader that reads `config/agents/registry.yaml` + every `agents/*/agent.yaml` per request (no hand-typed fleet numbers), `lib/narratives.ts` = read-only `node:sqlite` view of A002's `a002.db`, `lib/verdict.ts` = verdict/topic/tier vocabulary + the validated diverging palette. Run: `npm --prefix dashboard/frontend run dev` → http://localhost:3000. |
| `backend` | Python the dashboard calls, read-only: `trace_round.py` runs one round of messages through the real bus (`bootstrap.build_bus` + A015 kernel adapter) for `/trace`; `brain_check.py` asks `brain.AgentBrainView` whether an agent may read/write a namespace, on a throwaway in-memory brain, for `/brain`; `onchain_snapshot.py` returns A001's own health / coverage / flows / detectors / chains / metrics for `/onchain`. |
| `assets` | Static assets. |

### `data/`
| Folder | What it holds |
|--------|---------------|
| `raw` | Untouched captured data. |
| `processed` | Cleaned, normalized data. |
| `cache` | Short-lived cached responses. |
| `vector_store` | The vector database files. |
| `backups` | Database backups. |

### `docs/`
| Folder | What it holds |
|--------|---------------|
| `manual` | **This manual.** |
| `architecture` | Architecture design docs. |
| `adr` | Architecture Decision Records — why choices were made. **Now populated:** ADR-0001–0004 + index (2026-09-06). |
| `api` | API reference. |
| `agents` | Per-agent design specs. |
| `runbooks` | Operational how-tos. |

Plus top-level files in `docs/`: `STACK.md` (the chosen tech stack) and `SOURCES.md`
(a pointer to the `sources/` registry).

### `infra/`
| Folder | What it holds |
|--------|---------------|
| `docker` | Dockerfile + compose. |
| `k8s` | Kubernetes manifests. |
| `terraform` | Infrastructure-as-code. |

### `integrations/`
| Folder | What it holds |
|--------|---------------|
| `apis` | Third-party API clients. |
| `exchanges` | Exchange connectors. |
| `mcp_servers` | MCP server integrations. |
| `messaging` | Chat / messaging channels. |
| `webhooks` | Inbound/outbound webhooks. |

### `logs/`
| Folder | What it holds |
|--------|---------------|
| `agents` | Per-agent logs. |
| `system` | Platform/system logs. |
| `audit` | The audit trail — who/what did what. |

### `observability/`
| Folder | What it holds |
|--------|---------------|
| `metrics` | Metrics definitions/collection. |
| `traces` | Distributed traces. |
| `alerts` | Alerting rules. |
| `dashboards` | Monitoring dashboards. |
| `logs` | Observability log config. |

### `orchestrator/`
| Folder | What it holds |
|--------|---------------|
| `core` | The orchestrator runtime. |
| `event_bus` | **Built 2026-09-07 (slice 1)** — the message bus: `Message`/`Budget`/`Response`, an append-only replayable `TraceLog`, and `MessageBus` (register a handler, `send` a message). Every send is traced, gated (via `security.sentinel.gate`), and budgeted; handlers are thin adapters over an agent's entry points (stub/echo for now — real A001/A002 adapters are the next slice). |
| `router` | Task routing to agents (folded into `event_bus.send` for slice 1). |
| `scheduler` | Scheduled/periodic work. |
| `workflows` | Multi-step agent workflows. |
| `memory` | The orchestrator's own working memory. |

### `plugins/`
| Folder | What it holds |
|--------|---------------|
| `available` | Installed but not necessarily active plugins. |
| `enabled` | Currently active plugins. |

### `sandbox/`
| Folder | What it holds |
|--------|---------------|
| `containers` | Container-based isolation. |
| `exec` | Guarded execution environments. |

### `scripts/`
| Folder | What it holds |
|--------|---------------|
| `setup` | Bootstrap / install. |
| `dev` | Developer helpers. |
| `deploy` | Deployment scripts. |
| `maintenance` | Upkeep / cleanup. |

### `security/`
| Folder | What it holds |
|--------|---------------|
| `sentinel` | **Built 2026-09-07** — (a) the conformance enforcer (slice 1): reads the fleet and proves each agent's real code matches its manifest (trust, execution-gate, secrets, registry, deviation-only) — run `python -m security.sentinel scan`; (b) `gate.py`, the runtime action gate (`check_action` → ALLOW/HOLD/DENY, deny-by-default at the execution boundary) that the message bus consults. Design: [`docs/architecture/sentinel-conformance-design.md`](../architecture/sentinel-conformance-design.md). |
| `policies` | The rules agents must obey — now holds `sentinel.yaml` (policy-as-data for the checks above). |
| `auth` | Authentication / access control. |
| `secrets` | Secrets handling (never stored in tracked source). |
| `audit` | Security audit records. |

*(Full security model → [04 · Security](04-security.md). The sentinel is read-only
toward agents and imports no agent package — downward-only imports hold.)*

### `sources/`
Files, not sub-folders — the source catalog, split by access type:

| File | What it holds |
|------|---------------|
| `README.md` | Index, legend, rules, research findings. |
| `apis.md` | Live / queryable APIs. |
| `datasets.md` | Bulk / downloadable datasets. |
| `links.md` | Inbox for new URLs + portals/registries. |
| `mcp.md` | MCP servers. |
| `models.md` | ML models (not data feeds). |
| `infra.md` | Tooling (proxy, SDKs) — not feeds. |

*(Full data-source model → [05 · Data sources](05-data-sources.md).)*

### `src/`
| Folder | What it holds |
|--------|---------------|
| `core` | Core runtime and lifecycle. |
| `api` | Platform API (`routes/`, `middleware/`). |
| `models` | Data models. |
| `schemas` | Validation schemas. |
| `services` | Shared services. |
| `pipelines` | Data pipelines. |
| `utils` | Helpers. |

### `tests/`
| Folder | What it holds |
|--------|---------------|
| `unit` | Unit tests. |
| `integration` | Integration tests. |
| `e2e` | End-to-end tests. |
| `load` | Load/performance tests. |
| `fixtures` | Shared test data. |

**Built 2026-09-07:** `tests/test_architecture.py` — the downward-only-imports law
(§10). Package-local suites live with their code (`security/sentinel/tests/`,
`orchestrator/event_bus/tests/`, `bootstrap/tests/`, `brain/tests/`); run them all with
`python -m pytest security orchestrator bootstrap brain tests -q` (55 passing).

### `tools/`
| Folder | What it holds |
|--------|---------------|
| `builtin` | Built-in tools shipped with 026. |
| `custom` | Project-specific tools. |
| `registry` | The tool registry — typed definitions of every action. |

---

## Files

*File-by-file descriptions are added here the same session a file is created, moved,
or given a new role (per `AGENTS.md` §9.7). Folders not yet listed hold no built
files.*

### `docs/manual/`
| File | Role |
|------|------|
| `README.md` | Manual index — section list + status legend. |
| `01-overview.md` | What 026 is, in plain language. |
| `02-structure.md` | This file — every folder, and files as they land. |
| `04-security.md` | Trust levels, the sentinel, the execution gate, secrets. |
| `05-data-sources.md` | How the `sources/` registry governs data. |
| `07-glossary.md` | Every 026 term defined in one place *(new 2026-09-06)*. |

### `docs/adr/`
| File | Role |
|------|------|
| `README.md` | ADR index + template + how to write one *(new 2026-09-06)*. |
| `ADR-0001-os-for-a-fleet.md` | 026 as an OS for a fleet, not a single agent. |
| `ADR-0002-gated-execution-charter.md` | Gated execution replaces the "never trades" law. |
| `ADR-0003-minimal-stack.md` | Python + TypeScript + Postgres, deliberately minimal. |
| `ADR-0004-sources-by-access-type-and-stable-ids.md` | Registry organized by access-type, stable IDs. |

### `sources/`
| File | Role |
|------|------|
| `README.md` | Index, rules, **canonical row schema**, and the **master ID index** *(index added 2026-09-06)*. |
| `apis.md` · `datasets.md` · `mcp.md` · `models.md` · `infra.md` · `links.md` | Per-access-type catalogs; schema-aligned 2026-09-06 (+ 4 new sources S048–S051). **2026-09-07: +67 blockchain sources for A001** (S052–S118) from the operator's notes → registry now **109 rows, highest S118** (all `⬜`/`TBV`, not yet web-verified). |

---

[← Overview](01-overview.md) · [Index](README.md) · *Next: Architecture (planned)*
