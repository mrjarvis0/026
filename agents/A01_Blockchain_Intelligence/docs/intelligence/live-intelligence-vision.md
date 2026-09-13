# Live Intelligence Vision — Streaming Whale & Smart-Money Tracker

## A01 Blockchain Intelligence Agent

**Project:** CIE-OS (Crypto Intelligence Engine Operating System) → migrated into 026
**Document Type:** Build Vision / Forward Plan (operator-authored, not yet built)
**Version:** 1.0.0
**Status:** Proposed — approved direction, implementation pending
**Author:** Operator (026) + Claude, session 2026-09-13
**Language note:** Written in English for the docs, but this captures a plan
first discussed in Hinglish. Where a term was the operator's own framing it is
kept verbatim in quotes.

---

# 1. Why This Document Exists

The operator asked a sharp question that changes A01's data strategy:

> "Blocks ke data ko download karne ke bajay, us data ko online hi read karke,
> har second jo data mil raha hai usi blockchain par read karke calculation
> kare."

Translation: **stop treating history as a download job; treat the chain as a
live stream.** Read every new block as it arrives, compute on it, remember the
*intelligence* (not the raw blocks), and act.

This is a real architectural shift, not a cosmetic one, so it is written down
before it is built. The formal architecture docs
(`docs/architecture/future-evolution-architecture.md`,
`docs/intelligence/future-problems.md`) describe the *platform*; this document
describes the *specific capability* the operator wants next and the honest gap
between vision and current code.

**This is a plan. None of §4–§7 is built yet unless a status table says so.**

---

# 2. The Two Problems This Solves

As of 2026-09-13, A01's bottleneck is **data, not code** (see the gap audit,
§9). Two concrete numbers:

- **Data length:** `a01.db` holds **82 blocks** (block 25,723,714 →
  25,723,795), a **~16-minute** window on 2026-08-10. A01's own doctrine needs
  ≥3,600 blocks (~12h) before it may claim "nothing happened." We have **2.3%**
  of that. A batch-download model will always lag.
- **Data legibility:** `decimals_known = 0` for **all 30,113** token transfers
  across **637 tokens**. Raw on-chain amounts have no decimal point; without
  the token's `decimals` we cannot tell $5 from $5M. Only native ETH (always 18
  decimals) is currently valued.

The streaming model addresses the first. **SP-4 (decimals) must land first**,
or the live stream will arrive with token values still stuck at zero.

---

# 3. The Operator's Vision (as stated)

A single agent/tool that:

1. **Reads every incoming block, continuously** — not a one-off download.
2. **Focuses on large-value payments** rather than treating every transfer equally.
3. **"Online academy se sikhega"** — learns how whales and smart-money actually
   transact, and how to tell them apart. *(Reframed honestly in §5 — an agent
   does not learn from a course; it learns from labels, behaviour, and
   feedback.)*
4. **Reads everything, but calculates the important totals** — total in / total
   out per wallet.
5. **Remembers whale & smart-money wallet addresses**, keeps a permanent watch
   on them, and **raises alerts**.

This is not a trading bot. It is an **intelligence** system: watch, understand,
remember, warn. Execution of trades is explicitly out of scope here (see §8).

---

# 4. Vision Decomposed → 5 Capabilities (with honest status)

Each capability maps to what already exists in the tree so we build on it, not
beside it.

| # | Capability | What it means | Current status in code |
| --- | --- | --- | --- |
| C1 | **Live block reader (daemon)** | A long-running process that ingests each new block as it lands | ❌ **Missing.** `ingestion/poller.py` never sleeps — manual CLI only. Sensors + RPC connectors exist. |
| C2 | **Materiality focus** | Ignore dust; concentrate on large-value activity | ✅ **Exists.** `MaterialityGate` + `materiality_floor` already filter small transfers. Reuse, don't rebuild. |
| C3 | **Whale vs smart-money classification** | Decide whether a mover is a whale, an exchange, a market-maker, or "smart money" | 🟡 **Partial.** Detectors + `WhaleTransferSkill` + smart_money skill exist. `labels` table = 2,859 rows, **all `category=exchange`, all `unverified`**. `entities` table **empty**. |
| C4 | **Per-wallet flow accounting** | Running total in / total out per wallet | 🟡 **Partial.** Skill exists but blocked by `decimals_known=0` for tokens (native flow only today). |
| C5 | **Watchlist + memory + alerts** | Save notable addresses, watch them forever, notify | ❌ **Missing.** `entities` table empty; `Notifier` has no delivery sink (no Telegram/Discord/etc.). |

