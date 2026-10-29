# Phase 1 Event Bus (Slice 1 + 1b) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (native, this session). Steps use checkbox (`- [ ]`) syntax.

**Goal:** Durable, evidence-labelled events from A015 reach a persistent brain through a SQLite bus, with coverage/staleness tracking, plus a persisted bus trace and approval queue.

**Architecture:** `orchestrator/event_bus/{envelope,store}.py` (stdlib, no agent imports) hold the envelope validator and the SQLite store. Agents stay bus-unaware; `bootstrap/relays/a015.py` maps A015's `event_log` to envelopes and publishes; `bootstrap/consumers/librarian.py` records them in a persistent brain. The supervisor schedules poll → relay → consume.

**Tech Stack:** Python 3.14, stdlib `sqlite3`, `pyyaml` (already used), pytest. No new dependency.

**Spec:** `docs/superpowers/specs/2026-10-28-phase1-event-bus-design.md` · ADR: `docs/adr/ADR-0005-sqlite-event-bus.md`

## Global Constraints

- Store file `data/bus/bus.db`; per connection `PRAGMA journal_mode=WAL`, `busy_timeout=5000`, `synchronous=NORMAL`; writes use `BEGIN IMMEDIATE`; `PRAGMA user_version=1`.
- Event type regex `^[a-z0-9]+(\.[a-z0-9_]+){2,3}$`; envelope ≤ 65536 bytes canonical JSON; all timestamps timezone-aware ISO-8601 UTC.
- Maturity order `implemented < validated`; `consume` default `min_maturity="validated"`; `max_attempts=5`; events with `detector: null` always pass the maturity gate.
- Retention 90 days with a JSONL archive written before any delete; never delete an event a consumer has not passed.
- A015 polled for `binance, bybit, coinbase, okx` every 15 min; a source is stale after 2 × 15 = 30 min without an `ok` poll; a baseline poll is never `ok`.
- Layering (tested): agents import nothing from `orchestrator`/`bootstrap`/`brain`; relays and consumers live only in `bootstrap/`; `orchestrator` imports only `security.sentinel`.
- Agent test suites run one process each (T01 and T03 both put top-level packages on `sys.path`).
- TDD: every task writes the test, watches it FAIL for the stated reason, then implements. No git commit unless the operator asks. Nothing here touches T01/T03 or any order path; Slice 2 (T01 pause flag) and Slice 3 (A002 relay) are out of scope.

## Review Focus

- Two processes publish the same `event_id` at once → one row, both get the same `seq` (Task 2).
- A consumer handler fails on event N every time → N is parked and N+1.. still flow (Task 3).
- `poll_status.json` missing/corrupt, or an `event_log` file with torn JSON → relay does not crash, source is not `ok` (Tasks 4, 5).
- Event with `confidence` > `ceiling`, no evidence, or a naive timestamp → rejected, relay keeps going and reports it (Tasks 1, 5).
- `bus.db` locked by another writer longer than `busy_timeout` → clear `StoreBusy`, nothing half-written, CLI exits 1 (Tasks 2, 5).

---

### Task 1: Envelope, schemas, validator

**Files:**
- Create: `orchestrator/event_bus/envelope.py`, `config/events/{a015.listing.new,a015.listing.delisted,a015.market.status_changed,a015.market.pair_changed,system.source.stale}.v1.yaml`
- Test: `orchestrator/event_bus/tests/test_envelope.py`

