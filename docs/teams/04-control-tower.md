# 04 · Control Tower (`X`) — agents ki dekh-bhaal

[← Trading Desk](03-trading-desk.md) · [Teams](README.md) · *Next: [Handoffs aur contracts](05-handoffs-and-contracts.md)*

> **Mission:** A, R, T aur platform ko **chalte, sahi aur surakshit** rakhna — orchestration design, pipeline, communication aur handoff, rules, failure sambhalna, self-improvement, registry. Series `X`, IDs `X01`, `X02` … (T01 jaisi 2-digit).
>
> **Status:** poori team **planned**. Kuch bana nahi. Ye doc roster, jimmedari aur build order tay karta hai.

## 1. Steward vs machinery

Platform actors (`orchestrator`, `sentinel`, `librarian`, `operator-io`) **machinery** hain aur alag rehte hain (operator ka faisla). X unke upar baithi **stewards** hain.

| Machinery (execute karta hai) | Ghar | Steward (design/monitor/tune/repair) |
|---|---|---|
| `orchestrator` — bus, route, fuse | `orchestrator/` | X01 Conductor, X02 Courier |
| `sentinel` — trust, gate, scan | `security/` | X04 Rulesmith, X05 Medic |
| `librarian` — brain curation | `brain/`, `bootstrap/consumers/` | X02, X07 |
| `operator-io` — console, approvals | `dashboard/` | X07 (health feed) |
| supervisor — timer jobs | `live/supervisor.py` | X03 Pipeline Keeper, X05 |

**Teen hard rules:** X orchestrator ko replace nahi karta · X sentinel ko bypass nahi karta · X na market data fetch karta hai na trade karta hai.

## 2. Roster — X01 se X07

> Har blok: kaam · kya steward karta hai · **aaj code me kya beej hai** · input → output · trust/tools · pehla slice.

### X01 Conductor — orchestration design
- **Kaam:** playbooks likhna (deterministic), routing table, per-trace budget, fusion rules ka config. `orchestrator/` unhe *chalata* hai.
- **Aaj ka beej:** `orchestrator/event_bus/` (bus, trace, budget, gate hook). `router/`, `scheduler/`, `workflows/`, `memory/` — **0 files**. Fleet-level fusion kahin nahi.
- **Input → output:** manifests + bus trace → playbook files, routing table, budget policy.
- **Pehla playbook (audit §4.5 se):** *"delisting rumor"* = A002 rumor → A015 (confirm?) + A001 (exchange-wallet outflow) → fuse, min-confidence, split provenance.
- **Trust/tools:** 1; read-only on manifests/trace; playbook change = proposal.
- **Pehla slice:** playbook file ka format + ek playbook + `orchestrator` ka playbook runner (X01 sabse **aakhir** me, baaki X ke baad).

### X02 Courier — communication aur handoff
- **Kaam:** event schema registry, `produces`/`consumes` contract, subscription model, handoff packet + task states, poison/backpressure handling. Detail: [05](05-handoffs-and-contracts.md).
- **Aaj ka beej:** `orchestrator/event_bus/envelope.py` (validator), `store.py` (cursor/retry/park), `config/events/*.yaml` (5 schemas), `bootstrap/relays/a015.py`, `bootstrap/consumers/librarian.py`, sentinel `contracts` check.
- **Gap:** ek producer, ek consumer; `subscribe` API nahi; `consumes` kahin declare nahi.
- **Trust/tools:** 1; `store.read`; schema/contract changes = proposal.
- **Pehla slice:** manifest `consumes` field + sentinel `contracts` check use bhi dekhe.

### X03 Pipeline Keeper — pipeline
- **Kaam:** schedule/DAG, data contracts, freshness SLO, backfill/replay, `prune`.
- **Aaj ka beej:** `live/supervisor.py` — timer jobs (`a001` 30 min, `a002` 120, `a015` 15, `bus` 5; `_due()` `supervisor.py:226`; jobs `:289-292`), OS lock, retry+jitter, heartbeat, `--status`.
- **Gap:** dependency nahi dekhta; `prune` ka koi caller nahi (`store.py:338` sirf definition); replay sirf A015 ke log se.
- **Trust/tools:** 1; `store.read`; schedule changes = Evolver ke auto-lane me hi (§3) ya proposal.
- **Pehla slice:** `prune` schedule + `source_health` se freshness SLO table.

