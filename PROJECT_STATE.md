# PROJECT_STATE.md â€” 026 Intelligence Engine OS

> Current snapshot. **Overwritten each session.** History lives in `BUILD_LOG.md`.
> This file describes what *is* â€” not what is planned. Planned work lives in the
> roadmaps in `README.md`, `ROADMAP.md`, and `AGENTS.md`.

- **Last updated:** 2026-10-28
- **Repo root:** `F:\026`
- **Follow-ups (2026-10-29)** - committed in small chunks after Phase 1: bybit removed from `config/bus.json`
  (unreachable here); T03 `HUMAN_CONFIRM_TOKEN` -> `HUMAN_CONFIRM_PHRASE` (sentinel secrets false-positive gone,
  fleet verdict no longer FAIL); supervisor runs two parallel lanes (slow: A002/A001, fast: A015/bus/prune) and a
  weekly `bootstrap.prune` (90-day retention, JSONL archive); dashboard sentinel matrix shows `contracts`; T03
  scalper breakers now persist across steps (and never run on simulated equity); A002 re-clusters stored-but-
  unclustered items and isolates a poison item; A001 drains each block before polling the next; relay/envelope/
  store hardened after an independent review (poison reports, transient vs systemic failures, confidence needs a
  detector, parked-event retry `bootstrap.consume --retry-parked`). Tests: platform 229 pass / 0 fail; A002 68,
  A007 11, A015 49, T01 53, T03 27, A001 ingestion/cli/db/pipeline 249. **Slice 2 (T01 pause flags) is design only**
  (`docs/superpowers/specs/2026-10-29-slice2-t01-pause-flags-design.md`), awaiting operator approval.
  **T03 scalper exits (operator-approved 2026-10-29, testnet only, still armed + confirm phrase):** a risk halt now
  flattens the open position with a reduce-only market order, and every entry/resize gets a reduce-only
  STOP_MARKET one ATR away (the distance the size was risked on); if the stop cannot be placed the position is
  closed. Not run against the live testnet (needs keys / the 190k-bar download). Open: A001 stored history has 46 missing heights (`contiguous: false`) - a backfill
  would repair them.
- **Fleet teams (2026-10-28, ADR-0006, docs only)** - the fleet is divided into four teams:
  **A** Intelligence Team (collectors), **R** Analysis Bureau (analysts; reserved R01-R05 = today's
  A009/A010/A012/A013/A014 README scaffolds), **T** Trading Desk (T01-T03), **X** Control Tower
  (stewards; X01-X07 proposed, nothing built). Platform actors stay as they are. Design, 41-row
  gap register and research: `docs/teams/` (start at `README.md`). **No code, registry, manifest or
  folder changed**; ADR-0006 is `proposed` (names and the letter `R` provisional). Before an R/X
  agent is registered, `security/sentinel/fleet.py:12` (`_ROW`, `[AT]`) must be widened. Biggest
  findings: A005 Market Data (README-only) is the critical path for the whole R team and part of
  the Desk; A015's events carry `maturity: implemented`, so an A->T hard-stop pause is blocked by
  the maturity gate (G-ORG-06); T03's scalper breakers are inert (`scalper.py:267,275`).
- **Slice 2a pause flags (2026-10-29, platform side only; T01 untouched)** - `bootstrap/consumers/risk_flagger.py` (runs inside `bootstrap.consume`, `min_maturity="implemented"` because a flag only blocks new entries) turns A015 Binance facts into `data/risk/pause_flags.json` (atomic, versioned): `listing.delisted` -> no-expiry flag, `status_changed` to BREAK/HALT -> 24 h flag, TRADING / `listing.new` -> cleared; each change publishes a `system.risk.flag_set` / `flag_cleared` audit event (source SYS, `causation_id` = trigger). Operator: `python -m bootstrap.flags list | set <subject> --hours N | clear <subject>`. Live: 19 real BREAK flags set on the first cycle. **S2b (T01 reads the file) is NOT built** - funds boundary, needs operator sign-off after S2a has run on live events.
- **Phase 1 event bus (2026-10-28, ADR-0005)** - durable, evidence-labelled events. A015's facts now
  reach a persistent brain: A015 `poll` (+ `poll_status.json`, enriched `event_log`) -> `bootstrap/relay.py`
  -> `data/bus/bus.db` (SQLite WAL: immutable `events`, per-consumer cursor/retry/park, `source_health`,
  persisted bus `trace`, `approvals` queue) -> `bootstrap/consume.py` (librarian) -> `data/brain/brain.db`
  (`markets`, the first persistent brain). Maturity is a code path (`consume(min_maturity="validated")`
  default; the librarian is a recorder at `implemented`); a baseline poll is never "ok"; the health monitor
  publishes one `system.source.stale` per outage. New sentinel check `contracts` (manifest `produces`/
  `consumes`). Supervisor now also runs `a015` (every 15 min, binance/coinbase/okx) and `bus`
  (every 5 min); **running since 2026-10-28 13:40Z** (hidden, via `start-live.vbs`; not yet in the Startup folder). First live
  cycle found and fixed 6 defects (see BUILD_LOG). State: `data/bus/bus.db` 452 events (119 new listings, 24
  delistings, 289 pair changes, 19 real status changes), `data/brain/brain.db` 451 `markets` records; binance /
  coinbase / okx fresh, bybit was unreachable from this network and was removed from `config/bus.json` (2026-10-29). Check: `python -m bootstrap.bus_stats`. Tests: platform 194 pass
  + 2 known T03-secret red; A015 45, A002 64, A007 11, T01 53, T03 18. Not built: Slice 2 (T01 pause flag,
  needs its own design review), Slice 3 (A002 relay), dashboard pages for events/approvals (the sentinel
  page does not show the new `contracts` check yet).