**Interfaces — Produces:**
```python
class EnvelopeError(ValueError): ...
MATURITY_ORDER = {"implemented": 0, "validated": 1}
MAX_ENVELOPE_BYTES = 65536
def load_schemas(directory: Path | None = None) -> dict[str, dict]
    # type -> {"schema_version": int, "platform": bool, "required": {name: kind}, "optional": {name: kind}}
    # kind in {"str","int","number","bool","list","dict","any"}; optional fields may be null
def validate_event(event: dict, schemas: dict[str, dict], manifests: dict[str, dict]) -> None   # raises EnvelopeError
def canonical_json(event: dict) -> str          # sort_keys, separators (",", ":"), ensure_ascii=False
def type_matches(pattern: str, type_: str) -> bool   # exact, or trailing ".*"
def passes_maturity(event: dict, minimum: str) -> bool
def make_event_id(*parts: str) -> str           # "evt_" + sha1("|".join(parts)).hexdigest()[:16]
```
Schema YAML shape: `type`, `schema_version`, `platform` (true only for `system.*`), `data: {required: {...}, optional: {...}}`. Required `data` fields: `a015.listing.new` {exchange,symbol,base: str}; `.delisted` {exchange,symbol,base,stated_reason: str}; `a015.market.status_changed` {exchange,symbol: str, status_from,status_to: any}; `.pair_changed` {exchange,symbol,base_asset,quote_asset: str}; `system.source.stale` {source: str, max_age_s: number, last_ok_at: any}. Optional: `historical_context: str`, `trading_pairs: list`, `median_day_1_effect_pct`/`median_crash_pct`/`median_effect_pct: number`, `pair_added`/`pair_removed: any`.

- [ ] **Step 1: Failing tests** in `test_envelope.py`, with a helper `sample_event(**overrides)` returning the spec §6 `a015.listing.delisted` example (source `A015`, `detector={"id":"DELISTING","maturity":"implemented","ceiling":None}`, `confidence=None`, evidence of one item) and `MANIFESTS = {"A015": {"produces": [{"type": "a015.listing.delisted", "schema_version": 1}]}}`. Tests (each asserts `validate_event` passes or raises `EnvelopeError` matching the quoted word):
  `test_valid_event_passes`; `test_unregistered_type_rejected` ("type"); `test_source_without_produces_rejected` ("produce"); `test_platform_type_only_from_SYS` (`system.source.stale` from `A015` rejected, from `SYS` passes); `test_confidence_above_ceiling_rejected` (0.9 vs ceiling 0.6, "ceiling"); `test_confidence_none_allowed`; `test_detector_requires_evidence` (evidence `[]` → "evidence"); `test_naive_timestamp_rejected` ("timestamp"); `test_event_window_reversed_rejected`; `test_missing_required_data_field_rejected`; `test_wrong_data_type_rejected`; `test_optional_null_allowed`; `test_oversize_rejected` (data padded past 65536 bytes); `test_untrusted_event_with_instruction_key_rejected` (`untrusted=True`, `data["action"]`); `test_type_matches_wildcard` (`a015.*` matches `a015.listing.new`, not `a002.x.y`); `test_passes_maturity` (null detector passes `validated`; `implemented` fails `validated`; passes `implemented`); `test_make_event_id_stable_and_prefixed`.
- [ ] **Step 2:** `python -m pytest orchestrator/event_bus/tests/test_envelope.py -q` → FAIL (`ImportError: envelope`).
- [ ] **Step 3:** Implement `envelope.py` and the five schema files per Interfaces. Required top-level fields: `event_id,type,schema_version,source,subject,observed_at,trace_id,coverage,evidence,untrusted,data`; nullable: `event_time,event_window,known_at,detector,confidence,causation_id`. `published_at` is ignored by the validator (the store sets it).
- [ ] **Step 4:** same command → PASS.

### Task 2: EventStore — init, publish, read

**Files:** Create `orchestrator/event_bus/store.py`; Modify `orchestrator/event_bus/__init__.py` (export `EventStore, StoreBusy, EnvelopeError`); Test `orchestrator/event_bus/tests/test_store.py`.

