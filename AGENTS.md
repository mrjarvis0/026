# AGENTS.md â€” 026 Fleet Contract & Build Discipline

> This file governs every agent in 026 and every session that builds one.
> It is the single source of truth for agent identity, capability, governance,
> and the working method. If code and this file disagree, one of them is wrong â€”
> reconcile explicitly, in `BUILD_LOG.md`, never silently.

---

## 0. The laws

Every agent and every build session obeys these. They are not style â€” they are the
reason the system can be trusted:

- **Evidence standard** â€” an agent asserts only what its evidence licenses.
- **Maturity gates** â€” a detector may alert only when its error rate is *measured*.
- **Coverage before absence** â€” a negative claim requires proof the window was observed.
- **Provenance** â€” every conclusion traces to a raw, sourced, timestamped record.
- **Gated execution** â€” real-money trading is OFF by default and fires only through the sentinel's gate: paper-validated, risk-limited, human-approvable. No order is silent; each traces to its licensing evidence.
- **Downward-only imports** â€” layer N imports only from layers `< N`, mechanically checked.

Everything below is how these laws apply to a *fleet* instead of one agent.

---

## 1. What an agent is

An agent is a bounded, evidence-grade actor with a **vertical pipeline** and a
**declared contract**. It is not a chat wrapper. Each agent lives at
`agents/<AXX_Name>/` and owns its full stack:

```
sensors â†’ ingestion â†’ validation â†’ normalization â†’ store â†’ skills â†’ intelligence â†’ decision
```

The platform (kernel + services) surrounds this pipeline; it never reaches inside it.

---

## 2. Agent manifest

Every agent declares itself in `agents/<AXX>/agent.yaml`. The manifest is the
contract the orchestrator, sentinel, and brain read.

```yaml
id: A03
name: "DeFi Flow Intelligence"
version: 0.0.0
status: scaffold            # scaffold | partial | substantial | complete
role: >
  Tracks liquidity movement across DeFi protocols and reports flow anomalies
  with sourced provenance. Reports deviation only â€” never advice, never a trade.

model:
  tier: reasoning-heavy      # asks for a tier; the router picks the model
  fallback: balanced
  temperature: 0.2

memory:                      # brain namespaces this agent may touch
  reads:  [global, entities, defi, projects.*]
  writes: [defi, projects.*]

tools:                       # from the typed registry in tools/
  - rpc.call
  - brain.query
  - brain.write
  - store.read

trust:
  level: 2                   # 0 sandbox Â· 1 read-only Â· 2 write-scoped Â· 3 platform
  requires_approval:
    - external.post
    - store.delete

invariants:
  execution_enabled: false   # OFF by default; real-money orders require the sentinel gate
  reports_deviation_only: true

evidence:
  detectors:
    - id: DET-DEFI-FLOW-01
      maturity: implemented  # implemented â†’ may NOT alert until validated
      ceiling: 0.60
  coverage_required_for_absence: true

charter: |
  - Never fabricate a source. Cite every claim.
  - "Cannot be determined" outranks a guess.
  - Deviation, not judgement. Never bullish/bearish/manipulation.
  - Stop and ask before any action outside the declared tools.
```

An agent with no `evidence.detectors` and no tests **cannot leave trust level 1.**

---

## 3. The fleet

| ID    | Agent                     | Status    | Domain                            |
| ----- | ------------------------- | --------- | --------------------------------- |
| `A01` | Blockchain Intelligence   | substantial | On-chain: whales, flows, anomaly  |
| `A02` | News Intelligence         | substantial | Fake-news / rumor / market impact |
| `A03` | *(reserved)* DeFi Flow    | planned   | Cross-protocol liquidity          |
| `A04` | *(reserved)* Sentiment    | planned   | Social/market sentiment fusion    |
| `A05` | Market Data Intelligence  | planned   | Market OHLCV / quotes / orderbook across crypto, equities, FX |
| `A06` | Macro / Econ Intelligence | planned   | Macro & economic series (rates, indicators, filings) |

`A05` and `A06` were promoted from proposals to `planned` fleet members on
2026-09-06: roughly half the source registry (`sources/`) is assigned to them, so
they are real (if unbuilt) consumers, not placeholders. Recorded in `BUILD_LOG.md`
(2026-09-06) and `docs/adr/ADR-0004`.

