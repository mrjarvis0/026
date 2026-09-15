# sources/ — 026 Source Registry

> The dedicated home for **every external source 026 draws on** — APIs, datasets,
> links, MCP servers, models, infra. This is the *catalog* (what exists, where, and
> what it costs). It is **not** code and **not** secrets.

**Organized by TYPE** — one file per *access method*. The market/domain
(crypto, stock, macro…) is a **column inside** each file, so you can still filter
"all crypto" without splitting by market.

## The files

| File | Holds | Example |
|---|---|---|
| [`apis.md`](apis.md) | Live / queryable APIs (REST, WebSocket) | Binance API, CoinGecko, Yahoo, FRED |
| [`datasets.md`](datasets.md) | Bulk / downloadable historical datasets | data.binance.vision, Stooq, Kaggle datasets |
| [`links.md`](links.md) | **Inbox** for new raw URLs + portals/registries you browse to *find* sources | Kaggle search, AWS/GCP data registries |
| [`mcp.md`](mcp.md) | MCP servers (real-time data via MCP) | *(to be added)* |
| [`models.md`](models.md) | ML models — **not data feeds** | FinBERT |
| [`infra.md`](infra.md) | Tooling that *helps* access sources — not a feed | Massive (proxy), OpenBB (SDK), CCXT |

## The one rule that keeps this clean forever

1. **Every source has a global, stable ID** (`S001`, `S002`, …). The ID never
   changes and is **never reused**, no matter which file the row lives in — so
   moving a row later is painless and history stays honest.
2. **One row = one source + one access method.** A hybrid source (e.g. Binance =
   API + bulk download) gets **one row per method**, in the matching file,
   cross-linked by ID.
3. **New URLs land in [`links.md`](links.md) first** (the inbox), then get triaged
   into the right type file.

## Canonical row schema

Every type-file's table follows this schema (a source is not "real" until its row
is complete). `apis.md` and `datasets.md` carry the full set; `mcp.md`, `models.md`,
and `infra.md` carry the applicable subset (a model has no rate limit; a dataset has
an *access method* instead of a per-minute limit).

| Column | Meaning |
|---|---|
| **ID** | Global stable `S0xx` — the anchor, never reused |
| **Source** | Name + link |
| **Domain** | `crypto` · `onchain` · `stock` · `forex` · `macro` · `news` · `sentiment` · `mixed` |
| **Data / Access** | What it gives (APIs) or how you retrieve it (datasets) |
| **Auth** | none · key · OAuth · account |
| **Rate limit** | Requests/quota — `TBV` until a check is recorded in `BUILD_LOG.md` |
| **Cost** | Real cost of the usable tier (separate from Tier marker) |
| **Lands in** | The landing folder the connector/loader writes through |
| **Provenance field** | The fields every `data/raw/` record must carry to cite this source — **non-optional** |
| **ToS / License** | Terms/robots/license note — `check` until reviewed (never assume permission) |
| **Tier** | Cost class (below) |
| **Consumed by** | The agent that reads it |
| **Status** | Reality marker (below) |

**Tier:** `FREE` · `FREE*` (free but limited) · `PAID-LATER` (enable when funded) · `DEAD` · `INFRA` / `MODEL` (not a data feed)
**Status:** ⬜ known (limits unverified) · 🔜 web-verified 2026-09-05 · ✅ live (a connector lands a raw, cited record) · `TBV` inside a cell = that value still to be verified

**Consuming agents:** `A001` Blockchain · `A002` News · `A03` DeFi *(reserved)* ·
`A04` Sentiment *(reserved)* · `A05` Market Data · `A06` Macro/Econ · `orchestrator` (MCP).
*A05 and A06 are `planned` fleet agents in [`AGENTS.md`](../AGENTS.md) §3, promoted 2026-09-06 (see [`ADR-0004`](../docs/adr/ADR-0004-sources-by-access-type-and-stable-ids.md)).*

---

## Master index

> The **registry of the registry** — every allocated ID, where it lives, and its
> status. This is what answers *"where is S030?"* Keep it in sync when any row is
> added or moved (the ID is the anchor).