**Interfaces — Consumes:** Task 1. **Produces:**
```python
DEFAULT_DB: Path                        # <repo>/data/bus/bus.db
class StoreBusy(RuntimeError): ...
class EventStore:
    def __init__(self, db_path=DEFAULT_DB, *, schemas=None, manifests=None, clock=None, rnd=None, busy_timeout_ms: int = 5000)
    def publish(self, event: dict) -> tuple[int, bool]          # (seq, duplicate)
    def read(self, after_seq: int = 0, limit: int = 100, types: list[str] | None = None) -> list[dict]  # envelope + {"seq": n}
```
`clock` is a zero-arg callable returning aware UTC `datetime` (default `datetime.now(UTC)`). `schemas=None` → `load_schemas()`; `manifests=None` → `{}`. `__init__` creates parent dir and the full v1 schema in one go: `events` (+indexes, `events_immutable` UPDATE trigger), `consumers`, `attempts(…,next_at)`, `parked`, `source_health`, `relay_state`, `trace`, `approvals(id,at,trace_id,msg_id,to_agent,action_json,reason,status,decided_at,decided_by)`.

- [ ] **Step 1: Failing tests** (fixture `store(tmp_path)` with the Task 1 helpers/MANIFESTS and a fake clock): `test_publish_assigns_increasing_seq`; `test_duplicate_event_id_returns_same_seq_flagged` (`(1, False)` then `(1, True)`, one row); `test_published_at_set_by_store_not_payload`; `test_invalid_event_not_stored` (raises `EnvelopeError`, `read()` empty); `test_events_are_immutable` (`UPDATE events …` via a raw connection raises `sqlite3.IntegrityError`); `test_wal_and_user_version` (`PRAGMA journal_mode`=="wal", `user_version`==1); `test_read_filters_by_type_and_after_seq`; `test_two_processes_publish_same_event_once` (two `multiprocessing.get_context("spawn")` workers, module-level function, publish identical event; afterwards one row and both returned the same seq); `test_locked_database_raises_store_busy` (a raw connection holds `BEGIN IMMEDIATE`; a store with `busy_timeout_ms=50` raises `StoreBusy` and the table is unchanged).
- [ ] **Step 2:** run → FAIL (`ImportError: EventStore`).
- [ ] **Step 3:** Implement. One short-lived connection per call (`isolation_level=None`); `publish` = validate → `BEGIN IMMEDIATE` → `INSERT OR IGNORE` → if `changes()==0` select the existing seq → `COMMIT`; map `sqlite3.OperationalError("database is locked")` to `StoreBusy`. `seq` is `INTEGER PRIMARY KEY AUTOINCREMENT`; the stored envelope is `canonical_json` including `published_at`.
- [ ] **Step 4:** run → PASS.

### Task 3: consume, health, state, stats, prune

**Files:** Modify `orchestrator/event_bus/store.py`; Test `orchestrator/event_bus/tests/test_consume.py`.

**Interfaces — Produces (all on `EventStore` unless noted):**
```python
@dataclass class ConsumeStats: delivered=0; skipped_other_type=0; skipped_low_maturity=0; failed=0; parked=0; last_seq=0
def backoff_sec(attempt: int, rnd=random.random) -> float          # module fn: delay=min(300, 5*2**(attempt-1)); delay/2 + rnd()*delay/2
def consume(self, name: str, handler: Callable[[dict], None], *, types: list[str], min_maturity: str = "validated", batch: int = 50, max_attempts: int = 5) -> ConsumeStats
def record_health(self, source: str, *, ok: bool, detail: str = "", at: datetime | None = None) -> None
def health(self, source: str) -> dict | None      # {source,last_attempt_at,last_ok_at,ok,detail}
def stale_sources(self, sources: list[str], max_age_s: float) -> list[str]   # never seen or last_ok_at older than max_age_s
def get_state(self, relay: str, key: str, default: str | None = None) -> str | None
def set_state(self, relay: str, key: str, value: str) -> None
def parked(self, consumer: str | None = None) -> list[dict]
def stats(self) -> dict      # {"events": n, "parked": n, "consumers": {name: {"cursor": c, "lag": head-c}}, "sources": {...}}
def prune(self, older_than: datetime, archive_to: Path) -> int
```
Algorithm is spec §9: read `seq > cursor ORDER BY seq LIMIT batch`; skip non-matching (`type_matches`) and below-maturity events (counted) advancing the cursor; call `handler` outside any transaction; success → delete attempts row, cursor=seq; failure → `n+1`, `next_at = now + backoff_sec(n)`; if `now < next_at` for the event, stop the batch; if `n >= max_attempts` insert `parked`, advance past it. `prune` writes events older than `older_than` and with `seq <= min(cursor)` (all of them if no consumers) to the JSONL archive, deletes them, runs `PRAGMA wal_checkpoint(TRUNCATE)`, returns the count.