`A01` and `A02` moved from `planned` to `substantial` on 2026-09-06: their full
vertical pipelines were **migrated in from the CIE-OS project** (source kept intact
at `F:\CIE-OS`), then declared as fleet members — each now carries an
`agents/<dir>/agent.yaml` manifest and is registered in `config/agents/registry.yaml`.
`substantial` reflects **code + tests present in source**; runtime verification and
kernel wiring (bus / brain / sentinel) are still open — tracked in `BUILD_LOG.md`
(2026-09-06 · CIE-OS migration) as sub-projects SP-4 (wiring) and SP-5 (verify).

Platform actors (not domain agents â€” they run the fleet):

| Actor          | Home            | Trust | Job                                              |
| -------------- | --------------- | :---: | ------------------------------------------------ |
| `orchestrator` | `orchestrator/` |   3   | Plans work, routes tasks, fuses agent results    |
| `sentinel`     | `security/`     |   3   | Enforces trust, invariants, secrets, exec-gate   |
| `librarian`    | `brain/`        |   2   | Curates the shared brain, dedups entities        |
| `operator-io`  | `dashboard/`    |   3   | The human interface: chat, approvals, traces     |

---

## 4. Cross-agent correlation â€” 026's core power

The reason 026 is an OS and not a folder of scripts. Single agents answer single
questions. The **brain + orchestrator** let answers combine:

```
A02 (news):  "unverified exploit rumor on protocol X, coordination score 78/100"
A01 (chain): "anomalous outflow from X's treasury, DET-EXPLOIT-02, z=7.1"
             â”‚
             â–¼
orchestrator fuses â†’ a correlated finding, each half carrying its OWN provenance
             â”‚
sentinel gates â†’ no order without the execution gate, no alert above measured maturity
```

**Correlation rules:**

1. **Fusion never averages confidence.** The combined confidence is the *weakest* input's, not the mean â€” a strong rumor beside weak on-chain data is weak-on-chain-data with a rumor attached.
2. **Conflicts are recorded, not resolved.** If A01 and A02 disagree, both survive in the finding. Overwriting one would hide a real disagreement behind a plausible value.
3. **Provenance stays split.** A fused finding carries two independent chains, never a merged one.
4. **A correlation is a hypothesis, not a verdict** until each half independently clears its own maturity gate.

---

## 5. Communication protocol

Agents never call each other. Everything passes through the orchestrator's bus.

```json
{
  "id": "msg_01J...",
  "from": "orchestrator",
  "to": "A01",
  "type": "task.assign",
  "payload": { "question": "...", "window": {...} },
  "trace_id": "trc_...",
  "parent_id": "msg_...",
  "budget": { "calls": 500, "usd": 0.25 }
}
```

Every message is logged, traced, replayable, and **budgeted**. An agent that
exhausts its call/cost budget degrades to coarser output â€” it does not go dark
silently.

---

## 6. Trust & governance

| Level | Meaning                          | Example                       |
| :---: | -------------------------------- | ----------------------------- |
|   0   | Sandboxed â€” reasoning only       | New/untrusted plugin          |
|   1   | Read-only â€” no side effects      | A fresh agent, pre-evals      |
|   2   | Scoped writes â€” declared surface | A01, A02                      |
|   3   | Platform â€” human-adjacent        | orchestrator, sentinel        |

**Sentinel** sits over every action. Anything above an agent's declared trust â€”
or touching a `requires_approval` tool, or the execution boundary â€” is **held for
the operator in the dashboard.** The sentinel's checks pair each named invariant
with a **live surface scan**, because a flag reporting "ok" beside an exposed
write path is exactly the reassuring lie the check exists to prevent.

The security model â€” where policy, secrets, trust, and the execution boundary live
as real files â€” is specified in `docs/manual/` â†’ *04 Â· Security* and
implemented under `security/`.

---

## 7. Memory contract (the shared brain)

The brain is namespaced. Reads are logged; writes are versioned. Nothing is silent.

```
brain/
â”œâ”€â”€ global/          # everyone reads, librarian writes
â”œâ”€â”€ entities/        # the cross-agent ledger â€” addresses, tickers, orgs
â”œâ”€â”€ <agent>/         # e.g. defi/, news/ â€” that agent writes, others read
â”œâ”€â”€ projects/<id>/   # scoped per investigation
â””â”€â”€ private/<agent>/ # an agent's own scratchpad, unshared
```