- **Phase 0 hardening (2026-10-28)** - from the orchestration audit
  (`docs/architecture/orchestration-network-audit-2026-10-28.md`). Test-first; green per suite
  (platform 97 / A002 64 / A007 11 / A015 37 / T01 53 / T03 18). Run agent suites one process
  each - T01 and T03 both put their own top-level packages on `sys.path`.
  **Bus:** a non-read message must declare an action (else denied); a handler payload with
  `error` is a failed Response; duplicate `register` raises (`replace=True` to override); optional
  `timeout_s` (production bus: 60 s). **Adapters:** one family in `bootstrap/adapters/`
  (A001, A002, A015 all registered in `wire.py`); payload key `intent` (legacy `op` still read).
  **T01:** the live loop applies the T03 veto; `RealEngine.enabled` reads the DB flag every time,
  so the dashboard's enable/disable now reaches the running bot (**enable takes effect without a
  restart**; accuracy gate, credentials and `_guard` unchanged). **Supervisor:** OS lock,
  success-only stamping + backoff/jitter retry, atomic state, heartbeat, `--status`; it is **not
  running** right now (launched by hand / at login). **A015:** first poll = baseline, failed
  fetch reported, shrink guard, spot-only, atomic snapshot, durable `memory/event_log` written
  before the snapshot advances. **A002:** RFC-822 dates, secret redaction, transient-error
  retry, WAL. **A007:** natural-key ids, `known_at`, live fetch raises instead of returning `[]`.
- **T03 (Strategy Intelligence Hub) — merged 2026-10-27:** Brought in from
  `F:\my-agents\$trategy-master` (source preserved). 8 strategy agents ($001–$008,
  `reviewed`) + 6 new components built on top: MTF analyzer (`core/futures/mtf.py`),
  next-candle predictor (`core/futures/predict.py`), signal fuser
  (`core/futures/fuse.py`), futures scalper loop (`core/futures/scalper.py`),
  Binance USD-M Futures Testnet broker (`core/paper/binance_futures_testnet.py`),
  sentiment adapter (`core/research/sentiment.py`). Also: `$009-scalper` agent config
  (`agents/$009-scalper/`), `scripts/run_scalper.py` (CLI entry point, dry-run by default),
  T01 bridge (`bridge/t01_bridge.py` — T01 can call T03 for scan consensus + win-rate
  backtests), 18-case test suite (`tests/test_t03_foundation.py` — behavior, regression,
  architecture). 3 bugs fixed en route (sys.path registry bug, bar-dropping normalize()
  bug, market-order price bug in both broker files). Registered in `config/agents/registry.yaml`
  (T03, partial, trust=2, execution_agent=true, testnet-only). **Not yet kernel-wired.**
  `tests/test_t03_foundation.py` — 40/40 green (verified 2026-10-27).
- **T03 -> T01 soft veto (live since 2026-10-28):** the 2026-10-27 wiring in `decide()` was dead
  code (nothing called it). Now `TradingBot._decide` (bot.py) applies `engine.apply_t03_veto` to
  BUY entries only (a SELL/exit is never vetoed), asks T03 about the symbol T01 is actually
  trading, and runs off the event loop with a 20 s cap (slow/failed T03 = no veto). Knobs:
  `T03_ENABLED` (default **true**), `T03_SYMBOL` (fallback only), `T03_TIMEFRAME`.
- **T03 backtest results (BTC/USDT 1d, 2023-01-01→2026-10-27):** best by Sharpe:
  $007-oneil (0.98, +147%, 26.6% max DD), $005-seykota (0.87, +143%, 34.4% max DD),
  $003-darvas (0.68, +84%, 37.2% max DD). $001-dennis is the only loser (-34%, Sharpe -0.06)
  — candidate for disabling. All strategies underperform buy-and-hold BTC (Sharpe 1.12, +384%).
- **$009-scalper dry-run:** first run downloads ~193k 5m bars + MTF layers from Binance
  (one-time cache; 5m file 20 MB cached). Background download in progress 2026-10-27.
  Subsequent runs are fast. Futures Testnet keys needed in T03 `.env` to activate broker
  (see BUILD_LOG.md 2026-10-27 for setup steps); without keys, scalper runs in
  `simulated(no keys)` paper mode.
- **Live supervisor (2026-09-29):** `live/supervisor.py` keeps the dashboard fresh —
  A001 ingest every 30 min, A002 scan every 2 hours, a step-by-step refresh on
  every launch, and event-driven double rescans (A002's new `events` detector finds
  upcoming scheduled events; both agents fire twice, 5 min apart, at each). Local
  launchers: `start-026.vbs` (dashboard+T01), `start-live.vbs` (supervisor, for the
  Windows startup folder), `stop-026.bat`. A001 live loop runs **no-token, 60
  blocks/cycle** (free-key ceiling); flows refresh only on a manual token ingest.
- **Dashboard (operator console):** `dashboard/frontend/` is a Next.js 16 app built
  page by page. **Built: `/` (026 home), `/narratives`** (the one news page —
  A002's narratives by topic × 7-step verdict, 3D "narrative city", filters, per-claim
  evidence) **, `/agents`** (every agent's full manifest contract + a mouse-controlled
  3D model: drag/flick to spin, Ctrl+scroll or pinch to zoom, click a part for its facts)
  **and `/sentinel`** (runs the real `security.sentinel scan`, shows a 7 × 6 check matrix
  that marks exempt / 0-file PASSes as ∅, and an "Ask the gate" simulator that calls the
  real `gate.check_action` — animated in a 3D dome). The approval queue is shown as
  **not built** (the bus only traces `gate_hold` in memory). **`/trace`**: the bus keeps
  no persisted history, so the page sends operator-composed rounds through the **real**
  bus (`bootstrap.build_bus` + A015 kernel adapter, read-only) via
  `dashboard/backend/trace_round.py`, then shows the trace log, per-message replay and a
  3D flight replay. **`/orchestrator`**: the orchestrator's planner/router/scheduler/
  workflows/memory are empty (0 bytes) and `config/models/models.yaml` is empty, so the
  page is an honest status + a working command console (`A001 detectors`, `gate …`,
  `scan`, `open …`) over the real bus/gate/sentinel, a live 3D module anatomy and the
  model tiers agents request. **`/brain`**: the brain store + access layer are built but
  nothing runs a persistent `Brain(<path>)`, so it holds **no records**; the page shows
  the manifest memory contract (3D map + access matrix), an "Ask the brain" checker over
  the real `AgentBrainView` (throwaway in-memory brain) and the build status.
  **`/onchain`** (A001): its own IntelligenceService (via the bus adapter) + read-only
  `a001.db` — 82-block 3D chain coloured by capture state, coverage limits, exchange
  flows, largest transfers, tokens, detectors (code vs manifest), chain registry.
  **`/desk`** (T01): a server proxy to T01's FastAPI (allowlisted ops only) — live
  status, candles (3D), order book, metrics, gate progress, trades, activity; paper
  controls; a real-mode switch behind a typed confirmation, with T01's own accuracy +
  credentials gate still deciding. **All 9 pages are built** (026 · narratives · agents ·
  onchain · desk · brain · orchestrator · sentinel · trace). Not committed yet.
