# 06 · Gap register — kamiyon ki list

[← Handoffs](05-handoffs-and-contracts.md) · [Teams](README.md) · *Next: [Research](07-research.md)*

> **Date:** 2026-10-28. Har row ka evidence file/line ke saath. **Severity:** H (kuch toota ya trust boundary) · M (kaam rukta/dohra hota hai) · L (chhota ya baad ka).
> **Verified:** ✅ = aaj (2026-10-28) grep/read se dekha · 📄 = 10-28 ke [audit](../architecture/orchestration-network-audit-2026-10-28.md) ya `PROJECT_STATE.md` se, aaj dobara nahi chalaya · ⚠ = verify nahi hua.
> Line numbers aaj ke tree ke hain; badal sakte hain.

## Organization (teams ke beech)

| ID | Sev | ✓ | Kami | Evidence | Next step |
|---|---|---|---|---|---|
| G-ORG-01 | H | ✅ | Registry/manifest me team ka koi field nahi; A-series me collectors + analysts mile hain | `config/agents/registry.yaml` me `team` key nahi; A012/A014 README advisory/derived kaam batate hain | [ADR-0006](../adr/ADR-0006-fleet-teams.md); `team:` field (code, baad me) |
| G-ORG-02 | H | ✅ | `produces` sirf A015 declare karta hai; `consumes` kisi manifest me nahi | `grep produces agents/*/agent.yaml` → A015 only; `grep consumes` → none; T01 `agent.yaml:26` `reads: []` | X02: `consumes` + `contracts` check |
| G-ORG-03 | M | ✅ | Agents ki dekh-bhaal 5 jagah bikhri; kai platform dirs khali | `live/supervisor.py:289-292`; `orchestrator/event_bus/`; `security/sentinel/`; `bootstrap/{relays,consumers}`; dashboard. **0 files:** `orchestrator/{router,scheduler,workflows,memory}`, `observability/`, `tools/`, `plugins/`, `sandbox/`, `src/`, `security/{audit,auth}`, `brain/{reasoning,rag,llm}`, `config/feature_flags/` | Control Tower ([04](04-control-tower.md)) |
| G-ORG-04 | M | ✅ | `06-agents.md` §2/§4 purana: kehta hai T01 ka `agent.yaml`/registry row nahi | `agents/T01_…/agent.yaml` maujood; `registry.yaml` me T01 row | is doc-set me theek kiya |
| G-ORG-05 | M | ✅ | CI nahi | `.github/workflows/ci.yml`, `deploy.yml` — dono 0 bytes | X03/X07 (baad me); operator ka call |
| G-ORG-06 | H | ✅ | **A→T hard-stop maturity gate se ruka hai:** A015 ke content events `maturity: implemented` ke saath bus par; default consumer `validated` par unhe skip karega | `bootstrap/relays/a015.py:79` (`detector` block); A015 `agent.yaml` me paanchon detectors `implemented`; `consumers/librarian.py:39` jaanbujhkar `min_maturity="implemented"`; `envelope.passes_maturity` | operator: detectors validate karo **ya** transitions ko plain fact tay karo ([05 §3](05-handoffs-and-contracts.md)); source-stale pause bina iske chal sakta hai |

## Intelligence Team (A)

| ID | Sev | ✓ | Kami | Evidence | Next step |
|---|---|---|---|---|---|
| G-A-01 | H | ✅ | 18 A-slots me sirf 4 me code | `.py` count: A001 802, A002 49, A007 13, A015 26; A006 0 (manifest-only); A003, A004, A005, A008–A014, A016–A018 = 0 (README-only) | [01 §3](01-intelligence-team.md) priority |
| G-A-02 | H | ✅📄 | **A005 Market Data fleet ka critical path** par README-only | A005 me 0 `.py` ✅; "intended feeds" A005 → A009/A010/A012/A013/A014/T01/T02/T03 📄 (audit §2) | A005 sabse pehle |
| G-A-03 | M | ✅ | A007 ingestion mock-only | `registry.yaml:62` "MOCK data only"; PROJECT_STATE | live MCP fetch + CLI |
| G-A-04 | M | ✅ | Bus par ek hi producer aur ek hi consumer | `bootstrap/relays/` = `a015.py`; `bootstrap/consumers/` = `librarian.py`; A002 relay (Slice 3) bana nahi | A002 relay; X02 |
| G-A-05 | M | ✅ | Namespace drift: A015 `markets`, T02 `market` | A015 `agent.yaml` `reads/writes: [..markets..]`; T02 `agent.yaml` `[..market..]` | ek naam tay karo (X02 schema registry) |
| G-A-06 | L | 📄 | bybit is network se unreachable → STALE | PROJECT_STATE (2026-10-28) | operator: hatao ya network theek karo |

