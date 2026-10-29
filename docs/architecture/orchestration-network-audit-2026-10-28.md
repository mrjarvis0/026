# 026 orchestration, bus aur pipelines — audit aur sudhaar ka plan

> **Date:** 2026-10-28 · **Type:** research + audit (koi code nahi badla) · **Tag:** BUILD-NEW (doc)
> **Scope:** sirf orchestration, agent-to-agent connectivity/messaging aur data pipelines.
> Trading logic aur UI scope ke bahar hain.
>
> **Method:** 3 Explore agents ne code padha (A001/A002/A007/A015; T01/T02/T03 + supervisor + infra;
> platform + scaffolds + promised-vs-built) aur 20+ academic/official sources se milaya gaya.
> Audit claims **code padhkar** nikle, chalaye nahi gaye. Jo claims "verified" mark hain wo maine
> seedha grep/read se confirm kiye.

## Seedha nateeja

026 ka bus design sahi hai (gate, budget, trace), par abhi ek chalta hua system nahi hai.
Production me agents ke beech **ek bhi message nahi jaata**. Isliye A015 ka delisting T01 tak nahi
pahunch sakta, aur A002 ka rumor A001 ko nahi jaga sakta. Orchestration ka kaam abhi
`live/supervisor.py` karta hai, jo bus ke bahar hai aur 10-20 se band hai.

## 1. Abhi ki asli haalat

### Verified (seedha code/log se)

- **Bus kahin use nahi hota.** `bus.send()` sirf tests aur `dashboard/backend/trace_round.py` me hai.
  Bus 68 lines ka synchronous point-to-point hai (`orchestrator/event_bus/bus.py`).
- **Gate optional hai.** `message.action` na ho to gate chalta hi nahi (`bus.py:46`).
- **`usd` budget kabhi kharch nahi hota.** Sirf `calls` ghatte hain (`bus.py:59`).
- **Orchestrator khali hai.** `router/`, `scheduler/`, `workflows/`, `memory/` me files nahi;
  `orchestrator/core/__init__.py` 0 bytes; `config/models/models.yaml` 0 bytes; `tools/` khali.
- **Brain kahin persist nahi hota.** `Brain(...)` sirf tests, adapters aur dashboard checker me.
  `global` aur `entities` ka koi writer nahi.
- **Supervisor 10-20 se band.** `live/supervisor.log` ki aakhri line ek A001 ingest ka start hai,
  exit nahi. `state.json`: `a001_last` 10-13, `a002_last` 10-20. Audit ke din 10-28.
- **T01 me T03 ka veto dead code.** `decide()` (`T01/backend/strategy/engine.py:101`) ka koi caller
  nahi; live loop seedha `generate_signal` chalata hai (`T01/backend/bot.py:255`).
  Commit `5d5cb61` ka "T03 consensus wired into T01 decide()" claim galat nikla.
- **Real enable/disable asar nahi karta.** Dashboard throwaway `RealEngine()` banata hai
  (`T01/backend/main.py:243`, `:251`); bot ka apna instance hai (`bot.py:41`).

### Agents ke audit se (code padha, chalaya nahi)

- **Do adapter families:** `bootstrap/adapters.py` payload me `op` padhta hai,
  `orchestrator/adapters/*.py` `intent`. A002 ke do incompatible handlers hain; `bootstrap/wire.py:17`
  sirf A001 aur A002 register karta hai. `orchestrator/adapters/a002.py` `agents.*` import karta hai,
  isi se `tests/test_architecture.py` red hai.
- **Execution bus ke bahar:** T01 real orders aur T03 scalper sentinel gate se nahi guzarte.
  Sentinel ka execution scan `execution_enabled` agents skip karta hai
  (`security/sentinel/checks/execution.py:9-10`).
- **Trace aur approvals memory me:** `TraceLog.entries` in-memory list; `held` sirf trace entry +
  Response, persist nahi.
- **Namespace drift:** A015 `markets` likhta hai, T02 `market`. `projects.*` par last writer jeetta
  hai (`brain/store.py:55-57`), conflict record nahi hota. `brain/store.py:41-49` me version
  `SELECT MAX` + `INSERT` non-atomic hai.