**Takeaway:** roughly **40% of the vision already has scaffolding** in A01. The
missing pieces are a daemon (C1), verified labels + populated entities (C3), the
decimals unblock for accounting (C4), and an alert channel + watchlist store (C5).

---

# 5. "Learning" — What It Honestly Means

The operator's phrase was "online academy se sikhega." Stated plainly: **an
agent does not learn from a course.** Real, buildable learning comes from three
mechanisms, in increasing power:

### 5.1 Learning from labels (strongest, cheapest)
External sources (Etherscan, Arkham, community lists) already know that an
address is "Binance hot wallet" or "Wintermute (market maker)." Ingest these
into the **`entities`** table and identity is *looked up*, not guessed. This is
the fastest accuracy win and directly fills the empty `entities` table.
→ Constrained by `attribution-doctrine.md`: real-world identity claims are
capped at 0.40 confidence and must cite the external source.

### 5.2 Learning from behaviour (heuristics)
Identity by *pattern*, not by name:
- **Whale** = a large lump-sum mover relative to the token's normal size.
- **Exchange** = many-to-one / one-to-many hot-wallet fan patterns.
- **Smart money** = wallets whose *past positioning preceded favourable price
  moves.*

These are rules over observed structure — no name required. Governed by
`detection-catalog.md` and the confidence ceilings in §3 of the tradecraft index.

### 5.3 Learning from feedback (true self-learning) — the operator's real ask
This is what "ye unki jankari ek intelligence ki tarah yaad bhi karega" actually
means:

1. Agent makes a call ("Wallet X is accumulating; likely bullish").
2. After a fixed horizon (e.g. 24h) it **checks whether the call was right**
   against realised price/flow.
3. It **updates that wallet's track-record score.**

Over time, wallets that are repeatedly right get promoted to "smart money";
wallets that are repeatedly wrong get demoted. **The watchlist curates itself.**
This is the highest-value mechanism and the one A01 currently lacks entirely
(no outcome-scoring loop exists).

> Doctrine tie-in: this *is* the "confidence is a measurement, not a mood"
> commitment (tradecraft §3.3) applied to wallets. A wallet's score becomes a
> checkable, falsifiable track record — exactly the error-rate discipline the
> evidence standard demands.

---

# 6. Additional Ideas (Claude-proposed, operator-approved direction)

These extend the vision beyond the operator's original five points.

### 6.1 Self-curating watchlist (promotion / demotion)
Right → promote toward "smart money" + permanent watch. Wrong → demote / drop.
Directly implements §5.3 as a durable, evolving list.

### 6.2 Wallet clustering ("one player, many wallets")
A single actor often splits across 10+ addresses funded from one source.
Cluster them so the picture reads "1 big player," not "10 small ones."
→ **Hard constraint:** clustering is dangerous. Must respect
`attribution-doctrine.md` §3 (co-ownership ceiling 0.95, CoinJoin/collaborative-tx
exclusion, cluster-collapse circuit breaker). One bad merge contaminates
thousands of conclusions.

### 6.3 Exchange-flow direction as an early signal
Whale sends coins **to** an exchange → often pre-sell (bearish lean). Whale
withdraws **from** an exchange → often accumulation/HODL (bullish lean). The
`exchange_flow_hourly` table already exists to support this — it just needs
populating from the live stream.

### 6.4 A01 ↔ A02 fusion (the two-agent payoff)
A01: "whale is dumping token T." + A02 (News Intelligence): "token T has
coordinated fake hype right now." → combined **"possible rug / dump"** alert far
stronger than either signal alone. This is the whole reason both agents live in
026. Runs over the kernel bus (`orchestrator/event_bus`) already built.

### 6.5 Every alert carries confidence + a reason
Not "🚨 whale." Instead: "🚨 82% — Wallet X sent $2M USDC to Binance; this
wallet's last 4 calls were correct." Trust is built by showing the reasoning and
the track record, per the evidence standard.

### 6.6 Market-Impact / Event-Study Engine (operator idea, 2026-09-13)
The operator's framing:

> "Ye track karega ki kis wallet ne kaunsa, kitna, kis time transaction kiya —
> jisse kis token ya currency par pump ya dump aaya. Ek whale ka move aaya to ye
> har exchange par dekhega ki us transaction se kaunse token/currency par asar
> hua."

Plainly: treat each large wallet move as an **event**, and measure the
**price/volume impact** around it across venues. This is classic *event-study /
market-impact analysis* and is the highest-value capability in the vision — but
it is only honest if built statistically, not anecdotally.

