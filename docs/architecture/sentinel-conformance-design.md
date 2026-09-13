# Design — Sentinel (Conformance Enforcer), slice 1

- **Status:** approved (design) — implementation plan next; no sentinel code yet
- **Date:** 2026-09-07
- **Deciders:** operator, Claude
- **Scope:** SP-3, first kernel slice. Operator chose *sentinel/trust-gate first*, and
  within that a *static conformance enforcer that runs today*.
- **History:** `BUILD_LOG.md` → 2026-09-06 (CIE-OS migration), 2026-09-07 (SP-5 verify + this design).
- **Related:** `AGENTS.md` §0 (laws), §2 (manifest), §3 (fleet), §6 (governance);
  `docs/manual/04-security.md`; `docs/adr/ADR-0002` (gated execution).

---

## 1. Context

026 is an OS for a fleet; a **sentinel** (platform actor, trust 3, home `security/`)
"sits over every action." Two agents (A01 Blockchain, A02 News) were migrated in and
declared with `agent.yaml` manifests + `config/agents/registry.yaml`. Those manifests
make claims — `trust.level: 2`, `invariants.execution_enabled: false`,
`reports_deviation_only: true`, `evidence.detectors`. Nothing yet **enforces** that the
claims match reality; SP-2 verified it once, by hand.

The sentinel's defining discipline (`04-security.md`, §6): **pair every named rule with a
live surface scan** — "a flag that reports 'ok' next to an exposed write path is exactly
the reassuring lie the check exists to catch." This slice turns the manual SP-2 audit into
enforced, repeatable code.

No message bus exists yet, so slice 1 is **static**: it reads the fleet and scans source.
It does not intercept runtime actions (that seam is a later slice).

## 2. Scope

**In scope (slice 1):** load the fleet (registry + manifests); **six** conformance checks
(§4), each a rule paired with a scan; a per-agent, per-check **report** with evidence
(human table + JSON) and a meaningful **exit code**; a CLI `python -m security.sentinel
scan`; a test suite proving the real fleet passes AND that planted violations fail.

**Out of scope (later slices — named so they are not lost):**
- The **runtime gate** interface (`sentinel.check(action, agent) -> allow|hold|deny`) —
  needs the bus/action flow (SP-4).
- The **money execution gate** state machine (paper→limits→approval) — no order path is
  being built; ADR-0002's "gate before order path" still holds when it is.
- **Architecture-law** checks (downward-only imports / no-cycles, `AGENTS.md` §10) — a
  natural later sentinel check; deferred to keep slice 1 small.
- Any change to agent internals. The sentinel is **read-only** toward agents.

## 3. Architecture & placement

Everything under `security/` (the sentinel's home; a platform layer that reads agents but
which agents must never import — downward-only imports hold).

```
security/
├── sentinel/
│   ├── __init__.py
│   ├── sentinel.py         # Sentinel: load fleet → run checks → aggregate FleetReport
│   ├── fleet.py            # read registry.yaml + agent.yaml + AGENTS.md §3 → AgentRecord list
│   ├── checks/
│   │   ├── __init__.py     # ordered CHECKS registry
│   │   ├── base.py         # Check protocol + CheckResult
│   │   ├── manifest.py     # C1
│   │   ├── trust.py        # C2
│   │   ├── execution.py    # C3
│   │   ├── secrets.py      # C4
│   │   ├── registry.py     # C5 registry ↔ AGENTS.md §3 agreement
│   │   └── deviation.py    # C6 reports_deviation_only best-effort
│   ├── report.py           # AgentReport / FleetReport + human + JSON renderers
│   └── tests/
│       └── test_sentinel.py
└── policies/
    └── sentinel.yaml       # policy-as-data: patterns, word lists, trust rules, excludes
```

**Dependencies:** standard library + `PyYAML` (already installed). No new heavy deps.

## 4. The checks

Each check consumes an `AgentRecord` (dir, manifest dict, registry row, fleet-table row)
and returns a `CheckResult` (`verdict`, `evidence`, `scanned`). Verdicts: `PASS`,
`HOLD` (advisory), `FAIL` (hard — the manifest contradicts reality).

### C1 · manifest — *valid, complete manifest* → breach = **FAIL**
`agent.yaml` exists, parses, has required keys (`id, name, status, trust.level,
invariants.execution_enabled, evidence, charter`); `id` matches the registry key.