- [ ] **Step 1: Failing tests** (events published through the fixture with distinct ids/types/maturities; `handler` collects): `test_delivers_in_order_and_advances_cursor`; `test_second_consume_delivers_nothing`; `test_other_types_skipped_and_counted`; `test_low_maturity_skipped_counted_and_handler_not_called`; `test_recorder_with_min_maturity_implemented_receives`; `test_null_detector_event_passes_validated_gate`; `test_failure_stops_batch_and_records_attempt` (event 2 raises; event 3 not delivered; cursor == seq 1); `test_retry_waits_for_backoff` (immediate re-consume does not call handler; after advancing the fake clock past `next_at` it does); `test_poison_event_parked_and_stream_continues` (always raises with `max_attempts=2`; after enough clock steps event 3 is delivered and `parked()` has event 2 with `attempts==2`); `test_handler_may_publish_without_deadlock`; `test_backoff_sec_bounds` (`rnd=lambda:0` → half, `rnd=lambda:1` → full, large attempt → 300); health: `test_failed_poll_keeps_previous_last_ok_at`, `test_stale_sources_never_seen_and_old` (fake clock), `test_fresh_source_not_stale`; state: `test_state_roundtrip`; `test_stats_reports_lag`; prune: `test_prune_archives_then_deletes`, `test_prune_never_deletes_unconsumed`, `test_seq_not_reused_after_prune`.
- [ ] **Step 2:** run `pytest orchestrator/event_bus/tests/test_consume.py -q` → FAIL (`AttributeError: consume`).
- [ ] **Step 3:** Implement per Interfaces.
- [ ] **Step 4:** run → PASS; also run `test_store.py` and `test_envelope.py`.

### Task 4: A015 changes — enriched reports, poll status, `--exchange`

**Files:** Create `agents/A015_Exchange_Listing_Delisting_Intelligence/core/poll_status.py`; Modify `tools/ccxt_market_poller.py` (result gains `observed_at: str`, `spot_markets: int`), `cli.py`, `agent.yaml` (add `produces`); Test `tests/test_poll_status.py`.

**Interfaces — Produces:**
```python
# core/poll_status.py
POLL_STATUS_FILE: Path     # memory/poll_status.json
def write_poll_status(results: dict[str, dict], path: Path | None = None, now: datetime | None = None) -> dict
    # per exchange {ok, error, baseline, polled_at, spot_markets}; merges into the existing file (exchanges not polled this run are kept); atomic (tmp + os.replace)
def read_poll_status(path: Path | None = None) -> dict      # {} if missing or corrupt
```
`cli._log_events` adds to every report: `snapshot_digest` (= `res["old_digest"]`), `old_snapshot_at`, `observed_at`, `spot_markets`. `cli.poll(limit, exchange_ids)` calls `write_poll_status` after polling; `main` gains repeatable `--exchange` on `poll`. `agent.yaml` `produces`: the four `a015.*` types, `schema_version: 1`.

- [ ] **Step 1: Failing tests** (reuse the fake-exchange fixtures from `test_poller_hardening.py`, copying the helpers): `test_poll_writes_status_for_ok_failed_and_baseline` (three exchanges → `ok True/False`, `baseline True`); `test_status_merge_keeps_other_exchanges`; `test_corrupt_or_missing_status_reads_empty`; `test_status_write_is_atomic` (patch `os.replace` to raise → previous file intact); `test_event_log_reports_carry_digest_window_and_markets` (poll with a removed market; reload the written event file; assert `snapshot_digest`, `old_snapshot_at`, `observed_at`, `spot_markets == 99`); `test_exchange_flag_limits_polling` (`main(["poll","--exchange","binance"])` polls only binance).
- [ ] **Step 2:** `python -m pytest agents/A015_Exchange_Listing_Delisting_Intelligence/tests -q` → FAIL (new tests only).
- [ ] **Step 3:** Implement per Interfaces; keep existing behaviour and the 37 existing tests green.
- [ ] **Step 4:** run → all PASS.

