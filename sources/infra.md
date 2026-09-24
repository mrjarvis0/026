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
| S121 | [LuxAlgo Broker SDK](https://luxalgo.com) | SDK / aggregator | Read-only portfolio data across 22 brokers (Alpaca, Binance, Bybit, Kraken, Tradier, Interactive Brokers, Hyperliquid...) — balances, positions, trade history, FIFO win-rate | operator's own broker API keys (local-only, never leaves the machine) | `tools/` (SDK) | FREE | Open question — no consuming agent assigned yet. This is the operator's own portfolio data; doesn't fit A001–A006's "external world" domains. See `PROJECT_STATE.md` → *Open questions for the operator*. | ⬜ |

| S122 | [TradingAgents](https://github.com/tauricresearch/tradingagents) | framework / reference | Multi-agent LLM trading framework (108k ★, Apache-2.0) — analyst team → bull/bear researcher debate → trader → risk management → portfolio manager pipeline. Claude Sonnet 5 / Fable 5 supported. Point-in-time backtesting. | none (OSS) | `agents/` (pattern reference, not a connector) | FREE | Borrow: (1) bull-bear debate pattern → T02 swarm, (2) orchestration graph routing → orchestrator, (3) point-in-time backtest approach → T01 eval gate, (4) risk assessment flow → A012. Do NOT copy data connectors — 026 has its own. | ⬜ |

### Dashboard build stack (frontend libraries — landed 2026-09-23)

> One best-pick per job for the 026 Intelligence Hub dashboard. These are npm
> libraries the frontend imports, not data feeds. Code lands in `dashboard/frontend/`.

| ID | Tool | Kind | What it does | Auth | Lands in | Tier | Notes | Status |
|----|------|------|--------------|------|----------|------|-------|--------|
| S123 | [React Three Fiber](https://github.com/pmndrs/react-three-fiber) (+[Three.js](https://threejs.org)) | 3D / WebGL | React renderer for Three.js — 3D agent-network scene, particle fields, glowing nodes | none | `dashboard/frontend/` | FREE | **Best pick for 3D.** Use R3F (not raw Three.js) in React. `drei` helpers add cameras/controls. | ⬜ |
| S124 | [React Flow / xyflow](https://github.com/xyflow/xyflow) | graph / node-edge | Node-edge diagrams — Agent Network tab (2D topology), data-flow arrows | none | `dashboard/frontend/` | FREE | **Best pick for agent flow.** Most popular, React-native. 2D companion to R3F's 3D view. | ⬜ |
| S125 | [TradingView Lightweight Charts](https://github.com/tradingview/lightweight-charts) | financial charts | Candlestick / OHLCV / line charts — T01 trading tab, price panels | none | `dashboard/frontend/` | FREE | **Best pick for trading charts.** Purpose-built, tiny, fast. | ⬜ |
| S126 | [Apache ECharts](https://github.com/apache/echarts) | data charts | Rich metric charts — agent health, P&L curves, heatmaps (WebGL option) | none | `dashboard/frontend/` | FREE | **Best pick for metric/data viz.** Richer than Recharts; `echarts-for-react` wrapper. | ⬜ |
| S127 | [Tremor](https://github.com/tremorlabs/tremor) | dashboard UI | React dashboard blocks — KPI cards, meters, stat tiles (on shadcn/Recharts) | none | `dashboard/frontend/` | FREE | **Best pick for dashboard blocks.** Pairs with shadcn/ui for fleet-overview cards. | ⬜ |
| S128 | [shadcn/ui](https://github.com/shadcn-ui/ui) | component system | Base component library (tabs, cards, badges, dialogs) — copy-in, not a dep | none | `dashboard/frontend/` | FREE | **Best pick for UI base.** Owns the components (no lock-in). Tremor + AI-canvas build on it. | ⬜ |
| S129 | [Motion](https://github.com/framer/motion) (motion.dev) | animation | UI animations — tab transitions, card pulses, live-data enters | none | `dashboard/frontend/` | FREE | **Best pick for UI motion.** Modern framer-motion v11+. | ⬜ |
| S130 | [GSAP](https://gsap.com) | animation | Timeline animations — loading sequences, hero/intro, orchestrated reveals | none | `dashboard/frontend/` | FREE | **Best pick for complex timelines.** Use where Motion's declarative model isn't enough. | ⬜ |

**Deliberately skipped (YAGNI / covered by a better pick):**
- **Framer** (framer.com) — a design *tool*, not a lib; we design in code + Figma MCP (S131).
- **LottieFiles** — GSAP/Motion cover animation; add only if a designer ships Lottie JSON.
- **deck.gl** — large-scale geo/WebGL viz, overkill; R3F covers our 3D.
- **D3.js** — too low-level; ECharts covers our charts (drop to D3 only for a bespoke viz).
- **Cytoscape.js** — React Flow covers graph/network with a friendlier React API.
- **Playwright MCP** — a test tool, not a dashboard-build source.

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