## Analysis Bureau (R)

| ID | Sev | ✓ | Kami | Evidence | Next step |
|---|---|---|---|---|---|
| G-R-01 | H | ✅ | R01–R05 sirf README: manifest, registry, code, test kuch nahi | `agents/A009_*, A010_*, A012_*, A013_*, A014_*` me sirf `README.md`, 0 `.py` | A005 ke baad [02 §4](02-analysis-bureau.md) order |
| G-R-02 | M | ✅ | Teen TA, teen risk, teen correlation engines | TA: A009 README, T03 scanner, T01 `signals.py`; risk: A012 README, T03 `core/live/risk.py:50`, T01 `safety/circuit_breaker.py`; corr: A014 README, A002 internal | [03 §4](03-trading-desk.md) salah: chautha engine mat banao |
| G-R-03 | M | ✅📄 | Fleet-level fusion nahi (AGENTS.md §4 ka promise) | `grep fuse\|fusion` orchestrator/bootstrap/brain/security/live → koi nahi ✅; sirf T03 local `core/futures/fuse.py` 📄 | X01 (sabse aakhir) |
| G-R-04 | L | ✅ | Naye `R` IDs abhi sirf docs me; folders `A0NN` naam par | `ls agents/` | rename alag go-ahead par |

## Trading Desk (T)

| ID | Sev | ✓ | Kami | Evidence | Next step |
|---|---|---|---|---|---|
| G-T-01 | H | ✅ | T03 scalper ke breakers asar nahi karte | `scalper.py:267` har step naya `RiskEngine(limits)` (khali `RiskState`); `scalper.py:275` `can_trade(dict)` jabki `risk.py:70` `can_trade(self, equity: float)` maangta hai; khali state me `peak_equity`/`day_start_equity`=0 ⇒ drawdown/daily-loss check nahi chalte | test-first fix (T03); alag session |
| G-T-02 | H | ✅ | T01/T03 execution sentinel ki scan se bahar | `security/sentinel/checks/execution.py:9-10` ("execution_enabled=true; gate not asserted"); gate khud sab execution kinds deny karta hai (`gate.py` `EXECUTION_KINDS`); T01 apna `_guard()` (`real_engine.py:51`) | X04 + operator: `execution_tier` ([03 §3](03-trading-desk.md)) |
| G-T-03 | H | ✅ | T-series ka trust tier undefined | `06-agents.md` §4; sentinel aaj: "T03 level 2 not earned (no evidence.detectors) → capped to 1" | operator option chune |
| G-T-04 | M | ✅ | T01 ko A/R ka koi signal nahi | `T01 agent.yaml:26` `reads: []`; sirf T03 soft veto live (`bot.py:158-167`, `engine.py:102`) | Slice 2 + `consumes` |
| G-T-05 | M | ⚠ | Har order ka licensing-evidence record | AGENTS.md §0 law; T01 trades table me evidence refs hain ya nahi — **verify nahi kiya**; manifest kuch declare nahi karta | [03 §5](03-trading-desk.md) record |
| G-T-06 | M | 📄✅ | `ready()` false hote hi paper par switch; khuli real position? | `bot.py:145-148`; audit ne flag kiya, aaj behavior chalaya nahi | T01 session me reproduce |
| G-T-07 | M | ✅ | T03 sentinel FAIL (fleet verdict FAIL) | scan aaj: `core/paper/__init__.py:15` `HUMAN_CONFIRM_TOKEN = "I-CONFIRM-PAPER-ORDER"` — public phrase, secret nahi | operator: rename ya whitelist |
| G-T-08 | L | ✅ | T03 `runtime_verified: false` | `registry.yaml:112` | end-to-end run |
| G-T-09 | M | 📄 | T02 bus par nahi; `swarm.db` WAL nahi | audit §2; `registry.yaml:73` `kernel_wired: false` | relay jab tay ho |
| G-T-10 | M | ✅ | T01 `self_tune` khud trading param badalta hai | `strategy/engine.py:149`; `net_threshold` ∈ [1.0, 3.0] | grandfather ya Lane 2 ([04 §3](04-control-tower.md)) |