- **Known red tests (2026-10-28):** `security/sentinel/tests/test_sentinel_integration.py`
  (2 tests) - T03 FAILs the sentinel secrets check: `HUMAN_CONFIRM_TOKEN` in
  `T03/core/paper/__init__.py:15` is a public confirmation phrase, not a credential (regex false
  positive). Operator decision pending: rename it, or whitelist it in `security/policies/sentinel.yaml`.
  (The old `test_architecture` red - adapters importing `agents.*` - is fixed: adapters moved to
  `bootstrap/adapters/`.)
- **A002 (2026-09-28):** narratives now persist a topic `category` (A002's own
  `classify_category`, rules + ML) — new `category` column, auto-migrated. Live DB
  `a002.db` had been empty since 2026-09-15; restored from the legacy `a02.db`
  (447 items), backfilled categories, then a fresh `scan` → 590 items / 362
  narratives, 0 uncategorized.
- **T01 (Smart Binance Intelligence):** 2026-09-18 merged the reviewed Jules AI
  branch work — paper fees + expectancy, ATR-adaptive stops + volatility sizing,
  ATR/VWAP/ADX indicators + VWAP confluence, trailing stops, and a Binance→Kraken
  geo-block fallback. Then **built roadmap #16 (loss reflection)** properly:
  per-trade loss attribution (dominant factor / trend-chop regime / exit type) +
  targeted self-correction (regime gate / factor down-weight / wider stop), plus
  non-acting multi-scenario predictions. T01 test suite now 30 cases (green). Also
  fixed a repo-health bug: the blanket `data/` `.gitignore` was hiding
  `T01/backend/data/` source, so a fresh clone of `main` could not boot T01 — now
  committed. The 3 merge commits are pushed to origin + the 4 merged branches
  deleted; the #16 commit (d3b8cb3) is **local, not yet pushed**.
  **27 other Jules branches remain unmerged on origin** (A001/A002/A006/A007/T02)
  awaiting their own review — see `BUILD_LOG.md` 2026-09-18.
- **T01 F-track (foundation fixes F1–F4), built this session:** `F1` `.env.example`
  synced with every `config.py` knob (15 missing keys added); `F2` shared fee math
  (`backend/trading/fees.py`, BUILD-NEW) — real fills now record **net-of-fee** PnL
  via new `REAL_FEE_PCT` knob, same formula as paper; `F3` `param_history` audit table
  + `save_params(source, reason)` journaling (self_tune/reflection reasons included),
  `GET /api/params/history`; `F4` bot heartbeat (`last_cycle_ts`,
  `consecutive_errors`), `GET /api/health`, N=5 failed cycles → **auto-pause**.
  Touched: `config.py`, `.env.example`, `paper_engine.py`, `real_engine.py`,
  `database.py`, `strategy/engine.py`, `strategy/reflection.py`, `bot.py`, `main.py`
  (all MINOR-FIX except fees.py + test file BUILD-NEW). T01 suite now **43 cases,
  all green** (30 old + 13 new in `tests/test_t01_foundation.py`).
- **A001 / A002 (2026-09-18):** merged 21 of the 24 remaining Jules branches — 8
  A001 code-health refactors (A001 suite still 1846 pass / 1 skip = behavior
  preserved), 6 A002 features (Deribit options-IV, Google Fact Check, translation
  APIs, async healthcheck fix, regex-compile perf, N+1 narrative-load fix), and 7
  A002 test-coverage additions (A002 pytest 42→55; check()-style suites 63/45/4 pass
  as scripts). Skipped 2 (a competing options-IV impl + a redundant test). Caveat:
  the fact-check/options-IV/translation branches add blocking urllib calls that
  should be wrapped in asyncio.to_thread if used in async paths.
- **A006 (Macro/Econ Intelligence):** 2026-09-18 scaffolded from Jules branch
  `scaffold-a006-macroecon-agent` — manifest + README only (`enabled: false`, no
  code/detectors/tests yet). Forex/global-macro domain. Sentinel PASS.
- **A007 (Public-Record Intelligence):** 2026-09-18 pipeline merged from Jules
  branch `feat/build-a007-agent` — ingestion → normalization → SQLite store + two
  detectors (congress trade clusters, congress↔insider correlation) + tests (2 pass).
  Promoted scaffold→partial, enabled, sentinel PASS. **Ingestion is mock-only** (no
  live MCP fetch, no CLI yet) — real logic + tests, but not a live alerting agent.
- **T02 (Swarm Trading Intelligence):** 2026-09-18 merged from Jules branch
  `feat/t02-swarm-intelligence` — a working agent-based market simulator (1000
  bots, 6 strategies, SQLite, CLI; 4 tests pass). Fixed 3 bugs on the way in
  (unclosed SQLite connections × 2, an argparse `%` help-string crash on py3.14).
  Registered in the fleet + sentinel scan **PASS** (widened the sentinel fleet
  regex to see `T`-series, and fixed a pre-existing A007 name-mismatch failure).
  Open flag: T02 never trades (`execution_enabled: false`), so its `T` badge may be
  wrong — possible A-series renumber, operator's call. Local commit, not yet pushed.
