# ADR-0006 — The fleet is organised into four teams: A, R, T, X

- **Status:** proposed (structure approved by the operator 2026-10-28; team names and the `R` letter are provisional until the docs are reviewed — flip to *accepted* then)
- **Date:** 2026-10-28
- **Deciders:** operator, Claude
- **Supersedes (in part):** [`docs/manual/06-agents.md`](../manual/06-agents.md) §1 — the "three fleet layers" (Intelligence / Execution / Platform). The one-line test there is replaced by the four-question test below.
- **Design docs:** [`docs/teams/`](../teams/README.md)

## Context

026 has 21 agent folders (A001–A018, T01–T03) and four platform actors, but no team structure. The 2026-10-28 audit and a review of the repo found that: the A-series mixes agents that *collect* raw information from the outside world with agents that *derive* conclusions from other agents' output (A009/A010/A012/A013/A014); no manifest declares `consumes`, and only A015 declares `produces`; and the work of keeping agents healthy (scheduling, bus, rules, failure handling, self-improvement, registry) is scattered across `live/supervisor.py`, `orchestrator/event_bus`, `security/sentinel`, `bootstrap/` and the dashboard with no owner. The operator asked for the fleet to be divided into teams.

## Decision

1. **Four teams, four series.**
   - **A — Intelligence Team:** collectors; external sources → facts; read-only.
   - **R — Analysis Bureau:** analysts; derive from other agents' output/stored data; read-only, advisory. New series, new IDs `R01`–`R05` reserved for what are today the scaffolds A009, A010, A012, A013, A014.
   - **T — Trading Desk:** decision layer; consumes A and R, decides and acts, gated. T02 and T03 stay here.
   - **X — Control Tower:** stewards (orchestration design, pipeline, communication/handoff, rules, failure handling, self-improvement, registry). Roster `X01`–`X07` proposed, `X08+` reserved.
2. **Classification is by four ordered questions**, not by name: money/order → T; raw external source → A; derives from other agents, read-only → R; runs/monitors other agents → X.
3. **Platform actors are unchanged** (`orchestrator`, `sentinel`, `librarian`, `operator-io`). X is the *steward* of that machinery; it neither replaces the orchestrator nor bypasses the sentinel.
4. **Data flows downward A → R → T**; A → T directly only for hard-stop facts (halt, delisting), and only to pause new entries.
5. **Self-improvement has three lanes:** (1) auto for an allowlist of bounded, reversible, non-money operational knobs with automatic rollback and a lineage log; (2) propose-only for rules, thresholds, prompts, model tiers and code; (3) forbidden to X for trading parameters, the execution gate, signing/funds, secrets and trust levels.
6. **X agents are deterministic-first** (model tier `none`; an LLM only for diagnosis/proposal drafts), start at trust level 1, and write only to an `ops.*` brain namespace and `x0N.*` events.

## Consequences

- **Easy:** every agent and every future agent has one team and a short test to find it; contracts between teams (`produces`/`consumes`, the existing envelope) have a named owner (X02); the failure classes already seen (supervisor silently stopped; A015 stale but T01 keeps trading) map to a named steward (X05/X07).
- **Hard / cost accepted:** an `R` series and the A009→R01 … A014→R05 rename; a `team:` manifest/registry field; and — **before the first R or X agent can be registered** — `security/sentinel/fleet.py:12` (`_ROW = ^\|\s*`([AT]\d+)`…`) must be widened to `[ATRX]`, otherwise the registry check cannot see them. None of that is done here: this ADR and `docs/teams/` are **documentation only** (no code, registry, manifest or folder change).
- **Open (operator):** the series letter `R` and team names; whether the freed A-IDs are reused (A011 was); the T-series trust representation (proposed: an orthogonal `execution_tier: none|paper|testnet|real-gated`, see [`03-trading-desk.md`](../teams/03-trading-desk.md) §3 — a trust/funds boundary, so not decided here); whether T01's `self_tune`, which already adjusts a trading parameter, is grandfathered.
- **Revisit when:** the first R or X agent is built; or X05/X07 prove too small/large a unit for a single operator (the minimal viable Control Tower is X05 + X07).
