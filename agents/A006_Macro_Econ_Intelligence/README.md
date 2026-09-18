# A006 — Macro/Econ Intelligence (scaffold)

> **Status: scaffold** — manifest only, no code, no data pipeline, no tests.
> Not an active fleet member (`config/agents/registry.yaml`: `enabled: false`).
> Follows the MacroEconAgent Research & Development Specification.

## Why this agent exists

MacroEconAgent (A006) is a macroeconomic intelligence agent for Forex that continuously monitors economic releases, central-bank communication, market expectations, interest-rate dynamics, bond yields, and cross-asset reactions.

Its purpose is not to simply show economic news or produce a BUY/SELL prediction. The agent answers:
What changed, compared with what the market expected, how could that change central-bank policy expectations, what are yields doing, how is the currency reacting, what evidence confirms or contradicts the thesis, and how certain is the assessment?

## Scope

**In scope (this agent):**
- Inflation (CPI, PCE, PPI)
- Employment (NFP, Unemployment, Wage growth)
- Growth (GDP, Retail Sales, PMI, ISM)
- Policy (Interest-rate decisions, QE/QT, Statements, Minutes)
- Expectations (Yield Differential, Market Reaction)
- Priority FX Pairs (EUR/USD, GBP/USD, USD/JPY, USD/INR)
- Futures positioning (COT, CFTC)
- Fed communications (Federal Reserve Board)
- Federal legislation (GovInfo BILLSTATUS)

**Explicitly out of scope (routed elsewhere — do not duplicate):**
- Congressional trades, insider Forms 3/4/5, 13F, lobbying, patents, clinical trials, FDA → `A007` Public-Record
- Wikipedia pageviews → `A004` Sentiment (attention/interest proxy, not a filing)

## Core Intelligence Pipeline

```
Economic / Policy Event
        ↓
Actual vs Market Expectation
        ↓
Surprise Measurement
        ↓
Central Bank / Policy Implication
        ↓
Expected Interest-Rate Path
        ↓
Yield Differential
        ↓
FX Reaction
        ↓
Cross-Asset Confirmation
        ↓
Historical / Regime Context
        ↓
Contradiction & Risk Check
        ↓
Evidence-backed Macro Assessment
        ↓
Human Decision Layer
```

## Key Design Principles

1. **Economic Surprise ≠ Currency Direction**: The final reaction can differ due to market positioning, prior pricing, risk sentiment, simultaneous releases, central-bank communication, safe-haven flows, and yield reaction.
2. **Forecast as a Distribution**: Forecast is not a single number. Measure forecast dispersion and ranges.
3. **Point-in-Time Data Requirement**: Every macro observation preserves original value, revised value, release timestamp, revision timestamp, source, vintage. At timestamp T, the agent can only access information that was actually available at T.
4. **No autonomous trading**: Output is evidence-backed assessments, human-controlled output, and uncertainty risk profiling.

## Recommended Build Sequence

Do NOT build everything at once. Build sequentially:

1. Data Schema
2. Source Registry
3. Economic Event Engine
4. Revision / Vintage Engine
5. Surprise Engine
6. Central Bank Engine
7. Policy Expectations Engine
8. Yield Engine
9. FX Impact Engine
10. Cross-Asset Engine
11. Contradiction Engine
12. Historical Event Engine
13. Backtesting
14. LLM Reasoning
15. Production Monitoring

1. Flesh out `evidence.detectors` in `agent.yaml`.
2. Vertical slice first: **one** indicator → ingestion → normalization → store → **one** skill, before expanding.
3. Register in `config/agents/registry.yaml` with `enabled: true` only once tests exist.