- **Phase:** Genesis Â· **Phase 1 (source inventory)** â€” documentation system
  established and hardened; **platform kernel still unbuilt, but A001+A002 agents migrated in from CIE-OS 2026-09-06;** Stack chosen (`docs/STACK.md`);
  execution charter gated (`ADR-0002`).
- **Interpreter:** not yet provisioned for 026 (`.venv` does not exist); the two
  migrated agents target `python >= 3.11` (system has 3.14 — verify in SP-5).
- **Fleet:** A001 (Blockchain) + A002 (News) migrated in from CIE-OS on 2026-09-06 —
  declared as fleet members (manifests + registry) and **runtime-verified 2026-09-07**
  (A001: 1831 pytest passed / 1 skipped; A002: 212 offline checks passed) — but **not yet
  kernel-wired** (SP-4). See `BUILD_LOG.md` (CIE-OS migration / SP-5).

---

## Honest status

026's **platform kernel** is still at session zero for code, but the repository is no
longer an empty scaffold: as of 2026-09-06 **two agents (A001, A002) were migrated in
from CIE-OS** — full vertical pipelines with test suites, source kept intact at
`F:\CIE-OS`. The platform's *own* source (`src/`, `orchestrator/`, `brain/`,
`security/`) is still empty (0 bytes). Also built is the
**documentation and continuity system** â€” and as of 2026-09-06 that system is
internally consistent and follows its own rules: the source registry now has a master
index, a canonical schema its rows actually deliver, a glossary, and formal ADRs.

The platform kernel is taking shape. Built and green (**58 tests**, Python 3.14.7): the
**sentinel** conformance enforcer (`python -m security.sentinel scan` → **A001 PASS,
A002 PASS**), its **runtime gate** (`security/sentinel/gate.py`, deny-by-default at the
execution boundary), a **message bus** (`orchestrator/event_bus/` — gated, budgeted,
traced), **composition-root adapters** (`bootstrap/`) that let the bus reach the **real agents
read-only** — including **DB-backed reads** over the migrated databases (A001
`metrics`/`coverage`/`flows` over a001.db; A002 `stats` over a002.db, e.g. 447 items /
107 entities), the
**shared brain** (`brain/` — namespaced, versioned writes, logged reads, manifest-scoped
access), and an **architecture-law test** (`tests/test_architecture.py`) that mechanically
enforces downward-only imports. Still absent: **cross-agent correlation** (the payoff —
plumbing is now all in place for it), the brain's embeddings/RAG/knowledge-graph, the
join that has agents read/write the brain during a task, scheduler/workflows, `make
doctor`, and deeper agent↔bus wiring (investigative queries needing A001's DB / A002's live
sources). The two migrated agents, however, now **run and pass inside 026** on
Python 3.14.7 (SP-5, 2026-09-07): A001 **1831 passed / 1 skipped** (pytest), A002
**212 offline checks passed** across 7 suites. (A002's ML paths — sklearn/transformers/
pandas — were not exercised; those libs are not installed, so tests took the rule
fallback.) Any
present-tense statement in `README.md` / `AGENTS.md` about *behavior* describes the
**target**, not a shipped system. When something starts working, `BUILD_LOG.md`
records the command that proved it â€” until then, assume it does not.

---

## Verification basis

| Command | Result |
|---|---|
| any test suite | **none exists** â€” `tests/` is empty |
| `make doctor` | **not implemented** â€” target only |
| build / lint / typecheck | **not configured** â€” no `pyproject.toml`, `ruff`, `mypy`, `pytest.ini` |
| docs: markdown link scan + `S0xx` ID reconcile | run at end of the 2026-09-06 session â€” see `BUILD_LOG.md` |

There is no *code* to verify yet. The docs, however, are now checked: every source ID
resolves in the master index, and internal links resolve.

---

## What exists