### C2 · trust — *level ≥ 2 must be earned* → breach = **HOLD** (cap to L1)
`trust.level >= 2` requires non-empty `evidence.detectors` **and** a `tests/` dir with at
least one `test_*.py`. Breach → `HOLD` with `effective_trust: 1` (sentinel caps; never
edits the manifest).

### C3 · execution — *`execution_enabled:false` ⇒ no execution surface* → breach = **FAIL**
- **Scan:** every `.py` under the agent dir **except** `tests/`, `fixtures/`, `examples/`,
  `sandbox/`, `docs/`, `__pycache__/`. A match counts **only in live code** — matches
  inside comments or string literals are ignored (generalizes A01's own
  `test_no_signing_primitive_exists_in_the_source`). Preferred mechanism: Python
  `tokenize` to classify tokens; fallback = A01's line heuristic (skip lines whose
  stripped start is `# * " '`).
- **Banned patterns** (policy; baseline = A01's proven set + order primitives):
  `eth_sendRawTransaction, eth_sendTransaction, sendTransaction, sign_transaction,
  signTransaction, eth_sign, personal_sign, from_mnemonic, private_key, PRIVATE_KEY,
  place_order, submit_order, create_order, execute_trade`.
- **Verdict:** any live-code match → `FAIL` (evidence: `file:line: <match>`); else `PASS`
  (evidence: "N files scanned, 0 offenders").

### C4 · secrets — *no hardcoded credential in tracked source* → breach = **FAIL**
- **Scan:** `.py .yaml .yml .md .toml` under the agent dir, **excluding** files matched by
  the repo `.gitignore` secret rules (`.env`, `.env.*`, `**/.env*`, `**/API_KEYS.md`) and
  `tests/`/`fixtures/`. Shape-based (a pasted key is usually a literal), so no comment/
  string skipping here.
- **Patterns (policy):** private-key `0x[0-9a-fA-F]{64}`; assigned secret literal
  `(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*["'][A-Za-z0-9_\-]{16,}["']`.
- **Verdict:** any match → `FAIL` (evidence: `file:line`, value redacted); else `PASS`.

### C5 · registry — *registry.yaml agrees with `AGENTS.md` §3 fleet table* → breach = **FAIL / HOLD**
- **Scan:** parse the §3 fleet table (id, name, status) from `AGENTS.md`; compare with
  `config/agents/registry.yaml` and each `agent.yaml`.
- **Verdict:** an agent enabled in the registry but **absent** from §3, or an **id/name
  mismatch** across registry/manifest/§3 → `FAIL`. A **status drift** (e.g. §3 says
  `substantial`, manifest says `partial`) → `HOLD`. All agree → `PASS`.

### C6 · deviation — *`reports_deviation_only:true` ⇒ no advice/verdict in the output surface* → breach = **HOLD**
- **Nature:** **best-effort**, so the report **always** annotates this invariant as
  "declared · best-effort-scanned, not fully enforced." Verdict is capped at `HOLD` (never
  `FAIL`) to avoid false-positive hard-fails.
- **Scan:** string literals in the **output-facing** layers only — `decision/`,
  `reporting/`, `interfaces/`, `intelligence/narrative/` (or the agent's declared output
  composer) — for advice/verdict imperatives (policy word list):
  `\bbuy\b, \bsell\b, bullish, bearish, "you should", "we recommend", "guaranteed",
  "price will (rise|fall|go up|go down)"`. The list **deliberately excludes** legitimate
  score/detector names (`manipulation`, `whale`, `anomaly`, `coordination`) — A02's
  `manipulation.py` is a coordination score, not a verdict.
- **Verdict:** any match → `HOLD` (evidence: `file:line` for operator review); else
  `PASS`. Expected: both A01 ("Deviation, not judgement") and A02 ("no FAKE/REAL binary")
  `PASS`; C6 mainly guards against future drift.

## 5. Policy-as-data — `security/policies/sentinel.yaml`

```yaml
version: 1
execution:
  banned_primitives: [eth_sendRawTransaction, eth_sendTransaction, sendTransaction,
    sign_transaction, signTransaction, eth_sign, personal_sign, from_mnemonic,
    private_key, PRIVATE_KEY, place_order, submit_order, create_order, execute_trade]
  scan_globs: ["**/*.py"]
  exclude_dirs: [tests, fixtures, examples, sandbox, docs, __pycache__]
  ignore_in_comments_and_strings: true
secrets:
  patterns:
    private_key_hex: '0x[0-9a-fA-F]{64}'
    assigned_secret: '(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*["''][A-Za-z0-9_\-]{16,}["'']'
  scan_globs: ["**/*.py", "**/*.yaml", "**/*.yml", "**/*.md", "**/*.toml"]
  exclude_globs: ["**/.env", "**/.env.*", "**/API_KEYS.md"]
  exclude_dirs: [tests, fixtures, __pycache__]
trust:
  min_level_requiring_evidence: 2
deviation:
  output_dirs: [decision, reporting, interfaces, intelligence/narrative]
  advice_terms: ['\bbuy\b', '\bsell\b', bullish, bearish, "you should", "we recommend",
    guaranteed, 'price will (rise|fall|go up|go down)']
registry:
  agents_md: AGENTS.md          # parse §3 fleet table
  registry_file: config/agents/registry.yaml
```

## 6. Report & exit semantics

```
FleetReport { generated_at, sentinel_version, policy_version,
  agents: [ AgentReport { id, dir, effective_trust, verdict, checks: [CheckResult...] } ] }
```
- Agent `verdict` = worst check: any `FAIL` → `FAIL`; else any `HOLD` → `HOLD`; else `PASS`.
- **Human output:** one row per agent (id · verdict · effective_trust · one-line reason),
  then a detail block per non-`PASS` check with evidence. C6's invariant is always shown
  as "best-effort."
- **JSON output** (`--json`): the full `FleetReport` for CI/dashboard.
- **Exit code:** `2` if any agent `FAIL`; `1` if any `HOLD` and no `FAIL`; `0` if all
  `PASS`. (`make sentinel` hard-fails on a lie; a downgrade/best-effort concern is a
  warning.)

**CLI:** `python -m security.sentinel scan [--json] [--agent A01] [--policy PATH]`.

## 7. Test plan (the gate must be a gate, not a decoration)

`security/sentinel/tests/test_sentinel.py`, verified by execution
(`python -m pytest security/sentinel/tests -q`, per `AGENTS.md` §9):
1. **Fleet passes:** real fleet (A01, A02) → **no `FAIL`** (both expected `PASS`). Living
   successor to the manual SP-2 audit.
2. **Planted violations caught** (proves enforcement) — temp fake-agents:
   - live `sign_transaction(...)` with `execution_enabled:false` → C3 `FAIL`.
   - `api_key = "AKIA<16+ chars>"` literal → C4 `FAIL`.
   - `trust.level:2`, no detectors/tests → C2 `HOLD`, `effective_trust:1`.
   - registry lists an id absent from AGENTS.md §3 → C5 `FAIL`; status drift → C5 `HOLD`.
   - output-dir string `"you should buy now"` with `reports_deviation_only:true` → C6 `HOLD`.
   - missing/invalid `agent.yaml` → C1 `FAIL`.
3. **No false positives:** a banned primitive only inside a comment/string → C3 `PASS`;
   the word `manipulation` in `manipulation.py` → C6 `PASS`.

## 8. Laws & constraints honored

- **Read-only toward agents** — scans, never edits.
- **Downward-only imports** — `security/` reads agent files as data; no agent imports the
  sentinel; the sentinel imports no agent package.
- **No new heavy deps** — stdlib + PyYAML.
- **Evidence over flags** — every verdict carries scanned locations, not a bare "ok".
- **Honest scope** — C6 is labelled best-effort; architecture-law and runtime-gate
  enforcement are named as *not yet built* rather than implied.

## 9. Resolved decisions (operator, 2026-09-07)

1. `reports_deviation_only` → **flag it AND a best-effort semantic check** (C6, `HOLD`).
2. `HOLD` exit code → **warning (exit 1)**; only `FAIL` hard-fails (exit 2).
3. Registry ↔ `AGENTS.md` §3 cross-check → **included** (C5).

## 10. Next step

Create the implementation plan (via the writing-plans skill) and build slice 1
**test-first**. No sentinel code before that plan is approved.
