# 04 · Security

[← Index](README.md) · *Prev: Architecture (planned)* · [Next: Data sources →](05-data-sources.md)

> How 026 stays safe: who is allowed to do what, what can never happen silently, and
> how money is protected. The full, enforceable contract is in
> [`AGENTS.md`](../../AGENTS.md) §0 & §6 — this section is the plain-language guide.

---

## The sentinel

One platform actor, the **sentinel** (lives in `security/`), sits over **every**
action. Anything that exceeds an agent's declared trust, touches a
`requires_approval` tool, or crosses the execution boundary is **held for the
operator** in the dashboard — it does not just proceed.

The sentinel pairs each named rule with a **live surface scan**, because a flag
that reports "ok" next to an exposed write path is exactly the reassuring lie the
check exists to catch.

## Trust levels

Every agent declares a trust level; the sentinel enforces it.

| Level | Means | Example |
|-------|-------|---------|
| 0 | Sandboxed — reasoning only | New/untrusted plugin |
| 1 | Read-only — no side effects | A fresh agent, pre-evals |
| 2 | Scoped writes — a declared surface | A001, A002 |
| 3 | Platform — human-adjacent | orchestrator, sentinel |

An agent with no evidence detectors and no tests **cannot leave level 1.**

## The execution gate (money)

026 *can* trade — but only through a **gated execution layer** that is **OFF by
default**. Before any real-money order:

1. the strategy must be **paper-validated**,
2. **hard risk limits** are set (max position, daily loss cap, kill-switch),
3. and, by default, a **human approves**.

Data connectors are strictly **read-only** — a connector observes, it never places
an order. Execution is a separate path, isolated from every data connector. No
order fires silently, without limits, or without passing its gates; each traces to
the evidence that licensed it.

## Secrets

- 🔒 Real keys live in **`.env` only** — never in tracked source.
- `.env.example` holds the key *name* with a blank value.
- Secrets handling and the audit trail live under `security/`.

## The evidence guarantees (why it's "safe")

- **Coverage before absence** — a "nothing happened" claim requires proof the
  window was actually observed.
- **Maturity gates** — a detector may *alert* only once its error rate is
  *measured* (`VALIDATED`), never on a plausible-looking threshold.
- **Provenance** — every conclusion traces to a raw, sourced, timestamped record.
- **Downward-only imports** — a layer imports only from layers below it, checked in
  tests, so nothing sneaks a privileged path.

---

[← Index](README.md) · *Prev: Architecture (planned)* · [Next: Data sources →](05-data-sources.md)
