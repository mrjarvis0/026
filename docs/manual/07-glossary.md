# 07 · Glossary

[← Index](README.md) · *Prev: Agents (planned)* · *Next: Manual log (planned)*

> Every 026 term in one place. 026 is a dense system with a precise vocabulary —
> when two docs use the same word they must mean the same thing. If a term here and
> a term in code ever disagree, reconcile it explicitly in `BUILD_LOG.md`, never
> silently. Terms are grouped by theme; within a group, most-fundamental first.

---

## The evidence model (the heart of 026)

**Evidence standard** — 026's one law: *an agent may not assert what its evidence
cannot license.* Everything else exists to keep this promise. See
[`AGENTS.md`](../../AGENTS.md) §0.

**Evidence license** — what a given body of evidence actually permits you to claim.
A claim that goes beyond its license is a bug, however plausible it sounds.

**Provenance** — the origin of a fact: which source, which record, what timestamp.
Every conclusion must trace back through its provenance to a raw, sourced record.

**Provenance chain** — the full, unbroken links from a conclusion → the intermediate
findings → the raw `data/raw/` record → the catalogued source (its `S0xx` ID). If any
link is missing, the conclusion is not licensed.

**Provenance field** — the specific fields a `data/raw/` record must carry so it can
cite its source (e.g. `source_id`, `fetched_at`, `tx_hash`, `revision_id`). Declared
per source in the [`sources/`](../../sources/README.md) registry.

**Coverage** — proof that a window of time/space was *actually observed*, with what
completeness. Coverage is what separates "we looked and saw nothing" from "we didn't
look."

**Coverage before absence** — the rule that a negative claim ("no anomaly") requires
a coverage record. An absence claim without coverage is unlicensed.

**"Cannot be determined"** — a valid, respected answer. 026 prefers it to a
confident guess. Saying it is never a failure; a confident wrong answer is.

---

## Detection & maturity

**Detector** — a named rule/model that flags a specific pattern (e.g.
`DET-DEFI-FLOW-01`). A detector has a maturity and a confidence ceiling.

**Maturity gate** — the rule that a detector may **alert** only once its error rate
is *measured*, not merely plausible. Two states matter:
- **IMPLEMENTED** — code exists and runs, but its error rate is unmeasured. It may
  *not* alert, no matter how good it looks.
- **VALIDATED** — a backtest against a labelled window has measured its error rate
  and checked calibration. Only now may it alert.

**Backtest** — running a detector/strategy against historical, labelled data to
*measure* how often it is right or wrong — the evidence that promotes IMPLEMENTED →
VALIDATED.

**Calibration** — whether a stated confidence matches reality (a "70% sure" claim is
right ~70% of the time). Overconfidence is flagged, not smoothed over.

**Labelled window** — a slice of historical data with known-correct answers, used to
measure a detector's error rate honestly.

**Confidence ceiling** — the maximum confidence a detector is allowed to express
given its maturity — an IMPLEMENTED detector is capped low on purpose.

---

## Findings & correlation

**Finding** — a single agent's evidence-backed conclusion, carrying its own
provenance and confidence. The unit agents produce.

**Fusion** — the orchestrator combining findings from multiple agents into one
correlated result. See [`AGENTS.md`](../../AGENTS.md) §4.

**Correlation** — 026's core power: linking findings from different agents that
concern the same entity (e.g. a news rumor + an on-chain outflow for the same
protocol). A correlation is a *hypothesis* until each half independently clears its
own maturity gate.

**Fusion rules (the four).** (1) Fusion never averages confidence — the combined
confidence is the *weakest* input's. (2) Conflicts are recorded, not resolved. (3)
Provenance stays split — a fused finding carries each half's chain separately, never
merged. (4) A correlation is a hypothesis, not a verdict, until each half clears its
gate.

**Entity** — a thing findings can be *about*: an address, ticker, org, protocol.

**Entity ledger** — the cross-agent registry of entities in the `brain/`. An entity
A001 labels is one A002 can cite — this shared vocabulary is the fuel correlation runs
on.

---

## The platform (kernel · fleet · services)

**Agent** — a bounded, evidence-grade actor owning a full **vertical pipeline**
(`sensors → ingestion → validation → normalization → store → skills → intelligence →
decision`). Not a chat wrapper. Lives at `agents/<AXX_Name>/`.

**Vertical pipeline** — the full stack an agent owns end-to-end; the platform
surrounds it but never reaches inside.

**Fleet** — all the domain agents across the four teams (`A`, `R`, `T`; see **Team**). The fleet is only as strong
as its weakest agent — and its weakest claim.

**Team** — one of the four groups the fleet is divided into: Intelligence Team (`A`),
Analysis Bureau (`R`), Trading Desk (`T`), Control Tower (`X`). An agent is classified
by four ordered questions (money/order → T; raw external source → A; derives from
other agents, read-only → R; runs/monitors agents → X), never by its name. See
[`docs/teams/`](../teams/README.md) and [ADR-0006](../adr/ADR-0006-fleet-teams.md).

