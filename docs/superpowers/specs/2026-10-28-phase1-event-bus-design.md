# Phase 1 design — durable event bus (envelope + SQLite outbox)

> **Status:** approved by the operator 2026-10-28. **Slice 1 and 1b are implemented** (plan:
> `docs/superpowers/plans/2026-10-28-phase1-event-bus-slice1.md`); Slice 2 (T01) and Slice 3 (A002) are not. **Date:** 2026-10-28. **Decided:** SQLite transport ([ADR-0005](../../adr/ADR-0005-sqlite-event-bus.md)).
> **Follows:** `docs/architecture/orchestration-network-audit-2026-10-28.md` (§4, Phase 1) and
> `BUILD_LOG.md` 2026-10-28 (Phase 0). **Marks:** `[call]` = my decision, change it if you disagree;
> decisions the operator took are in §14 ("decided" in the text).

## 1. Intent and why

Today agents cannot tell each other anything. `MessageBus.send` is a synchronous request/response
used only by tests and the dashboard; A015's delisting events sit in a JSON file nobody reads; the
brain is empty; nothing connects A002's rumor to A001 or A015 to T01.

Phase 1 adds the missing half of the bus: **durable, replayable, evidence-labelled events** that
agents *produce* and other components *consume*, so facts can travel between agents without any
agent importing another and without losing anything on a crash. `send` (ask a question, get an
answer) stays exactly as it is.

## 2. Goals, non-goals, anti-goals

**Goals**
- One envelope every agent's facts can be put in (provenance, time triple, maturity, coverage).
- Durable, ordered, at-least-once delivery to named consumers, with retries and a dead-letter.
- Idempotent everywhere: replaying a producer's log or redelivering to a consumer is harmless.
- "No event" is only meaningful with proof the source was observed (coverage before absence).
- One end-to-end vertical slice that is *real*: A015 poll → bus → persistent brain → visible.
- Zero new infrastructure: stdlib `sqlite3`, the files and processes 026 already has.

**Non-goals (Phase 1)**
- Not the orchestrator/planner, fusion, or entity ledger (Phases 2–3).
- No consumer that can move money. T01/T03 are not consumers in the first slice (§12, slice 2).
- No cross-host delivery, no multi-tenant access control, no schema evolution tooling.
- No replacement of `send`/`Response`, the gate, or the adapters from Phase 0.

**Anti-goals (a failure even if it "works")**
- An event from an unvalidated detector reaching something that *acts* as if it were an alert.
- A silent gap: events lost, or "nothing happened" reported while the producer was down.
- Agents importing `orchestrator`/`bootstrap` (breaks `tests/test_architecture.py`).
- A second source of truth: the agent's own store stays canonical; the bus is a transport + log.

## 3. Constraints (from the repo and the platform)

- **Layering (mechanically tested):** `orchestrator` imports only lower layers (`security.sentinel`);
  agents import neither `orchestrator`, `bootstrap` nor `brain`. So agents cannot call `publish`.
  Wiring lives in `bootstrap/` (composition root).
- **Windows, single operator, several OS processes** (supervisor subprocesses, dashboard subprocess
  per request, T01 FastAPI service, CLIs). Python 3.14, stdlib preferred (ADR-0003 spirit).
- **SQLite WAL facts** (sqlite.org/wal.html, fetched 2026-10-28): readers don't block the writer and
  the writer doesn't block readers; **only one writer at a time**; all processes must be on the same
  host (no network filesystem); with always-overlapping readers the WAL file grows without bound; WAL
  mode persists in the file. → keep write transactions tiny, readers short-lived, checkpoint in
  maintenance.
- **Laws (AGENTS.md §0):** evidence standard, maturity gates, coverage before absence, provenance,
  gated execution, downward-only imports. §13 maps each to a mechanism.
- **ADR-0002:** no order path before the gate. This design adds none.
- **Existing manifests tolerate extra keys** (`checks/manifest.py` only requires `_REQUIRED`), so
  `produces`/`consumes` are additive.

