# STACK.md — 026 Language & Technology Stack

> The **chosen** language/tech stack for 026 and what each language does.
> This is the target; code lands per `BUILD_LOG.md`. Present-tense "what *is*"
> lives in `PROJECT_STATE.md`.

**Guiding principle — minimize languages.** Two primary languages do ~95% of the
work: **Python** (the thinking) and **TypeScript** (the showing). One database
engine (PostgreSQL, with extensions) plus Redis. Everything else is config, ops,
or a *future, measured* exception. Fewer moving parts is how the evidence-grade
discipline actually holds for a small team.

---

## Primary languages

### 1. Python (3.11+) — the entire backend brain & fleet
Async-first, `pydantic` v2. This is where all the intelligence lives. Every job:

| Area | What Python does |
|---|---|
| **Ingestion** | Pull data from world-wide sources — APIs, exchanges (read-only), wikis, websites, global datasets |
| **MCP connectors** | Real-time data from multiple MCP servers, surfaced through the tool registry |
| **Real-time feeds** | WebSocket / streaming ingestion via `asyncio` (`websockets`, `httpx`) — no separate Node runtime needed |
| **Validation & provenance** | Validate, normalize, tag every raw record with its source + timestamp |
| **Storage orchestration** | Write to Postgres / TimescaleDB / Redis; manage the tiered store |
| **ML / prediction** | Market-move & direction prediction models (train, evaluate, serve) |
| **Analysis engine** | Real-time signals, indicators, cross-source correlation |
| **Backtesting** | Test predictions/strategies against historical data — measure accuracy |
| **Paper trading** | Live simulation, no real money — prove the system before funding it |
| **Strategy logic** | "Take this trade or not," expected profit/loss reasoning |
| **Agent fleet** | Each agent = a full vertical pipeline (sensors → … → decision) |
| **Orchestrator + bus** | Plan, route, fuse; the message bus between agents |
| **Risk engine** | Position limits, daily loss caps, kill-switch, exposure checks |
| **Execution client** | Broker/exchange order placement — **DISABLED by default, gated** (see below) |
| **Backend API** | Serves the dashboard (HTTP/WebSocket) |

### 2. TypeScript + JavaScript (React / Next.js) — the dashboard / UI
The one face for the whole fleet. Every job:

- Charts & real-time market views
- Prediction / signal display, alerts & notifications
- Backtest & paper-trade result visualizations
- **Trade approval controls** — the human-in-the-loop gate before real-money orders
- Risk / health / coverage / cost dashboards
- Next.js **API routes** = thin BFF (backend-for-frontend) between browser and the Python core

### 3. SQL — data queries
- PostgreSQL + TimescaleDB queries (time-series market/on-chain data)
- Schema & migrations, analytical queries
- `pgvector` similarity search for the shared brain (RAG)

---

## Supporting / ops languages

### 4. Bash + PowerShell — scripts & automation
- Bootstrap, setup, maintenance (`scripts/`)
- `Makefile` targets (`make doctor`, `make dev`)
- Scheduled tasks
- (Windows dev → PowerShell; POSIX/CI → Bash)

### 5. Config & markup — YAML / TOML / JSON / HTML / CSS / Markdown
- **YAML** — CI workflows (`.github/`), config, MCP server configs
- **TOML** — `pyproject.toml` (Python project, deps, tooling)
- **JSON** — manifests, `.vscode/`, assorted config
- **HTML / CSS** — dashboard markup & styling (with React)
- **Markdown** — all docs (already in use across the repo)

### 6. Dockerfile — containers (`infra/`)
- Container images, deploy manifests

### 7. Rust (reserved — only if a *measured* hot path needs it) — via PyO3
- **Not adopted now.** Only if profiling proves a specific Python path too slow.
- Fits the ethos: *verify by execution, not assumption.* YAGNI until evidence says otherwise.

---

## Data layer (not languages, but part of the stack)

| Tech | Role |
|---|---|
| **PostgreSQL** | Relational ledger — the source of truth |
| **TimescaleDB** (Postgres extension) | Time-series market / on-chain data |
| **pgvector** (Postgres extension) | Embeddings / RAG for the shared brain — one engine, no separate vector DB |
| **Redis** | Cache + queue / message bus |

---

## Execution safety (because real money is a goal)

Real-money execution is a target for 026, but it ships **safe by default**:

1. **Execution is DISABLED by default.** It is off until explicitly enabled.
2. **Gates before any real-money order:**
   paper-trade validation passed → hard risk limits set (max position, daily loss
   cap, kill-switch) → **human approval** (default). Full auto-execution is an
   opt-in per stage, never the default.
3. This matches the operator's staged plan: **paper first, real money only after
   it passes.**

> ✅ **Charter (decided 2026-09-05):** the old "never trades" law was evolved to
> *"trades only through a gated, risk-limited, paper-validated, human-approvable
> execution layer that is OFF by default"* — recorded in `BUILD_LOG.md`
> (2026-09-05). Execution code still does not exist; only the charter now tells
> the truth about the target.

---

## The one-line summary

**Python thinks. TypeScript shows. Postgres remembers. Redis speeds. Rust waits
until the profiler calls it.**
