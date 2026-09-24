# A018 — Token Unlock/Vesting Intelligence (spec scaffold)

> **Status: spec scaffold** — folder + this spec only. No code / manifest / registry
> entry yet. A-series (read-only intelligence). `execution_enabled: false` (hard-coded,
> never trades — same posture as A001/A002/A015/A016/A017). Build deferred ("baaki kaam baad me").
> Rewritten to 026 conventions from the operator's research spec.

**Series:** A-series (read-only) · **Trust (target):** 1 · **Markets:** crypto (token supply)
**Reuse:** built fresh in 026 (no cross-agent code copy — CIE-OS convention); reuses A001's
canonical-fact / deviation-report format. **A001's narrower/sharper cousin**; complementary to
A017 (both supply/positioning-side risk) and A013 (Arbitrage).

---

## 1. Mission
Detect scheduled **token-unlock / vesting-cliff** events and **team/VC/treasury wallet
movements** — supply-shock events that predictably precede selling pressure — as early as
possible from **free/public** sources, and report them as **canonical, timestamped facts with
evidence-capped historical context** — never buy/sell signals.

**Not**: a trade bot, a hedging tool, or a predictor that a *specific* recipient will sell
(§3.1: unlock ≠ automatic sale, even though the base rate is strongly one-directional). It
reports the scheduled event + wallet activity as facts, with history attached only where backed.

---

## 2. Why this gap exists in the fleet
| Existing agent | Covers | Why it doesn't cover this |
|---|---|---|
| A001 Blockchain | *Generic* whale/exchange flow | Watches *any* large move without knowing *whose* wallet or *why*. A018 is sharper: tracks known team/VC/treasury/vesting wallets **and** a calendar-known unlock schedule — it flags the unlock date weeks ahead; A001 could only stumble onto the sale after as an anomaly |
| A007 Public-Record | Congress/insider/13F | Crypto vesting has no mandatory filing regime — public *contracts/schedules*, not regulatory *filings* |
| A015 Listing/Delisting | Exchange status changes | A token can be fully listed + stable, then hit by an unlock with zero exchange-status change |
| A016 Protocol/Infra | Forks/governance/exploits | Unlocks are tokenomics-scheduled, not protocol-technical |
| A017 Derivatives/Leverage | Funding/OI/positioning | A017 = leveraged *derivatives*; A018 = *spot supply* mechanics — complementary (unlock + crowded longs = compounding risk) |

Token unlocks are calendar-predictable well in advance and deserve their own schedule-aware
detector rather than being left to A001's general anomaly detection.

---

## 3. Evidence base (operator research — cited in §11; strongest large-N base of A015–A018)
**3.1 Headline + key nuance.** A **Keyrock study across 16,000+ unlock events / 40 tokens** found
**90% of unlocks generated negative price pressure** — the strongest large-N evidence in any of
these specs. **Critical nuance (same source): the impact typically starts ~30 days *before* the
unlock**, as traders price in the dilution early. Design implication (§6): the detector must fire
on a **scheduled future date**, not react on the day, or it misses most of the documented effect.

**3.2 What sets magnitude — converging multi-factor framework.**
- **Size vs circulating / volume:** unlocks **> 2.4× average daily volume** flagged as the
  liquidity-strain tipping point — a concrete threshold (contrast A017, where no fixed threshold
  exists; unlocks are a pure supply mechanic, not sentiment).
- **Cliff vs linear:** cliff = sharp shock; linear = absorbed far more easily (*the* key
  structural distinction, more than raw size).
- **Recipient type:** team/investor unlocks sell more than ecosystem/community → a
  `recipient_category` field is justified, not assumed.
- **Ambient market:** bull absorbs supply better than bear/sideways — context, not a property.

**3.3 Named 2026 cases.** Mar-2026: >$6B released, WhiteBIT $4.18B alone (~69% of the month).
Apr-2026 (magnitude is case-by-case): Celestia (TIA) **17.2% one-day supply expansion**; Wormhole
(W) **$90M unlock vs $85M market cap** (raw ratio catastrophic, but market didn't follow the naive
read — caution against over-mechanical interpretation); Hyperliquid (HYPE) 0.14%-of-cap (the
"resilient" case, below the 2.4× threshold); LayerZero (ZRO) $48.85M to core contributors
(recipient-driven). Aug-2026: PROVE/IP/YZY; general "10–40% dip depending on behavior/conditions"
(a range, not one number). ARB & OP both fell ~8% on first major unlock.