## 4. Decisions

| # | Decision | Why |
|---|---|---|
| D1 **decided** | **Transport = SQLite (WAL) file `data/bus/bus.db`**, not Redis Streams — operator, 2026-10-28; recorded in [ADR-0005](../../adr/ADR-0005-sqlite-event-bus.md) | Redis is not installed here (no `redis-server`, no `redis` package); on Windows it needs Memurai or WSL2 per redis.io; it adds a daemon to supervise. Event volume is tiny (tens/day). ADR-0003 itself says the stack is "chosen, not proven". |
| D2 `[call]` | **Agents stay bus-unaware; "relays" in `bootstrap/` publish for them** (polling-publisher pattern) | Keeps the layering test green, needs no agent rewrite, and the agent's own fact store (A015 `event_log`, A002 DB, A001 DB) stays canonical. |
| D3 `[call]` | **Delivery = at-least-once, ordered per consumer by `seq`; consumers are idempotent by `event_id`** | Exactly-once across two SQLite files/processes isn't attainable cheaply; idempotency makes redelivery harmless. |
| D4 `[call]` | **Per-consumer cursor + attempts + park**, not a delivery row per (event, consumer) | Preserves order, tiny schema. A poison event is parked after N attempts so it can't block the stream. |
| D5 `[call]` | **Maturity is enforced mechanically at consume time** (`min_maturity`, default `validated`) | The evidence standard becomes a code path, not a convention. Recorders opt down explicitly. |
| D6 `[call]` | Event payloads validated against small YAML schemas in `config/events/`, no new dependency | Same lazy rule as the rest of the repo; swap to JSON Schema if it outgrows. |

Alternatives rejected: **Redis Streams** (real consumer groups, but a new daemon + Windows friction,
nothing to gain at this volume — kept as an escape hatch, §11); **JSONL file per agent + polling
only** (what A015 does today: no shared cursors, no dead-letter, no cross-agent ordering);
**in-process asyncio queue** (not durable, agents run in separate processes).

## 5. Architecture

```
 agent (own process, own store)         bootstrap/ (composition root)            consumers
 ┌───────────────────────────┐   ┌────────────────────────────────────┐   ┌─────────────────────┐
 │ A015 poll → event_log/*.json│──▶│ relays/a015.py: map → envelope     │   │ librarian → brain    │
 │ A002 → a002.db   (later)    │   │   │ validate · authorize producer  │   │ (recorder, slice 1)  │
 │ A001 → a001.db   (later)    │   │   ▼                                │──▶│ dashboard feed       │
 └───────────────────────────┘   │ EventStore.publish() ─▶ data/bus/   │   │ T01 risk flag (S2)   │
        facts stay canonical     │   events · consumers · parked ·     │   │ orchestrator (Ph.2)  │
                                 │   source_health · trace             │   └─────────────────────┘
                                 └────────────────────────────────────┘
 MessageBus.send(...)  request/response — unchanged, still gated + budgeted
```

Two kinds of traffic, deliberately separate: **commands/queries** (`send`, synchronous, gated) and
**facts** (events, asynchronous, append-only). Events never carry an instruction to act.

## 6. The event envelope

Canonical JSON, validated before append. `source` and `published_at` are set by the system, never
taken from the payload.