- **Supervisor:** lock nahi, retry nahi, `run()` kuch return nahi karta to timeout bhi "success"
  gina jaata hai, `state.json` non-atomic likha jaata hai.
- **Registry flags galat:** `kernel_wired` A001 ke liye false (code me wired), A015 ke liye true
  (`wire.py` me nahi). AGENTS.md §3 me T03 nahi, to sentinel registry check T03 ko FAIL karega.
- **Promised-vs-built:** planner, router, scheduler, workflows, fleet-level fusion, entity ledger,
  model router, trace persistence, approval queue, pub/sub — sab AGENTS.md/ADR me promised,
  code me nahi. USD budget field hai par kharch nahi hota; default 100 calls vs spec 500 calls / $0.25.

## 2. Har agent: sabse badi kami aur kya jodna chahiye

| Agent | Sabse badi pipeline/connectivity kami | Kya emit/consume karna chahiye |
|---|---|---|
| **A001** | Checkpoint store se aage badh jaata hai (`ingestion/poller.py:339-343`), crash par permanent hole. `investigate` ke findings persist nahi hote aur bus par exposed nahi. 60 blocks/30 min chain se slow, lag ka signal nahi. "Read-only" adapter migrate/WAL pragma chalata hai. | Emit: exchange-flow, exploit-outflow (DET-EXPLOIT-02 manifest me bhi nahi), ingest-stalled/lag. Consume: A002 rumor (address/protocol watch-list). |
| **A002** | RSS `pubDate` (RFC-822) parse nahi hota to publish time fetch time ban jaata hai (`normalize.py:52-64`). Dedup copies drop karta hai, link nahi, jabki manifest "copies confirmation nahi" kehta hai. `core/resilience.py` (382 lines) kahin import nahi. API keys URL me, logs me leak. `a002.db` WAL me nahi. Items commit hone ke baad clustering fail ho to items kabhi cluster nahi hote. | Emit: rumor opened/flip, retraction, scheduled events. Consume: A015 announcements, A001 anomalies. |
| **A007** | Mock-only. `uuid4` id + `INSERT OR IGNORE` = rerun par duplicates. `mock=False` -> `[]`, "koi trade nahi" se alag nahi dikhta. Clusters `transaction_date` par bante hain, filing 45 din late public hoti hai => look-ahead risk. | Emit: cluster/correlation with `known_at`. Consume: A002 ticker rumors. |
| **A015** | Snapshot detection se pehle overwrite hota hai. Fetch fail par `{}` => mass false DELISTING ban sakti hai (shrink check nahi). Cold start par NEW_LISTING flood. `memory/event_log/` hamesha khali => adapter hamesha `count: 0`. Spot/swap/future/option mixed. `stated_reason` hamesha "unspecified". | Emit: DELISTING, HALT (T01 pause ke liye). Consume: A002 rumors. |
| **T01** | Bus par nahi; memory `reads: []`; A-series ka koi signal nahi pahunchta; hard-coded local gates (`_guard`, circuit breaker). Real position ke dauraan `ready()` false ho to paper engine par switch, open real position unmanaged. | Consume: A015 delisting/halt, A012 risk. |
| **T03** | Scalper ka `RiskEngine` har step fresh banta hai aur dict ko float ki jagah pass karta hai => daily-loss/drawdown breakers trip nahi ho sakte. Cache key me aaj ki date => intraday bars pehle download par jam jaate hain. Order bhejne ke baad state save hota hai => crash par order dobara. Gate sirf string constant (`HUMAN_CONFIRM_TOKEN`). | A005 (market data) ka intezaar. |
| **T02, A006** | T02 bus par nahi, `swarm.db` WAL nahi. A006 sirf manifest. | Pehle bus contract, phir wiring. |
| **A003-A018 baaki** | Sirf README (manifest nahi). | `produces/consumes` declare karo build se pehle. |

**Intended feeds (READMEs se):** A005 -> A009, A010, A012, A013, A014, T01, T02, T03.
A016/A017/A018 -> A013 (arbitrage pause). A009, A010, A014, A017 -> A012 -> gate -> T01/T03.
A015 -> T01 kahin declare nahi.

