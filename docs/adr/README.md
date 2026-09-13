# Architecture Decision Records (ADRs)

> One durable, findable document per **significant** decision. `BUILD_LOG.md` records
> *when* and *in what session* a decision happened (append-only history); an ADR
> records the decision itself — its context, the choice, and its consequences — so a
> newcomer can understand *why* 026 is shaped this way without reading the whole log.

## What earns an ADR

A decision that shapes structure, interfaces others depend on, or a law the whole
system inherits. Not every choice — a small fix lives in `BUILD_LOG.md` only.

## How to write one

Copy the template below. Number monotonically (`ADR-000N`); never reuse a number.
An ADR is **immutable once accepted** — to change a decision, write a new ADR that
supersedes it (link both ways), don't rewrite history.

```markdown
# ADR-000N — <short title>

- **Status:** proposed | accepted | superseded by ADR-000M
- **Date:** YYYY-MM-DD
- **Deciders:** operator, Claude

## Context
What forced the decision. The constraints and the problem.

## Decision
What we chose, stated plainly.

## Consequences
What this makes easy, what it makes hard, and what we accept as the cost.
```

## Index

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [0001](ADR-0001-os-for-a-fleet.md) | 026 is an OS for a fleet, not a single agent | accepted | 2026-09-04 |
| [0002](ADR-0002-gated-execution-charter.md) | Gated execution replaces the "never trades" law | accepted | 2026-09-05 |
| [0003](ADR-0003-minimal-stack.md) | Deliberately minimal stack: Python + TypeScript + Postgres | accepted | 2026-09-05 |
| [0004](ADR-0004-sources-by-access-type-and-stable-ids.md) | Source registry organized by access-type with stable IDs | accepted | 2026-09-05 |

*These four ADRs formalize decisions already recorded in [`BUILD_LOG.md`](../../BUILD_LOG.md)
(sessions 2026-09-04 → 2026-09-05). They add no new decision — they make the existing
ones findable and durable. Written 2026-09-06.*
