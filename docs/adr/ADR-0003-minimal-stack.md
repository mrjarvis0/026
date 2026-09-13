# ADR-0003 — Deliberately minimal stack: Python + TypeScript + Postgres

- **Status:** accepted
- **Date:** 2026-09-05
- **Deciders:** operator, Claude
- **History:** [`BUILD_LOG.md`](../../BUILD_LOG.md) → session 2026-09-05; full detail in [`docs/STACK.md`](../STACK.md)

## Context

026 spans ingestion, real-time feeds, ML, backtesting, a risk engine, a gated
execution client, an API, and a dashboard. A polyglot backend could justify itself
technically for almost any one of these, but the operator is a small team, and 026's
evidence-grade discipline only holds if the number of moving parts stays small enough
to reason about. Surface area is a cost, not a capability.

## Decision

Two primary languages do ~95% of the work:

- **Python (3.11+, async-first, pydantic v2)** — the entire backend brain and fleet:
  ingestion, MCP connectors, WebSocket feeds (`asyncio`, no separate Node runtime),
  validation/provenance, ML/prediction, analysis, backtesting, paper trading, the
  risk engine, the gated execution client, and the backend API.
- **TypeScript + React/Next.js** — the dashboard, including the human-in-the-loop
  trade-approval controls.

One database engine — **PostgreSQL** with **TimescaleDB** (time-series) and
**pgvector** (RAG) extensions — plus **Redis** for cache/queue/bus. **Rust is
reserved** for a *measured* hot path only (via PyO3), not adopted now.

## Consequences

- **Easy:** one backend language to master; `asyncio` handles streaming without a
  second runtime; one DB engine instead of a separate vector database.
- **Hard / cost accepted:** Python's raw throughput ceiling on hot paths — accepted
  under YAGNI until a profiler proves a specific path too slow, then Rust via PyO3.
- **Rejected:** a separate Node backend for feeds/API (Python covers it; Next.js
  already carries the only Node the UI needs).
- **Not yet validated:** this stack is *chosen*, not proven — no `.venv`,
  `pyproject.toml`, or build exists. `make doctor` must make it real before it is
  trusted.
