# ADR-0001 — 026 is an OS for a fleet, not a single agent

- **Status:** accepted
- **Date:** 2026-09-04
- **Deciders:** operator, Claude
- **History:** [`BUILD_LOG.md`](../../BUILD_LOG.md) → session 2026-09-04 (genesis)

## Context

026 could have been a single intelligence pipeline — one script that watches a source
and reports. The operator's actual goal is bigger: several specialists (on-chain,
news, sentiment, market data, macro) whose findings *combine*. A folder of standalone
scripts cannot combine findings under one honest governance layer; each script would
carry its own ad-hoc rules, and a cross-source claim ("rumor + matching outflow")
would have no place to live that keeps each half's evidence separate.

## Decision

Build 026 as an **operating system for a fleet of agents**: a shared kernel (config,
core runtime, brain, message bus), platform services (sentinel, observability,
dashboard), and a fleet of numbered agents (`A001`…), each owning a full vertical
pipeline. The differentiator is **cross-agent correlation** under one governance
layer (the sentinel) that never lets a claim outrun its evidence.

Architecture is **kernel + fleet + services** with **downward-only dependencies** —
the kernel never imports an agent.

## Consequences

- **Easy:** adding an agent (copy the contract, plug into the bus); fusing findings
  across agents; enforcing one evidence standard everywhere.
- **Hard / cost accepted:** more upfront structure than a single script; the platform
  must exist before the first agent delivers value. We accept this because
  combination is the whole point — see [`AGENTS.md`](../../AGENTS.md) §4.
- **Locks in:** the correlation contract (never average confidence, record conflicts,
  split provenance) and the layer ranking that `tests/test_architecture.py` will
  enforce.
