# 07 · Research — sources aur bharosa

[← Gap register](06-gap-register.md) · [Teams](README.md)

> **Date:** 2026-10-28. 10-28 ka [audit](../architecture/orchestration-network-audit-2026-10-28.md) (§3) pehle se 20+ sources de chuka hai (MAST, A2A, Anthropic multi-agent, Magentic-One, outbox, AWS retries, OTel, Prompt Infection, TradingAgents/FinCon …). Unhe yahan **dohraya nahi** — sirf wo jo teams ke sawal me kaam aaye, aur naye sources jo teams ke liye khoje.
>
> **Confidence tag:** `[primary]` = maine page/paper seedha fetch ya dekha · `[secondary]` = blog/vendor/summary — direction ke liye, rule ke liye nahi.

## Team structure

| Source | Kya kehta hai | 026 me kya bana |
|---|---|---|
| [Fowler — Team Topologies](https://martinfowler.com/bliki/TeamTopologies.html) `[primary summary]` | Chaar team types (stream-aligned, platform, enabling, complicated-subsystem); teen interaction modes (collaboration, X-as-a-Service, facilitating); Conway ka kaanoon; platform ka asli fayda **cognitive load** ghatana. | A/T = stream-aligned; **R = complicated-subsystem**; **X = platform + enabling**. Teams ke beech sirf *X-as-a-Service* contract ([05](05-handoffs-and-contracts.md)). |
| [Team Topologies handbook/guides](https://handbook.agilelab.it/TeamTopologies.html) `[secondary]` | Complicated-subsystem teams mostly X-as-a-Service, kabhi-kabhi short collaboration. Collaboration temporary. | R ↔ Desk: output as a service; naya R agent banate waqt Desk ke saath chhoti collaboration. |

**Seemaa:** original *Team Topologies* kitab maine nahi padhi — Fowler ka saar aur secondary guides. Ye framework human teams ke liye hai; agents par laagu karna *analogy* hai, scientifically proven mapping nahi.

## AgentOps

| Source | Kya kehta hai | 026 me kya bana |
|---|---|---|
| [AWS Well-Architected Agentic AI Lens — AGENTOPS03](https://docs.aws.amazon.com/wellarchitected/latest/agentic-ai-lens/agentops03.html) `[primary]` | Har agent ka owner + lifecycle state + transition criteria; agent-specific CI/CD (quality gates, staged rollout, auto-rollback on regression); ek catalog + cross-team dependency tracking; common issues: owner-less agents, unit tests jo prompt/tool regressions nahi pakadte, redundant agents, **undocumented dependencies jo upstream badalne par downstream tod dete hain**. | X07 Registrar (lifecycle/owner/dependency catalog), X06 (eval gate + rollback), `consumes` declare (G-ORG-02). |
| Teradata / Gravitee AgentOps pieces `[secondary]` | Prompts, models, tool lists ko versioned release artifacts; kill switch + decommission runbook maturity ke upar. | Lane 2 proposals me prompt/model-tier versioned; kill switch ([04](04-control-tower.md) X05). |

**Seemaa:** AWS ke BP01/BP02 sub-pages maine fetch nahi kiye — sirf AGENTOPS03 ka index/intent. Vendor sources ka scope aapas me alag hai (kuch AgentOps = sirf evaluation).

## Failure handling

| Source | Kya kehta hai | 026 me kya bana |
|---|---|---|
| [Erlang/OTP — Supervisor design principles](https://www.erlang.org/docs/17/design_principles/sup_princ.html) `[primary]` | Restart strategies `one_for_one`, `one_for_all`, `rest_for_one`; **restart intensity MaxR/MaxT** — MaxT second me MaxR se zyada restart ho to supervisor sab children aur khud ko band karke parent ko escalate karta hai; child types `permanent`/`transient`/`temporary`; start order me start, reverse me stop. | X05 ka supervision spec: job-class ko strategy + `MaxR/MaxT` → zyada girne par **operator ko escalate**, retry loop nahi. Relay → consume = `rest_for_one`. |
| Circuit breaker / bulkhead / saga / idempotency — [tianpan.co](https://tianpan.co/blog/compensating-transactions-failure-recovery-agentic-systems), [Gravitee](https://gravitee.io/corpus/gen-1332/out-of-all-them-bright-stars/llm-gateway-circuit-breakers-and-bulkheads-for-agent-reliability.html) `[secondary]` | Breaker per tool/provider/session; bulkhead = per-agent-class concurrency cap (noisy neighbour); **idempotency keys sabse zyada recommended** (LLMs tool calls ~15–30% retry karte hain — ye unka claim hai); saga me compensation deterministic aur testable ho, runtime par model na chune; breaker **orchestrator par**, agent ke andar nahi. | X05: breakers orchestrator me; order idempotency key (T03 ka crash→dobara-order); compensation deterministic. |
| [AWS Builders' Library — timeouts, retries, jitter](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter) (audit §3 se) | Retries "selfish"; capped exponential backoff + jitter. | Supervisor me pehle se (Phase 0). |

**Seemaa:** "let it crash" philosophy ka seedha text maine fetch nahi kiya — sirf supervisor *mechanism*. Circuit-breaker/saga wale sources practitioner blogs hain; percentages unke apne claims hain, maine verify nahi kiye.

## Self-improvement

| Source | Kya kehta hai | 026 me kya bana |
|---|---|---|
| [Darwin Gödel Machine (arXiv 2505.22954, ICLR 2026)](https://arxiv.org/abs/2505.22954) `[primary: paper page/abstract; safety details search summary se]` | Agent apna code khud badalta hai; har change benchmark par **empirically** parkha jaata hai (proof nahi); archive me har self-modification ka lineage; saare experiments **sandbox + strict time limit + human oversight** me. SWE-bench 20.0→50.0% (paper ka claim). Underlying foundation model nahi badla. | Lane 2: proposal → eval gate → approval. **Lineage log** har change ka. Auto-lane tabhi jab rollback + lineage ho. |
| [Reflexion (NeurIPS 2023)](https://proceedings.neurips.cc/paper_files/paper/2023/hash/1b44b878bb782e6954cd888628510e90-Abstract.html) `[primary: abstract]` | Weights nahi, **verbal reflection** episodic memory me; Actor/Evaluator/Self-Reflector. | T01 `reflection.py` aur A002 learning loop isi family ke hain; X06 ledger unka common record. |
| Anthropic multi-agent research system (audit §3) | Effort-scaling rules prompt me; checkpoint se resume; bade outputs reference se. | X06/X01: resume-capable workflows, artifact-by-reference. |

**Seemaa:** DGM ke safety claims ka ek hissa search snippets aur ek AI-generated review se aaya — paper khud primary hai, par maine poora paper nahi padha. Reflexion ke secondary pages ke numbers aapas me alag hain; sirf NeurIPS abstract par bharosa.

## Handoffs

| Source | Kya kehta hai | 026 me kya bana |
|---|---|---|
| OpenAI Agents SDK / handoff comparisons ([Splunk](https://www.splunk.com/en_us/blog/learn/openai-swarm-framework.html), [Airbyte](https://airbyte.com/agentic-data/multi-agent-orchestration) …) `[secondary]` | Handoff = control transfer; delegation boundary par jaankari ka sirf hissa jaata hai; failure modes: over-compression, endless handoffs, galat fact ka cascade. | [05 §6](05-handoffs-and-contracts.md) ke 5 niyam: evidence refs (summary nahi), bounded chain, har hop re-label. |

**Seemaa:** official OpenAI SDK docs search me aayi hi nahi — ye sab vendor/blog comparisons hain; nested-handoff-history jaisi cheez beta bataayi gayi. Isliye 026 ke rules in sources par *tike nahi* — ye audit ke MAST aur A2A se mile-jule hain.

## A2A, MAST aur baaki (audit se)

Is doc-set me jo audit-sources kaam aaye (poori table: [audit §3](../architecture/orchestration-network-audit-2026-10-28.md)):

- **A2A spec v1.0** — task states (SUBMITTED, WORKING, INPUT_REQUIRED, AUTH_REQUIRED, COMPLETED, FAILED, CANCELED, REJECTED) → [05 §5](05-handoffs-and-contracts.md).
- **MAST (Berkeley, arXiv 2503.13657)** — 14 failure modes, 3 categories (system design, inter-agent misalignment, task verification) → message contracts + verification step ka tark.
- **Prompt Infection (arXiv 2410.07283)** — compromised agent se injection phailta hai → collector niyam #8, envelope ka `untrusted`.
- **TradingAgents / FinCon** — trader aur execution ke beech risk layer → R03 → gate → Desk.
- **Anthropic multi-agent research system** — subagent ko objective/format/tools/boundaries → X01 playbooks.

## Bharosa kitna (poora doc-set)

- **Primary dekha:** Fowler (summary), Erlang supervisor docs, AWS AGENTOPS03 index, DGM (paper page).
- **Sirf secondary:** Team Topologies guides, circuit-breaker/saga blogs, handoff comparisons, Teradata/Gravitee.
- **Fetch nahi hua:** Team Topologies kitab, AWS BP01/BP02, Erlang "let it crash" text, official OpenAI Agents SDK docs.
- **Analogy, theorem nahi:** human-team frameworks (Team Topologies) aur Erlang (processes) ko LLM agents par laagu karna design-guide hai; 026 me ye kabhi measure nahi hua.
- **Code-evidence alag cheez hai:** gap register ke ✅ rows aaj grep/read se verify hue; research sources ki vajah se koi gap *nahi* banaya.