**3.4 Treasury/team-wallet movement — distinct, harder sub-signal.** Pi Network: after its 2024
unlock hit price, a 6-month vesting *pause* relieved calendar but not market pressure ("rescheduling
supply doesn't manufacture demand") → a *rescheduled/paused* unlock is itself an event (§6.4).
Pump.fun (PUMP): every team/treasury tranche tracked wallet-by-wallet in real time → A018 needs
*both* a schedule mechanism and a wallet-monitoring mechanism. **Honest limit:** identifying that
an address *is* a team/VC/treasury wallet is a labeling problem free tools only partially solve.

**3.5 What this justifies — and where it's thinner.** Schedule side (§6.1–6.3) ships with real
large-N backing; wallet side (§6.4) ships as a narrower, case-evidenced (Pi/Pump.fun) but not
statistically-validated feature — same depth-vs-breadth honesty as A015/A016/A017.

---

## 4. Data sources (free — one key boundary to verify)
| Source | Covers | Method | Caveat |
|---|---|---|---|
| **DefiLlama emissions (free)** | Vesting/unlock schedules for ~300–326+ projects (date, amount, % supply, cliff/linear, category) | `defillama.com/unlocks/{protocol}` + underlying free emissions dataset | **Free vs Pro boundary needs a direct check** — A016 found "token unlocks" listed among DefiLlama Pro's ($300/mo) endpoints, while community tools pull ~300–326 projects keyless. Likely: basic schedule free, richer analytics Pro. See §7-Q1 |
| **Etherscan / chain explorers (free tier)** | Raw tx/address data — confirms an unlock moved on-chain, or a wallet transferred out | Etherscan API free tier (rate-limited) | gives raw data, **not entity labels** — can't tell you a wallet *is* "the team wallet" without a known label |
| **Project's own vesting-contract / tokenomics disclosure** | Authoritative team/investor/treasury addresses | per-project blog/docs/verified contract at TGE | free but **not uniform/structured** (same "no clean API" shape as A016's exploit trackers) |
| **Nansen (free tier exists; labeling paid)** | Wallet entity labels, Smart-Money | `api.nansen.ai/api/v1` | free tier exists, but the **wallet-labeling** core (what §6.4 needs most) is paid (Standard ~$99/mo) — A018's equivalent of A017's Coinglass gap |

**4.1 Schedule side (6.1–6.3):** free + reachable — multiple independent keyless community tools
already scrape DefiLlama's unlock pages into structured calendars (~300–326 projects), confirming
the schedule data is free-reachable even if the API-vs-Pro boundary needs a build-time check.
**4.2 Wallet side (6.4):** harder — no single free structured source for "is this a team wallet".
Realistic free approach: seed the watchlist from **project-disclosed** addresses, then monitor
*those specific* addresses via Etherscan's free tx endpoint (exactly how Pump.fun was tracked in
practice). Narrower than auto-classification, but genuinely free. **Verify before build** — the
DefiLlama free/Pro unlocks boundary is the single most important thing to resolve (§7-Q1); sandbox
could not fetch it live.

---