## Control Tower (X)

| ID | Sev | ✓ | Kami | Evidence | Next step |
|---|---|---|---|---|---|
| G-X-01 | H | ✅ | Fleet kill switch nahi | `grep kill_switch\|killswitch` orchestrator/bootstrap/security/live/brain → koi nahi; sirf T01-local `backend/safety/circuit_breaker.py` | X05 design review (trust boundary) |
| G-X-02 | H | ✅ | Orchestrator-level circuit breaker/bulkhead nahi | wahi grep; bus me sirf per-message timeout (production 60 s, PROJECT_STATE) | X05 |
| G-X-03 | H | ✅ | Dead-man switch nahi: A015 stale event aata hai par koi T ko rokta nahi | `bootstrap/consumers/` = sirf librarian; "Slice 2 (T01 pause flag)" PROJECT_STATE me *not built*. (`system.source.stale` platform event hai, maturity gate se guzarta hai — [05 §3](05-handoffs-and-contracts.md)) | X05 + T01 design review |
| G-X-04 | M | ✅ | Approvals ka dashboard nahi | table `store.py:47`; dashboard `app/` me 9 pages (agents, brain, desk, narratives, onchain, orchestrator, sentinel, trace, home) — approvals/events nahi | `operator-io` + X07 |
| G-X-05 | M | ✅ | Pipeline timer-only; prune/backfill adhoora | `supervisor.py:226 _due`, `:289-292`; `prune` ka koi caller nahi (`store.py:338` definition); replay sirf A015 log se | X03 |
| G-X-06 | M | ✅ | Orchestration khali | `orchestrator/{router,scheduler,workflows,memory}` 0 files | X01 |
| G-X-07 | M | ✅ | Self-improvement bikhri, koi shared ledger/rollback nahi | `T01 engine.py:149`, `reflection.py`; A002 `cli/main.py:283 resolve`; A001 `evaluation/promotion.py` | X06 read-only report |
| G-X-08 | M | ✅ | Communication: `subscribe` API nahi; handoff me `deadline`/`ack` nahi | bus code me `subscribe` ka koi hit nahi; `message.py` me `deadline`/`ack` field nahi | X02 ([05](05-handoffs-and-contracts.md)) |
| G-X-09 | M | ✅ | Rules 3 jagah, versioning/test nahi | `security/policies/sentinel.yaml`; manifest `charter`; hard-coded `real_engine.py:51`, `risk.py` | X04 inventory |
| G-X-10 | M | ✅📄 | Registry flags haath se bharte hain | `registry.yaml` ke comments; audit me `kernel_wired` galat nikla (Phase 0 me theek hua) 📄 | X07 computed flags |
| G-X-11 | M | 📄 | Supervisor heartbeat hai, par use koi dekhta nahi; Startup folder me nahi | PROJECT_STATE ("not yet in the Startup folder") | X07 silent-death alert |
| G-X-12 | M | ✅ | Observability aur cost rollup nahi | `observability/` 0 files; `Budget` sirf per-message (`message.py:17`) | X07 |
| G-X-13 | L | ✅ | Message signing nahi (par producer authorize hota hai) | `envelope.py:114` source ko manifest `produces` se authorize; crypto signing nahi — single host par theek ([ADR-0005](../adr/ADR-0005-sqlite-event-bus.md)) | multi-host par dobara |
| G-X-14 | L | 📄✅ | Agent suites ek-ek process me; fleet e2e sirf A015 ka | PROJECT_STATE (T01/T03 `sys.path`); `tests/integration/test_event_bus_e2e.py` | golden-trace suite (X06 harness) |
| G-X-15 | M | 📄 | Entity ledger nahi (A001/A002/A015/A007 join nahi ho sakte) | audit §1: `global`/`entities` ka koi writer nahi; AGENTS.md §4/§7 promised | librarian + X02 |

## Gino to

H: 12 · M: 24 · L: 5 → **41 kamiyan** (6 org · 6 A · 4 R · 10 T · 15 X). Verify-status: **31 pure ✅** (aaj grep/read), **5 mixed ✅📄**, **5 sirf 📄/⚠** (A-06, T-05, T-09, X-11, X-15) — in 10 rows ko kaam uthate waqt dobara reproduce karna hai.
