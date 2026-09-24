# A015 — Exchange Listing/Delisting Intelligence (spec scaffold)

> **Status: spec scaffold** — folder + this spec only. No code / manifest / registry
> entry yet. A-series (read-only intelligence). `execution_enabled: false` (hard-coded,
> never trades — same posture as A001/A002). Build deferred ("baaki kaam baad me").
> Rewritten to 026 conventions from the operator's research spec.

**Series:** A-series (read-only) · **Trust (target):** 1 · **Markets:** crypto (CEX)
**Reuse:** built fresh in 026 (no cross-agent code copy — CIE-OS reuse-audit convention);
reuses A001's canonical-fact / deviation-report format; complementary to A013 (Arbitrage)
and A007 (Public-Record).

---

## 1. Mission
Detect exchange **listing, delisting, and trading-pair status-change** events across
centralized exchanges (CEX) as early as technically possible from **free/public** sources,
and report them as **canonical, timestamped facts with historically-grounded impact
context — capped by how much evidence actually backs that context** — never as buy/sell
signals. Same epistemic posture as A002: describe what happened + what has historically
followed, assign confidence, let downstream consumers (a human, T01, a dashboard) decide.

**Not**: a trade-execution bot, a "snipe the listing" tool, or a predictor of an event
before the exchange announces it. It reports facts + an evidence-gated historical
annotation (§3.4 is explicit where that annotation isn't backed yet).

---

## 2. Why this gap exists in the fleet
| Existing agent | Covers | Why it doesn't cover this |
|---|---|---|
| A001 Blockchain | On-chain whale/exchange flow (7 EVM chains) | Sees money moving to/from exchanges, not the listing *decision* — a listing can happen with zero on-chain signature until deposits open |
| A002 News | Narrative/rumor detection, impact probability | Covers *rumors about* a listing; its verification pipeline is tuned for social/news text, not structured exchange-status diffs |
| A005 Market Data (scaffold) | OHLCV/orderbook | Reacts to price *after* the move; doesn't watch the causal event |
| A007 Public-Record | Congress/insider/13F | Different regulatory domain |
| A013 Arbitrage (scaffold) | Cross-exchange price gaps | A015 is a natural **upstream feeder**: a new listing creates exactly the temporary cross-exchange mismatch A013 detects |

No current fleet agent ingests exchange-status data directly.

---

## 3. Evidence base (operator research — cited in §11; treat as sourced claims, cap until A015 measures its own)
**3.1 Listing effect (bullish):** Binance listings ~+41% median day-1, ~+73% within 30d
(Ren & Heinrich, 26 coins/18mo); a 2025 study: Binance +87% pump / 98% later dump (~70%
giveback), Bybit +61%/92%, Coinbase +41%/-28% (mildest). "Coinbase Effect" +20–30%.

**3.2 Delisting effect (bearish):** ~25–30% crashes within hours (some sources 30–50%/24h).
Apr-2026 Binance 6-token delisting: FUN −27.9%, MDT −22.8% … WAN −1.2% — the spread shows
*liquidity depth of the specific token* drives magnitude, not delisting alone. Only ~15% of
delisted tokens regain a major listing. Regulatory delistings (privacy coins, AML/MiCA) show
a distinct sharper-drop-then-partial-recovery pattern (Monero −40% → recovery).

**3.3 Justifies two structurally different detectors** — listing magnitude ∝ *which
exchange*; delisting magnitude ∝ *liquidity depth + stated reason* (see §7).

**3.4 Honest limit (read before building):** every quantified % above is from exactly
**three exchanges (Binance, Bybit, Coinbase)**. §4 lists 16 detectable exchanges —
**detection breadth ≠ evidence depth, kept separate on purpose**: A015 *detects* on all 16
with the same mechanism, but *annotates* with a historical % only on those 3; every other
venue gets the fact with confidence `insufficient sample` (never a borrowed Binance number).
Over time A015's own observed listing-day deltas accumulate into per-exchange evidence —
same "cap until measured" discipline A001 applies to its detectors.

---

## 4. Exchange coverage
Base: CoinGecko trust-score top-20 (Sept 2026), cross-referenced against **CCXT**
(`ccxt/ccxt`, open-source unified API, 104 exchanges). CCXT is why this is a 16-exchange
spec, not 4: one `fetch_markets()` works identically across all — exchange-specific code
stays in config, not per-exchange clients.

**Covered (17 = top-20 minus 4 gaps, plus Bybit for its evidence base):** `binance`,
`bybit`, `coinbase`, `kraken`, `okx`, `gate`, `bitget`, `bitstamp`, `mexc`, `kucoin`,
`gemini`, `lbank`, `binanceus`, `hashkey`, `bitvavo`, `bitso`, `cryptocom`.
**Gaps (stated plainly):** OSL & Bullish (no CCXT id — bespoke client, not v1); Bitunix &
Bitkub (confirmed absent from CCXT 4.5.81 — re-check at build time).

`fetchMarkets=True` for all 17 (the detection mechanism). `fetchStatus` is True on 8
(binance, bybit, kraken, okx, mexc, kucoin, binanceus, hashkey) — only those can fire
HALT/BREAK signals (§7.3). Rate limits vary widely (kucoin 7.5ms … bitso 2000ms) — set
poll interval per exchange accordingly.

**4.1 Detection mechanism — polling-diff, not webhooks:** periodically `fetch_markets()`
per exchange, diff against the last stored snapshot, treat any new/missing/status-changed
symbol as a candidate event. Where a native announcement-text source exists (Binance
Telegram, Gate.io WebSocket) it usually *precedes* the symbol change — that text layer is
earliest-detection, structured-diff is the confirmation layer (mirrors A002's tiers).

**4.2 Verify before build (unrestricted env):** re-run `ccxt.<id>().has['fetchMarkets' /
'fetchStatus']` + a real `fetch_markets()` call. Live network reachability was NOT confirmed
end-to-end in the research pass — this is the first implementation step, not assumed.

---

## 5. Phased build (not "20 exchanges at once")
- **Phase 1 — the 3 evidence-backed:** Binance, Bybit, Coinbase — only these ship
  `NEW_LISTING`/`DELISTING` annotations with real confidence. Proves poller + diff + detectors.
- **Phase 2 — breadth:** OKX, Kraken, Gate, MEXC, KuCoin, Bitget, Binance US, HashKey
  (structured diff, `insufficient sample` confidence).
- **Phase 3 — the rest:** Bitstamp, Gemini, LBank, Bitvavo, Bitso, Crypto.com.
- **Not planned:** OSL, Bullish, Bitunix, Bitkub (no CCXT path today).

---

## 6. Architecture (one unified CCXT poller — mechanism is identical across all 17)
```
A015_Exchange_Listing_Delisting_Intelligence/
├── config/       exchanges.yaml (ccxt_id, phase, poll_interval_s, has_native_text_feed) · detectors.yaml · watchlist.yaml
├── tools/        ccxt_market_poller.py (one generic poller) · diff_engine.py (generic snapshot-diff)
│   └── text_feeds/  binance_telegram.py · gate_websocket.py   # deliberately source-specific, kept separate
├── memory/       symbol_snapshots/ · event_log/ (append-only fact ledger) · PROJECT_STATE.md
├── detectors/    new_listing.py · delisting.py · status_change.py · pair_change.py
├── reports/      deviation_report_schema.json   # A001-style, never buy/sell
└── BUILD_LOG.md
```
**Reuse audit (CIE-OS convention):** use CCXT (`pip install ccxt`) — do NOT write bespoke
REST clients. Check A001/A005 for an existing snapshot-diff util before writing one. Reuse
A001's deviation-report schema + A002's 7-level epistemic scale for confidence.

---

## 7. Detectors
- **`NEW_LISTING`** — symbol appears in `fetch_markets()` not in last snapshot, or text feed
  shows listing language. Fields: exchange, symbol, detected_via, first_seen_ts, trading_pairs,
  phase. Annotation evidence-gated (Binance ~41% / Bybit ~61% / Coinbase ~20–30%; all others
  `insufficient sample`).
- **`DELISTING`** — tracked symbol disappears, or status→BREAK/HALT with no reversal, or text
  feed shows delisting language. Fields: exchange, symbol, detected_via, announced_effective_date,
  `stated_reason` (regulatory | low-liquidity | compliance-vote | unspecified), withdrawal_deadline.
  Annotation split by reason (low-liquidity −25…−30% wide variance; regulatory sharper-then-recover).
- **`SUPPORT_CHANGE` / `MAINTENANCE_HALT`** — status→HALT/BREAK without delisting language;
  only fires where `fetchStatus=True` (8 exchanges). No price annotation — fleet-internal risk
  signal (e.g. tells A013 not to route arbitrage through that pair now).
- **`PAIR_CHANGE`** — an already-listed asset gains/loses a specific pair. Smaller-magnitude
  sibling of NEW_LISTING (one case: CFG +60% on pair additions — single case, low confidence).

---

## 8. Trust & capping (mirrors A001)
Starting **trust 1**; historical-annotation confidence capped per §3.4 until (1) ≥ N real
events/exchange observed (N≈10, A001's threshold) and (2) cross-validated vs A002 (agreement
builds trust; disagreement is logged, not silently resolved). `execution_enabled: false`,
hard-coded, no path to true.

## 9. Fleet relationships
→ **A013**: NEW_LISTING is a near-perfect trigger to watch cross-exchange mismatch. →
**A002**: supplies the "why"; for Coinbase (no native text feed) this is a requirement. →
**T01**: may consume Binance-specific facts, gated behind its triple-gate; A015 never trades.
→ **A007**: only intersects on regulatory-driven delistings (v2 idea).

## 10. Open questions before build
1. Confirm live `fetch_markets()` reachability end-to-end (first impl step).
2. Concrete poll interval per exchange (Kraken 1000ms / Bitso 2000ms set the floor).
3. Bybit datacenter-IP-block risk — run the live smoke-test before Phase 1 relies on it.

## 11. Sources (operator research)
Ren & Heinrich Binance listing study (CoinDesk, Jan 2023) · 2025 pump/dump study (BitPinas,
Mar 2025) · Apr-2026 Binance delisting case data (CryptoNomist, BeInCrypto) · 2026 delisting
patterns + MiCA driver (FinanceFeeds, Volity, PrimeXBT) · Monero recovery (SimpleSwap) ·
CoinGecko exchange ranking (Sept 2026) · CCXT 4.5.81 capability matrix · exchange API docs
(Binance exchangeInfo, OKX public/instruments) · `tokenearly/awesome-crypto-listing-alerts`
(prior-art reference). *All percentages are cited third-party claims — A015 caps them until it
measures its own.*