## 5. Phased build (evidence-ranked)
- **Phase 1 — `UNLOCK_SCHEDULED`**: strongest evidence (§3.1's 16k-event study), free mechanism
  confirmed reachable; must exist first (30-day-lead finding = this is where the early-warning
  value is).
- **Phase 2 — `UNLOCK_SEVERITY` + `UNLOCK_CLASSIFICATION`**: layer §3.2's multi-factor framework
  (2.4× volume threshold, cliff/linear, recipient, market conditions) on the calendar.
- **Phase 3 — `TREASURY_WALLET_ACTIVITY`**: last — narrower seed-watchlist mechanism (§4.2),
  case-evidenced (§3.4), not statistically validated.
- **Deferred:** paid Nansen-level auto wallet-classification — build Phase 3 on the free
  self-disclosed-address approach instead (free-first, same posture A017 took on Coinglass).

---

## 6. Detectors
- **`UNLOCK_SCHEDULED`** (P1) — a known vesting schedule shows an unlock within a forward window
  (**≥30 days**, matching §3.1's pre-event lead). Fields: token, unlock_date, amount_tokens,
  estimated_value_usd, pct_of_circulating_supply, days_until_unlock. Annotation: Keyrock base rate
  (90% negative, ~30-day lead) — a base rate, **not** a per-token guarantee (see Wormhole counter-case).
- **`UNLOCK_SEVERITY`** (P2) — §3.2 factors. Fields: unlock_to_avg_daily_volume_ratio (flags the
  2.4× threshold), ambient_market_condition (bull|bear|sideways — links to A010), severity_flag
  (elevated|not) — **no** single "expected drop %" (evidence gives a 10–40% range + counter-cases).
- **`UNLOCK_CLASSIFICATION`** (P2) — Fields: vesting_type (cliff|linear|mixed), recipient_category
  (team|investors|ecosystem|treasury/DAO|mixed), is_rescheduled_or_paused (Pi Network case — a
  pause is its own fact, flagged separately, not silently overwriting the schedule).
- **`TREASURY_WALLET_ACTIVITY`** (P3) — on-chain movement (free Etherscan) from a **seed-watchlist**
  address captured from the project's *own* disclosure. Fields: token, wallet_address,
  wallet_role_as_disclosed, movement_type (transfer-out | to-exchange-deposit | other), amount,
  timestamp. Framed as disclosure-dependent, **not** a general wallet-classification engine.

---

## 7. Trust & capping (mirrors A001; split by evidence depth)
Starting **trust 1**; 6.1–6.3 cite real large-N evidence from day one; 6.4 ships case-evidence
only (Pi/Pump.fun) with **no fabricated %** until self-accumulated. Builds via (1) N≈10 observed
unlocks — cleaner internal feedback than peers, since the 30-day-lead lets A018 validate its own
lead-time vs realized price; (2) cross-validation vs A017 (unlock + POSITIONING_EXTREME/cascade
risk = compounding-risk joint signal) and A001 (TREASURY_WALLET_ACTIVITY ↔ EXCHANGE-01 inflow
anomaly = confirmation). `execution_enabled: false`, hard-coded.

## 8. Fleet relationships
→ **A017**: the most natural pairing — an unlock landing on a token A017 flags as crowded-long is
a compounding-risk joint report. → **A001**: `TREASURY_WALLET_ACTIVITY` is a schedule-aware special
case of A001's whale detectors — cross-validation partner, not a duplicate. → **A013**: a large
unlock is a candidate driver of cross-exchange dislocation (flag, not asserted). → **A007**: no
overlap (traditional-securities disclosure has no crypto-vesting equivalent).

## 9. Open questions before build
1. **Most important:** is DefiLlama's unlock/emissions data (date/amount/%/cliff-linear/recipient)
   reachable via a genuinely free keyless API, or is structured access in the $300/mo Pro tier
   (free = web page → scrape)? Direct fetch test before Phase 1.
2. Nansen free-tier's actual wallet-labeling capability — confirm before assuming paid is required.
3. Is the 2.4×-daily-volume threshold corroborated elsewhere or single-origin? Check before trusting.
4. What fraction of tokens cleanly disclose vesting addresses (§6.4 depends on it)? Small pilot first.

## 10. Sources (operator research)
Keyrock 16k-event study (via mychores.in, Jul 2026); 90%-pressure + 2.4× threshold (KuCoin, Feb
2026); cliff/linear + recipient/market factors (KuCoin May 2026, CoinGabbar Apr 2026 — ARB/OP ~8%).
Cases: WhiteBIT $4.18B (KuCoin), Apr-2026 Celestia/Wormhole/Hyperliquid/LayerZero (bex.co),
Aug-2026 PROVE/IP/YZY (KuCoin). Wallets: Pi Network + Pump.fun (crypto.news, Jul 2026). API:
DefiLlama emissions (community tool listings) + Pro-tier note; Coinglass paid `token/vesting` docs;
Etherscan free tier + Nansen tier structure (eco.com pricing snapshot). *All figures cited
third-party claims — A018 caps them until it measures its own.*