**The core danger — correlation ≠ causation.** A whale move and a price move at
the same time does **not** prove the whale caused it:
1. **Reverse causality** — news (A02) may have moved price first; the whale
   *reacted*. Then the whale is a *follower*, not a *cause*.
2. **Confounders** — a third factor (macro news, another large actor) was the
   real driver.
3. **Single events prove nothing** — one match can be coincidence. Confidence
   comes from the pattern across **many** events, never one.

**How it must be built (per event):**
1. **Capture the event** — wallet, token, amount, exact time (block timestamp).
2. **Before/after window** — price of the affected token (and native) in, e.g.,
   the 1h before and 1h after.
3. **Subtract a baseline** — compare the move against the token's normal
   volatility. "+2%" only matters if normal is 0.3%. This removes noise.
4. **Direction match** — deposit to exchange → dump lean; withdrawal from
   exchange → pump lean (from `exchange_flow_hourly`).
5. **Score it** — was the implied call right or wrong? Feeds the **feedback
   loop (§5.3)**. After N events: "after this wallet's large moves, TOKEN falls
   within 1h 70% of the time" — now checkable and falsifiable.

**Data reality ("har exchange par dekhega"):**
- **DEX (Uniswap, etc.)** — on-chain, already ingestible. ✅
- **CEX (Binance, Coinbase, etc.)** — **not on-chain.** Price/volume must come
  from each exchange's **own API**. Today only **one** price source (DeFiLlama,
  keyless) is wired. Multi-venue requires new connectors (extends SP-1).
- **Blocker:** without token **decimals (SP-4)** we cannot even say which token
  moved how much. SP-4 gates this feature.

**Suggestions (Claude):**
- **Never alert on a single event** — only once a wallet has a track record.
- **Fuse A02** — if news preceded the move, A01 must self-label as *follower,
  not cause.* This is the main defence against false causal claims.
- **Impact score per event** — magnitude, speed, and excess-over-baseline in one
  number.
- **Observe before predict** — this engine first *records* what happened; only
  after enough history does it *forecast*. Reversing that produces confident
  fiction (cf. the current placeholder `intelligence/prediction/`).
- **Confidence + reason on every output** (§6.5).

**Doctrine tie-in:** a causal claim ("whale X moved token T") is a strong
assertion; it must obey `evidence-standard.md` (grounded, falsifiable, retained
contradicting evidence) and the confidence ceilings in the tradecraft index. An
impact correlation is **not** proof of intent or identity.

**Where it sits:** builds *on top of* SP-4 + the live daemon + multi-venue price
connectors. It is the roof, not the foundation — see build order §10 (step 8).

---

# 7. Streaming Architecture (target shape)

```text
                 ┌─────────────────────────────┐
   WebSocket     │  C1 Live Block Reader        │   ← subscribe to newHeads
   (newHeads) ──▶│  (daemon, 24/7)              │     (push, not per-second poll)
                 └──────────────┬──────────────┘
                                │ each new block
                                ▼
                 ┌─────────────────────────────┐
                 │  C2 Materiality Gate         │   ← drop dust, keep big moves
                 └──────────────┬──────────────┘
                                ▼
        ┌───────────────────────────────────────────────┐
        │  Decimals resolve (SP-4)  →  value in USD      │   ← MUST land first
        └──────────────┬────────────────────────────────┘
                        ▼
   ┌────────────────────────────┐     ┌────────────────────────────┐
   │ C4 Rolling flow accounting │     │ C3 Classify mover           │
   │  (12h window totals in mem)│     │  labels + behaviour + score │
   └──────────────┬─────────────┘     └───────────────┬────────────┘
                  └───────────────┬───────────────────┘
                                  ▼
                 ┌─────────────────────────────┐
                 │  C5 Watchlist + memory       │  ← entities table, track record
                 │      + Alerts (channel)      │  ← Telegram/Discord sink
                 └──────────────┬──────────────┘
                                ▼
                 ┌─────────────────────────────┐
                 │  Feedback loop (§5.3)        │  ← 24h later: was it right?
                 └─────────────────────────────┘
```

**Key design decisions:**
- **Push, not poll.** Subscribe to `newHeads` over WebSocket; the node pushes
  each block. Avoids hammering the RPC every second and avoids missed blocks.
- **Remember intelligence, not raw blocks.** Keep rolling **summaries** (12h
  running totals, per-wallet state, watchlist) in state/DB — not the full block
  history. This is the operator's core insight: the *conclusion* is worth
  keeping, the raw block is not.
- **The "no-absence-without-coverage" rule survives.** Even streaming, A01 may
  not claim "no whale activity" until the rolling window has ≥ the required
  coverage. The window is what backs the claim, not the disk archive.