**Counts (2026-09-07):** 109 catalogued rows — **82** live APIs · **8** datasets ·
**6** portals/links · **1** model · **12** infra · **0** MCP (none yet). Plus **1**
dead (`S023`, tracked, no row) and **8** reserved/dropped IDs (gaps). Highest ID: `S118`.
*(+67 blockchain sources for A001 added 2026-09-07 from the operator's
`blockchain-data-sources-notes.md`; catalogued `⬜`/`TBV` — not yet web-verified. Skipped:
embedded-wallet & tax tooling, see `infra.md`.)*
*(The operator's original list was ~40 items; the count differs because 4 free
multipliers were added, some list items resolved to dead/infra/model, and a few
mapped to more than one access method.)*

| ID | Source | File | Domain | Tier | Consumed by | Status |
|----|--------|------|--------|------|-------------|--------|
| S001 | Binance Public Data | datasets | crypto | FREE | A05 | ⬜ |
| S002 | Binance Spot API | apis | crypto | FREE | A05 | ⬜ |
| S003 | CryptoDataDownload | datasets | crypto | FREE | A05 | ⬜ |
| S004 | CoinGecko API | apis | crypto | FREE | A05 | ⬜ |
| S005 | CoinCap API | apis | crypto | PAID-LATER | A05 | 🔜 |
| S006 | CoinPaprika API | apis | crypto | FREE | A05 | 🔜 |
| S007 | CoinMarketCap API | apis | crypto | FREE* | A05 | ⬜ |
| S008 | Kaggle — Bitcoin historical (search) | links | crypto | FREE | — (discovery) | ⬜ |
| S009 | Blockchain.com Explorer API | apis | onchain | FREE | A001 | ⬜ |
| S010 | Etherscan API | apis | onchain | FREE | A001 | ⬜ |
| S011 | Alpaca | apis | stock+crypto | FREE | A05 | 🔜 |
| S012 | Kaiko | apis | crypto | PAID-LATER | A05 | 🔜 |
| S013 | Glassnode API | apis | onchain | PAID-LATER | A001 | 🔜 |
| S014 | CryptoQuant API | apis | onchain | PAID-LATER | A001 | 🔜 |
| S015 | AWS Public Blockchain | datasets | onchain | FREE* | A001 | ⬜ |
| S016 | BigQuery public blockchain | datasets | onchain | FREE* | A001 | ⬜ |
| S017 | Dune API | apis | onchain | PAID-LATER | A03 | 🔜 |
| S018 | *reserved / dropped in research* | — | — | — | — | — |
| S019 | *reserved / dropped in research* | — | — | — | — | — |
| S020 | Yahoo Finance (`yfinance`) | apis | stock | FREE | A05 | ⬜ |
| S021 | Alpha Vantage | apis | stock | FREE* | A05 | ⬜ |
| S022 | Nasdaq Data Link | apis | stock+macro | FREE* | A06 | 🔜 |
| S023 | ~~IEX Cloud~~ | — | stock | DEAD | — | ✖ dead (shut 2024-08-31) |
| S024 | Tiingo | apis | stock | FREE* | A05 | ⬜ |
| S025 | Finnhub | apis | stock | FREE | A05 | ⬜ |
| S026 | Massive | infra | — | INFRA | — (scrape tool) | 🔜 |
| S027 | FRED | apis | macro | FREE | A06 | ⬜ |
| S028 | SEC EDGAR | apis | stock | FREE | A06 | ⬜ |
| S029 | Stooq | datasets | stock | FREE | A05 | ⬜ |
| S030 | *reserved / dropped in research* | — | — | — | — | — |
| S031 | Polygon.io | apis | stock | FREE* | A05 | ⬜ |
| S032 | Twelve Data | apis | stock | FREE* | A05 | ⬜ |
| S033 | World Bank Open Data | apis | macro | FREE | A06 | ⬜ |
| S034 | OpenBB | infra | mixed | FREE | — (SDK) | ⬜ |
| S035 | *reserved / dropped in research* | — | — | — | — | — |
| S036 | *reserved / dropped in research* | — | — | — | — | — |
| S037 | *reserved / dropped in research* | — | — | — | — | — |
| S038 | *reserved / dropped in research* | — | — | — | — | — |
| S039 | *reserved / dropped in research* | — | — | — | — | — |
| S040 | Google Cloud Marketplace — datasets | links | mixed | FREE* | — (discovery) | ⬜ |
| S041 | AWS Open Data Registry | links | mixed | FREE | — (discovery) | ⬜ |
| S042 | HuggingFace — finance datasets (search) | links | sentiment | FREE | — (discovery) | ⬜ |
| S043 | Kaggle — Financial news sentiment | datasets | sentiment | FREE | A04 | ⬜ |
| S044 | HuggingFace — bitcoin tweets sentiment | datasets | sentiment | FREE | A04 | ⬜ |
| S045 | Kaggle — Reddit crypto sentiment | datasets | sentiment | FREE | A04 | ⬜ |
| S046 | FinBERT (ProsusAI) | models | sentiment | MODEL | A04 | 🔜 |
| S047 | GDELT Project | apis | news | FREE | A002 | ⬜ |
| S048 | CCXT | infra | crypto | FREE | A001 / A05 | ⬜ |
| S049 | Frankfurter | apis | forex | FREE | A06 | ⬜ |
| S050 | Reddit API | apis | sentiment | FREE* | A04 | ⬜ |
| S051 | Fear & Greed Index (alternative.me) | apis | sentiment | FREE | A04 | ⬜ |
| S052 | BscScan | apis | onchain | FREE* | A001 | ⬜ |
| S053 | PolygonScan | apis | onchain | FREE* | A001 | ⬜ |
| S054 | Arbiscan | apis | onchain | FREE* | A001 | ⬜ |
| S055 | Optimistic Etherscan | apis | onchain | FREE* | A001 | ⬜ |
| S056 | Snowtrace | apis | onchain | FREE* | A001 | ⬜ |
| S057 | FTMScan | apis | onchain | FREE* | A001 | ⬜ |
| S058 | Basescan | apis | onchain | FREE* | A001 | ⬜ |
| S059 | Blockscout | apis | onchain | FREE | A001 | ⬜ |
| S060 | Solscan | apis | onchain | FREE* | A001 | ⬜ |
| S061 | SolanaFM | apis | onchain | FREE* | A001 | ⬜ |
| S062 | TronScan | apis | onchain | FREE* | A001 | ⬜ |
| S063 | Mempool.space | apis | onchain | FREE | A001 | ⬜ |
| S064 | Blockchair | apis | onchain | FREE* | A001 | ⬜ |
| S065 | Celoscan | apis | onchain | FREE* | A001 | ⬜ |
| S066 | zkSync Era Explorer | apis | onchain | FREE | A001 | ⬜ |
| S067 | Alchemy | infra | — | INFRA (FREE*) | A001 | ⬜ |
| S068 | Infura | infra | — | INFRA (FREE*) | A001 | ⬜ |
| S069 | QuickNode | infra | — | INFRA (FREE*) | A001 | ⬜ |
| S070 | Ankr | infra | — | INFRA (FREE*) | A001 | ⬜ |
| S071 | Moralis | infra | — | INFRA (FREE*) | A001 | ⬜ |
| S072 | GetBlock | infra | — | INFRA (FREE*) | A001 | ⬜ |
| S073 | Chainstack | infra | — | INFRA (FREE*) | A001 | ⬜ |
| S074 | PublicNode | infra | — | INFRA (FREE) | A001 | ⬜ |
| S075 | DeFi Llama | apis | onchain | FREE | A001 | ⬜ |
| S076 | The Graph | apis | onchain | FREE* | A001 | ⬜ |
| S077 | Nansen | apis | onchain | PAID-LATER | A001 | 🔜 |
| S078 | IntoTheBlock | apis | onchain | FREE* | A001 | ⬜ |
| S079 | Covalent (GoldRush) | apis | onchain | FREE* | A001 | ⬜ |
| S080 | Footprint Analytics | apis | onchain | FREE* | A001 | ⬜ |
| S081 | Token Terminal | apis | onchain | PAID-LATER | A001 | 🔜 |
| S082 | CryptoCompare | apis | crypto | FREE | A001 / A05 | ⬜ |
| S083 | Messari | apis | crypto | FREE* | A001 / A05 | ⬜ |
| S084 | OpenSea | apis | onchain | FREE* | A001 | ⬜ |
| S085 | Reservoir | apis | onchain | FREE* | A001 | ⬜ |
| S086 | Alchemy NFT API | apis | onchain | FREE* | A001 | ⬜ |
| S087 | NFTScan | apis | onchain | FREE* | A001 | ⬜ |
| S088 | Whale Alert | apis | onchain | PAID-LATER | A001 | 🔜 |
| S089 | Blocknative | apis | onchain | FREE* | A001 | ⬜ |
| S090 | BitQuery | apis | onchain | FREE* | A001 | ⬜ |
| S091 | Chainbase | apis | onchain | FREE* | A001 | ⬜ |
| S092 | Flipside Crypto | apis | onchain | FREE* | A001 | ⬜ |
| S093 | Arkham Intelligence | apis | onchain | FREE* | A001 | ⬜ |
| S094 | DeBank | apis | onchain | FREE* | A001 | ⬜ |
| S095 | Zerion | apis | onchain | FREE* | A001 | ⬜ |
| S096 | Uniswap Subgraph | apis | onchain | FREE* | A001 | ⬜ |
| S097 | Aave | apis | onchain | FREE* | A001 | ⬜ |
| S098 | Compound | apis | onchain | FREE* | A001 | ⬜ |
| S099 | 1inch | apis | onchain | FREE* | A001 | ⬜ |
| S100 | Helius | apis | onchain | FREE* | A001 | ⬜ |
| S101 | Birdeye | apis | onchain | FREE* | A001 | ⬜ |
| S102 | DexScreener | apis | onchain | FREE | A001 | ⬜ |
| S103 | GeckoTerminal | apis | onchain | FREE | A001 | ⬜ |
| S104 | Jupiter | apis | onchain | FREE | A001 | ⬜ |
| S105 | Meteora | apis | onchain | FREE | A001 | ⬜ |
| S106 | GMGN | apis | onchain | FREE* | A001 | ⬜ |
| S107 | Bags | apis | onchain | FREE* | A001 | ⬜ |
| S108 | Chainalysis | apis | onchain | PAID-LATER | A001 | 🔜 |
| S109 | TRM Labs | apis | onchain | PAID-LATER | A001 | 🔜 |
| S110 | Coinglass | apis | crypto | FREE* | A001 | ⬜ |
| S111 | Hyperdash | apis | crypto | FREE* | A001 | ⬜ |
| S112 | Zapper | apis | onchain | FREE* | A001 | ⬜ |
| S113 | Step Finance | apis | onchain | FREE* | A001 | ⬜ |
| S114 | Tatum | apis | onchain | FREE* | A001 | ⬜ |
| S115 | dRPC | infra | — | INFRA (FREE*) | A001 | ⬜ |
| S116 | Cielo | apis | onchain | FREE* | A001 | ⬜ |
| S117 | igorbarinov/awesome-bitcoin | links | onchain | FREE | — (discovery) | ⬜ |
| S118 | best-of-crypto | links | mixed | FREE | — (discovery) | ⬜ |