| Field | Type | Meaning / rule |
|---|---|---|
| `event_id` | `evt_<16 hex>` | Deterministic from content + the snapshot it was derived from (A015 already does this). Unique in the store → publish is idempotent. |
| `type` | `<src>.<domain>.<past-verb>` | e.g. `a015.listing.delisted`. Regex `^[a-z0-9]+(\.[a-z0-9_]+){2,3}$`. Must be in the schema registry. |
| `schema_version` | int ≥ 1 | Version of the `data` schema for this type. |
| `source` | agent id | `A015`. Must declare `produces: [type]` in its manifest or publish is refused. |
| `subject` | `kind:key…` | The entity: `market:binance:XYZ/USDT`, later canonicalized by the entity ledger (Ph.3). |
| `event_time` | ISO-UTC \| null | When it happened in the world. `null` = unknown (A015 cannot know). |
| `event_window` | `{from,to}` \| null | The uncertainty around `event_time` (A015: previous snapshot time → observed time). |
| `observed_at` | ISO-UTC | When the agent saw it. |
| `known_at` | ISO-UTC \| null | When it was public (A007 filings). Consumers must not act before it. |
| `published_at` | ISO-UTC | Set at append. |
| `trace_id`, `causation_id` | str, str\|null | Same ids the bus already uses; `causation_id` = the event/message that led to this. |
| `detector` | `{id, maturity, ceiling}` \| null | `maturity ∈ {implemented, validated}`. `null` for plain facts (heartbeat). |
| `confidence` | float \| null | `null` = cannot be determined. Invariant: `0 ≤ confidence ≤ ceiling` when both set. |
| `coverage` | `{complete, as_of, lag_s, note}` | What was actually observed. `complete: null` = unknown. |
| `evidence` | `[{source, locator, retrieved_at}]` | Provenance chain; ≥ 1 for any event that asserts something. |
| `untrusted` | bool | `data` contains third-party text (A002). It is data, never instructions (Prompt-Infection defence). |
| `data` | object | Type-specific, schema-checked, ≤ 64 KB total envelope. |

**Invariants the validator enforces:** required fields present; `type` registered and `source` allowed
to produce it; `confidence ≤ ceiling`; `evidence` non-empty when `confidence` or a detector is set;
`event_window.from ≤ to`; size cap; timestamps parse as UTC; `untrusted` events must not carry a key
named like an instruction (`action`, `command`, `tool`).

