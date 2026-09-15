# apis.md — Live / queryable APIs

> REST / WebSocket APIs 026 can call programmatically. Domain is tagged per row.
> See [`README.md`](README.md) for legend, rules & the master ID index. Bulk
> downloads live in [`datasets.md`](datasets.md); a hybrid source (e.g. Binance) is
> cross-linked by ID.

**Schema (per `ROADMAP.md` catalog template).** Every row carries its access,
limits, cost, landing folder, and **provenance field** — the last is non-optional:
it is how a `data/raw/` record cites its origin. Unverified values are marked `TBV`
(to-be-verified); a value is only stated as fact once `BUILD_LOG.md` records the
check. `ToS` = terms/robots note (`check` where not yet reviewed — never assume permission).

| ID | Source | Domain | Data it gives | Auth | Rate limit | Cost | Lands in | Provenance field | ToS/robots | Tier | Agent | Status |
|----|--------|--------|---------------|------|-----------|------|----------|------------------|-----------|------|-------|--------|
| S002 | [Binance Spot API](https://binance-docs.github.io/apidocs/spot/en/) *(bulk → S001)* | crypto | Real-time + historical OHLCV, orderbook, trades (REST+WS) | keyless (public) | TBV (weight-based) | free | `integrations/exchanges/` | `source_id`, `symbol`, `fetched_at` | check | FREE | A05 | ⬜ |
| S004 | [CoinGecko API](https://www.coingecko.com/en/api) | crypto | Prices, market cap, 17k+ coins, exchanges | demo key | ~30/min (demo) | free demo (monthly cap) | `integrations/apis/` | `source_id`, `fetched_at` | check | FREE | A05 | ⬜ |
| S005 | [CoinCap API](https://coincap.io/) | crypto | Prices, market data | key (v3) | TBV | ⚠️ v3 prepaid/paid (keyless v2 gone) | `integrations/apis/` | `source_id`, `fetched_at` | check | PAID-LATER | A05 | 🔜 |
| S006 | [CoinPaprika API](https://coinpaprika.com/api/) | crypto | Prices, markets, 2k+ assets | none | 20k req/month | free | `integrations/apis/` | `source_id`, `fetched_at` | check | FREE | A05 | 🔜 |
| S007 | [CoinMarketCap API](https://coinmarketcap.com/api/) | crypto | Prices, market cap, rankings | API key | TBV (credit-based) | free tier (limited credits) | `integrations/apis/` | `source_id`, `fetched_at` | check | FREE* | A05 | ⬜ |
| S009 | [Blockchain.com Explorer API](https://www.blockchain.com/explorer/api) | onchain | BTC chain data, addresses, tx, charts | none | TBV | free | `integrations/apis/` | `source_id`, `tx_hash`, `fetched_at` | check | FREE | A001 | ⬜ |
| S010 | [Etherscan API](https://etherscan.io/api/pricing) | onchain | ETH tx, balances, contracts, gas, tokens | API key | ~5 req/s, ~100k/day | free tier | `integrations/apis/` | `source_id`, `tx_hash`, `block`, `fetched_at` | check | FREE | A001 | ⬜ |
| S011 | [Alpaca](https://alpaca.markets/) | stock+crypto | Stock & crypto OHLCV/trades/quotes | key (crypto keyless) | TBV | free data (stocks IEX feed) | `integrations/exchanges/` | `source_id`, `symbol`, `fetched_at` | check | FREE | A05 | 🔜 |
| S012 | [Kaiko](https://www.kaiko.com/pages/sample-data) | crypto | Market-data research / feeds | signup | TBV | ⚠️ free = charts only; raw feeds enterprise | `integrations/apis/` | `source_id`, `fetched_at` | check | PAID-LATER | A05 | 🔜 |
| S013 | [Glassnode API](https://studio.glassnode.com/) | onchain | On-chain metrics (SOPR, HODL, flows) | account | TBV | ⚠️ API paid (Pro + add-on); free = web only | `integrations/apis/` | `source_id`, `metric`, `fetched_at` | check | PAID-LATER | A001 | 🔜 |
| S014 | [CryptoQuant API](https://cryptoquant.com/) | onchain | Exchange flows, on-chain indicators | account | TBV | ⚠️ free plan = NO API | `integrations/apis/` | `source_id`, `metric`, `fetched_at` | check | PAID-LATER | A001 | 🔜 |
| S017 | [Dune API](https://dune.com/) | onchain | SQL over on-chain data, dashboards | API key | TBV (minimal credits) | ⚠️ free tier view-only / minimal credits | `integrations/apis/` | `source_id`, `query_id`, `fetched_at` | check | PAID-LATER | A03 | 🔜 |
| S020 | [Yahoo Finance](https://finance.yahoo.com/) (`yfinance`) | stock | Global stocks/ETF/index/FX/crypto OHLCV | none (unofficial) | be polite (unofficial) | free | `integrations/apis/` | `source_id`, `symbol`, `fetched_at` | ⚠️ unofficial — check Yahoo ToS | FREE | A05 | ⬜ |
| S021 | [Alpha Vantage](https://www.alphavantage.co/) | stock | Global stocks, FX, crypto, indicators | API key | ~25 req/day, 5/min | free* | `integrations/apis/` | `source_id`, `symbol`, `fetched_at` | check | FREE* | A05 | ⬜ |
| S022 | [Nasdaq Data Link](https://data.nasdaq.com/institutional-investors) | stock+macro | 13F holdings + econ/financial datasets | API key | 50k calls/day (auth) | free datasets (many premium) | `integrations/apis/` | `source_id`, `dataset_code`, `fetched_at` | check | FREE* | A06 | 🔜 |
| S024 | [Tiingo](https://www.tiingo.com/) | stock | EOD stocks, crypto, news, fundamentals | API key | TBV | free tier (limited) | `integrations/apis/` | `source_id`, `symbol`, `fetched_at` | check | FREE* | A05 | ⬜ |
| S025 | [Finnhub](https://finnhub.io/) | stock | Global stocks, FX, crypto, news | API key | ~60/min | free | `integrations/apis/` | `source_id`, `symbol`, `fetched_at` | check | FREE | A05 | ⬜ |
| S027 | [FRED](https://fred.stlouisfed.org/) | macro | 800k+ macro / economic series | API key | ~120 req/min | free | `integrations/apis/` | `source_id`, `series_id`, `fetched_at` | check (St. Louis Fed) | FREE | A06 | ⬜ |
| S028 | [SEC EDGAR](https://www.sec.gov/edgar/search/) | stock | US filings (10-K, 13F, 8-K), full-text | none (fair-use UA) | ~10 req/s (fair-use) | free | `integrations/apis/` | `source_id`, `accession_no`, `fetched_at` | ⚠️ fair-use User-Agent required | FREE | A06 | ⬜ |
| S031 | [Polygon.io](https://polygon.io/) | stock | Stocks, options, FX, crypto (REST+WS) | API key | ~5 req/min (free) | free* (EOD) | `integrations/apis/` | `source_id`, `symbol`, `fetched_at` | check | FREE* | A05 | ⬜ |
| S032 | [Twelve Data](https://twelvedata.com/) | stock | Global stocks / FX / crypto / ETF | API key | ~800/day, 8/min | free* | `integrations/apis/` | `source_id`, `symbol`, `fetched_at` | check | FREE* | A05 | ⬜ |
| S033 | [World Bank Open Data](https://data.worldbank.org/) | macro | Global macro indicators | none | TBV | free, open | `integrations/apis/` | `source_id`, `indicator`, `country`, `fetched_at` | open data | FREE | A06 | ⬜ |
| S047 | [GDELT Project](https://www.gdeltproject.org/) | news | Global news events + tone, ~15 min | none | TBV (be polite) | free, open | `integrations/apis/` | `source_id`, `event_id`, `fetched_at` | open | FREE | A002 | ⬜ |
| S049 | [Frankfurter](https://www.frankfurter.app/) | forex | ECB FX reference rates (latest + historical) | none | TBV (be polite) | free, no key | `integrations/apis/` | `source_id`, `base`, `date`, `fetched_at` | open (ECB data) | FREE | A06 | ⬜ |
| S050 | [Reddit API](https://www.reddit.com/dev/api/) | sentiment | Subreddit posts/comments (crypto/finance) | OAuth (free app) | TBV (OAuth tiered) | free tier | `integrations/apis/` | `source_id`, `permalink`, `fetched_at` | ⚠️ Reddit API terms + data-use limits — check | FREE* | A04 | ⬜ |
| S051 | [Fear & Greed Index](https://alternative.me/crypto/fear-and-greed-index/) (alternative.me) | sentiment | Crypto fear & greed index (daily + historical) | none | TBV | free | `integrations/apis/` | `source_id`, `date`, `fetched_at` | check | FREE | A04 | ⬜ |
| S052 | [BscScan](https://bscscan.com/apis) | onchain | BNB Chain tx/balances/contracts/tokens (Etherscan V2 — same key family as S010) | API key | TBV | free tier | `integrations/apis/` | `source_id`, `tx_hash`, `block`, `fetched_at` | check | FREE* | A001 | ⬜ |
| S053 | [PolygonScan](https://polygonscan.com/apis) | onchain | Polygon tx/balances/contracts (Etherscan V2) | API key | TBV | free tier | `integrations/apis/` | `source_id`, `tx_hash`, `block`, `fetched_at` | check | FREE* | A001 | ⬜ |
| S054 | [Arbiscan](https://arbiscan.io/apis) | onchain | Arbitrum tx/balances/contracts (Etherscan V2) | API key | TBV | free tier | `integrations/apis/` | `source_id`, `tx_hash`, `block`, `fetched_at` | check | FREE* | A001 | ⬜ |
| S055 | [Optimistic Etherscan](https://optimistic.etherscan.io/apis) | onchain | Optimism tx/balances/contracts (Etherscan V2) | API key | TBV | free tier | `integrations/apis/` | `source_id`, `tx_hash`, `block`, `fetched_at` | check | FREE* | A001 | ⬜ |
| S056 | [Snowtrace](https://snowtrace.io/apis) | onchain | Avalanche C-Chain tx/balances (Etherscan V2) | API key | TBV | free tier | `integrations/apis/` | `source_id`, `tx_hash`, `block`, `fetched_at` | check | FREE* | A001 | ⬜ |
| S057 | [FTMScan](https://ftmscan.com/apis) | onchain | Fantom tx/balances/contracts (Etherscan V2) | API key | TBV | free tier | `integrations/apis/` | `source_id`, `tx_hash`, `block`, `fetched_at` | check | FREE* | A001 | ⬜ |
| S058 | [Basescan](https://basescan.org/apis) | onchain | Base tx/balances/contracts (Etherscan V2) | API key | TBV | free tier | `integrations/apis/` | `source_id`, `tx_hash`, `block`, `fetched_at` | check | FREE* | A001 | ⬜ |
| S059 | [Blockscout](https://www.blockscout.com) | onchain | Multi-chain open-source explorer: tx, balances, tokens | none | TBV | free | `integrations/apis/` | `source_id`, `tx_hash`, `block`, `fetched_at` | check | FREE | A001 | ⬜ |
| S060 | [Solscan](https://public-api.solscan.io) | onchain | Solana tx/accounts/tokens | API key | TBV | free tier | `integrations/apis/` | `source_id`, `signature`, `fetched_at` | check | FREE* | A001 | ⬜ |
| S061 | [SolanaFM](https://docs.solana.fm) | onchain | Solana explorer/indexer data | API key | TBV | free tier | `integrations/apis/` | `source_id`, `signature`, `fetched_at` | check | FREE* | A001 | ⬜ |
| S062 | [TronScan](https://tronscan.org/#/apis) | onchain | Tron tx/accounts/tokens | key / none | TBV | free | `integrations/apis/` | `source_id`, `tx_hash`, `fetched_at` | check | FREE* | A001 | ⬜ |
| S063 | [Mempool.space](https://mempool.space/docs/api/rest) | onchain | Bitcoin mempool, fees, tx, blocks | none | TBV | free | `integrations/apis/` | `source_id`, `tx_hash`, `block`, `fetched_at` | open | FREE | A001 | ⬜ |
| S064 | [Blockchair](https://blockchair.com/api/docs) | onchain | Multi-chain explorer data (BTC/ETH/…) | key / none | TBV | free tier | `integrations/apis/` | `source_id`, `tx_hash`, `fetched_at` | check | FREE* | A001 | ⬜ |
| S065 | [Celoscan](https://celoscan.io/apis) | onchain | Celo tx/balances/contracts (Etherscan V2) | API key | TBV | free tier | `integrations/apis/` | `source_id`, `tx_hash`, `block`, `fetched_at` | check | FREE* | A001 | ⬜ |
| S066 | [zkSync Era Explorer](https://explorer.zksync.io) | onchain | zkSync Era tx/contracts | none | TBV | free | `integrations/apis/` | `source_id`, `tx_hash`, `fetched_at` | check | FREE | A001 | ⬜ |
| S075 | [DeFi Llama](https://defillama.com/docs/api) | onchain | TVL, protocols, yields, stablecoins, prices | none (no key) | TBV | free | `integrations/apis/` | `source_id`, `metric`, `fetched_at` | open | FREE | A001 | ⬜ |
| S076 | [The Graph](https://thegraph.com/docs) | onchain | Indexed subgraph queries (GraphQL) | API key | TBV | free tier | `integrations/apis/` | `source_id`, `query`, `fetched_at` | check | FREE* | A001 | ⬜ |
| S077 | [Nansen](https://www.nansen.ai) | onchain | Smart-money labels, wallet intelligence (incl. Smart Money product #52) | API key | TBV | ⚠️ paid | `integrations/apis/` | `source_id`, `address`, `fetched_at` | check | PAID-LATER | A001 | 🔜 |
| S078 | [IntoTheBlock](https://api.intotheblock.com) | onchain | On-chain analytics / indicators | API key | TBV | free tier | `integrations/apis/` | `source_id`, `metric`, `fetched_at` | check | FREE* | A001 | ⬜ |
| S079 | [Covalent (GoldRush)](https://goldrush.dev/docs) | onchain | Unified multichain balances/tx/NFT | API key | TBV | free tier | `integrations/apis/` | `source_id`, `address`, `fetched_at` | check | FREE* | A001 | ⬜ |
| S080 | [Footprint Analytics](https://docs.footprint.network) | onchain | On-chain / DeFi analytics (SQL/API) | API key | TBV | free tier | `integrations/apis/` | `source_id`, `metric`, `fetched_at` | check | FREE* | A001 | ⬜ |
| S081 | [Token Terminal](https://docs.tokenterminal.com) | onchain | Protocol financial metrics | API key | TBV | ⚠️ paid | `integrations/apis/` | `source_id`, `metric`, `fetched_at` | check | PAID-LATER | A001 | 🔜 |
| S082 | [CryptoCompare](https://min-api.cryptocompare.com) | crypto | Prices, OHLCV, news (REST+WS) | API key | TBV | free | `integrations/apis/` | `source_id`, `symbol`, `fetched_at` | check | FREE | A001 / A05 | ⬜ |
| S083 | [Messari](https://messari.io/api) | crypto | Asset metrics, news, research | API key | TBV | free tier | `integrations/apis/` | `source_id`, `asset`, `fetched_at` | check | FREE* | A001 / A05 | ⬜ |
| S084 | [OpenSea](https://docs.opensea.io) | onchain | NFT collections / listings / events | API key | TBV | free tier | `integrations/apis/` | `source_id`, `contract`, `token_id`, `fetched_at` | check | FREE* | A001 | ⬜ |
| S085 | [Reservoir](https://docs.reservoir.tools) | onchain | Aggregated NFT market data | API key | TBV | free tier | `integrations/apis/` | `source_id`, `contract`, `token_id`, `fetched_at` | check | FREE* | A001 | ⬜ |
| S086 | [Alchemy NFT API](https://www.alchemy.com/docs/reference/nft-api-quickstart) | onchain | NFT ownership / metadata (vendor → S067) | API key | TBV | free tier | `integrations/apis/` | `source_id`, `contract`, `token_id`, `fetched_at` | check | FREE* | A001 | ⬜ |
| S087 | [NFTScan](https://docs.nftscan.com) | onchain | Multi-chain NFT data | API key | TBV | free tier | `integrations/apis/` | `source_id`, `contract`, `token_id`, `fetched_at` | check | FREE* | A001 | ⬜ |
| S088 | [Whale Alert](https://docs.whale-alert.io) | onchain | Large-transfer / whale tx alerts | API key | TBV | ⚠️ paid | `integrations/apis/` | `source_id`, `tx_hash`, `fetched_at` | check | PAID-LATER | A001 | 🔜 |
| S089 | [Blocknative](https://docs.blocknative.com) | onchain | Mempool / pending-tx / gas | API key | TBV | free tier | `integrations/apis/` | `source_id`, `tx_hash`, `fetched_at` | check | FREE* | A001 | ⬜ |
| S090 | [BitQuery](https://docs.bitquery.io) | onchain | GraphQL over many chains: tx, DEX, transfers (also fronts Pump.fun #67 & Coinpath AML #71) | API key | TBV | free tier | `integrations/apis/` | `source_id`, `tx_hash`, `fetched_at` | check | FREE* | A001 | ⬜ |
| S091 | [Chainbase](https://docs.chainbase.com) | onchain | Multichain indexed data / SQL | API key | TBV | free tier | `integrations/apis/` | `source_id`, `address`, `fetched_at` | check | FREE* | A001 | ⬜ |
| S092 | [Flipside Crypto](https://docs.flipsidecrypto.xyz) | onchain | Free SQL over on-chain data | account | TBV | free | `integrations/apis/` | `source_id`, `query`, `fetched_at` | check | FREE* | A001 | ⬜ |
| S093 | [Arkham Intelligence](https://www.arkhamintelligence.com) | onchain | Entity/wallet intelligence, labels | API key | TBV | free tier | `integrations/apis/` | `source_id`, `address`, `fetched_at` | check | FREE* | A001 | ⬜ |
| S094 | [DeBank](https://open.debank.com/docs) | onchain | Wallet portfolio / DeFi positions | API key | TBV | free tier | `integrations/apis/` | `source_id`, `address`, `fetched_at` | check | FREE* | A001 | ⬜ |
| S095 | [Zerion](https://zerion.io/api) | onchain | Wallet + DeFi portfolio | API key | TBV | free tier | `integrations/apis/` | `source_id`, `address`, `fetched_at` | check | FREE* | A001 | ⬜ |
| S096 | [Uniswap Subgraph](https://docs.uniswap.org/api/subgraph/overview) | onchain | Uniswap pools/swaps (via The Graph) | key (Graph) | TBV | free tier | `integrations/apis/` | `source_id`, `pair`, `fetched_at` | check | FREE* | A001 | ⬜ |
| S097 | [Aave](https://docs.aave.com) | onchain | Aave lending markets / positions | none / subgraph | TBV | free | `integrations/apis/` | `source_id`, `market`, `fetched_at` | check | FREE* | A001 | ⬜ |
| S098 | [Compound](https://docs.compound.finance) | onchain | Compound markets / positions | none / api | TBV | free | `integrations/apis/` | `source_id`, `market`, `fetched_at` | check | FREE* | A001 | ⬜ |
| S099 | [1inch](https://portal.1inch.dev) | onchain | DEX aggregation quotes / swap data | API key | TBV | free tier | `integrations/apis/` | `source_id`, `pair`, `fetched_at` | check | FREE* | A001 | ⬜ |
| S100 | [Helius](https://www.helius.dev) | onchain | Solana RPC + enriched data (DAS, webhooks) | API key | TBV | free tier | `integrations/apis/` | `source_id`, `signature`, `fetched_at` | check | FREE* | A001 | ⬜ |
| S101 | [Birdeye](https://docs.birdeye.so) | onchain | Multi-chain (Sol+EVM) token price/trading/whale | API key | TBV | free tier | `integrations/apis/` | `source_id`, `token`, `fetched_at` | check | FREE* | A001 | ⬜ |
| S102 | [DexScreener](https://docs.dexscreener.com) | onchain | Real-time DEX pairs / liquidity / volume | none | TBV | free | `integrations/apis/` | `source_id`, `pair`, `fetched_at` | check | FREE | A001 | ⬜ |
| S103 | [GeckoTerminal](https://www.geckoterminal.com/dex-api) | onchain | DEX / pool data (CoinGecko onchain arm) | none | TBV | free | `integrations/apis/` | `source_id`, `pool`, `fetched_at` | check | FREE | A001 | ⬜ |
| S104 | [Jupiter](https://station.jup.ag/docs/apis) | onchain | Solana swap routing, token list, price | none | TBV | free | `integrations/apis/` | `source_id`, `token`, `fetched_at` | check | FREE | A001 | ⬜ |
| S105 | [Meteora](https://docs.meteora.ag) | onchain | Solana liquidity pool data | none | TBV | free | `integrations/apis/` | `source_id`, `pool`, `fetched_at` | check | FREE | A001 | ⬜ |
| S106 | [GMGN](https://gmgn.ai) | onchain | Smart-money / KOL signals, memecoin tracking | key / none | TBV | free* | `integrations/apis/` | `source_id`, `address`, `fetched_at` | ⚠️ unofficial — check | FREE* | A001 | ⬜ |
| S107 | [Bags](https://bags.fm) | onchain | Solana token launch / creator data | key / none | TBV | free* | `integrations/apis/` | `source_id`, `token`, `fetched_at` | check | FREE* | A001 | ⬜ |
| S108 | [Chainalysis](https://www.chainalysis.com) | onchain | Forensics, sanctions screening | API key | TBV | ⚠️ enterprise | `integrations/apis/` | `source_id`, `address`, `fetched_at` | check | PAID-LATER | A001 | 🔜 |
| S109 | [TRM Labs](https://www.trmlabs.com) | onchain | Risk scoring, blockchain intelligence | API key | TBV | ⚠️ enterprise | `integrations/apis/` | `source_id`, `address`, `fetched_at` | check | PAID-LATER | A001 | 🔜 |
| S110 | [Coinglass](https://www.coinglass.com/api) | crypto | Futures OI, funding rates, liquidations | API key | TBV | free tier | `integrations/apis/` | `source_id`, `symbol`, `fetched_at` | check | FREE* | A001 | ⬜ |
| S111 | [Hyperdash](https://hyperdash.info) | crypto | Hyperliquid-specific analytics | key / none | TBV | free* | `integrations/apis/` | `source_id`, `symbol`, `fetched_at` | check | FREE* | A001 | ⬜ |
| S112 | [Zapper](https://protocol.zapper.xyz) | onchain | Multi-chain portfolio + DeFi positions | API key | TBV | free tier | `integrations/apis/` | `source_id`, `address`, `fetched_at` | check | FREE* | A001 | ⬜ |
| S113 | [Step Finance](https://step.finance) | onchain | Solana portfolio dashboard / API | key / none | TBV | free* | `integrations/apis/` | `source_id`, `address`, `fetched_at` | check | FREE* | A001 | ⬜ |
| S114 | [Tatum](https://tatum.io) | onchain | 100+ chains unified wallet/NFT/tx API, WalletDNA scoring | API key | TBV | free tier | `integrations/apis/` | `source_id`, `address`, `fetched_at` | check | FREE* | A001 | ⬜ |
| S116 | [Cielo](https://cielo.finance) | onchain | Real-time smart-money wallet tracking + copy-trading feeds | key / none | TBV | free* | `integrations/apis/` | `source_id`, `address`, `fetched_at` | check | FREE* | A001 | ⬜ |

**New this session (2026-09-07):** S052–S066, S075–S114, S116 — 56 blockchain API sources
from the operator's `blockchain-data-sources-notes.md` (A001). Values are `⬜`/`TBV`
(catalogued, not yet web-verified — a check will move them to `🔜`/`✅` in `BUILD_LOG.md`).
Dups already catalogued: Etherscan `S010`, Blockchain.com `S009`, CoinGecko `S004`,
CoinMarketCap `S007`, Binance `S002`, Glassnode `S013`, CryptoQuant `S014`, Dune `S017`,
Kaiko `S012`. Etherscan Gas Tracker (#48) is a sub-endpoint of `S010`.

**Dead — do not build:** ~~IEX Cloud~~ (`S023`) — shut down Aug 31 2024. Migrate to Alpha Vantage / Polygon / FMP. *(Tracked in the master index ([`README.md`](README.md#master-index)) as `DEAD`, no row here.)*

**New this session (2026-09-06):** S049 Frankfurter, S050 Reddit, S051 Fear & Greed —
free multipliers previously only noted in `BUILD_LOG.md`, now landed as governed rows.
