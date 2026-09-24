# A016 — Protocol/Infrastructure Event Intelligence (spec scaffold)

> **Status: spec scaffold** — folder + this spec only. No code / manifest / registry
> entry yet. A-series (read-only intelligence). `execution_enabled: false` (hard-coded,
> never trades — same posture as A001/A002/A015). Build deferred ("baaki kaam baad me").
> Rewritten to 026 conventions from the operator's research spec.

**Series:** A-series (read-only) · **Trust (target):** 1 · **Markets:** crypto (protocol-native)
**Reuse:** built fresh in 026 (no cross-agent code copy — CIE-OS convention); reuses A001's
canonical-fact / deviation-report format; complementary to A001 and A002.

---

## 1. Mission
Detect blockchain **protocol & infrastructure** events — hard forks / network upgrades, DAO
governance proposals, bridge / cross-chain exploits, and validator/staking stress — as early
as possible from **free/public** sources, and report them as **canonical, timestamped facts
with evidence-capped historical context** — never buy/sell signals. Same posture as A002/A015:
describe what happened + what has historically followed, assign confidence, let consumers decide.

**Not**: a trade bot, a smart-contract auditor, or an exploit-predictor. It detects that a
proposal was posted, a fork is scheduled, or an exploit already occurred — then annotates with
history where evidence supports it (§3.5 is explicit where it doesn't yet).

---

## 2. Why this gap exists in the fleet
| Existing agent | Covers | Why it doesn't cover this |
|---|---|---|
| A001 Blockchain | On-chain whale/exchange flow — *transactions* | Sees money moving, not the network-level event causing it. A fork / bridge exploit / DAO vote is a structural event, not an address-level flow |
| A002 News | Narrative/rumor detection | Covers the *social conversation about* an event, not GitHub releases / governance forums / exploit feeds (structured technical sources) |
| A015 Listing/Delisting | Exchange-side status changes | Watches what *exchanges* decide about a token; A016 watches what the *protocol itself* does — disjoint sources, complementary events |
| A006 Macro/Econ (scaffold) | CPI/rates/central-bank policy | TradFi macro, not blockchain-native infra |
| A013 Arbitrage (scaffold) | Cross-exchange price gaps | Downstream consumer — a bridge exploit/chain halt should make A013 pause on affected assets |

Protocol-level technical events are well-evidenced, high-impact, and currently unwatched.

---

## 3. Evidence base (operator research — cited in §11; sourced claims, cap until measured)
**3.1 Hard fork / upgrade:** ETH London (Aug 2021, EIP-1559 burn) ran ~+21% the week before,
$2,600→$2,780 within ~1h of activation. Pattern across ETH's fork history: **issuance-reducing
/ supply-burning forks correlate with the largest price reactions; pure plumbing forks barely
move price** — so the detector must classify *what kind* of fork it is. Dencun (Mar 2024): no
price-shock, but L2 fees dropped 90–95% (a real non-price signal). 2025+: ETH moved to a
twice-yearly scheduled cadence (Pectra May-2025, Fusaka Dec-2025) — forks are now
calendar-predictable in advance.

**3.2 Bridge / cross-chain exploits (strongest evidence here):** H1-2026 — TRM Labs: 207 hacks
/ ~$972M; CertiK (broader def): $1.32B; bridges specifically $340.7M / 14 exploits (PeckShield).
Two largest 2026 incidents were bridge/cross-chain-adjacent: **Kelp DAO ~$292M** (forged
LayerZero cross-chain message, Aave froze the asset) and **Drift ~$285M** (6-month social-eng
against admin keys) — ~76% of 2026 hack value from 2 incidents (NK-affiliated). Historical
scale: Ronin $625M, Wormhole $320M, Nomad $190M (all 2022). **Root cause varies** (key
compromise / signature forgery / oracle / social-eng / config error) → needs a `root_cause`
field, not one generic label.

**3.3 DAO governance:** no quantified price-impact study found (genuine gap) — ships
**detection-only, no % annotation**. Snapshot is used by tens of thousands of DAOs (ENS, Aave,
Uniswap, Arbitrum, Optimism) → broad mechanism reach even without an impact-size base yet.

**3.4 Validator/staking stress:** thinnest evidence (one illustrative post-Merge case) —
possible Phase-3+ stretch goal, not a launch feature.

**3.5 Evidence depth ≠ category breadth** (same honesty as A015 §3.4): bridge exploits get real
numbers; hard forks get gated annotation; governance ships fact-only; validator-stress is
honestly labelled "thin" rather than given a manufactured number.

---

## 4. Data sources (all free, keyless where noted — verified as documented, not live-reached)
| Source | Covers | Method | Auth |
|---|---|---|---|
| **GitHub REST API** | Client releases (ETH exec/consensus, L2, bridge repos) | `GET /repos/{o}/{r}/releases` | none (60/h unauth; free PAT → 5,000/h) |
| **Snapshot Hub GraphQL** | DAO proposals/votes across thousands of spaces | `POST hub.snapshot.org/graphql` | none (100/min) |
| **DefiLlama free API** | Protocol/chain TVL — a bridge exploit = sharp TVL drop (confirmation signal) | `GET api.llama.fi/protocols`, `/tvl/{p}` | none (Pro $300/mo adds bridge/unlock endpoints — out of scope; TVL-drop is a proxy) |
| **Exploit trackers** (TRM/CertiK/PeckShield/DEXTools) | Curated exploit reports + root cause | public web pages; **no confirmed keyless JSON API** | — (v1 likely RSS/text monitoring) |
| **ETH client repos** (`go-ethereum`, `consensus-specs`, `OffchainLabs/nitro`, `ethereum-optimism/optimism`) | Fork scheduling/specs | same GitHub API | releases confirm *shipped* code; *scheduled* forks live in blogs/forums (Ethereum Magicians) |

**4.1 Mixed-mechanism, not one pattern** (unlike A015's single CCXT interface): governance =
clean keyless GraphQL; GitHub = clean keyless REST (but "shipped" ≠ "scheduled/market-relevant");
bridge exploits = hardest (evidence is human analyst write-ups, no clean API — DefiLlama TVL is
confirmation only); validator/staking = thinnest. **Verify before build** (`api.github.com`,
`hub.snapshot.org`, `api.llama.fi` reachability) — not confirmed live in the research pass.

---

## 5. Phased build
- **Phase 1 — `BRIDGE_EXPLOIT`:** highest evidence + impact; DefiLlama free TVL gives a workable
  confirmation signal today. Strongest reason to build this agent at all.
- **Phase 2 — hard fork / upgrade:** GitHub releases + governance-forum monitoring; calendar-
  predictable; useful even without a large-N study.
- **Phase 3 — DAO governance:** cleanest mechanism (Snapshot GraphQL) but ships **fact-only**
  until evidence is built.
- **Deferred — validator/staking stress:** thinnest evidence, no clean free source found.

---

## 6. Detectors
- **`BRIDGE_EXPLOIT`** (P1) — sharp TVL drop on a tracked bridge (DefiLlama, vs rolling baseline)
  OR analyst-tracker text match. Fields: protocol, chains_affected, detected_via (tvl-drop |
  tracker-text), estimated_loss_usd, `root_cause` (key-compromise | signature-forgery |
  oracle | social-eng | config | unspecified). Annotation = *comparison context* vs historical
  cases (Nomad/Wormhole/Ronin; Kelp/Drift), explicitly not a prediction.
- **`HARD_FORK_SCHEDULED` / `HARD_FORK_ACTIVATED`** (P2) — GitHub release matching fork-naming
  cross-referenced vs forum/blog activation date. Fields: network, fork_name,
  scheduled_block_or_date, `supply_effect` (issuance-reducing | fee-burning | neutral/plumbing |
  unknown). Annotation gated by supply_effect (issuance/burn → London-style reference; plumbing →
  no price annotation, only operational note like Dencun's L2-fee drop).
- **`GOVERNANCE_PROPOSAL`** (P3) — new/`active→closed` Snapshot proposal. Fields: space, title,
  state, voting_ends, `proposal_category` (treasury | fee-param | tokenomics | upgrade-signal |
  other). **No annotation in v1** (§3.3/3.5).
- **(Unscoped) Validator/staking stress** — noted for completeness, not built in v1.

---

## 7. Trust & capping (mirrors A001/A015)
Starting **trust 1**; real dollar-comparisons for `BRIDGE_EXPLOIT`, gated supply-effect
annotations for hard forks, **zero** fabricated annotation for governance until (1) ≥ N events/
sub-detector observed (N≈10) and (2) cross-validated vs A001 (a TVL cliff + an A001 on-chain
flow anomaly at the same time = trust-building agreement; a pure key-compromise/social-eng
exploit with no on-chain signature is *expected*, not a contradiction). `execution_enabled: false`.

## 8. Fleet relationships
→ **A013**: a BRIDGE_EXPLOIT on a wrapped-asset bridge = pause arbitrage (peg may be broken). →
**A001**: transaction-level cross-validation partner. → **A002**: supplies narrative/sentiment
around a fork/exploit. → **T01**: a HARD_FORK_ACTIVATED on an ETH-ecosystem asset may be a
signal input, gated behind T01's triple-gate.

## 9. Open questions before build
1. Confirm live reachability of the 3 APIs (first impl step).
2. No confirmed keyless structured API for exploit-tracker data — decide the concrete
   `tracker-text` source (RSS? site monitor? analyst feed?) before Phase 1.
3. GitHub 60/h unauth is thin — decide free-PAT (5,000/h) vs slower cadence.
4. Confirm A016 is scoped as a 3-detector agent (validator/staking explicitly deferred), or
   re-scope the 4th as a future A0XX.

## 10. Sources (operator research)
London fork reaction (CoinDesk/CNBC/MoneyWeek, 2021) · ETH fork history + Dencun L2-fee effect
(Blockready) · post-Merge staking/issuance (VanEck, 2023) · H1-2026 hack totals (TRM Labs,
CertiK via DEXTools) · Kelp DAO (KuCoin/TRM/1inch) · Drift (Phemex) · bridge totals (SpazioCrypto/
PeckShield) · historical bridge cases (Fortune 2022) · Snapshot GraphQL scale (Nansen docs) ·
GitHub REST + DefiLlama API surface (official docs). *No governance price-impact study exists —
stated as a gap, not filled with an estimate.*
