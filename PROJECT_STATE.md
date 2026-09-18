# PROJECT_STATE.md â€” 026 Intelligence Engine OS

> Current snapshot. **Overwritten each session.** History lives in `BUILD_LOG.md`.
> This file describes what *is* â€” not what is planned. Planned work lives in the
> roadmaps in `README.md`, `ROADMAP.md`, and `AGENTS.md`.

- **Last updated:** 2026-09-18
- **Repo root:** `F:\026`
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
