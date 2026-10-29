# ADR-0005 — The event bus runs on SQLite (WAL), not Redis, for now

- **Status:** accepted
- **Date:** 2026-10-28
- **Deciders:** operator, Claude
- **Supersedes (in part):** [ADR-0003](ADR-0003-minimal-stack.md) — only its "Redis for cache/queue/bus" line, for the *bus*
- **Design:** [`docs/superpowers/specs/2026-10-28-phase1-event-bus-design.md`](../superpowers/specs/2026-10-28-phase1-event-bus-design.md)

## Context

The orchestration audit (2026-10-28) found that agents cannot pass facts to each other: the bus is a
synchronous request/response used only by tests and the dashboard, and nothing durable carries an
agent's output to a consumer. Phase 1 adds a durable event log with per-consumer delivery.

ADR-0003 named Redis for "cache/queue/bus", but it also said the stack was "chosen, not proven".
Checked on the operator's machine: no `redis-server`, no `redis` Python package; per redis.io, Redis
on Windows needs Memurai or WSL2, and either is one more daemon to install and keep running. Event
volume is tens per day. SQLite in WAL mode (sqlite.org/wal.html) gives concurrent readers beside a
single writer, which suits one machine with several short-lived processes; it requires all processes
on the same host and short transactions.

## Decision

The Phase 1 event bus (envelope, append-only `events`, per-consumer cursors, dead-letter, source
health) is stored in **one SQLite database in WAL mode** at `data/bus/bus.db`, using only the Python
standard library. Agents stay bus-unaware; relays in `bootstrap/` publish on their behalf.

Redis Streams remains a documented **escape hatch**: the store's surface is `publish / read / consume
/ health`, so a Redis implementation could replace its body without touching relays or consumers. No
abstract interface is added until that is needed.

## Consequences

- **Easy:** no install, no new daemon, crash-safe by construction, queryable with any SQLite tool,
  trivially backed up (copy the file).
- **Hard / cost accepted:** one writer at a time (fine at this volume); the file must live on a local
  disk, not a network or sync folder; a long-lived reader can make the WAL grow, so readers stay
  short-lived and `prune` checkpoints. No consumer groups or blocking reads — consumers poll.
- **Revisit when:** sustained event rate in the hundreds per second, consumers on another host, or a
  second machine joins the fleet.
- ADR-0003's other decisions (Python + TypeScript, Postgres for the main store) are unchanged.