**Example — what A015's `DELISTING` becomes (golden test fixture):**
```json
{"event_id":"evt_3f9a…","type":"a015.listing.delisted","schema_version":1,"source":"A015",
 "subject":"market:binance:XYZ/USDT","event_time":null,
 "event_window":{"from":"2026-10-28T09:00:00Z","to":"2026-10-28T09:15:02Z"},
 "observed_at":"2026-10-28T09:15:02Z","known_at":null,
 "detector":{"id":"DELISTING","maturity":"implemented","ceiling":null},
 "confidence":null,
 "coverage":{"complete":true,"as_of":"2026-10-28T09:15:02Z","lag_s":0,"note":"spot only, 3705 markets"},
 "evidence":[{"source":"ccxt.fetch_markets:binance","locator":"snapshot:3f9a21c0e4b1","retrieved_at":"2026-10-28T09:15:02Z"}],
 "untrusted":false,
 "data":{"exchange":"binance","symbol":"XYZ/USDT","stated_reason":"unspecified","base":"XYZ"}}
```
`confidence: null` and `maturity: implemented` are honest: A015's reports carry neither today
(`detector.id` is A015's own detector name from its manifest — `NEW_LISTING`, `DELISTING`, …).
The relay can only build `event_window`, `evidence.locator` and `coverage` if the A015 report
carries them, which today's `event_log` entries don't: see the A015 change in §10.

## 7. Types, schemas and manifests

- `config/events/<type>.v<N>.yaml` — `required` and `optional` field → type for `data`
  (`str|int|float|bool|list|dict`). Slice 1 types: `a015.listing.new`, `a015.listing.delisted`,
  `a015.market.status_changed`, `a015.market.pair_changed`, `system.source.stale`.
- Manifests gain two optional keys (additive, no sentinel break):
```yaml
produces:                       # types this agent's relay may publish
  - {type: a015.listing.delisted, schema_version: 1}
consumes:                       # types it wants; used by consumers + the contracts check
  - {type: a015.listing.*, min_maturity: implemented}
```
- **Who may produce a type.** Agent types (`a015.*`): the source's manifest must list it under
  `produces`. Platform types (`system.*`, e.g. `system.source.stale`): the schema file lists
  `producers: [SYS]`, and only platform code in `bootstrap/` publishes as `SYS` (the health monitor).
  One authority per type, never two.
- **New sentinel check `contracts`:** FAIL if a `produces` type has no schema; HOLD if a `consumes`
  pattern matches no producer in the fleet (orphan) or `min_maturity` is invalid. This is what would
  have caught the `market` vs `markets` namespace drift.

## 8. The store (`data/bus/bus.db`, gitignored by `*.db` and `data/`)

Pragmas on every connection: `journal_mode=WAL`, `busy_timeout=5000`, `synchronous=NORMAL`
(a power loss may lose the last transaction, which is harmless because relays re-publish from the
canonical agent store idempotently). Python `sqlite3` with `isolation_level=None`
and explicit `BEGIN IMMEDIATE` for writes (takes the single write lock up front instead of failing on
lock upgrade). `PRAGMA user_version` carries the schema version for migrations.

```sql
CREATE TABLE events (
  seq INTEGER PRIMARY KEY AUTOINCREMENT,      -- never reused, even after pruning
  event_id TEXT NOT NULL UNIQUE,
  type TEXT NOT NULL, source TEXT NOT NULL, subject TEXT NOT NULL,
  maturity TEXT, schema_version INTEGER NOT NULL,
  published_at TEXT NOT NULL, envelope TEXT NOT NULL);   -- canonical JSON
CREATE INDEX events_type ON events(type, seq);
CREATE INDEX events_subject ON events(subject, seq);
CREATE TRIGGER events_immutable BEFORE UPDATE ON events
  BEGIN SELECT RAISE(ABORT, 'events are immutable'); END;

CREATE TABLE consumers (name TEXT PRIMARY KEY, cursor INTEGER NOT NULL DEFAULT 0, updated_at TEXT);
CREATE TABLE attempts  (consumer TEXT, seq INTEGER, n INTEGER, last_error TEXT, next_at TEXT,
                        PRIMARY KEY(consumer, seq));          -- next_at = backoff, see §9
CREATE TABLE parked    (consumer TEXT, seq INTEGER, attempts INTEGER, last_error TEXT, parked_at TEXT,
                        PRIMARY KEY(consumer, seq));          -- dead-letter, visible, replayable
CREATE TABLE source_health (source TEXT PRIMARY KEY, last_attempt_at TEXT, last_ok_at TEXT,
                        ok INTEGER, detail TEXT);             -- coverage proof, e.g. 'A015:binance'
CREATE TABLE relay_state (relay TEXT, key TEXT, value TEXT, PRIMARY KEY(relay, key));  -- high-water marks
CREATE TABLE trace (id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT, kind TEXT, msg_id TEXT,
                    trace_id TEXT, sender TEXT, recipient TEXT, type TEXT, reason TEXT);  -- slice 1b
```
`approvals` (the persisted `held` queue) is designed in slice 1b, not here.

**API** (`orchestrator/event_bus/store.py`, sync, stdlib; ~150 lines):
- `publish(event, *, manifests) -> (seq, duplicate: bool)` — validate → authorize producer →
  `BEGIN IMMEDIATE; INSERT OR IGNORE; COMMIT`. On duplicate returns the existing `seq`.
- `read(after_seq, limit) -> rows`.
- `consume(name, handler, *, types, min_maturity="validated", batch=50, max_attempts=5) -> Stats` — see §9.
- `record_health(source, ok, detail)`, `health(source)`, `stats()` (lag per consumer, parked count,
  oldest unconsumed age), `prune(older_than, archive_to)` (exports JSONL first; the only delete path; default retention
  **90 days**, operator's choice).
- Async callers wrap with `asyncio.to_thread`; each call opens its own short-lived connection.

## 9. Delivery semantics

1. Consumer reads `seq > cursor ORDER BY seq LIMIT batch` (all types; cheap at this volume).
2. For each row: events not matching `types`, or below `min_maturity`, are **skipped** (counted in
   `Stats.skipped_low_maturity`, never silently dropped) and the cursor passes them.
3. Matching events call `handler(event)` **outside** any DB transaction.
4. Success → `cursor = seq` (one small write). Failure → `attempts.n += 1` and
   `next_at = now + backoff` (capped exponential + jitter, as in `live/supervisor.backoff_sec`); if
   `n < max_attempts` **stop the batch** (order preserved). A later poll before `next_at` does nothing
   for that consumer, so a brief outage (a locked DB) can't burn through the attempts in one
   30-second supervisor tick. At `n == max_attempts` write `parked`, advance past it, and count it in
   `Stats.parked`.
5. A crash between handler and cursor write redelivers that event → **handlers must be idempotent**
   (key effects by `event_id`). The slice-1 brain writer is: same key, same value.

Not promised: exactly-once, global ordering across producers (only `seq` order), delivery to
consumers that didn't register a cursor.

## 10. Relays, coverage and the A015 slice

`bootstrap/relays/a015.py` (polling publisher): reads `memory/event_log/*.json` after the high-water
filename in `relay_state`, maps each report to an envelope with a **pure function** (`to_envelope`,
unit-tested against golden fixtures), publishes, advances the mark. Re-reading is always safe
(`event_id` unique).

| A015 report | Event type | Notes |
|---|---|---|
| `NEW_LISTING` | `a015.listing.new` | `data.median_day_1_effect_pct` kept as-is, `null` stays `null` |
| `DELISTING` | `a015.listing.delisted` | `stated_reason` stays `unspecified` unless a feed supplied one |
| `STATUS_CHANGE` | `a015.market.status_changed` | |
| `PAIR_CHANGE` | `a015.market.pair_changed` | |

**Coverage before absence.** Today A015 only prints poll results, so "no delistings" can't be
distinguished from "poll never ran". Slice 1 makes three small A015 changes (all in `cli.py`):
1. `poll` writes `memory/poll_status.json` atomically
   (`{exchange: {ok, error, baseline, polled_at, spot_markets}}`).
2. `_log_events` enriches every report it writes to `event_log` with `snapshot_digest` (the
   `old_digest` already used for `event_id`), `old_snapshot_at`, `observed_at` and `spot_markets`, so
   the relay can fill `event_window`, `evidence.locator` and `coverage` honestly instead of guessing.
3. `poll` accepts `--exchange` (repeatable) so the supervisor can poll a chosen list (today it only
   takes `--limit`, default 2).

The relay copies `poll_status.json` into `source_health` (`A015:binance`, …). **A baseline poll
(first poll of an exchange) is recorded but does not count as `ok`**: it proves a snapshot exists,
not that a diff was checked. Rule for every consumer/dashboard: a negative answer ("no delisting of
X") is valid only if `source_health.last_ok_at` is fresh (`now − last_ok_at ≤ 2 × poll interval`).
When it isn't, the health monitor (platform source `SYS`) emits `system.source.stale` once per
outage, not per tick. That is the bus-level form of the coverage law, and it is what would have
flagged a supervisor that stopped running.

**Scheduling.** Nothing schedules A015 today (the supervisor runs only A001/A002). Slice 1 adds three
supervisor jobs, reusing Phase 0's retry/backoff/lock: `a015_poll`, then `relay_once`
(`python -m bootstrap.relay --once`), then `consume_once` (`python -m bootstrap.consume --once`).
**Decided (operator, 2026-10-28):** poll `binance, bybit, coinbase, okx` every **15 minutes**, so the
staleness bound is 2 × 15 = 30 minutes. One `fetch_markets` call per exchange per run (network, no
API keys); the supervisor tick is serial, so a slow exchange delays A001/A002 by at most the
per-job 900 s timeout (§16).

## 11. Consumers, escape hatch and what changes where

**Slice-1 consumer — `librarian` (recorder).** `bootstrap/consumers/librarian.py` reads
`a015.*` with `min_maturity="implemented"` (a *recorder* may store lower-maturity facts **because it
stores the label with them**) and writes to a **persistent** brain (`data/brain/brain.db`, the first
one that exists): namespace `markets`, key `event:<event_id>`, value = the envelope, `by="librarian"`.
This gives `global/markets` real content, makes the dashboard's `/brain` page show records, and proves
the whole path with no funds-boundary risk.

**Escape hatch.** `EventStore`'s surface is `publish / read / consume / health`. If throughput ever
needs it, a Redis-Streams implementation can replace the SQLite body without touching relays or
consumers. No interface/abstract class is added now (YAGNI).

| Change | Where | Kind |
|---|---|---|
| Envelope + validator | `orchestrator/event_bus/envelope.py` | BUILD-NEW |
| EventStore | `orchestrator/event_bus/store.py` | BUILD-NEW |
| Event schemas | `config/events/*.yaml` | BUILD-NEW |
| A015 relay + CLI | `bootstrap/relays/a015.py`, `bootstrap/relay.py` | BUILD-NEW |
| Librarian consumer + CLI | `bootstrap/consumers/librarian.py`, `bootstrap/consume.py` | BUILD-NEW |
| `contracts` sentinel check | `security/sentinel/checks/contracts.py` + `sentinel.py` | BUILD-NEW |
| `poll_status.json`, enriched event_log reports, `--exchange` | `agents/A015…/cli.py`, `core/event_log.py` callers | MINOR-FIX |
| Health monitor (`system.source.stale`) | `bootstrap/relay.py` | BUILD-NEW |
| Supervisor jobs `a015_poll`, `relay_once`, `consume_once` | `live/supervisor.py` | MINOR-FIX |
| Manifests `produces/consumes` | `agents/A015…/agent.yaml` | data correction |
| Unchanged | `MessageBus.send`, gate, adapters, all agent pipelines except the A015 status file | — |

## 12. Slices

- **Slice 1 (this design):** envelope, store, A015 relay, librarian, source_health/staleness,
  `contracts` check, supervisor jobs. Ends with: a real A015 poll visible in the persistent brain and
  a measurable lag/parked/stale report (`python -m bootstrap.bus_stats`).
- **Slice 1b:** persisted `TraceLog` (sink into `trace`) and the persisted approval queue for `held`
  actions (also gives the dashboard `/sentinel` its missing queue).
- **Slice 2 (T01 risk flag).** **Operator decided (2026-10-28):** yes, T01 may consume A015 events
  at the `implemented` bar, **pause-only**. Semantics `[call]`, to be confirmed in Slice 2's own review:
  from `a015.listing.delisted` and `a015.market.status_changed` (HALT/BREAK — the more preventive
  signal, since A015 sees a delisting only after the market has left the list), T01 stops opening
  **new** entries on `market:binance:<symbol>`; it never closes or touches an open position, never
  enables or loosens anything, and never reads a flag as permission to trade. The flag clears when an
  `a015.listing.new` for the same market arrives or the operator clears it, and every set/clear is
  traced. It goes through the gate as a declared action (`risk.flag.set`, kind `write`). How T01 (a
  separate FastAPI process) reads flags — read-only helper vs an endpoint — is **not** decided here;
  Slice 2 gets its own design review before any code because it touches the real-money agent.
- **Slice 3:** A002 relay — blocked on a natural key for narratives (A002 ids are resettable ints) and
  on `untrusted` handling; first orchestrator playbook "delisting rumor" (A002 → ask A015 + A001 → fuse).

## 13. Laws → mechanisms

| Law | Mechanism |
|---|---|
| Evidence standard | `confidence`, `evidence[]`, `ceiling` invariants in the validator; `null` = cannot determine |
| Maturity gates | `detector.maturity` in every event; `consume(min_maturity="validated")` default; skips counted |
| Coverage before absence | `coverage` field + `source_health` freshness rule + `system.source.stale` |
| Provenance | `evidence[]`, `trace_id`, `causation_id`, immutable `events`, `relay`→`event_id` determinism |
| Gated execution | events carry facts, never commands; any consumer with side effects acts through `send` + gate |
| Downward-only imports | agents stay bus-unaware; envelope/store in `orchestrator`; wiring in `bootstrap`; arch test extended |

Security (ASI07/ASI08-style): producers authorized from the manifest, never from the payload;
`untrusted` text is data only; size caps; a parked event can't block the stream (blast-radius
isolation); `events` is append-only (UPDATE aborted by trigger, delete only via logged `prune`).

## 14. Decisions taken and what is still open

Operator answers, 2026-10-28:
1. **Transport:** SQLite (WAL), superseding ADR-0003's Redis line for the bus -> [ADR-0005](../../adr/ADR-0005-sqlite-event-bus.md).
2. **A015 polling:** binance, bybit, coinbase, okx, every 15 minutes (§10).
3. **T01 (Slice 2):** may consume A015 events at the `implemented` bar, pause-only (§12). Its read path
   and pause semantics get a separate design review before code.
4. **Retention:** 90 days, with a JSONL archive written before anything is deleted (§8).

**Still open:** nothing blocks Slice 1. The one thing to approve is this document as a whole.

## 15. Evaluation gate (AGENTS.md §10)

- **Behavior (golden):** each A015 report type → expected envelope (§6 fixture); validator accepts it.
- **Regression (named for the defect):** duplicate publish returns the same `seq`; a crash between
  handler and cursor redelivers; a poison event is parked and later events still flow; a producer not
  declaring the type is refused; `confidence > ceiling` is rejected; unknown/empty fetch does not make
  `source_health.ok` true; a below-`min_maturity` event never reaches an acting consumer.
- **Concurrency:** two processes publishing and one consuming against one file — no loss, no
  duplicate `seq`, `SQLITE_BUSY` handled by `busy_timeout`.
- **Architecture:** agents import nothing from the bus; relays/consumers live only in `bootstrap`;
  `contracts` check green on the real fleet and red on a seeded orphan.
- **End-to-end (Slice 1 exit):** fake exchange → `cli poll` → `poll_status.json` + `event_log` →
  `relay --once` → `bus.db` → `consume --once` → `brain.db`; rerun the whole chain: nothing duplicates.

## 16. Self-critique

- **Fragile:** one SQLite writer lock shared by relays, consumers and the supervisor — fine at tens of
  events/day, but a long reader on `bus.db` would grow the WAL (mitigation: short-lived readers +
  scheduled `wal_checkpoint(TRUNCATE)` in `prune`). `synchronous=NORMAL` relies on relays being able to
  re-publish.
- **Assumed:** the volume stays small; A015's `event_id` determinism (old snapshot digest) holds across
  restarts; `data/` is on a local disk, not a synced/network folder (OneDrive would break WAL).
- **Untested:** all of it — this is a design. Specifically unproven on this machine: concurrent
  multi-process publish on Windows file locking, and ccxt polling 4 exchanges inside one supervisor tick
  (the tick is serial; a slow exchange delays A001/A002 — may need its own timeout, already 900 s).
- **Left to the builder:** exact YAML schema syntax, retry numbers (`max_attempts=5`, backoff
  base/cap), the `bus_stats` output format, `prune` archive naming, the staleness multiplier.
- **Known loose ends I am deliberately not fixing here:** T02's manifest writes namespace `market`
  while A015 writes `markets` (the librarian uses `markets`; T02 needs aligning when it joins the
  bus); `Brain.write` appends a new version on every redelivery (same key, same value — harmless
  noise); `prune` is the only intended delete, but nothing besides "agents never open this file"
  prevents another delete.

## 17. Design inputs (why these choices)

Transactional outbox / polling publisher & idempotent consumers (microservices.io); CloudEvents required
attributes `id/source/type/specversion` (+ `time/subject/dataschema`); MCP's split between protocol and
execution errors (already adopted in Phase 0); AWS Builders' Library on bounded retries with jitter;
Collaborative Memory (arXiv 2505.18279) on immutable provenance per memory fragment; Prompt Infection
(arXiv 2410.07283) on treating inter-agent text as data; sqlite.org/wal.html for the concurrency limits
in §3. Secondary sources are noted in the audit report.