### X04 Rulesmith — rules design
- **Kaam:** policy-as-data, rule versioning, rule tests (golden allow/hold/deny), trust-tier / `execution_tier` design ([03](03-trading-desk.md) §3), hard-coded rules ki inventory. **Enforce sentinel karta hai; X04 design karta hai.**
- **Aaj ka beej:** `security/policies/sentinel.yaml` (banned primitives, secret regex, advice terms), `security/sentinel/gate.py` (deny-by-default), manifest `charter`, aur hard-coded: T01 `_guard()`, T03 `RiskEngine`.
- **Gap:** rules 3 jagah; versioning/test nahi; `execution_tier` undefined; money-gate bana nahi.
- **Trust/tools:** 1 → 2; policy files read; **koi bhi rule change operator approval se** (trust boundary).
- **Pehla slice:** rule inventory (har rule kahan rehta hai) + gate ke golden tests.

### X05 Medic — failure handling
- **Kaam:** supervision spec, orchestrator-level circuit breakers/bulkheads, **kill switch**, incident log, dead-man switch, idempotency/saga rules.
- **Aaj ka beej:** supervisor retry+jitter+backoff; A015 `system.source.stale` event; T01 local `backend/safety/circuit_breaker.py`. **Fleet kill switch nahi** (platform code me grep: koi nahi).
- **Design ([Erlang OTP](07-research.md#failure-handling)):** har job-class ko restart *strategy* (`one_for_one` default; `rest_for_one` jahan order ho — jaise relay → consume), `MaxR`/`MaxT` restart-intensity (zyada baar girne par band karke operator ko escalate), `transient` vs `permanent` jobs.
- **Kill switch:** *engage* X05 ya operator kar sake (fail-safe), *disengage* sirf operator. Teeno level: global / team / agent. **Trust-boundary — operator approve karega.**
- **Dead-man switch:** A015 stale (bina naya fact) → Desk naye entry pause. Wahi "Slice 2" jo [BUILD_LOG](../../BUILD_LOG.md) me design-review ke liye rukka hai.
- **Idempotency:** har order par idempotency key (T03: order bhejne ke *baad* state save hota hai → crash par order dobara — audit).
- **Trust/tools:** 1 → 2; `store.read`; flags likhna operator-approved.
- **Pehla slice:** incident log + silent-death alert; kill switch ka *design review* (build nahi).

### X06 Evolver — self-improvement
- **Kaam:** calibration ledger (prediction → outcome), shared eval harness, proposals (diff + evidence + eval result), staged rollout, rollback, lineage log. Niyam: §3.
- **Aaj ka beej (alag-alag jagah):** T01 `strategy/engine.py:149 self_tune` + `reflection.py`; A002 `resolve`/`metrics`/`backtest`; A001 `evaluation/promotion.py` (detector promotion).
- **Gap:** koi shared ledger/harness/rollback nahi; sab local.
- **Trust/tools:** 1; `store.read`; kuch bhi seedha nahi likhta (§3 ke lanes).
- **Pehla slice:** **read-only calibration report** (koi auto-change nahi) + auto-lane allowlist file.

### X07 Registrar — registry, lifecycle, health, cost
- **Kaam:** lifecycle states + owner + dependencies, **computed** registry flags, silent-death detector, cost/budget rollup, fleet health feed.
- **Aaj ka beej:** `config/agents/registry.yaml` (haath se bharte hain; audit me `kernel_wired` galat nikla), sentinel `registry`/`manifest`/`trust` checks, `bootstrap/bus_stats.py`, supervisor heartbeat (`--status`).
- **Gap:** lifecycle/owner/dependency catalog nahi; heartbeat ko koi dekhta nahi; `observability/` 0 files.
- **Reference:** [AWS AgentOps03](07-research.md#agentops) — owner + lifecycle state + single catalog + dependency tracking.
- **Trust/tools:** 1; read-only.
- **Pehla slice:** computed flags + supervisor-not-running alert.

### X08+ (reserved)
"Baaki dekh lenge": runbook archivist, red-team (prompt-injection tests A002 pipeline par), cost controller, replay simulator.

## 3. Self-improvement ke teen lanes (operator ka faisla: low-risk auto)

| Lane | Kya | Guardrails |
|---|---|---|
| **1 · Auto** | sirf **allowlist** ke operational knobs: poll interval, retry count/backoff, batch size | bounded range · reversible · **non-money** · metric regress par **auto-rollback** · har change lineage log me |
| **2 · Propose-only** | rules/policies, detector thresholds aur maturity, prompts, model tier, code | proposal (diff + evidence + eval result) → eval gate → **operator approval** → staged rollout |
| **3 · X ke liye mana** | T agents ke trading params, execution gate, signing/funds, secrets, trust levels | [AGENTS.md](../../AGENTS.md) §9 escalation boundaries |

**Research ne kya sikhaya:** DGM me self-improvement tabhi chala jab har change *sandbox + benchmark + traceable lineage* ke saath hui. AWS AgentOps: changes sirf agent-specific eval gates, staged rollout aur auto-rollback se. Dono ka matlab: auto-lane tabhi safe hai jab rollback aur lineage pehle se ho — isliye X06 ka pehla slice **read-only report** hai, auto nahi. ([07](07-research.md#self-improvement))

**Flag — grandfathered:** T01 ka `self_tune` (`net_threshold` ∈ [1.0, 3.0]) aaj bhi khud *trading param* badalta hai. Ye X se pehle ka aur T01-local hai. Naye niyam ke hisaab se ye Lane 3 hota — to isko "grandfathered: Evolver ko nahi chhuna" likha jaye, ya baad me Lane 2 me laya jaye. **Operator ka sawal.**

## 4. X ke niyam (sab ek jagah)

1. **Deterministic-first.** Model tier `none`; LLM (`balanced`) sirf diagnosis/proposal draft me, kabhi action me nahi. (Audit: "pehle deterministic playbooks.")
2. **Trust 1 se shuru**, tests + evidence se 2. Naya agent bina `evidence.detectors` aur tests ke level 1 se upar nahi ([AGENTS.md](../../AGENTS.md) §2).
3. **Likhna sirf `ops.*` namespace + `x0N.*` events me.** Doosre agent ka store/code nahi.
4. **Sentinel gate sab par lagta hai.** X ke `requires_approval` tools: rule change, kill-switch disengage, rollout.
5. **X khud ek failure point na bane:** X ke girne par fleet ruk nahi sakta (Medic/Registrar khud bhi supervisor ke neeche); X ka failure sirf "monitoring andha" hai, "trading band" nahi.

## 5. Build order (meri salah) aur sabse chhota viable Control Tower

1. **X05 Medic + X07 Registrar** — wahi incidents band karte hain jo asli me dikhe: supervisor silent band raha; A015 stale par T01 pause nahi.
2. **X03 Pipeline Keeper, X02 Courier** — pipeline aur contracts, kyunki R/T ko A se jodne se pehle ye chahiye.
3. **X04 Rulesmith** — jab operator `execution_tier` chun le.
4. **X06 Evolver** — jab T se outcomes aane lagein.
5. **X01 Conductor** — sabse aakhir, kyunki playbooks tabhi sahi likhe jayenge jab baaki X chal rahe hon.

**Agar 7 solo operator ke liye zyada lagta hai:** sabse chhota viable Control Tower = **X05 + X07**. Baaki jab zaroorat dikhe.

## 6. Is team ki kamiyan

[Gap register](06-gap-register.md): `G-X-01` … `G-X-15`, aur `G-ORG-03`, `G-ORG-06`.
