# A017 — Derivatives/Leverage Intelligence (spec scaffold)

> **Status: spec scaffold** — folder + this spec only. No code / manifest / registry
> entry yet. A-series (read-only intelligence). `execution_enabled: false` (hard-coded,
> never trades — same posture as A001/A002/A015/A016). Build deferred ("baaki kaam baad me").
> Rewritten to 026 conventions from the operator's research spec.

**Series:** A-series (read-only) · **Trust (target):** 1 · **Markets:** crypto (perp futures)
**Reuse:** built fresh in 026 (no cross-agent code copy — CIE-OS convention); reuses A001's
canonical-fact / deviation-report format; **direct risk-signal feeder to A013 (Arbitrage) and
T01**; complementary to A010 (Volatility Regime, scaffold).

---

## 1. Mission
Detect **leverage-driven market stress** — extreme funding rates, open-interest spikes,
long/short positioning extremes, and liquidation cascades — as early as possible from
**free/public** sources, and report it as **canonical, timestamped facts with evidence-capped
historical context** — never a buy/sell signal, and **explicitly never as a claim that a fixed
threshold predicts a reversal** (the evidence itself says no such threshold exists — §3.5).

**Not**: a trade bot, a margin calculator, or a predictor of the exact cascade moment. It
reports current derivatives conditions (funding/OI/positioning) + historical comparison, and
is explicit that "extreme funding" and "reversal imminent" are **different claims** (§3.5).

---

## 2. Why this gap exists in the fleet
| Existing agent | Covers | Why it doesn't cover this |
|---|---|---|
| A001 Blockchain | On-chain flows (7 EVM chains) | A cascade happens inside an exchange's futures engine — no on-chain footprint for CEX perps |
| A002 News | Narrative/rumor | Covers the conversation *about* a crash, not the leverage mechanics *causing* it |
| A005 Market Data (scaffold) | Spot OHLCV/orderbook | No funding / OI / positioning — derivatives-specific metrics with no spot equivalent |
| A010 Vol Regime (scaffold) | Classifies *price* vol after the fact | A017 watches the leverage buildup that *precedes/amplifies* it — a leading input, not a duplicate |
| A013 Arbitrage (scaffold) | Cross-exchange price gaps | A017 feeds risk context: a live cascade means gaps may be liquidity stress, not stable arb |
| T01 (execution) | Spot TA-signal bot | T01's signals are all spot-price-derived — leverage positioning is a genuinely new category for it |

No current fleet agent ingests funding/OI/positioning — historically the most reliable
early-warning layer for the sharpest crypto moves.

---

## 3. Evidence base (operator research — cited in §11; sourced claims, cap until measured)
**3.1 Funding rate — real signal, NOT a fixed-threshold system.** BTC funding above ~0.10%/8h
(~0.30%/day) has often coincided with local peaks (2021 hit 0.15–0.20% in euphoria); extreme
funding creates a self-correcting unwind loop; a 2025 Gate.io analysis found compressed/negative
funding preceded some reversals (works both directions). **Critical (stated by the sources, not
inferred): "there's no universal funding rate level that reliably signals a reversal."** A 2026
26-exchange study (35.7M obs) found CEX dominate price discovery (all significant flow CEX→DEX,
zero reverse) → weight CEX funding primary, DEX confirmatory.