**ID ledger.** IDs are assigned monotonically. The gaps `S018, S019, S030,
S035–S039` are **reserved / dropped during research** — a candidate that merged,
turned out dead/duplicate, or was cut before earning a row. They are recorded here so
the gap is *accounted for, not silent*; per rule #1 these IDs are **not reused** —
new sources take fresh IDs from `S119` onward. (If the operator recalls a real source
one of these was meant for, it can be re-documented under that same ID.)

## ⚠️ Research findings (2026-09-05) — status changes

Seven sources are not what they seem — flagged in their rows too:

- **IEX Cloud → DEAD** (shut down Aug 2024).
- **CoinCap → PAID** (free keyless v2 gone; v3 needs key + prepaid credits).
- **Massive.com → not a data source** — it's a residential proxy / web-scrape tool → `infra.md`.
- **Glassnode / CryptoQuant / Dune → API is paid** (free tiers have no/*minimal* API).
- **Kaiko → free = research charts only**; raw feeds enterprise.

## What lives elsewhere (not here)

| Layer | Where | When |
|---|---|---|
| Machine config (URLs, rate limits, key-names code reads) | `config/sources/*.yaml` | later, when code arrives |
| Connector code | `integrations/` | later (Phase 2) |
| Secrets (real keys) | `.env` (never git) | when a source goes live |

---

<sub>A connector without a catalogued, governed, verified source is a claim
without provenance — 026 would rather say "cannot be determined." Research: 2026-09-05.
Master index + schema + 4 new sources: 2026-09-06.</sub>