### Task 5: A015 relay and health monitor

**Files:** Create `bootstrap/relays/__init__.py`, `bootstrap/relays/a015.py`, `bootstrap/relay.py`, `config/bus.json`; Test `bootstrap/tests/test_relay_a015.py`.

**Interfaces — Consumes:** Tasks 2–4. **Produces:**
```python
# config/bus.json
{"a015_exchanges": ["binance","bybit","coinbase","okx"], "a015_every_min": 15, "stale_factor": 2, "retention_days": 90}
# bootstrap/relays/a015.py
EVENT_TYPES = {"NEW_LISTING": "a015.listing.new", "DELISTING": "a015.listing.delisted",
               "STATUS_CHANGE": "a015.market.status_changed", "PAIR_CHANGE": "a015.market.pair_changed"}
def to_envelope(report: dict, detector_maturity: dict[str, str]) -> dict     # pure
@dataclass class RelayResult: published=0; duplicates=0; files=0; health_updated=0; rejected: list[str]
def relay_once(store: EventStore, *, event_log_dir=None, poll_status_path=None, detector_maturity=None) -> RelayResult
# bootstrap/relay.py
def monitor_once(store: EventStore, sources: list[str], max_age_s: float) -> list[str]   # newly stale sources
def main(argv: list[str] | None = None) -> int     # --once; builds store from build_store(); exit 1 on StoreBusy or any rejected
```
`to_envelope` mapping (spec §6/§10): `event_id` from the report; `source "A015"`; `subject f"market:{exchange}:{symbol}"`; `observed_at = report["observed_at"] or detected_at`; `event_window {from: old_snapshot_at, to: observed_at}` or `null` if `old_snapshot_at` absent; `detector {id: event_type, maturity: detector_maturity.get(event_type,"implemented"), ceiling: None}`; `confidence None`; `coverage {complete: True, as_of: observed_at, lag_s: None, note: f"spot only, {spot_markets} markets"}`; `evidence [{source: f"ccxt.fetch_markets:{exchange}", locator: f"snapshot:{snapshot_digest or 'unknown'}", retrieved_at: observed_at}]`; `trace_id "trc_"+event_id[4:]`; `untrusted False`; `data` = the schema's fields taken from the report (`base` via `core.symbols.base_of`). `relay_once`: walk `event_log/*.json` with name `>` `relay_state("a015","last_file")` in name order, skip files with torn JSON (counted in `rejected`), publish each report (an `EnvelopeError` → `rejected` entry, never stops the run), then set the mark; then for each exchange in `poll_status.json` call `record_health(f"A015:{ex}", ok=st["ok"] and not st["baseline"], detail=…, at=polled_at)`. `monitor_once` publishes one `system.source.stale` (source `SYS`, `event_id=make_event_id("stale", source, str(last_ok_at))`) per outage using `relay_state("monitor", f"stale:{source}")`, and clears the flag when the source is fresh again. `build_store()` (in `bootstrap/wire.py`) → `EventStore(manifests=<fleet manifests>)`.

- [ ] **Step 1: Failing tests:** one golden `to_envelope` test per type (assert `type`, `subject`, `detector.maturity=="implemented"`, `confidence is None`, evidence locator, and that `validate_event` accepts it); `test_relay_publishes_and_advances_mark` then `test_relay_twice_only_duplicates_when_mark_cleared`; `test_torn_event_file_is_skipped_not_fatal`; `test_report_missing_symbol_rejected_and_run_continues`; `test_report_without_digest_still_publishes_with_unknown_locator`; `test_baseline_poll_is_not_ok_health`; `test_corrupt_poll_status_updates_no_health`; `test_monitor_flags_once_per_outage_and_clears_on_recovery`; `test_never_seen_source_is_stale`; `test_main_exits_1_when_store_busy` (monkeypatch store to raise `StoreBusy`).
- [ ] **Step 2:** `python -m pytest bootstrap/tests/test_relay_a015.py -q` → FAIL (import).
- [ ] **Step 3:** Implement per Interfaces.
- [ ] **Step 4:** run → PASS.

