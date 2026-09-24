# links.md — Inbox & portals

> Two jobs:
> 1. **Inbox** — new raw URLs the operator drops land here first, unsorted. Then
>    they get triaged into [`apis.md`](apis.md) / [`datasets.md`](datasets.md) /
>    [`mcp.md`](mcp.md) / [`models.md`](models.md) / [`infra.md`](infra.md).
> 2. **Portals / registries** — pages you *browse* to discover many sources/datasets
>    (not a single source themselves).

## Portals & registries (browse to find sources)

| ID | Link | Domain | What it is | Tier | Status |
|----|------|--------|------------|------|--------|
| S008 | [Kaggle — Bitcoin historical (search)](https://www.kaggle.com/datasets?search=bitcoin+historical+data) | crypto | Search page → pick specific BTC datasets (each becomes a `datasets.md` row) | FREE | ⬜ |
| S040 | [Google Cloud Marketplace — datasets](https://console.cloud.google.com/marketplace/browse?filter=solution-type:dataset) | mixed | Browse curated public datasets (finance, blockchain) | FREE* | ⬜ |
| S041 | [AWS Open Data Registry](https://registry.opendata.aws/) | mixed | Registry of thousands of public datasets | FREE | ⬜ |
| S042 | [HuggingFace — finance datasets (search)](https://huggingface.co/datasets?task=text-classification&search=finance) | sentiment | Search page → pick specific finance-sentiment datasets | FREE | ⬜ |
| S117 | [igorbarinov/awesome-bitcoin](https://github.com/igorbarinov/awesome-bitcoin) | onchain | Verified-trusted curated list (CC0, official awesome badge) — Bitcoin-side API/market-data base list | FREE | ⬜ |
| S118 | [lukasmasuch/best-of-crypto](https://github.com/lukasmasuch/best-of-crypto) | mixed | Highly-trusted auto-ranked list (3.1k projects, weekly updated) — broad crypto/open-source discovery | FREE | ⬜ |

## Inbox — unsorted (triage into a type file)

> *(empty — new URLs from the operator land here, then get sorted)*

| Raw URL | Dropped | Notes |
|---------|---------|-------|
| — | — | — |

## Dashboard reference repos (inspiration — not deps)

> Repos we *study* for layout/UX patterns while building the 026 Intelligence Hub.
> Not imported; the actual build stack is the S123–S134 rows in `infra.md` / `mcp.md`.
> Dropped 2026-09-23.

| Repo | What to borrow |
|------|----------------|
| [tradingagents-dashboard (QuocBaoLabs)](https://github.com/QuocBaoLabs/tradingagents-dashboard) | Dashboard for the S122 TradingAgents framework — direct layout reference for our agent tabs |
| [FlowAI — agentic workflow builder](https://github.com/aiudalabs/flowAI) | Visual agent-workflow canvas — pattern for the Agent Network tab |
| [shadcn AI Canvas/Node/Edge/Panel](https://www.shadcn.io/ai/canvas) | React-Flow + shadcn components purpose-built for AI-agent graphs |
| [LangChain Agent Chat UI](https://github.com/langchain-ai/agent-chat-ui) | Chat + trace surface — pattern for operator-io chat/approvals |
| [OpenTerminal](https://github.com/ErTasselli/OpenTerminal) · [OpenTerminalUI](https://github.com/laanito/OpenTerminalUI) | Trading-terminal layout density |
| [shadcn-fintech](https://github.com/abderrahimghazali/shadcn-fintech) · [ShadcnVaults](https://github.com/Aldhanekaa/ShadcnVaults) | Fintech UI blocks on shadcn |
| [threejs-dashboard](https://github.com/opencolin/threejs-dashboard) | 3D dashboard motion/scene reference for R3F work |
| [Refine](https://github.com/refinedev/refine) | Data-driven React admin framework — evaluate only if CRUD/admin views grow |