**Collector / analyst** — a *collector* (`A`) fetches raw facts from an external source;
an *analyst* (`R`) derives conclusions from other agents' output and may not fetch
externally. An analyst's confidence never exceeds its weakest input (`AGENTS.md` §4).

**Steward vs machinery** — platform actors (orchestrator, sentinel, librarian,
operator-io) are the *machinery* that executes; Control Tower (`X`) agents are their
*stewards*: they design, monitor, tune and repair, and never replace the machinery or
bypass the sentinel.

**Handoff** — a transfer of responsibility between agents, teams, a human, or build
sessions. Four kinds: intel (A→R/T facts), human (approvals), task (orchestrator →
agent), session (`PROJECT_STATE.md` + `BUILD_LOG.md`). The sender owns it until the
receiver acknowledges. See [`docs/teams/05-handoffs-and-contracts.md`](../teams/05-handoffs-and-contracts.md).

**Lane (self-improvement)** — one of three tiers limiting what the Evolver (`X06`) may
change: *auto* (allowlisted, bounded, reversible, non-money knobs, auto-rollback),
*propose-only* (rules, thresholds, prompts, code — operator approval), *forbidden*
(trading parameters, execution gate, funds, secrets, trust levels).

**Kernel** — the shared lowest layers: `config/`, `src/`, `brain/`, `orchestrator/`.
The kernel never imports an agent.

**Orchestrator** — the manager: plans work, routes tasks to agents, fuses results,
runs the message bus. Trust level 3.

**Brain** — the shared, namespaced memory: short/long-term, embeddings, the entity
ledger, cross-agent RAG. "Write like others will read."

**Sentinel** — the security actor over *every* action: enforces trust levels,
invariants, secrets, and the execution gate. Pairs each named check with a **live
surface scan**. Trust level 3. See [04 · Security](04-security.md).

**Librarian** — the actor that curates the brain and dedups entities. Trust level 2.

**operator-io** — the human interface (dashboard): chat, approvals, traces. Trust
level 3.

**Message bus** — the only path agents communicate through; agents never call each
other. Every message is logged, traced, replayable, and **budgeted**.

**Budget** — the call/cost allowance carried in a message. An agent that exhausts its
budget degrades to coarser output — it does not go dark silently.

**Degraded mode** — reduced-fidelity operation when a budget, key, or source is
missing. Explicit and reported, never a silent failure.

---

## Trust, safety & execution

**Trust level** — how much a component is allowed to do, enforced by the sentinel:
- **0 — Sandboxed:** reasoning only (new/untrusted plugin).
- **1 — Read-only:** no side effects (a fresh agent, pre-evals).
- **2 — Scoped writes:** a declared surface (A001, A002…).
- **3 — Platform:** human-adjacent (orchestrator, sentinel).

An agent with no evidence detectors and no tests **cannot leave level 1.**

**Execution gate** — the single, isolated, gated path through which any real-money
order must pass. **OFF by default.** Before an order: paper-validated → hard risk
limits set → (by default) human approval. No order fires silently, without limits,
or without passing its gates.

**Kill-switch** — a hard stop that halts execution immediately, part of the required
risk limits before the gate can open.

**Paper trading** — live simulation with no real money, used to prove a strategy
*before* any real funds. A gate prerequisite.

**Risk limits** — hard bounds (max position, daily loss cap, kill-switch) that must
be set before the execution gate can open.

**Downward-only imports** — an architecture invariant: a layer imports only from
layers below it, mechanically checked in `tests/`, so no component sneaks a
privileged path.

---

## The source registry

**Source** — any external origin of evidence (API, dataset, MCP server, model,
infra tool). Each has a stable `S0xx` ID that is never reused.

**S-ID** — a source's global stable identifier (`S001`, `S002`, …). The anchor for
provenance and for moving a row between files painlessly. See
[`sources/README.md`](../../sources/README.md#master-index).

**Tier** — a source's cost class: `FREE` · `FREE*` (limited) · `PAID-LATER` · `DEAD`
· `INFRA`/`MODEL` (not a feed).

**Source status** — reality marker on a source row: ⬜ known (limits unverified) · 🔜
web-verified · ✅ live (a connector lands a raw, cited record). `TBV` inside a cell =
that value still to be verified.

**Landing folder** — where a source's connector/loader writes (e.g.
`integrations/apis/`, `data/raw/`). Fixed per source so raw records have a known home.

---

## Documentation & continuity

**BUILD_LOG.md** — append-only history: how we got here and why. Never overwritten.

**PROJECT_STATE.md** — the living snapshot of what *is*, overwritten each session.

**ADR** — Architecture Decision Record: one durable, findable document per
significant decision (context → decision → consequences). Lives in
[`docs/adr/`](../adr/README.md).

**Manual** — this handbook (`docs/manual/`), updated whenever a file is created,
moved, or given a new role (build discipline, [`AGENTS.md`](../../AGENTS.md) §9.7).

---

[← Index](README.md) · *Prev: Agents (planned)* · *Next: Manual log (planned)*