### Task 6: Librarian consumer, persistent brain, CLIs

**Files:** Create `bootstrap/consumers/__init__.py`, `bootstrap/consumers/librarian.py`, `bootstrap/consume.py`, `bootstrap/bus_stats.py`; Modify `bootstrap/wire.py` (`build_store`, `build_brain`); Test `bootstrap/tests/test_librarian.py`.

**Interfaces:**
```python
BRAIN_DB: Path    # <repo>/data/brain/brain.db
def librarian_handler(brain: Brain) -> Callable[[dict], None]   # skips if brain.history("markets", f"event:{id}") non-empty; else brain.write("markets", f"event:{id}", event, by="librarian")
def run_once(store: EventStore, brain: Brain) -> ConsumeStats    # name "librarian", types ["a015.*"], min_maturity="implemented"
# consume.py: main(argv) -> int (--once; prints ConsumeStats; exit 1 if parked grew); bus_stats.py: main(argv) -> int (prints store.stats(), parked, source health; --approvals lists pending)
```
- [ ] **Step 1: Failing tests:** `test_event_lands_in_markets_with_label` (value keeps `detector.maturity`, written_by `librarian`); `test_redelivery_adds_no_new_version` (`len(brain.history(...))==1` after `run_once` twice and after resetting the cursor); `test_brain_persists_across_instances` (tmp file); `test_run_once_idempotent`; `test_bus_stats_prints_lag_and_stale` (capsys).
- [ ] **Step 2–4:** run `pytest bootstrap/tests/test_librarian.py -q` → FAIL → implement → PASS.

### Task 7: `contracts` sentinel check

**Files:** Create `security/sentinel/checks/contracts.py`; Modify `security/sentinel/sentinel.py` (add the check; pass the loaded fleet list); Test `security/sentinel/tests/test_contracts.py`; grep `dashboard/frontend` for fixed check counts and adjust if it assumes 6 columns.

**Interface:** `def check_contracts(record: AgentRecord, policy: dict, fleet: list[AgentRecord], schemas: dict[str, dict] | None = None) -> CheckResult` — FAIL when a `produces` type has no schema; HOLD when a `consumes` pattern matches no `produces` in the fleet nor a platform schema; PASS otherwise (including "no contracts declared").
- [ ] **Step 1: Failing tests:** `test_no_declarations_passes`; `test_produces_unknown_type_fails`; `test_orphan_consume_holds`; `test_consume_matched_by_other_agent_passes`; `test_consume_matched_by_platform_type_passes`; `test_real_fleet_a015_passes` (via `run_sentinel`).
- [ ] **Step 2–4:** run `pytest security/sentinel/tests -q` → FAIL → implement → PASS. Update any existing test that hard-codes 6 checks per agent; the two known-red T03 tests must stay the only failures.

### Task 8: Supervisor jobs

**Files:** Modify `live/supervisor.py`, `live/README.md`; Test `live/test_supervisor_hardening.py`.

**Interfaces:** `a015_poll() -> bool` (`run([...A015 cli, "poll", "--exchange", ex …])` for each exchange in `config/bus.json`); `bus_cycle() -> bool` (`run(["bootstrap.relay","--once"])` then `run(["bootstrap.consume","--once"])`, True if both exit 0). `tick` job table becomes `a002, a001, a015 (every a015_every_min), bus (every 1 min)`; `_fresh_state` gains `a015_*`/`bus_*` keys; the startup loop forces all four due; config read with `json` (supervisor stays stdlib-only).
- [ ] **Step 1: Failing tests** (monkeypatch the job functions): `test_a015_runs_on_its_own_cadence`; `test_failed_a015_does_not_block_bus_cycle`; `test_old_state_gains_a015_and_bus_keys`; `test_a015_command_lists_all_configured_exchanges` (capture the `run` args).
- [ ] **Step 2–4:** `pytest live/test_supervisor_hardening.py -q` and `python live/test_supervisor.py` → FAIL → implement → PASS.

