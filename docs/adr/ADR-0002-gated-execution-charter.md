# ADR-0002 — Gated execution replaces the "never trades" law

- **Status:** accepted
- **Date:** 2026-09-05
- **Deciders:** operator, Claude
- **History:** [`BUILD_LOG.md`](../../BUILD_LOG.md) → session 2026-09-05 (stack + charter)

## Context

Genesis 026 carried an absolute law: `no_trade_execution` — the platform would never
place a trade or move funds. That was honest for an *intelligence-only* system, but
false for the operator's actual goal: world-wide data → analysis → prediction →
backtest / paper-trade → **eventually gated real-money execution**. Keeping a law the
project intends to break would be exactly the kind of reassuring-but-wrong statement
026 exists to avoid. Silently deleting it would be worse.

## Decision

Evolve the law, explicitly and on the record, from *"never trades"* to **gated
execution, OFF by default**:

1. Execution is **DISABLED by default**.
2. Before any real-money order: **paper-trade validated** → **hard risk limits** set
   (max position, daily loss cap, kill-switch) → **human approval** (default).
3. Real-money orders fire **only** through the sentinel's gate. Every order traces to
   the evidence that licensed it; nothing fires silently.
4. **Data connectors stay strictly read-only** — execution is a separate, isolated
   path, never mixed into a data connector.

## Consequences

- **Easy:** the charter now tells the truth about the target; the operator's staged
  plan (paper first, real money only after it passes) is encoded.
- **Hard / cost accepted:** the charter now *promises a gate that does not exist yet*.
  Until `security/` implements the gate and a test proves an order cannot fire without
  passing it, this is a design commitment, not a running safeguard. Therefore: the
  **first execution-related code must be the gate and its test** — never an order path
  first.
- **Boundary:** turning the gate on is always the operator's decision, per stage,
  after paper-trade evidence. No prediction or backtest result licenses it.
