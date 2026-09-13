# 026 — Intelligence Engine OS

> An operating system for a **fleet of evidence-grade intelligence agents**.
> A shared brain, an orchestrator, cross-agent correlation, and governance —
> wrapped around agents that each refuse to speak beyond their evidence.

---

## What 026 is

026 hosts, schedules, and correlates a fleet of intelligence agents. Each agent
owns a full vertical pipeline — it observes a source, validates and stores what it
sees, reasons over it, and decides what it can honestly claim. The platform gives
the fleet a kernel, a message bus, a shared memory, governance, and one face.

The point of an OS (instead of standalone scripts) is **combination**: one agent's
sourced finding becomes fuel for another's, under one governance layer that never
lets a claim outrun its evidence.

---

## The one rule everything inherits

> **An agent may not assert what its evidence cannot license.**

This is the whole personality of the system. It shows up everywhere:

- A negative claim ("no anomaly") requires **coverage** — proof the window was actually observed, not merely empty.
- A detector may **alert** only at `VALIDATED` maturity — a *measured* error rate against a labelled window, not a plausible-looking threshold.
- Every conclusion carries a **provenance chain** back to a raw, timestamped, sourced record.
- The platform **moves real money only through a gated execution layer** — OFF by default, unlocked only after paper-trade validation, hard risk limits, and (by default) human approval. Every order traces to the evidence that licensed it; nothing fires silently — enforced by the sentinel's gate plus a live surface scan, not a comment.

026 would rather say *"cannot be determined"* than say something that looks confident and is wrong.

---

## Architecture

026 is a **kernel + fleet + services** design. The kernel and platform services
are shared; each agent brings its own vertical pipeline.

```
                         ┌──────────────────────────────┐
                         │        Dashboard (UI)        │  ← one face, whole fleet
                         └───────────────┬──────────────┘
                                         │
                         ┌───────────────▼──────────────┐
                         │         Orchestrator         │  plan · route · fuse
                         │        (message bus)         │
                         └───┬───────────┬──────────┬───┘
                             │           │          │
          ┌──────────────────▼─┐   ┌─────▼──────┐   │
          │  Agent A01         │   │ Agent A02  │   │   … A03, A04 …
          │  (on-chain intel)  │   │ (news)     │   │
          │                    │   │            │   │
          │  sensors→ingest→   │   │  ingest→   │   │
          │  validate→norm→    │   │  narrative→│   │
          │  store→skills→     │   │  verify→   │   │
          │  intelligence→     │   │  impact→   │   │
          │  decision          │   │  learn     │   │
          └─────────┬──────────┘   └─────┬──────┘   │
                    │                    │          │
        ┌───────────▼────────────────────▼──────────▼───────────┐
        │                     SHARED BRAIN                       │
        │   memory · embeddings · entities · cross-agent RAG     │
        └───────────┬───────────────────────────────┬───────────┘
                    │                               │
        ┌───────────▼──────────┐        ┌───────────▼───────────┐
        │      Sentinel        │        │     Observability     │
        │  policy · trust ·    │        │  traces · metrics ·   │
        │  exec-gate · secrets │        │  cost · health        │
        └──────────────────────┘        └───────────────────────┘
```

**KERNEL** — `config/`, `src/`, `brain/`, `orchestrator/`
Identity, configuration, core runtime, shared memory, the message bus. Everything
above depends downward only; nothing in the kernel imports an agent.

**FLEET** — `agents/`
Each agent (`A01_*`, `A02_*`, …) is a self-contained vertical pipeline: sensors →
ingestion → validation → normalization → store → skills → intelligence → decision.
The platform hosts them; it never reaches inside them.

**SERVICES** — `security/` (sentinel), `observability/`, `dashboard/`, `integrations/`, `tools/`, `plugins/`, `sandbox/`

---

## Directory Map

| Path             | Layer            | Purpose                                                        |
| ---------------- | ---------------- | -------------------------------------------------------------- |
| `config/`        | Kernel           | Settings, model routing, feature flags, secrets seams          |
| `src/`           | Kernel           | Core runtime, lifecycle FSM, the agent base contract           |
| `brain/`         | Kernel           | Shared memory: short/long-term, vector, entity ledger          |
| `orchestrator/`  | Kernel           | Planner, scheduler, message bus, result fusion                 |
| `agents/`        | Fleet            | Numbered agents (`A01_…`, `A02_…`), each a full pipeline        |
| `integrations/`  | Service          | External providers, APIs, MCP servers, connectors              |
| `sources/`       | Governance       | Source registry — the catalog of APIs, datasets, links, MCP, models (what exists) |
| `tools/`         | Service          | Typed tool registry — the actions agents may take              |
| `data/`          | Service          | Tiered store (CACHE → HOT → WARM → LEDGER)                      |
| `security/`      | Service          | Sentinel: policy, trust levels, the execution gate, secrets    |
| `sandbox/`       | Service          | Isolated, policy-gated execution                               |
| `observability/` | Service          | Traces, metrics, cost, health                                  |
| `logs/`          | Service          | Structured runtime logs (gitignored in prod)                   |
| `dashboard/`     | Service          | The fleet UI: chat, traces, coverage, health                   |
| `plugins/`       | Service          | Drop-in capability packs                                       |
| `infra/`         | Ops              | IaC, containers, deploy manifests                              |
| `scripts/`       | Ops              | Bootstrap, maintenance, scheduled tasks                        |
| `requirements/`  | Ops              | Layered dependency manifests                                   |
| `docs/`          | Docs             | The manual, architecture, evidence standard, per-agent specs   |
| `tests/`         | Quality          | Unit, integration, architecture invariants                     |

Every folder and file is catalogued in the living manual: **[`docs/manual/`](docs/manual/README.md)** (a folder — start at its `README.md`).

---

## Documentation & Continuity

Four documents keep the build legible and honest across sessions:

| File                | Role                                                                     |
| ------------------- | ------------------------------------------------------------------------ |
| `docs/manual/`      | **The handbook** (a folder — start at its `README.md`) — every folder, file, security role, and data source. Grows with the project. Hand this to anyone learning 026. |
| `AGENTS.md`         | The contract: how agents are defined, governed, and built                |
| `PROJECT_STATE.md`  | **Living snapshot** — overwritten each session. Where we are *now*        |
| `BUILD_LOG.md`      | **Append-only history** — never overwritten. How we got here             |

Read `docs/manual/` to understand the project. Read `PROJECT_STATE.md` to know
the current state. Read `BUILD_LOG.md` to know why.

---

## Status

**Genesis.** The repository is scaffolded and the documentation system exists.
**No platform code is implemented yet** — see `PROJECT_STATE.md` for the honest
snapshot. This README describes the target, not a shipped system. Nothing here
claims to run until `BUILD_LOG.md` records it running.

---

## Quick Start (target)

```bash
make setup                 # bootstrap venv + deps
cp .env.example .env       # provider keys (all optional → degraded mode)
make doctor                # verify the kernel before trusting it
make dev                   # orchestrator + dashboard
```

Until the kernel lands, `make doctor` is the first thing worth making real.

---

## Design Ethos

1. **Evidence over confidence.** "Cannot be determined" is a valid, respected answer.
2. **Verify by execution, not assumption.** A green suite that proves nothing is a reason to write the missing test.
3. **Honest state.** Docs describe what *is*, tagged from what is *planned*.
4. **Downward-only dependencies.** The kernel never learns about an agent.
5. **No silent side effects.** Every tool call is logged; every log is queryable.
6. **The fleet is only as strong as its weakest agent.** Design each one like it matters.

---

<sub>Built by the operator and Claude — two brains, one evidence standard.</sub>