Rule: **write like others will read**, because in 026 they will. An entity A01
labels is an entity A02 can cite â€” that is the correlation layer's fuel.

---

## 8. Model routing

Agents ask for a *tier*; `config/models.yaml` picks the model. Fallbacks, cost
caps, and rate limits live there, not in agent code.

```yaml
tiers:
  reasoning-heavy: [claude-opus-5, claude-opus-4-8]
  balanced:        [claude-sonnet-5]
  fast:            [claude-haiku-4-5]
  local:           [ollama/llama-3.1-70b]
```

Default to the most capable Claude model for reasoning-heavy work; drop tiers
only where latency or budget demands it.

---

## 9. Build discipline (how a session works)

Every build session follows this method. It is the reason the codebase can be
trusted.

**Before writing code:**
1. Read `PROJECT_STATE.md` (where we are) and the tail of `BUILD_LOG.md` (why).
2. Audit before building â€” the thing you mean to add may already exist. Grep, don't assume.
3. State the session goal.

**While building:**
4. **Reuse by default.** Replace only on failing tests, a correctness-risking invariant violation, or a structural block.
5. Tag every touched file: `BUILD-NEW`, `MINOR-FIX`, `REFACTOR`, or `data correction`.
6. Verify by **execution**. A test that would pass on the broken code proves nothing.

**After building:**
7. Update `PROJECT_STATE.md` (overwrite), append to `BUILD_LOG.md` (never overwrite), and update `docs/manual/` for any file created, moved, or given a new role.
8. Write the **self-critique**: what is *fragile*, *assumed*, *untested*.
9. Record **open questions for the operator** â€” especially anything at a trust, trade, or secrets boundary.
10. Say where the next session should start.

**Escalate, don't decide unilaterally**, at three boundaries:
- weak-justification replacement of working code,
- the execution-gate / signing / funds boundary,
- secrets and credentials.

---

## 10. Evaluation gate

Every agent ships with:

- **Behavior tests** â€” golden inputs â†’ the *shape* of correct output.
- **Regression tests** â€” each named for the defect it guards.
- **Architecture tests** â€” downward-only imports, no cycles, no ungated trade path.

A detector reaches `VALIDATED` (may alert) **only** after a backtest against a
labelled window puts it there â€” measured error rate, calibration checked,
overconfidence flagged. Until then it sits at `IMPLEMENTED` and stays muted, no
matter how good the code looks.

---

## 11. Rules of the fleet

1. An agent that cannot explain its action must not take it.
2. Every tool call is logged. Every log is queryable.
3. No agent bypasses the sentinel.
4. Memory is a shared library, not a private diary â€” write like others will read.
5. Fusion never averages away a disagreement.
6. The platform trades only through the sentinel's gate â€” OFF by default, never silently.
7. When uncertain, ask the operator. When wrong, say so â€” in `BUILD_LOG.md`.

---

## 12. Roadmap for the fleet

- [ ] Kernel: config â†’ core runtime â†’ shared brain â†’ message bus (the first real `make doctor`)
- [ ] A01 and A02 built behind the kernel socket, tests green
- [ ] Orchestrator: plan â†’ route â†’ fuse, with budgets
- [ ] Cross-agent correlation layer + the entity ledger
- [ ] Sentinel: trust enforcement + live execution-gate surface scan (no order bypasses the gate)
- [ ] Dashboard: chat, traces, coverage, cost, health across the fleet
- [ ] A03 / A04 / A05 / A06 as later agents once the pattern is proven

---

<sub>The fleet is only as strong as its weakest agent â€” and its weakest claim.
Design each one like it matters, because a wrong confident answer is worse than none.</sub>

<!-- ============================================================ -->
<!-- MERGED FROM CIE-OS: F:\CIE-OS\AGENTS.md on 2026-09-06 -->
<!-- 026's original content is ABOVE. CIE-OS original also preserved at integrations\CIE-OS\ -->
<!-- ============================================================ -->

# CIE-OS / A01 Blockchain Intelligence Agent â€” Agent Instructions