**Overlaps:** teen TA engines (A009, T03, T01), teen risk engines (A012, T03 `core/live/risk.py`,
T01 breaker), "correlation" ke teen matlab (A014, A002 cross-asset, orchestrator fusion). Fleet-level
fusion kahin nahi; sirf T03 (`core/futures/fuse.py`) me local.

## 3. Research kya kehti hai aur 026 pe matlab

| Source | Finding | 026 ke liye |
|---|---|---|
| [MAST, Berkeley (arXiv 2503.13657)](https://arxiv.org/abs/2503.13657) | 1,600+ traces, 14 failure modes, 3 categories: system design, inter-agent misalignment, task verification. | Message contracts aur verification step zaroori; sirf behtar model kaafi nahi. |
| [Scaling agent systems (arXiv 2512.08296)](https://arxiv.org/abs/2512.08296) | Bina central verification errors zyada phailte hain. v1: independent 17.2x vs centralized 4.4x; latest abstract: parallelizable financial reasoning +80.8%, sequential planning -70%. **Numbers versions me alag.** | Orchestrator ko validation bottleneck rakho. T01/T03 free-run na karein. Fan-out sirf parallel kaam me. |
| [Anthropic multi-agent research (official)](https://www.anthropic.com/engineering/multi-agent-research-system) | Har subagent ko objective, output format, tools, boundaries. Effort-scaling rules prompt me. Checkpoint se resume. Bade outputs external store me, sirf reference pass. Multi-agent ~15x tokens. Synchronous execution slowest subagent par block hota hai. | Brain me artifact-by-reference. Budget per trace. Resume-capable workflows. |
| [Magentic-One (arXiv 2411.04468)](https://microsoft.github.io/autogen/0.4.9/user-guide/agentchat-user-guide/magentic-one.html) | Orchestrator: task ledger (plan + facts) + progress ledger (loop detection, agla agent). | Planner ko ledger banao; shuru me deterministic playbooks. |
| [A2A spec v1.0](https://a2a-protocol.org/latest/specification/) | Agent Card (identity, skills, auth). Task states: SUBMITTED, WORKING, INPUT_REQUIRED, AUTH_REQUIRED, COMPLETED, FAILED, CANCELED, REJECTED. Streaming + push. | `agent.yaml` ko Agent Card ki tarah. `held` ko AUTH_REQUIRED jaisi persisted state. HTTP nahi, sirf data model. |
| [MCP tools spec](https://modelcontextprotocol.io/specification/2025-06-18/server/tools) | Declared output schema, client validate kare. Protocol error aur execution error alag channels. | "Unknown intent" abhi `ok=True` aata hai — error banao. |
| [CloudEvents](https://docs.cloud.google.com/eventarc/docs/cloudevents-json) (secondary doc) | Required: `specversion`, `id`, `source`, `type`. Optional: `time`, `subject`, `dataschema`. | Fleet ka common event envelope. |
| [Transactional outbox](https://microservices.io/patterns/data/transactional-outbox) | Event business change ke saath ek hi transaction me. At-least-once => consumer idempotent (processed-id table). Outbox table prune karo. | A015 snapshot + event atomic. Consumers dedup. |
| [AWS Builders' Library](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter) | Retries "selfish". Capped exponential backoff with jitter. Timeout upar wali layer ki deadline respect kare. | Supervisor aur A002 fetch. |
| [OTel GenAI spans](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-agent-spans) | `invoke_agent`, `execute_tool` spans. Spec abhi "Development" status me. | TraceLog persist, field names milao. |
| [Prompt Infection (arXiv 2410.07283)](https://arxiv.org/abs/2410.07283) | Compromised agent se injection doosre agents me phailta hai. | A002 untrusted news padhta hai; output sirf structured fields, raw text kabhi instruction na bane. |
| OWASP Agentic Top 10, ASI07/ASI08 ([secondary](https://goteleport.com/blog/owasp-top-10-agentic-applications)) | Insecure inter-agent comms, cascading failures. Defence: signed/authenticated messages, blast-radius isolation, least agency. | Sender verify. Official OWASP document tak nahi pahunche. |
| Blackboard ([2510.01285](https://arxiv.org/abs/2510.01285), [2507.01701](https://arxiv.org/abs/2507.01701)), [MetaGPT](https://arxiv.org/abs/2308.00352) | Shared board par agents khud decide karte hain contribute karna hai (13-57% behtar, authors ka claim). MetaGPT: pub/sub message pool, structured outputs. | Brain ko subscribable blackboard. |
| [AgentPrune, ICLR 2025](https://arxiv.org/abs/2410.02506) | Redundant messages prune: 28-73% tokens bachat. | Broadcast nahi, relevance-based subscription. |
| [Collaborative Memory (arXiv 2505.18279)](https://arxiv.org/abs/2505.18279) | Har memory fragment par immutable provenance; private/shared tiers; read/write policies. | AGENTS.md §7 se match. Brain records me provenance fields. |
| [Covariance Intersection](https://en.wikipedia.org/wiki/Covariance_intersection) | Unknown correlation me bhi consistent fusion, conservative. | Sirf analogy; evidence double-counting par direct source nahi mila. |
| [FIPA Contract Net](https://www.fipa.org/specs/fipa00029/XC00029G.html) | `cfp` me deadline, phir propose/refuse/accept/reject. | "Kaun jawab de sakta hai, kitne samay me" routing pattern. |
| [TradingAgents (2412.20138)](https://arxiv.org/abs/2412.20138), [FinCon (2407.06567)](https://arxiv.org/abs/2407.06567) | Dono me trader aur execution ke beech risk layer. FinCon hierarchical (zyada discussion costly/slow). | A012 -> gate -> T01/T03 ka shape sahi. |
| [LangGraph durable execution](https://docs.langchain.com/oss/python/langgraph/durable-execution), [Temporal](https://docs.temporal.io/ai) | Checkpointer + thread id se resume; steps idempotent. | Workflows ke liye SQLite checkpoint. |

## 4. Smart banane ka design

1. **Common event envelope** (CloudEvents jaisa): `event_id`, `schema_version`, `type`
   (jaise `a015.delisting.detected`), `source`, `subject` (entity key), `event_time` /
   `observed_at` / `known_at` alag-alag, `trace_id`, `parent_id`, `confidence` + `ceiling` +
   `maturity`, `coverage` (window, complete, lag), `evidence_refs`, `data`.
2. **Durable bus bina naye infra ke.** SQLite WAL me `events` table (outbox) +
   `deliveries(consumer, event_id, attempts, next_at)`. At-least-once, consumer side
   `processed(consumer, event_id)` se dedup. Single-operator Windows setup par Redis/Kafka overkill;
   ADR-0003 ka Redis baad me.
3. **Manifest me `produces` / `consumes`.** Sentinel check: har consumer ka producer, har topic ka
   schema. Isse orphan namespaces (`market` vs `markets`) pakde jaate hain.
4. **Entity ledger.** Canonical id + aliases (ticker, `chain:contract`, exchange symbol, insider
   naam/CIK). Iske bina A001, A002, A015, A007 join nahi ho sakte.
5. **Orchestrator ko dimaag.** Pehle deterministic playbooks, jaise "delisting rumor": A002 ->
   A015 (confirm?) + A001 (exchange wallet outflow) -> fuse. Router agent cards se capability
   dekhe. Scheduler supervisor ki jagah le: lock, retry with jitter, heartbeat. LLM planner baad me.
6. **Fusion rules.** Min-confidence, conflicts record, split provenance (AGENTS.md §4) rakho.
   Jodo: independence **underlying source** se naapo, agent se nahi — A002 rumor aur A015
   announcement ek hi source se aa sakte hain.
7. **Gate mandatory.** Har message type ka default action. `held` persisted approval queue me.
   Gate sentinel ka *capped* trust level padhe, declared level nahi.
8. **Event-driven reactions, timer nahi.** A002 rumor par A001 sirf related addresses ka targeted
   ingest. A015 delisting par T01 pause.
9. **Coverage aur health pehle se.** Har event me `as_of` + `lag`. Heartbeat events; sentinel
   staleness dekhe. Supervisor 8 din band raha aur kisi ko pata nahi chala.
10. **Calibration loop.** A002 `resolve` aur T01 reflection ke outcomes brain me, maturity gates
    ko feed karein.

## 5. Roadmap (priority se)

- **Phase 0 — bug fixes (chhota, sabse zyada asar):**
  - Dead T01 veto ko live loop me jodo ya hata do; T03 ka symbol T01 ke symbol ke saath chale.
  - Supervisor: lock, atomic state, exit-code check, retry with jitter, heartbeat; phir restart.
  - Real enable/disable ek hi source of truth se.
  - Bus: default gate, `usd` spend, handler timeout, duplicate register par error, unknown intent
    par `ok=False`.
  - Adapters ek family me, `intent` standard (red architecture test bhi theek).
  - A015: atomic event log, fetch fail par snapshot na mitao, market-type filter.
  - A002: RSS date parse (stdlib `email.utils.parsedate_to_datetime`), `resilience.py` wire,
    key redaction, WAL.
  - A007: natural key + `known_at`.
  - Registry flags aur AGENTS.md §3 (T03) sach karo.
- **Phase 1 — durable bus:** envelope, SQLite outbox, subscribe/consume, trace persist.
- **Phase 2 — orchestrator:** ledger planner, capability router, scheduler, budget per trace.
- **Phase 3 — fusion aur entity ledger.**
- **Phase 4 — execution gate:** T01/T03 orders bus aur gate se guzarein.

## 6. Operator ke faisle (trust boundaries)

- **Money gate (ADR-0002).** Gate abhi saare execution kinds deny karta hai. T01/T03 orders ko gate
  ke through bhejna design me bada badlaav; AGENTS.md ka escalation boundary — operator ki
  manzoori ke bina nahi.
- **LLM planner.** API key + cost. Salah: pehle deterministic playbooks.
- **Bus transport.** SQLite (salah) ya ADR-0003 ka Redis.

## 7. Kitna bharosa karein

- Teeno audits code padhkar hue, kuch chalaya nahi. Sabse bade claims upar "Verified" me alag hain.
- Scaling paper ke numbers versions me alag.
- OWASP aur CloudEvents ke liye secondary sources mile, official text nahi.
- A2A ka well-known URI path spec ke us hisse me nahi mila jo fetch hua.
- OTel GenAI conventions abhi "Development" status me.
- Covariance Intersection sirf analogy hai.

## Self-critique

- **Fragile:** per-agent findings Explore agents ke code-read par tike hain; line numbers us din ke
  tree ke hain aur badal sakte hain.
- **Assumed:** SQLite-based bus single-operator load ke liye kaafi hai; throughput measure nahi kiya.
- **Untested:** koi test/run nahi hua is session me; Phase 0 items ko fix karte waqt dobara
  reproduce karna hoga.

## Agla session kahan se shuru kare

Phase 0, is order me: T01 dead veto + real enable/disable, supervisor hardening + restart, bus
fixes (`bus.py`), adapters unify. Phir Phase 1 ka envelope design review.

## Phase 0 ke baad (2026-10-28) — corrections aur status

Phase 0 isi din test-first complete hua; detail `BUILD_LOG.md` (2026-10-28) me. Is report ke kuch
claims jaanch ke baad badle:

- **`usd` budget:** "kabhi kharch nahi hota" overstated tha. Bus usd enforce karta hai; kharch wo
  handler karta hai jise cost lagti hai. Abhi koi handler paisa kharch nahi karta, isliye ye bug nahi.
- **Supervisor:** "10-20 se band / crash" imprecise tha. Wo manually/login par launch hota hai, band
  hona normal hai. Asli kami band hone ka signal na hona thi: ab `--status` + heartbeat hai.
- **T01 veto:** 2026-10-27 wala wiring dead code tha (confirmed). Ab live: BUY entries par hi, T01 ke
  traded symbol ke liye.
- **Fixed (Phase 0):** bus gate/timeout/duplicate/error, adapters ek family me, supervisor
  lock/retry/atomic state, T01 real enable/disable, A015 baseline/shrink-guard/spot-only/event_log,
  A002 dates/redaction/retry/WAL, A007 natural key/known_at, registry + docs.
- **Abhi bhi khula:** T03 sentinel secret false-positive (operator decision), T03 scalper
  `RiskEngine`, A002 dedup/clustering gap, adapters ka "read" path par DDL, A001 checkpoint-vs-store,
  aur Phase 1+ (event envelope, outbox, orchestrator, entity ledger, execution gate).
