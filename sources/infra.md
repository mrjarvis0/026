# infra.md — Tooling (not data feeds)

> Tools that *help* 026 access other sources but are **not data sources themselves**.
> Kept here so the catalog stays honest — these are capabilities, not feeds.
> Code lands in `tools/` or `infra/`. Master ID index: [`README.md`](README.md#master-index).

| ID | Tool | Kind | What it does | Auth | Lands in | Tier | Notes | Status |
|----|------|------|--------------|------|----------|------|-------|--------|
| S026 | [Massive](https://massive.com/) (joinmassive.com) | proxy / scrape | Residential-proxy + web-scrape / render / search APIs — for reaching sites with no clean API | account | `tools/` or `infra/` | INFRA (paid) | ⚠️ Not a market-data feed. Use only if a needed source has no API and its ToS permits scraping. | 🔜 |
| S034 | [OpenBB](https://openbb.co/) | SDK / aggregator | Open-source finance SDK — one interface over many data providers (the finance analogue of CCXT) | free + provider keys | `tools/` (SDK) | FREE | A convenience layer; the underlying providers still each need a catalog row. | ⬜ |
| S048 | [CCXT](https://github.com/ccxt/ccxt) | SDK / aggregator (library) | Unified library over 100+ crypto exchanges — read-only market data (OHLCV, orderbook, trades) | none (per-exchange keys optional) | `integrations/exchanges/` (via `tools/`) | FREE | Crypto counterpart to OpenBB. **Read-only** — order execution is never routed through a data aggregator. Underlying exchanges still each need a row. | ⬜ |
| S067 | [Alchemy](https://www.alchemy.com/docs/reference/api-overview) | RPC / node provider | Multi-chain JSON-RPC + enhanced APIs (also fronts NFT API → S086) | API key | `integrations/apis/` (via `tools/`) | FREE* | Free tier; the endpoint a connector actually calls. A001 already resolves RPC via `config/rpc/`. | ⬜ |
| S068 | [Infura](https://docs.infura.io) | RPC / node provider | Multi-chain JSON-RPC (ETH + L2s) | API key | `integrations/apis/` (via `tools/`) | FREE* | Free tier request cap. | ⬜ |
| S069 | [QuickNode](https://www.quicknode.com/docs) | RPC / node provider | Multi-chain JSON-RPC + add-ons | API key | `integrations/apis/` (via `tools/`) | FREE* | Free tier. | ⬜ |
| S070 | [Ankr](https://www.ankr.com/rpc) | RPC / node provider | Public + premium multi-chain RPC | none / key | `integrations/apis/` (via `tools/`) | FREE* | Free public RPC endpoints (keyless) available. | ⬜ |
| S071 | [Moralis](https://docs.moralis.io) | RPC / data provider | Multi-chain RPC + Web3 data APIs (balances, NFT, tx) | API key | `integrations/apis/` (via `tools/`) | FREE* | Free tier; part RPC, part data API. | ⬜ |
| S072 | [GetBlock](https://getblock.io/docs) | RPC / node provider | Multi-chain JSON-RPC | API key | `integrations/apis/` (via `tools/`) | FREE* | Free tier request cap. | ⬜ |
| S073 | [Chainstack](https://docs.chainstack.com) | RPC / node provider | Multi-chain nodes + JSON-RPC | API key | `integrations/apis/` (via `tools/`) | FREE* | Free tier. | ⬜ |
| S074 | [PublicNode](https://www.publicnode.com) | RPC / node provider | Free public multi-chain RPC endpoints | none | `integrations/apis/` (via `tools/`) | FREE | Keyless public RPC — good Tier-1 fallback. | ⬜ |
| S115 | [dRPC](https://drpc.org) | RPC / node provider | Multi-chain routed RPC, low-latency load-balancing | none / key | `integrations/apis/` (via `tools/`) | FREE* | Routed aggregator over many node providers. | ⬜ |

**Landed 2026-09-07:** S067–S074, S115 — RPC/node providers from the operator's
`blockchain-data-sources-notes.md`. Classed as infra (access endpoints, not feeds
themselves), consistent with CCXT/OpenBB. A001's live RPC resolution already lives in
`agents/A001_Blockchain_Intelligence/config/rpc/`; these rows are the governed catalog of
what those endpoints are.

**Not catalogued (deliberately) — not data feeds:**
- **Embedded wallets / account abstraction** — Privy, Dynamic, Pimlico, Coinbase WaaS
  (#76–79): wallet infrastructure, not an intelligence data source for A001. Also, A001 is
  read-only and holds no keys — a wallet-signing service is out of its trust surface.
- **Crypto tax / reporting** — CoinLedger, TaxBit (#83–84): user tax tooling, not on-chain
  intelligence data. Re-add later only if a real A0x consumer needs them.

**Landed this session (2026-09-06):** S048 CCXT — previously a "recommended addition"
note only; now a governed row.