**3.2 Open interest — leverage-buildup gauge.** Aug-2026: OI fell ~$3B in a rapid slide →
$308M liquidations in minutes (total OI $48–51B, BTC ~$24B); **no single cause** — ordinary
leverage unwinding at speed (frame differently from A016's exploit events). OI-to-spot-volume
ratio is a cleaner stress gauge than OI alone.

**3.3 Liquidation cascades — strongest, most specific evidence.** Oct 10–11 2025: largest ever,
**>$19B** liquidated (~$16.7B longs), ~1.6M traders, total perp OI **−43%** ($217B→$123B) in a
day (Hyperliquid −57%). Then Jan-20-2026 $1.08B, Feb-1-2026 "Black Sunday II" $2.2B, Jun-2-2026
$1.8B, **Aug-20-2026 $1.74B short squeeze** (cascades run both ways). **>85% of liquidations in
major events are longs.** Three factors set cascade size: OI level, average leverage, price
velocity — directly usable as detector fields (§6.3).

**3.4 Positioning / long-short ratio — contrarian gauge (dated case).** Nov-2025: at BTC's
$126k ATH, Binance global L/S ratio sat at multi-year lows <0.6 (big accounts net-short into
strength); over the next 45 days BTC fell >35% and the ratio surged to **3.87** (net-long into
weakness). Rule-of-thumb (cited, not A017's own): >3.0 ≈ tops, <0.5 ≈ bottoms. Top-trader
positioning is flagged as more predictive than retail → track Binance's 3 ratio types
separately. Caveat: ratios are **account count**, not notional.

**3.5 What this justifies — and what it does NOT.** Four structurally distinct detectors (§6).
**It does NOT justify any fixed numeric threshold that reliably calls a reversal** — report the
metric + its own-symbol historical percentile, flag the extreme zone, and stop. Never phrase
output as "reversal imminent." This is A017's caveat being *stricter* than A015/A016 — the
evidence itself rejects threshold-prediction.

---

## 4. Data sources (free/keyless — verify reachability before build)
| Source | Covers | Method | Caveat |
|---|---|---|---|
| **Binance Futures public API** | Funding (current+hist), OI, 3 long/short ratios | `fapi.binance.com` `/fapi/v1/fundingInfo`, `/openInterest`, `/futures/data/globalLongShortAccountRatio` + `topLongShortAccountRatio` + `topLongShortPositionRatio` | L/S endpoints return **only last 30 days** — older history must be self-captured going forward |
| **Bybit v5 public API** | Funding history, OI, ticker | `api.bybit.com/derivatives/v3/public/...` | keyless; same history-depth caution likely |
| **CCXT** (reused from A015) | Unified funding/OI across venues | `fetch_funding_rate()`, `fetch_open_interest()` | check `.has` per exchange, not uniform |
| **DefiLlama free** (reused from A016) | TVL cross-check (DeFi perp deleveraging) | `api.llama.fi` | secondary/confirmatory only |

**4.1 The one real gap — no free cross-exchange liquidation-heatmap API.** Coinglass is the
dominant aggregator but its **API is paid ($29/mo Hobbyist min, no free API tier)** — its free
website is view-only. Stated plainly (like A016's DefiLlama-Pro / A015's Bybit-IP gaps). Free
alternatives: (a) `vsching/liquidation-heatmap` (GitHub, MIT, CCXT+Streamlit) **reconstructs** a
Coinglass-style heatmap from live order-book depth + leverage-tier math (Binance/OKX/Bybit) — a
legitimate free substitute, not equal precision; (b) big newsworthy cascades are confirmable via
ordinary news citing Coinglass's *public dashboard* (natural reuse with A002). **Verify before
build:** `fapi.binance.com` / `api.bybit.com` reachability not confirmed live (sandbox limit).

---

## 5. Phased build (evidence-ranked)
- **Phase 1 — `LIQUIDATION_CASCADE_RISK` + `OI_SPIKE`/`OI_COLLAPSE`** (ship together — OI is an
  input to cascade-risk): strongest, most specific evidence (§3.2/3.3), highest impact. Binance
  OI endpoint + free `vsching`-style heatmap give a workable free start.
- **Phase 2 — `FUNDING_EXTREME`**: clean keyless Binance/Bybit funding; no-fixed-threshold
  caveat built in from day one.
- **Phase 3 — `POSITIONING_EXTREME`**: cleanest endpoints but 30-day history limit → real
  percentile baselines must be self-accumulated first; ships with the Nov-2025 case as context.
- **Deferred:** paid cross-exchange liquidation heatmaps (Coinglass $29+/mo) — mature the free
  reconstruction instead, consistent with the fleet's free-first philosophy.

---

## 6. Detectors (all use own-symbol rolling **percentiles**, never fixed absolute thresholds)
- **`FUNDING_EXTREME`** — funding beyond a rolling historical percentile for that symbol (e.g.
  95th), not "funding > 0.10%". Fields: exchange, symbol, current_funding_rate,
  historical_percentile, direction (extreme-pos | extreme-neg), sustained_duration.
- **`OI_SPIKE` / `OI_COLLAPSE`** — OI moves sharply over a short window (either direction),
  optionally vs OI-to-spot-volume ratio. Fields: exchange, symbol, oi_change_pct, window,
  oi_to_spot_volume_ratio, direction. (An OI collapse is worth surfacing even with no cause —
  unlike A016's exploit-driven drops.)
- **`LIQUIDATION_CASCADE_RISK`** (P1) — composite of §3.3's three factors: OI level + leverage
  proxy + price velocity. Fields: exchange, symbol, oi_level, price_velocity_window,
  estimated_leverage_proxy, long_short_skew, risk_flag (elevated | not) — **not** a numeric
  "probability of cascade" (no calibrated model exists / is being invented).
- **`POSITIONING_EXTREME`** — Binance global / top-trader-account / top-trader-position L/S ratio
  in a historically extreme zone (own-symbol percentile). Fields: exchange, symbol, ratio_type,
  current_ratio, historical_percentile, divergence_from_retail (smart-money vs crowd).

Annotations are *comparison context* (2021 funding range, Aug-2026 OI event, the 2025–26 cascade
set, Nov-2025 positioning case) — explicitly illustrative, never "this reading = reversal".

---

## 7. Trust & capping (mirrors A001; stricter on prediction)
Starting **trust 1**; every annotation barred from being phrased as a predictive claim (§3.5 —
stricter than A015/A016 because the evidence rules out threshold-prediction). Builds via
(1) self-accumulated own-symbol percentiles (N≈10 significant events; needed for 7.1/7.4 given
the 30-day API limit) and (2) cross-validation vs A001 (cascade ↔ on-chain exchange inflows) and
A016 (exploit/fork ↔ leverage cascade — logged as correlation candidates, not assumed causation).
`execution_enabled: false`, hard-coded.

## 8. Fleet relationships
→ **A013**: a cascade flag = treat cross-exchange gaps as liquidity stress, widen CI / pause. →
**A010**: leverage buildup is a *leading* input to regime classification. → **T01**: a genuinely
new signal category (no leverage input today), gated behind T01's triple-gate. → **A001**:
cross-validation partner. → **A002**: large liquidation events are confirmable via news (reuse,
not a new pipeline).

## 9. Open questions before build
1. Confirm `fapi.binance.com` / `api.bybit.com` reachability + rate limits (first step).
2. Re-check Coinglass free/paid tiers at build time before committing to the free-only approach.
3. `vsching/liquidation-heatmap` accuracy vs a true feed — validate once both run.
4. `estimated_leverage_proxy` (7.3) has no confirmed direct free source — infer from OI/velocity,
   or accept a data gap; decide before building that field.

## 10. Sources (operator research)
Funding: Bitget Academy (Mar 2026), MetaMask News (May 2026, "no universal level"), Gate.io via
Yellow.com, MDPI 26-exchange study (Jan/Apr 2026). OI: KuCoin/TradingView (Aug 2026 $3B event).
Cascades: KuCoin/Bitsgap/PrimeXBT (Oct 2025 $19B; Jan/Feb/Jun/Aug 2026), Coinglass >85%-long +
three-factor framing. Positioning: The Block (Nov 2025 0.6→3.87), Sharpe.ai (rule-of-thumb).
API: Binance/Bybit official docs; Coinglass paid-tier snapshots; `vsching/liquidation-heatmap`
README. *All figures are cited third-party claims — A017 caps them; no fixed-threshold prediction.*
