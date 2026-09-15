# A002 News Intelligence Agent — Config

Central configuration for the A002 agent using Pydantic v2 settings.

## Structure

```
config/
├── __init__.py          # exports: get_settings, Settings, etc.
├── constants.py         # hardcoded constants (agent ID, version, thresholds)
├── environment.py       # Environment enum (development/production/testing)
├── paths.py             # filesystem paths (data dirs, DB, .env)
├── settings.py          # main Settings class with all sub-settings
├── sources.py           # news/social source registry (RSS feeds, API endpoints)
```

## Settings Hierarchy

```
Settings (A002_)
├── agent: AgentSettings (A002_AGENT_)
├── ingestion: IngestionSettings (A002_INGESTION_)
├── news: NewsSourceSettings (A002_NEWS_)
├── social: SocialSourceSettings (A002_SOCIAL_)
├── market: MarketSettings (A002_MARKET_)
├── narrative: NarrativeSettings (A002_NARRATIVE_)
└── model: ModelSettings (A002_MODEL_)
```

## Environment Variables

All settings use `A002_` prefix. Copy `.env.example` to repo-root `.env` and fill keys you have. All keys are optional — agent runs in degraded mode without them.

Key groups:
- `A002_NEWS_*`: Tiingo, NewsAPI, Alpaca, Finnhub, FinancialJuice
- `A002_SOCIAL_*`: Reddit, Telegram, X/Twitter
- `A002_MARKET_*`: Alpha Vantage, Binance
- `A002_MODEL_*`: ML model configs

## Source Registry

`sources.py` defines `SOURCES` tuple — single source of truth for all connectors. Each source has:
- `name`: unique identifier (e.g., `rss_cnbc`, `tiingo`)
- `kind`: `rss` | `api` | `social`
- `endpoint`: URL or identifier
- `enabled`: bool
- `credibility_tier`: 1-6 (used by verification)

## Usage

```python
from agents.A002_News_Intelligence.config import get_settings
settings = get_settings()
print(settings.news.tiingo_api_key.get_secret_value())
```