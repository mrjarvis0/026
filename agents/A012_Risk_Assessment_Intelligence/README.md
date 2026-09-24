# A012 — Risk Assessment Intelligence (empty scaffold)

> **Status: empty scaffold** — folder + this note only. No code / manifest /
> registry entry yet. A-series (read-only, *advisory* — it computes, it never
> places an order). New domain (A012). Build deferred.

**Layer:** Risk / Decision · **Markets:** crypto · forex · stocks

## What it will do
Computes position sizing, stop-loss placement, and portfolio-level exposure
(correlation-adjusted). **Advisory only** — it outputs risk numbers for the human
and the gated execution layer; execution itself stays in the T-series (e.g. T01),
never here.

**Maps to:** operator research #12 (RiskAssessmentAgent).

**Reference implementation:** [`S122` TradingAgents](https://github.com/tauricresearch/tradingagents) —
borrow their risk management + portfolio manager flow pattern (`tradingagents/agents/risk_management/`).
Key distinction: in 026 the Portfolio Manager role is split — A012 outputs advisory risk numbers,
the **sentinel** (`security/sentinel/`) holds the execution gate. A012 never places an order.