## Project Overview
**A01** is a blockchain intelligence agent with a strict **13-layer architecture** (Identity â†’ Interfaces). Currently ~30% implemented â€” configuration, memory, tools/adapters, and planning are substantial; intelligence engines, skills, data pipeline, and API server are mostly scaffolded/empty.

**Root:** `F:\CIE-OS (crypto intelligence engine-opreting system\`
**Agent code:** `agents/A01_Blockchain_Intelligence/`

---

## Key Commands

### Test (no pytest config â€” run modules directly)
```bash
# Adapter tests (root)
python tests/test_adapters.py

# Planning engine (352 assertions, complete suite)
python agents/A01_Blockchain_Intelligence/planning/tests/test_core.py
python agents/A01_Blockchain_Intelligence/planning/tests/test_goals.py
python agents/A01_Blockchain_Intelligence/planning/tests/test_tasks.py
python agents/A01_Blockchain_Intelligence/planning/tests/test_routing.py
python agents/A01_Blockchain_Intelligence/planning/tests/test_execution.py
python agents/A01_Blockchain_Intelligence/planning/tests/test_reasoning.py
python agents/A01_Blockchain_Intelligence/planning/tests/test_monitoring.py
python agents/A01_Blockchain_Intelligence/planning/tests/test_utils.py
python agents/A01_Blockchain_Intelligence/planning/tests/test_schemas.py

# Blockchain transport tests
python agents/A01_Blockchain_Intelligence/blockchain/tests/test_transport.py
python agents/A01_Blockchain_Intelligence/blockchain/tests/test_providers.py
python agents/A01_Blockchain_Intelligence/blockchain/tests/test_reorg.py

