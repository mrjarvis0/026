# A02 News Intelligence Agent — Data

Runtime data directories (created automatically).

## Structure

```
data/
├── raw/                 # raw fetched items (not used currently — items go straight to DB)
├── processed/
│   └── a02.db           # SQLite database (items, narratives, impact_events, scan_stats, market_prices)
└── outcomes/            # reserved for exported training data, backtest results
```

## Database Schema (`a02.db`)

### `items`
- `id`, `source`, `source_key`, `url`, `title`, `content`, `author`, `published_at`
- `title_fingerprint`, `content_fingerprint`, `entities_json`, `created_at`
- Indexes: `url`, `title_fp`, `content_fp`, `published_at`

### `narratives`
- `id`, `claim_text`, `entities_json`, `status`, `mention_count`, `source_count`, `platform_count`
- `stance_counts_json`, `fomo_score`, `velocity`, `epistemic_status`, `confidence`, `coordination_score`
- `manipulation_json`, `evidence_json`, `first_seen`, `last_seen`, `created_at`, `updated_at`
- Indexes: `status`, `first_seen`, `fomo_score`

### `narrative_items`
- `narrative_id`, `item_id`, `stance`, `created_at`

### `impact_events` (Phase 4+5)
- `id`, `narrative_id`, `asset`, `category`, `first_seen`, `horizon_hours`
- `measured_return`, `fomo_score`, `epistemic_status`, `confidence`, `coordination`
- **Phase 5**: `predicted_direction`, `predicted_probability`, `predicted_mean_pct`
- **Phase 5**: `actual_return`, `actual_direction`, `truth_outcome`, `resolved_at`
- Indexes: `asset`, `category`

### `scan_stats` (Phase 5)
- `id`, `created_at`, `items_fetched`, `items_stored`, `items_dup`, `narratives`, `verdicts_json`

### `market_prices`
- `id`, `symbol`, `interval`, `open_time`, `open`, `high`, `low`, `close`, `volume`, `created_at`
- Index: unique on `(symbol, interval, open_time)`

## Auto-Creation

Directories and DB created on first `Storage.init()` call (via `cli doctor` or `cli scan`).

## Backup

```bash
# Backup DB
cp data/processed/a02.db data/processed/a02.db.backup.$(date +%F)

# Export training data
python -c "
import asyncio
from agents.A02_News_Intelligence.core.storage import Storage
from agents.A02_News_Intelligence.core.phase7 import export_training_data
storage = Storage('data/processed/a02.db')
asyncio.run(storage.init())
n = asyncio.run(export_training_data(storage, 'data/outcomes/training.json'))
print(f'Exported {n} samples')
"
```