| Path | State | Notes |
|---|---|---|
| `README.md` | âœ… written | Vision, architecture, directory map, honest genesis status |
| `AGENTS.md` | âœ… written | Fleet contract (now A01â€“A006), manifest schema, governance, build discipline |
| `PROJECT_STATE.md` | âœ… this file | Living snapshot |
| `BUILD_LOG.md` | âœ… written | Append-only history; 2026-09-06 docs-hardening session recorded |
| `ROADMAP.md` | âœ… written | Phased plan; Phase 1 now has an explicit "definition of done" |
| `docs/manual/` | âœ… growing | Sections 01, 02, 04, 05 + **07 Glossary (new)**; 03/06/08 planned |
| `docs/adr/` | âœ… written | **New:** ADR index + ADR-0001â€“0004 (formalize existing decisions) |
| `docs/STACK.md` | âœ… written | Chosen language/tech stack |
| `sources/` | âœ… hardened | Registry: **master index** + canonical schema on every row; **42 catalogued rows** (26 apis Â· 8 datasets Â· 4 links Â· 1 model Â· 3 infra Â· 0 mcp), 1 dead (`S023`), 8 reserved/dropped IDs; + 4 new sources S048â€“S051 |
| `docs/SOURCES.md`, `ARCHITECTURE.md`, `CHANGELOG.md` | âœ… pointer | Redirect stubs (kept so links don't break) |
| all source dirs | â¬œ empty | Structure only â€” `agents/`, `brain/`, `orchestrator/`, `config/`, `src/`, `security/`, `dashboard/`, `data/`, `tools/`, `integrations/`, `plugins/`, `sandbox/`, `observability/`, `infra/`, `scripts/`, `tests/`, `requirements/`, `logs/` |
| `Makefile`, `requirements*.txt`, `.env.example`, `.gitignore`, `.editorconfig` | â¬œ empty | Present, 0 bytes â€” filled when code/deps/keys arrive |
| `.github/workflows/ci.yml`, `deploy.yml` | â¬œ empty | 0 bytes â€” inert (no git repo) |

---

## Source registry â€” count reconciliation (2026-09-06)

The old loose "40 sources" claim is retired. Actual: **42 catalogued rows**, **1 dead**
(`S023` IEX, tracked, no row), **8 reserved/dropped IDs** (`S018, S019, S030,
S035â€“S039`), highest ID `S051`. Full breakdown + master index:
[`sources/README.md`](sources/README.md#master-index).

---

## Data-exposure status

- **Not a git repository.** No `.git`, no remotes. Nothing is pushed anywhere.
- **CI/deploy workflows are empty (0 bytes)** and cannot run â€” no data leaves via them.
- **Local only.** `F:\026` is a plain drive path, not a cloud-sync folder.
- Data leaves the machine **only** if the operator later adds a git remote, a deploy
  target, or a connector. None exists today.

---

## Architecture invariants â€” status

None hold yet â€” there is no code to hold them. Recorded so the target is unambiguous:

| Invariant | Status | Where it will live |
|---|---|---|
| Downward-only imports, no cycles | â¬œ NOT YET | `tests/test_architecture.py` |
| Gated execution â€” OFF by default, multi-gate before any order | â¬œ NOT YET | `security/` (sentinel) + `config/constants.py` |
| Coverage required before an absence claim | â¬œ NOT YET | per-agent `skills/` |
| Alerting gated on `VALIDATED` maturity | â¬œ NOT YET | per-agent `decision/maturity.py` |
| Secrets never in tracked source | â¬œ NOT YET | `security/` + doctor check |
| Single-writer state / atomic upserts | â¬œ NOT YET | `brain/` + `data/` store |

---

## Open questions for the operator

1. **The 8 reserved/dropped IDs** (`S018, S019, S030, S035â€“S039`) are recorded as gaps.
   If any was meant for a real source you recall, name it and it takes that ID back;
   otherwise they stay reserved (never reused).
2. **Phase 1 vs Tier-1 design specs.** Phase 1 docs are now clean. Next: keep
   verifying â¬œ source rows (â†’ ðŸ”œ), or start the deferred, docs-only **Tier-1 design
   specs** (evidence-record schemas, correlation, validation harness, coverage,
   execution-gate)? Both are docs, no code.
3. **`.env.example`** â€” seed key *names* now (for the first buildable sources), or
   defer until connector work? Recorded as a Phase-1 exit item either way.
4. **Journal + Broker SDK placement (from LuxAlgo research, 2026-09-15).** These are
   the operator's own trading data (personal journal + read-only broker portfolio via
   the operator's own keys) â€” they don't fit `A001`â€”`A006`'s “external world” domains.
   Candidates: extend `T01` with a reporting/reconciliation capability, or surface
   through `operator-io` (Platform). Not decided â€” see `docs/manual/06-agents.md` §6
   and `sources/infra.md` `S121`.

---

## Next session should start at

Phase 1 is close to its "definition of done" (`ROADMAP.md`). Remaining docs-only work:

1. Verify the highest-value free rows against provider docs (advance â¬œ â†’ ðŸ”œ):
   Binance public, CoinGecko, yfinance, Finnhub, FRED, GDELT, + the 4 new sources.
2. Pick and list the **buildable-now set** for (future) Phase 2.
3. Seed `.env.example` with key *names* for that set, or record the deferral.
4. *(Operator's call)* begin the deferred **Tier-1 design specs** â€” still docs, no code.

Do **not** start connector/kernel code until the operator says Phase 1 is done and
green-lights code. A tenant on an unverified foundation inherits an unverified one.

<!-- ============================================================ -->
<!-- MERGED FROM CIE-OS: F:\CIE-OS\PROJECT_STATE.md on 2026-09-06 -->
<!-- 026's original content is ABOVE. CIE-OS original also preserved at integrations\CIE-OS\ -->
<!-- ============================================================ -->

# PROJECT_STATE.md â€” CIE-OS A001 Blockchain Intelligence Agent

> Current snapshot. Overwritten each session. History lives in `BUILD_LOG.md`.

- **Last updated:** 2026-08-21
- **Repo root:** `F:\CIE-OS`
- **Agent root:** `F:\CIE-OS\agents\A001_Blockchain_Intelligence`
- **Interpreter:** `F:\CIE-OS\.venv\Scripts\python.exe`

## Verification basis

| Command | Result |
|---|---|
| `python -m pytest -q` | **1,831 passed**, 1 skipped, **0 failed** |
| `python -m cli doctor` | **14/14 `ok`**, schema **v8**, exit 0 |
| `python -m cli detectors` | **5** detectors, 4 `validated` and alerting, 1 `implemented` and muted |
| `python -m cli verify detectors` | **4/4 promotable**, zero FPR, perfect recall |
| `python -m cli skills` | **19** skills implemented |
| `python -m cli providers` | 21 endpoints, 9 usable, 12 dormant, **1 keyed active** (alchemy) |
| `python -m cli chains` | **15** chains registered, 13 observable, 13 token-capable |

## 2026-08-21 -- triage + reconciliation

Health re-verified against the code, not the doc: **1,792 passed, 1 skipped, 0
failed**; `cli doctor` 14/14; no TODO/FIXME debt; every `NotImplementedError`
is a provider seam or abstract base method (e.g. `BaseAgent.execute`), not a
gap. `pytest-asyncio 1.4.0` is now installed, which is why the suite is green.

Reconciled stale claims below to match the code: WARM/LEDGER tiers are built and
tested (were "schema only"), whale-label wiring and the exchange-flow detector
are done (were "decisions left").

**Fixed:** `memory/storage/sqlite.py::connect()` leaked its live connection when
called twice (a caller connecting the storage and then the repository wrapping
it hit this) â€” aiosqlite reported it deleted-before-closed at GC. `connect()` is
now idempotent. Guarded by `test_storage.py -W error::ResourceWarning`.

**Still open (operator's call):** DET-EXPLOIT-02 stays muted until a labelled
drain corpus exists â€” deliberately, not for lack of code: promoting it on
synthetic cases would make it fire on legitimate unlocks/migrations, so it is
held at `implemented` until real announcement data and 90 days of reserve
history exist.

## 2026-08-22 -- pyflakes bug sweep (3 latent NameErrors fixed)

A `pyflakes` pass over the whole agent surfaced eight undefined-name hits.
Three were genuine `NameError` crashes waiting in code paths the collected
suite never drove -- which is why a green run hid them. All three fixed, each
guarded by a new regression test named for the defect. Suite 1,828 -> **1,831**.

| File | Bug | Fix |
|---|---|---|
| `memory/base/conversation.py:1871` | `health_check()` aggregated with a bare `_is_healthy(...)`; it is a method, so `overall_status` raised `NameError` every call | `self._is_healthy(...)` |
| `memory/base/vector_memory.py:1717` | `_row_to_entry()` fell to a bare `uuid4()` (only `uuid` is imported) when a row's id was empty | `uuid.uuid4()` |
| `tools/adapters/subprocess.py:241` | `stream()` caught `except AdapterError` but imported only the subclasses; any spawn failure raised `NameError` in the except clause, masking the real error | import `AdapterError` |

Two more were type-only latent defects (string annotations, no runtime crash),
also fixed: `tools/lifecycle/cleanup.py` used `Sequence` unimported; `tools/core/cache.py`
annotated `_futures` as the non-existent `"concurrent_future"` (now `"Future[Any]"`
under `TYPE_CHECKING`). The remaining pyflakes undefined-name hit --
`tools/adapters/rest.py:134` `"ssl.SSLContext"` -- is a **false positive**: a
string return annotation, never evaluated, with `ssl` imported locally inside
the method body by design.

New tests: `memory/base/tests/test_base_regressions.py` (2),
`tools/tests/test_subprocess_stream.py` (1). `memory/base/` had no
pytest-collected coverage before this, which is the coverage gap that let the
first two bugs ship.

## 2026-08-22 -- stablecoin flow normalised to dollars

Token/stablecoin attribution (decision #2 below) is closed. The rollup still
reads native value only, but the stablecoin skill now resolves decimals from a
curated table and reports flow as a summable face-dollar figure â€” which raw
base units never could.

- **`knowledge/stablecoins.py`:** curated `(chain, address) -> Stablecoin(symbol,
  decimals, peg)` for USDC/USDT/DAI/BUSD/USDP across 7 EVM chains. No `eth_call`;
  decimals fixed at deployment. Keyed by the registry's own slugs â€” fixing a
  latent bug where the old symbol list keyed BNB as `bnb` and the decimals
  resolver keyed it as `bsc`, neither of which a `bnb_chain` lookup ever hit.
  BNB-chain USDC/USDT are recorded at 18 decimals, not 6.
- **`skills/stablecoin/analysis.py`:** rewritten to normalise every stablecoin to
  its face-dollar quantity and sum across them; per-token and net USD figures,
  sorted by dollar throughput. Bounds state the figure is dollars *at par* â€”
  decimals resolved, but no price read, so a de-pegged coin is still counted at $1.
- **`contracts/decimals.py`:** the same slug bug in the general decimals
  resolver's `WELL_KNOWN` table (BNB keyed as `bsc`) is fixed to `bnb_chain`, so
  BNB's USDC/USDT/WBNB/ETH now resolve offline instead of falling through to an
  eth_call. A regression test guards it.
- **21 tests** (`knowledge/tests/test_stablecoins.py`,
  `skills/tests/test_stablecoin.py`): registry-slug keys, the BNB 18-decimal
  guard, decimals agreeing with `contracts.decimals.WELL_KNOWN`, and a USDC+DAI
  flow summing into one dollar total.

## 2026-08-21 -- approval-risk wired to stored data

The approval-risk decoder and exposure replay (39 tests, complete since the
security pass) are now reachable from stored data. Additive only â€” a new table
and a new read path, nothing existing changed.

- **migrations v8:** `approvals` table + indexes, keyed on
  `chain:tx_hash:log_index` and cascaded from `blocks`, so a replayed block is
  idempotent and a reorg withdrawal removes its grants with it. `CURRENT_VERSION`
  is derived, so doctor now reports schema v8.
- **`normalization/approvals.py`:** `normalize_approvals()` binds each decoded
  grant to its own block hash (sibling of `normalize_logs`). `contracts/events.py`
  still refuses approvals as non-transfers; this is the separate path that keeps
  them.
- **`database/approvals.py`:** `SqliteApprovalRepository` â€” FK-safe, idempotent
  writes; `approvals_for_owner()` hydrates back to `DecodedApproval` so the proven
  replay consumes them unchanged. Canonical reads only.
- **`database/writer.py`:** optional approval repository, off by default â€” a
  writer without one behaves exactly as before. **`cli approvals --db --address`**
  replays the stored log into `exposure_for_owner` and prints breadth plus the
  three things it cannot determine.
- **20 tests** across `database/tests/test_approvals.py` and
  `cli/tests/test_cli.py`: round-trip into the screen, revocation replay,
  idempotency, reorg withdrawal, opt-in capture, and the CLI's limits.

## 2026-08-20 -- security pass

Four workstreams, all complete. Suite 1,466 -> **1,679 passing, 0 failing**.

### 1. Security audit of the existing modules

`config/security` (1,117 lines) and `tools/security` (1,416) read line by
line. **16 defects, 8 reproduced against the shipped code before the fix.**
Full record: `agents/A001_Blockchain_Intelligence/docs/architecture/security-audit-2026-08-20.md`.

The four that mattered most:

| Defect | Effect |
|---|---|
| `SecretsManager` path traversal | `resolve("../../pyproject.toml")` returned 2,220 bytes from outside `secrets_dir` |
| `Rule()` defaulted to allow-everything | a rule dict missing its `permission` key authorized every principal for everything |
| No MAC on `encrypt_text` | one flipped ciphertext byte turned `admin=0` into `admin=9`, no error raised |
| `guard()` passed rules the mapping | a payload with a script tag and DROP TABLE cleared a "hard security gateway" untouched |

Also: token expiry raised `ModuleNotFoundError` and was never enforced;
`ApiKeyManager()` recursed until the stack ran out; the sandbox env scrub was
a denylist that missed `ALCHEMY_URL` and `DATABASE_URL`; `block_hosts` let
`169.254.169.254` through; `PermissionError` subclassed the builtin so
`except OSError` swallowed denials; `allow_all()` allowed nothing.

**67 regression tests** in `tools/security/tests/test_hardening.py` and
`config/tests/test_security_hardening.py`, each named for the defect it
guards.

### 2. DET-EXPLOIT-02 -- anomalous outflow

| | |
|---|---|
| Measurement | `blockchain/security/exploit_detection/outflow.py` -- pure, no I/O |
| Judgement | `intelligence/analysis/exploit.py` -- `ExploitAnalyzer` |
| Maturity | **`implemented`**, ceiling 0.60, **may not alert** |
| Tests | 50 |

Gate is the catalog's: `outflow_fraction >= 0.30` in `<= 3` blocks **and**
`z >= 6`. The z is read against the **modified** z-score (MAD / 0.6745, with a
mean-absolute-deviation fallback), because the classical one is self-defeating
here -- measured, one prior drain in the baseline costs it 11.8x of its
separation against 4.1x for the robust estimator. Calibration: **0 false
positives on 1,998 simulated ordinary windows**, injected drain caught.

Deliberately **not** promoted. There is no labelled corpus of protocol drains,
so the error rate is `unmeasured`, and section 7.3 bars an unmeasured detector
from alerting. It is the first detector in the registry to sit below the
ceiling since promotion, which is a useful demonstration that the gate does
something.

### 3. Approval risk screening

| | |
|---|---|
| Decoder | `blockchain/security/approval_risk/approvals.py` -- ERC-20, ERC-721, `ApprovalForAll` |
| Exposure | `blockchain/security/approval_risk/exposure.py` -- replay to the live grant set |
| Tests | 39 |

`contracts/signatures.py` sent `ApprovalForAll` here by name; this is the
consumer that note pointed at. Three traps handled explicitly: ERC-20
`Approval` and `ApprovalForAll` share a layout and differ only by `topic0`;
each standard revokes differently; and the three key a grant differently --
ERC-20 by spender, ERC-721 by token id (approve *replaces*), `ApprovalForAll`
by operator.

**Complete and not reachable from stored data.** There is no approvals table
and `contracts/events.py` refuses approval logs as non-transfers, so nothing
feeds it. The decoder had to exist before capturing the logs was worth doing;
wiring it needs a migration, which is the operator's call. *(Wired 2026-08-21 â€”
see "approval-risk wired to stored data" above; schema v8.)*

### 4. The eight pointer directories now hold code

`api/`, `monitoring/`, `models/`, `plugins/`, `reasoning/`, `reporting/`,
`security/`, `workflows/` are **redirect packages**: each binds the canonical
module object itself and forwards every other name to it live through
`__getattr__`. `api.rest is interfaces.rest` -- identity, so drift is
impossible by construction rather than by instruction.

`security/` is the exception that proves it: it binds `config.security` and
`tools.security` under `configuration` and `runtime` and refuses to merge
them, because both define a secret wrapper with different hardening and a
merged `security.Secret` would hide the choice.

`sandbox/` stays empty. There is nothing to redirect it to, and code placed
there ships by accident. **56 tests** in `tools/tests/test_redirects.py`.

### Also fixed along the way

- **The venv was broken.** `pyvenv.cfg` pointed at another machine's user
  (`C:/Users/thaha/AppData/Roaming/uv/python/...`), which does not exist here.
  Repointed at the local CPython 3.14.7; backup at `.venv/pyvenv.cfg.bak`.
- `interfaces/service.py` told API callers "None has a measured error rate, so
  none alerts" -- false since the four promotions. Now derived.
- `cli detectors` said "Confidence ceiling is 1.0" unconditionally. Now
  derived, and reports what is muted.
- Three tests asserted the *snapshot* "all detectors are validated" rather
  than the invariant. Rewritten to assert that a detector reaches `validated`
  only if a backtest put it there, and that anything below it names its
  blocker.
- The `blockchain/security/*` placement note blamed "event decoding beyond
  transfers", which `contracts/` has done since the contracts layer landed.
  Corrected to the real blocker: bytecode analysis and an ABI source.

---

## Steps completed

| Step | What | Status |
|---|---|---|
| 1 | `Coverage` incompleteness reason (`logs_missing` vs `selective`) | âœ… **DONE** |
| 2 | Call-budget wiring via dispatcher hook | âœ… **DONE** |
| 3 | Label loader â€” 2,859 addresses, 316 operators, schema v6 | âœ… **DONE** |
| 4 | Exchange flow â€” schema v7, 1,379/25,743 transfers attributed | âœ… **DONE** |
| 5 | 15-chain restructure + terminal depth | âœ… **DONE** |

## Step 5 â€” what was built

**15-chain directory structure** at `chains/`, one numbered directory per chain:

```
chains/
  __init__.py      â€” chain order, directory path
  base.py          â€” ChainAdapter, EvmAdapter, UtxoAdapter, SolanaAdapter
  01_ethereum/     â€” through 15_bitcoin/
    README.md      â€” chain description, what A001 can do, known limits
    endpoints.yaml â€” all provider endpoints, API key fields empty
    limits.yaml    â€” finality, reorg depth, block time, constraints
    adapter.py     â€” chain-specific adapter (EVM, UTXO, or Solana)
```

Key design decisions:
- **Bitcoin gets its own UtxoAdapter.** The EVM account model does not apply:
  no accounts with balances, no event logs, common-input-ownership is
  probabilistic. The adapter and README document why.
- **Solana gets SolanaAdapter.** Slots differ from blocks, RPC dialect is
  different. No sensor exists yet.
- **13 EVM chains share EvmAdapter.** Thin adapters that delegate to the
  existing EVM sensor.
- **endpoints.yaml has empty API key fields** with comments naming where to
  get each key. No credential appears in any file.
- **limits.yaml is sourced from knowledge/chains.py** capability data,
  measured 2026-08-14.
- **17 new tests** verify: all 15 directories exist with required files,
  adapters are importable and correctly typed, YAML configs are valid,
  Bitcoin does not claim account-based features, chain names match between
  files and registry.

Terminal depth: `cli chains` now references the per-chain directory for
detailed documentation. 9 REST routes, 14 CLI commands.

## Selective capture â€” the data-layer rebuild

The full-transaction mirror is replaced. Measured anti-pattern:
**0.70 MB per ethereum block** (77 blocks = 54.2 MB) â€” ~5 GB/day for one chain.

Superseded by the live measurement: **1,502 bytes/block, 358x**. The
floor is derived from the chain's own percentile, never a fixed currency amount.

| Tier | Window | Holds | Status |
|---|---|---|---|
| CACHE | seconds | raw provider responses, memory only | done |
| HOT | 7 days | per-block aggregates + material tx | repository built |
| WARM | 90 days | hourly aggregates (the anomaly baseline) | built + tested (`tiers/warm.py`) |
| LEDGER | forever | entities, track records, labels | built + tested (`tiers/ledger.py`) |

## Architecture Invariants status

| Invariant | Status | Evidence |
|---|---|---|
| Single-writer state via `asyncio.Lock` | **HOLDS** | `core/agent.py:1160-1168` |
| Atomic-upsert-only DB writes | **HOLDS** | `database/repositories.py:165,233` |
| ReorgDetector | **HOLDS** | `blockchain/reorg/detector.py` + tests |
| Idempotency keying | **HOLDS** | capture gaps deliberately excluded from `record_id` |
| Shared rate-limiter / backoff | **HOLDS** | `blockchain/rpc/rate_limit/bucket.py` |
| Downward-only imports, no cycles | **MEASURED â€” 2 known, ratcheted** | `tests/test_architecture.py` |
| No trade execution | **HOLDS** | `config/constants.py::NO_TRADE_EXECUTION` + doctor + tests |
| Secrets never in source | **HOLDS** | doctor: "no plaintext escape" |

### Known import violations (allowlisted, ratcheted)

| Where | Pulls | Direction |
|---|---|---|
| `skills/whale_detection/transfers.py:52` | `DEFAULT_PERCENTILE` | skills â†’ intelligence |
| `intelligence/narrative/composer.py:45` | `Stance` | intelligence â†’ decision |
| cycle `intelligence <-> skills` | consequence of the first | â€” |

## Detectors

| ID | Analyzer | Maturity | Ceiling | Alerts |
|---|---|---|---|---|
| DET-WHALE-01 | whale | **validated** | 1.00 | **yes** |
| DET-DORMANT-01 | dormant | **validated** | 1.00 | **yes** |
| DET-ANOMALY-01 | anomaly | **validated** | 1.00 | **yes** |
| DET-EXCHANGE-01 | exchange_flow | **validated** | 1.00 | **yes** |

All four promoted 2026-08-19 after backtesting against 535 labelled evaluation
cases (â‰¥100 per detector). Zero false positives, perfect recall, no
overconfidence. Confidence ceiling lifted from 0.60 to 1.00.

## Coverage gaps

| Chain | Stored | Notes |
|---|---|---|
| ethereum | 77 blocks / 25,743 tx | 45 complete, 32 incomplete |
| base | 266 blocks (build halted) | all complete |
| 13 other chains | none | registry entries, sensors readable |

## What is left for Section 19

| Criterion | Status |
|---|---|
| DATA | âœ… multi-chain, fallback, provenance, reorg/finality |
| INTELLIGENCE | âœ… entity/whale/anomaly/exchange flow |
| MULTI-AGENT | âœ… verified 2026-08-11 |
| TERMINAL | âœ… 14 CLI commands, 9 REST routes, HTML dashboard, 15-chain directory |
| ENGINEERING | âœ… 1,101 tests, observability, error recovery, docs, reproducibility |

### Decisions â€” status reconciled 2026-08-21

1. **Whale skill labels.** âœ… **DONE.** `skills/whale_detection/transfers.py`
   reads the label ledger (`LabelRepository`/`LabelSet`); `counterparty_type`
   now answers from a sourced claim, `unlabelled` when the list is empty.
2. **Token transfer attribution.** âœ… **DONE (2026-08-22).** Stablecoin flow is
   now normalised to dollars via `knowledge/stablecoins.py` (curated decimals).
   The rollup (`tiers/hot.py`, `tiers/warm.py`) still reads native value only;
   attribution lives in the stablecoin skill, which is where a value with a
   resolved exponent belongs. See "stablecoin flow normalised to dollars" above.
3. **Exchange flow detector.** âœ… **DONE.** `DET-EXCHANGE-01` (exchange_flow)
   is validated and alerting.

### Completed (previously out of scope)

**Label verification system.** Built 2026-08-19:
- `pipeline/verification.py` â€” label corroboration (cross-reference sources),
  manual verification, batch scan, status reporting
- `evaluation/promotion.py` â€” detector promotion pipeline (run backtests,
  produce promotion verdicts, build promoted registry)
- `cli verify labels` â€” corroborate labels from CLI
- `cli verify detectors` â€” run backtests and report promotion readiness
- All four detectors promoted to VALIDATED (confidence ceiling 1.0, may alert)
- 23 new tests (12 promotion + 11 verification)

## Configuration / secrets

`.env.local` at the agent root. Two variables: `A001_PYTHON` and one provider
key (`cli providers` reports alchemy active). The file is gitignored; **no
credential appears in tracked source**.
