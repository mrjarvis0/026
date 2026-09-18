# 06 · Agents

[← Data sources](05-data-sources.md) · [Index](README.md) · *Next: Manual log (planned)*

> One place to see every agent, which **fleet layer** it belongs to, and why —
> so identifying "what is this thing and what can it do" is a glance, not a search.
>
> **Note on the word "layer":** this page's layers are *fleet-level* (which
> category of agent). They are unrelated to the **13-layer architecture**
> *inside* an agent like A001 (identity → interfaces) — see
> [`A001_Blockchain_Intelligence/README.md`](../../agents/A001_Blockchain_Intelligence/README.md).
> Same word, two different scopes — don't conflate them.

---

## 1. The three fleet layers

| Layer | Series | Can it act on the world? | Trust (§6 of `AGENTS.md`) | Members today |
|---|---|---|---|---|
| **Intelligence** | `A0NN` | No — read-only, `NO_TRADE_EXECUTION`. Writes findings to the brain, never money, never orders. | 2 — scoped writes | A001, A002 *(A003–A006 reserved; A007 scaffolded)* |
| **Execution** | `T0N` | Yes — but **gated** (ADR-0002): paper-trade proof required before real orders, real orders must pass the sentinel gate. | not yet assigned — see [§4](#4-open-item-t01-is-not-yet-onboarded) | T01; T02 *(simulation only — never places an order, so by the one-line test below it is really intelligence‑flavoured; numbering is an open call, see §2)* |
| **Platform** | actor | Runs the fleet itself — not a domain question-answerer. | 3 — human-adjacent | `orchestrator`, `sentinel`, `librarian`, `operator-io` |

**The one-line test:** *does it ever touch money or place an order?*
No → **Intelligence** (`A`-series). Yes → **Execution** (`T`-series). Neither, it
runs the other agents → **Platform**.

This is *why* the fleet uses two number-series instead of one continuous count
(see `AGENTS.md` §1–§3): giving an execution agent the same `A0NN` badge as a
read-only intelligence agent would make the name lie about
`NO_TRADE_EXECUTION`.

---

## 2. Current members, categorized

| ID | Name | Layer | Domain | Status | Registered in fleet contract? |
|---|---|---|---|---|---|
| `A001` | Blockchain Intelligence | Intelligence | On-chain: whales, flows, anomaly | substantial | ✅ `agent.yaml` + `config/agents/registry.yaml` |
| `A002` | News Intelligence | Intelligence | Fake-news / rumor / market impact | substantial | ✅ `agent.yaml` + `config/agents/registry.yaml` |
| `T01` | Smart Binance Intelligence | Execution | Binance spot trading — paper-trade now, real orders locked behind a 70%-accuracy gate | built (live FastAPI dashboard; paper trading with fee-aware PnL, ATR/trailing stops, VWAP confluence, loss reflection — see agent.md §8, updated 2026-09-18) | ❌ see [§4](#4-open-item-t01-is-not-yet-onboarded) |
| `T02` | Swarm Trading Intelligence | Execution* | Market consensus: a 1000-bot agent-based swarm simulating how a market reacts to a trade event | built (swarm sim + SQLite store + CLI; 4 tests pass) | ✅ `agent.yaml` + `config/agents/registry.yaml` (sentinel PASS) |

**\*T02's numbering is an open call.** By §1's one-line test — *does it ever place
an order?* — T02 is **No** (`execution_enabled: false`, reports simulated reactions
only), which makes it intelligence‑flavoured despite the `T` badge. It was merged
2026-09-18 from the Jules branch `feat/t02-swarm-intelligence` under the name the
branch gave it; renumbering it into the `A`-series (e.g. a Market/Consensus slot)
is a decision left to the operator. Unlike T01, T02 **is** registered in the fleet
contract and passes the sentinel scan.

*(Reserved, not yet built: `A003` DeFi Flow, `A004` Sentiment, `A005` Market Data,
`A006` Macro/Econ — `AGENTS.md` §3. `A007` Public-Record is scaffolded — has
`agent.yaml` + README, still not a registered fleet member — see §6 below.)*

---

## 3. Platform actors (not domain agents — they run the fleet)

| Actor | Home | Trust | Job |
|---|---|:---:|---|
| `orchestrator` | `orchestrator/` | 3 | Plans work, routes tasks, fuses agent results |
| `sentinel` | `security/` | 3 | Enforces trust, invariants, secrets, the execution gate |
| `librarian` | `brain/` | 2 | Curates the shared brain, dedups entities |
| `operator-io` | `dashboard/` | 3 | The human interface: chat, approvals, traces |

---

## 4. Open item: T01 is not yet onboarded

Flagging this rather than fixing it silently — it's a real gap, not a documentation
nitpick:

- T01 has **no `agent.yaml`** (A001 and A002 both do — `AGENTS.md` §2 calls this
  "the full contract").
- T01 has **no row** in `config/agents/registry.yaml` or in the fleet table in
  `AGENTS.md` §3.
- T01 doesn't cleanly fit an existing trust level (§6): trust 2 is defined as
  "scoped writes" (A001/A002's brain writes) — placing a real order is a bigger
  claim than that. Trust 3 is "platform, human-adjacent" — T01 is domain-specific,
  not a platform actor. **T-series likely needs its own trust tier**, not a
  reuse of 2 or 3.
- T01 currently gates itself (its own 70%-accuracy unlock + circuit breaker) —
  it does **not** yet go through the shared `security/sentinel` gate that
  ADR-0002 describes as the one path real orders must clear.

None of this blocks using T01 as a paper-trader today. It matters once real-money
execution is considered, per ADR-0002's own boundary: *"turning the gate on is
always the operator's decision, per stage, after paper-trade evidence."*
When that decision is ready, this section is the checklist: add `agent.yaml`,
add the registry row, add the `AGENTS.md` §3 row, assign a T-series trust tier,
wire T01's unlock into `sentinel.gate`.

---

## 5. Adding a new agent — quick reference

| Building… | Series | Trust | Must ship |
|---|---|---|---|
| A read-only analysis/intelligence agent | next `A00N_Domain_Intelligence` | 2 | `agent.yaml`, tests, a `config/agents/registry.yaml` row, a §3 row in `AGENTS.md` |
| An agent that acts on the world (trades, sends, executes) | next `T0N_Domain_Role` | *(see §4 — decide the tier first)* | same as above, **plus** ADR-0002's paper-trade-before-real-execution path and a sentinel-gate wire-up |

---

## 6. Queued upgrades from LuxAlgo research (2026-09-15)

The operator researched LuxAlgo's MCP server (`mcp.luxalgo.com/mcp`, 42 hosted
tools, free/keyless for public data) and asked which fleet agents its 6 data
categories should feed. Recorded here so the next build session starts
oriented, not re-researching. **Nothing below is built, wired, or tested** —
this is a queued-upgrade ledger, per `AGENTS.md` §9 (record open questions /
where the next session starts).

Full source record: [`sources/mcp.md`](../../sources/mcp.md) `S119` (hosted
server) and `S120` (Whale Options, a separate local MCP); the Broker SDK is
[`sources/infra.md`](../../sources/infra.md) `S121` (an SDK, not a feed).

| LuxAlgo tool family | Target | Change | Why |
|---|---|---|---|
| `trackers_*` — 10 of 18 datasets (Congress trades, insider Forms 3/4/5, 13F, lobbying, campaign finance, PAC, patents, clinical trials, FDA, hearings) | **`A007`** *(new, scaffolded)* | New agent | Doesn't fit `A004`/`A006` without blurring both — see [`agents/A007_Public_Record_Intelligence/README.md`](../../agents/A007_Public_Record_Intelligence/README.md) |
| `trackers_*` — COT, Fed communications, legislation | `A006` Macro/Econ *(reserved)* | Upgrade — first real source | Matches `A006`'s existing domain (rates, indicators, filings) |
| `trackers_*` — Wikipedia pageviews | `A004` Sentiment *(reserved)* | Upgrade — first real source | Attention/interest proxy, not a filing |
| `edge_*` (Edge Stats — historical win-rate, N + 95% CI) | `A005` Market Data *(reserved)* | Upgrade — first real source | Matches `A005`'s domain (OHLCV/quotes/orderbook) |
| Whale Options (16 local tools — options prints, net GEX) | `A005` Market Data *(reserved)* | Upgrade | Same domain as Edge Stats — market microstructure |
| `library_*` (850+ trading concepts + Pine source) | `librarian` → `brain/global/` (Platform) | Upgrade | Shared reference, not agent-specific — any agent can cite it |
| `propfirms_*` (Monte Carlo pass-probability simulator) | `T01` (existing, built) | Upgrade — new tool/skill | Stateless calculator, not an evidence-gathering agent; T01 already does paper-trade-before-real gating — same job |
| `journal_*` (OAuth) + Broker SDK (local, operator's own keys) | **Open question** | Not assigned | Operator's own trading data, doesn't fit A001–A006's "external world" domains. See `PROJECT_STATE.md` → *Open questions for the operator* |

**Bottom line:** 0–1 new agent numbers needed (just `A007`); everything else is
an upgrade to a slot or agent that already exists. None of this is scheduled —
per `ROADMAP.md`, connector/kernel code (including `A007`) waits for the
operator's Phase 1 → Phase 4 green light.

---

[← Data sources](05-data-sources.md) · [Index](README.md) · *Next: Manual log (planned)*