# CLI (working)
python -m agents.A01_Blockchain_Intelligence.cli doctor
python -m agents/A01_Blockchain_Intelligence.cli investigate --address 0x123...
python -m agents/A01_Blockchain_Intelligence.cli detectors
```

### No build/lint/typecheck configured
- No `pyproject.toml`, `ruff`, `mypy`, `black`, `pytest.ini`
- Dependencies in `requirements.txt` (Pydantic v2, aiosqlite, asyncpg, redis)

---

## Architecture (Must-Know)

### 13-Layer Dependency Order (enforced)
```
Identity â†’ Configuration â†’ Core â†’ Memory â†’ Sensors â†’ Ingestion â†’ Validation
â†’ Normalization â†’ Database â†’ Skills â†’ Intelligence â†’ Decision â†’ Interfaces
```
**Rule:** Code in layer N may only import from layers < N. Violations break architecture.

### Package Layout (502 files, ~93k lines)
| Package | Status | Notes |
|---------|--------|-------|
| `config/` | âœ… Complete | Pydantic v2 settings, 9-chain RPC registry, feature flags |
| `core/` | âš ï¸ Partial | `agent.py`=2,338 lines (needs split), duplicate `AgentRuntime` class |
| `memory/` | âœ… Substantial | Short/long-term, vector (Chroma), SQLite/PostgreSQL/Redis backends |
| `tools/` | âœ… Substantial | 155 files: REST, RPC, WS, MCP, gRPC, CLI, Docker adapters â€” all tested |
| `planning/` | âœ… Complete | Goals, tasks, routing, execution, reasoning â€” full test coverage |
| `intelligence/` | ðŸŸ¦ Scaffold | 146 files, 69 lines/file avg â€” only 2 analyzers (whale, dormant) |
| `skills/` | âŒ Empty | 18 skill dirs created, zero implementation |
| `sensors/`, `ingestion/`, `validation/`, `normalization/`, `database/` | âŒ Empty | No data pipeline yet |
| `blockchain/` | ðŸŸ¦ Scaffold | Full domain structure, minimal implementation |
| `api/`, `cli/`, `monitoring/`, `security/`, `evaluation/`, `reasoning/`, `reporting/`, `knowledge/`, `prompts/`, `workflows/` | âŒ Empty | Delete duplicate dirs at `A01_Blockchain_Intelligence/{api,cli,monitoring,security,blockchain}` |

### Entry Points
- **CLI:** `agents/A01_Blockchain_Intelligence/cli/main.py` â†’ `investigate`, `detectors`, `doctor`
- **No API server** â€” `api/` is empty
- **Runtime:** `core/runtime.py` (AgentRuntime), `core/agent.py` (BaseAgent), `core/lifecycle.py` (FSM)

---

## What's Done vs Missing

### âœ… Working
- Configuration (env-driven, secret-safe, multi-env)
- RPC management (9 chains, fallback, health, rate limiting)
- Memory system (multi-backend, vector search)
- All adapter transports (tested)
- Planning engine (complete + tested)
- CLI commands

### âŒ Critical Gaps (block "runnable agent")
1. **No data pipeline** â€” sensors â†’ ingestion â†’ validation â†’ normalization â†’ database all empty
2. **No skills implemented** â€” 18 dirs, zero code
3. **Intelligence engines scaffolded** â€” only behavior/anomaly/risk engines have partial code; 2 analyzers total
4. **No API server** â€” cannot serve requests
5. **No evaluation framework** â€” cannot validate detector maturity
6. **Core structural debt** â€” `agent.py` too large, duplicate `AgentRuntime`

---

## Development Workflow (Per Architecture Docs)

Follow **vertical slice** build order (`agents/A01_Blockchain_Intelligence/README.md`):
1. âœ… Identity â†’ Config â†’ Knowledge â†’ Core (mostly done)
2. ðŸ”„ **ONE sensor** â†’ ingestion (dedup + reorg handling) â†’ normalization â†’ database
3. **ONE skill** â†’ full pipeline validation
4. Expand to remaining chains/skills/intelligence engines

### Key Files to Reference
- Architecture: `agents/A01_Blockchain_Intelligence/docs/architecture/layered-architecture.md`
- Data flow: `agents/A01_Blockchain_Intelligence/docs/architecture/data-flow.md`
- Component specs: each subpackage has `README.md` with design spec
- Intelligence: `agents/A01_Blockchain_Intelligence/docs/intelligence/evidence-standard.md`, `detection-catalog.md`

---

## Gotchas

- **No CI/CD, no lint, no typecheck** â€” verify manually
- **Optional deps guarded** â€” Chroma, gRPC, msgpack, YAML, OpenTelemetry imported conditionally
- **SQLite DB at** `data/long_term_global.db` (created at runtime)
- **Empty `.env`** â€” copy `.env.example` if it exists, or set `A01_*` vars manually
- **Duplicate top-level dirs** â€” delete `agents/A01_Blockchain_Intelligence/{api,cli,monitoring,security,blockchain}` (empty, shadow real packages)
- **Import style** â€” absolute from `agents.A01_Blockchain_Intelligence.*`; relative within package
- **Async-first** â€” all I/O is async; sync helpers marked explicitly

---

## References
- Identity docs: `agents/A01_Blockchain_Intelligence/docs/identity/*.md`
- Architecture docs: `agents/A01_Blockchain_Intelligence/docs/architecture/*.md`
- Intelligence docs: `agents/A01_Blockchain_Intelligence/docs/intelligence/*.md`

---

# CIE-OS / A02 News Intelligence Agent

**A02** is the fake-news/rumor intelligence agent (stocks, crypto, forex). Built in 15 phases under a **minimal structure** (config/, core/, intelligence/, models/, data/, cli/) â€” deliberately small vs A01's 40 folders.

**Root:** `agents/A02_News_Intelligence/`

## Key Commands
```bash
# Doctor (validate foundation) / live ingestion + narrative cycle / narratives view / market impact
python -m agents.A02_News_Intelligence.cli doctor
python -m agents.A02_News_Intelligence.cli scan
python -m agents.A02_News_Intelligence.cli narratives
python -m agents.A02_News_Intelligence.cli impact <narrative_id>
python -m agents.A02_News_Intelligence.cli resolve --all   # learning loop: resolve predictions vs live price
python -m agents.A02_News_Intelligence.cli metrics         # accuracy, Brier, calibration, drift
python -m agents.A02_News_Intelligence.cli backtest        # replay resolved predictions
python -m agents.A02_News_Intelligence.cli output <id>     # flagship 12-point report

# Offline tests
python agents/A02_News_Intelligence/tests/test_core.py       # Phase 1 (38 assertions)
python agents/A02_News_Intelligence/tests/test_narrative.py  # Phase 2 (33 assertions)
python agents/A02_News_Intelligence/tests/test_verification.py  # Phase 3 (28 assertions)
python agents/A02_News_Intelligence/tests/test_impact.py     # Phase 4 (34 assertions)
python agents/A02_News_Intelligence/tests/test_learning.py   # Phase 5 (35 assertions)
python agents/A02_News_Intelligence/tests/test_phase6.py     # Phase 6 (31 assertions)
python agents/A02_News_Intelligence/tests/test_phase7.py     # Phase 7 (13 assertions)
```

## Phase Plan (current)
- Phase 0 âœ… Foundation (config, paths, sources registry, CLI stub, doctor OK)
- Phase 1 âœ… Ingestion vertical slice: RSS (keyless) + Tiingo/NewsAPI (keyed) connectors, normalization, dedup (url/title/content fp), rule-based entity extraction, SQLite storage (`data/processed/a02.db`) â€” `scan` command live-tested (137 items, dedup verified)
- Phase 2 âœ… Narrative intelligence: claim extraction (entity sentence + time hints), clustering (title-jaccard + entity overlap; no-shared-entity titles penalized 0.5x to stop pattern-headline false merges), stance (support/deny/neutral/question), propagation (mention/source/platform counts, velocity), FOMO score (velocity/sources/platforms/urgency) + lifecycle status (emergingâ†’spreadingâ†’peak_hypeâ†’verifyingâ†’resolved). `narratives` command live-tested.
- Phase 3 âœ… Verification + manipulation: credibility tiers (official 1 â†’ anonymous 6 by domain + source), source-level dedup for confirmations (identical content fp = 1 underlying source), epistemic status 7-tier verdict + confidence 0-1 (denies outrank confirms; official deny = confirmed_false; satire markers = fabricated), coordination score 0-100 (identical text, timing burst, author/platform concentration) â€” separate from FOMO & truth. DB auto-migrates new columns.
- Phase 4 âœ… Market impact + prediction: Binance klines (keyless crypto) + Alpha Vantage (keyed) price data, event-study returns (1h/6h/24h) + volatility + volume surge, category classification (etf/hack/delisting/regulatory/fraud/earnings/partnership/macro), historical correlation engine (similar past events â†’ expected range + confidence), prediction = measured move + historical analog + verification â†’ direction/probability/range/risk. `impact <id>` command live-tested with real BTC data (learning loop: each query stores an impact event).
- Phase 5 âœ… Learning + backtest: prediction snapshot stored per impact (direction/probability/mean), `resolve` captures realized outcome vs live price, `metrics` computes accuracy + multi-class Brier + calibration bins (overconfident flagged) + verification truth agreement + scan drift snapshots, `backtest` replays resolved events vs naive baseline, `output <id>` = flagship 12-point consumer report (claim â†’ next signal). All 5 suites green (168 assertions).
- Phase 6 âœ… ML models + extended categories + new connectors: sklearn TF-IDF+LogReg classifiers for category/stance/verification with rule fallback (models/ml_models.py); 21 impact categories including product_launch, executive_change, merger_acquisition, guidance_change, dividend, stock_split, bankruptcy, clinical_trial, patent, contract_win, investigation, sanctions; Telegram (bot API) and X/Twitter (API v2) connectors; ML verification signal integrated into verdict; source tiers for new connectors. All 6 suites green (199 assertions).
- Phase 7 âœ… Reddit connector + transformer fake detector + multi-asset correlation + retraining: Reddit public API connector; Hugging Face transformer pipeline with rule fallback; cross-asset Pearson correlation + prediction propagation; export/retrain utilities for ML models. All 7 suites green (212 assertions). A02 phase plan complete (7/7).
- Phase 8+ (optional stretch): Reddit OAuth for private subreddits, fine-tuned FinFakeBERT, multi-horizon impact modeling, portfolio-level risk integration

## A02 Gotchas
- **Env prefix `A02_`** â€” read from repo-root `.env`; all keys optional (degraded mode)
- **Minimal structure rule** â€” do NOT expand folders like A01; add files only when a phase needs them
- **No binary FAKE/REAL output** â€” epistemic status + confidence + impact range + uncertainty
- **FOMO â‰  Truth â‰  Coordination** â€” three separate scores
- Source-level dedup mandatory: 10 articles copying 1 tweet = 1 underlying source, not 10 confirmations
- Python 3.14, pydantic 2.13; async-first I/O