### Task 9: Slice 1b — persisted trace and approval queue

**Files:** Modify `orchestrator/event_bus/{trace,bus,store}.py`, `bootstrap/wire.py` (`build_bus(repo_root=None, store=None)`), `bootstrap/bus_stats.py`; Test `orchestrator/event_bus/tests/test_persistence.py`.

**Interfaces:**
```python
TraceLog(entries=[], sink: Callable[[dict], None] | None = None)      # sink(entry) after each append
MessageBus(..., on_hold: Callable[[Message, str], int | None] | None = None)   # held Response.payload gains {"approval_id": id}
EventStore.record_trace(entry: dict) -> None
EventStore.trace_for(trace_id: str) -> list[dict]
EventStore.hold(message: dict, reason: str) -> int
EventStore.pending_approvals() -> list[dict]
EventStore.decide(approval_id: int, approved: bool, by: str) -> bool     # False if already decided
```
- [ ] **Step 1: Failing tests:** `test_trace_sink_receives_every_entry`; `test_trace_survives_a_new_bus_instance` (`build_bus(store=store)` send → new store object over the same file → `trace_for(trace_id)` has `send`+`response`); `test_held_message_creates_pending_approval` (`status=="held"`, `payload["approval_id"]`); `test_decide_once` (second `decide` returns False; status stored); `test_bus_without_store_unchanged` (existing behaviour).
- [ ] **Step 2–4:** run → FAIL → implement → PASS; rerun `orchestrator bootstrap` suites.

### Task 10: End-to-end, architecture test, docs

**Files:** Create `tests/integration/test_event_bus_e2e.py`; Modify `tests/test_architecture.py` (agents-import rule extended from A001/A002 to every `agents/*` dir; any pre-existing violation is recorded in BUILD_LOG, not skipped silently), `PROJECT_STATE.md`, `BUILD_LOG.md`, `docs/manual/02-structure.md` (new files), spec status line (`Slice 1/1b implemented`).
- [ ] **Step 1: Failing test** `test_a015_poll_to_brain_end_to_end`: fake exchange (spot, 100 → 99 markets), tmp dirs for snapshots/event_log/poll_status/bus.db/brain.db → `cli.poll` → `relay_once` → `run_once`; assert `brain.read("markets", f"event:{id}")` has `type == "a015.listing.delisted"` and `detector.maturity == "implemented"`; rerun the whole chain → no new rows/versions; set the fake clock past 30 min → `monitor_once` publishes one `system.source.stale`.
- [ ] **Step 2–4:** run → FAIL → fix wiring gaps → PASS.
- [ ] **Step 5: Verify everything:** `pytest orchestrator bootstrap brain security tests live -q` (only the 2 known T03-secret failures), each agent suite in its own process (A002 64+, A007 11, A015 37+new, T01 53, T03 18), `python live/test_supervisor.py`, then one real offline smoke: `python -m bootstrap.relay --once` and `python -m bootstrap.bus_stats` against a temp `--db`.
- [ ] **Step 6: Docs:** PROJECT_STATE (overwrite Phase 1 bullet), BUILD_LOG entry with tags, self-critique and open questions, manual file table.

## Self-review

Spec coverage: envelope §6 → T1; store §8 → T2/T3; delivery §9 → T3; relays/coverage/scheduling §10 → T4/T5/T8; consumer §11 → T6; contracts §7 → T7; trace/approvals §12 (1b) → T9; evaluation gate §15 → T10. Out of scope by decision: Slice 2/3, dashboard pages, A002/A001 relays. Names used across tasks (`relay_once`, `monitor_once`, `run_once`, `build_store`, `ConsumeStats`, `StoreBusy`) are defined once in Interfaces.