- **Backfill is separate.** A short historical backfill (to warm the 12h window
  on startup) is a bounded job, not the primary data strategy.

---

# 8. Safety Guardrails (non-negotiable)

Carried from `ADR-0002` and the migration decisions:

- This capability is **read-only intelligence**. It **watches and warns; it
  never places, signs, or executes a trade or transfer.**
- `config/constants.py::NO_TRADE_EXECUTION=True` stays true. The runtime gate
  (`security/sentinel/gate.py`) DENIES execution by default.
- Any future order path is a **separate, later, operator-gated** stage
  (roadmap SP-8..SP-12), reached only after paper-trading + risk-limits, and
  turned on by the operator per-stage — never by Claude.
- Alerts are **information**, not instructions to act.

---

# 9. Honest Position (gap audit, 2026-09-12)

Live-verified, read-only — nothing was changed to produce these:

- pytest **1,843 pass**; doctor **14/14**.
- Detectors: **4 validated + alerting, 1 muted**; **19 skills all `LIMITED`**.
- Only **1 keyed provider** (Alchemy) of 21 endpoints.
- `a01.db`: **82 blocks** (2.3% of the 3,600 needed for absence claims).
- `decimals_known = 0` on **all 30,113** token transfers (637 tokens).
- `labels`: 2,859 rows, all `category=exchange`, all `unverified`.
- `entities`, `hourly_aggregates`, `approvals` tables: **empty**.
- Built-but-unwired: `TokenDecimalsResolver`, `rpc_sensor.balance/token_balance`
  have **zero production callers**; `normalization/logs.py:219` hardcodes
  `decimals_known=False`.
- `intelligence/prediction/` is placeholder arithmetic (`price*(1+drift*i)`).
- 9 empty dirs under `intelligence/` (risk, reasoning, probability,
  manipulation, liquidity_engine, digital_twin, confidence_engine,
  blockchain_dna, behavior_engine).

**Honesty flags to remember:**
- `agent.yaml` still says no detector is validated — stale vs `decision/maturity.py`.
- The 535-case backtest corpus is **synthetic** (`evaluation/labelled.py`
  generates `0x{i:040x}` addresses) → "validated" means arithmetic-verified,
  **not** measured real-world precision/recall.
- Skills registry says "no balance sensor" but the sensor exists — the real
  bound is *unwired*, not *absent*.

Report artifact:
https://claude.ai/code/artifact/dfad5f56-98f8-453d-b832-5ffba52814f2

---

# 10. Build Order (recommended)

Strict dependency order — each unblocks the next:

1. **SP-4 — Token decimals wiring.** Wire `TokenDecimalsResolver`; fix
   `normalization/logs.py:219`. Unblocks token USD value **everywhere**. Cheap,
   highest leverage. *Do this first.*
2. **C1 — Live block reader / daemon.** The operator's streaming engine.
   WebSocket `newHeads` → materiality → normalize. Turn `ingestion/poller.py`
   into a real long-running loop.
3. **C3 labels/entities — populate identity.** Ingest verified labels into
   `entities`; move labels beyond all-`exchange`/all-`unverified`.
4. **C4 — Rolling per-wallet flow accounting.** 12h in-memory window totals,
   in/out per wallet (now valued, post-SP-4).
5. **Feedback loop (§5.3) + self-curating watchlist (§6.1).** The real
   "self-learning." Score calls at a horizon; promote/demote wallets.
6. **C5 alert channel.** Give `Notifier` a real sink (Telegram/Discord),
   confidence + reason per alert (§6.5).
7. **A01 ↔ A02 fusion (§6.4).** Combined rug/dump alerts over the kernel bus.
8. **Market-impact / event-study engine (§6.6).** Correlate whale events with
   cross-venue price/volume impact; build per-wallet impact track records.
   Requires SP-4 + daemon + multi-venue price connectors first. Observe before
   predict. The roof of the whole vision.

Clustering (§6.2) slots in after C3, behind the attribution-doctrine safeguards.
Multi-venue (incl. CEX) price connectors are a prerequisite for step 8 and
extend SP-1.

---

# 11. Cross-References

- Platform evolution: `docs/architecture/future-evolution-architecture.md`
- What breaks over time: `docs/intelligence/future-problems.md`
- Attribution limits (identity/clustering ceilings): `attribution-doctrine.md`
- Evidence + confidence discipline: `evidence-standard.md`
- How each detection works: `detection-catalog.md`
- Execution safety: `ADR-0002` (deny-by-default runtime gate)

---

**End of Live Intelligence Vision** — *proposed, not yet built. Build order in §10.*
