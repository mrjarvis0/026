# datasets.md — Bulk / downloadable datasets

> Historical data you download in bulk (CSV / parquet / cloud tables) rather than
> call live. These land in `data/raw/` via a loader (later). Portals/registries you
> *browse* to find datasets live in [`links.md`](links.md). Master ID index lives in
> [`README.md`](README.md#master-index).

**Schema.** Same registry shape as [`apis.md`](apis.md): a dataset has no per-minute
rate limit, so the **Access** column carries its retrieval method (download / cloud
query); everything else — cost, landing folder, **provenance field**, ToS/license —
is filled the same way. `TBV` = to-be-verified. A dataset's license is its ToS —
`check` until reviewed.

| ID | Source | Domain | Data it gives | Auth | Access | Cost | Lands in | Provenance field | ToS/license | Tier | Agent | Status |
|----|--------|--------|---------------|------|--------|------|----------|------------------|-------------|------|-------|--------|
| S001 | [Binance Public Data](https://data.binance.vision/) *(API → S002)* | crypto | Historical klines / trades / orderbook dumps (CSV/ZIP) | none | bulk download | free, no key | `data/raw/` (loader) | `source_id`, `symbol`, `date`, `fetched_at` | check | FREE | A005 | ⬜ |
| S003 | [CryptoDataDownload](https://www.cryptodatadownload.com/) | crypto | Free historical CSVs across exchanges/pairs | none | CSV download | free | `data/raw/` (loader) | `source_id`, `exchange`, `pair`, `fetched_at` | check | FREE | A005 | ⬜ |
| S015 | [AWS Public Blockchain](https://registry.opendata.aws/aws-public-blockchain/) | onchain | BTC/ETH (+more) full chain data (S3 / Athena) | AWS acct | S3 / Athena query | free dataset (AWS query costs apply) | `data/raw/` (loader) | `source_id`, `chain`, `block`, `fetched_at` | AWS open-data terms | FREE* | A001 | ⬜ |
| S016 | [BigQuery public blockchain](https://cloud.google.com/blog/products/data-analytics/data-for-11-more-blockchains-in-bigquery-public-datasets) | onchain | 11+ chains, full history, in BigQuery | GCP acct | BigQuery | free datasets (BQ 1 TB/mo free query) | `data/raw/` (loader) | `source_id`, `chain`, `block`, `fetched_at` | GCP public-data terms | FREE* | A001 | ⬜ |
| S029 | [Stooq](https://stooq.com/db/h/) | stock | Global historical EOD CSV (stocks, indices, FX) | none | bulk CSV | free | `data/raw/` (loader) | `source_id`, `ticker`, `date`, `fetched_at` | check | FREE | A005 | ⬜ |
| S043 | [Kaggle — Financial news sentiment](https://www.kaggle.com/datasets/ankurzing/sentiment-analysis-for-financial-news) | sentiment | Financial PhraseBank labelled sentiment | Kaggle acct | Kaggle download | free | `data/raw/` (loader) | `source_id`, `dataset_slug`, `version` | ⚠️ Kaggle + dataset license — check | FREE | A004 | ⬜ |
| S044 | [HuggingFace — bitcoin tweets sentiment](https://huggingface.co/datasets/cvnberk/bitcoin_tweets_sentiment_kaggle) | sentiment | Labelled BTC tweets | HF acct | HF datasets | free | `data/raw/` (loader) | `source_id`, `dataset_id`, `revision` | ⚠️ dataset license — check | FREE | A004 | ⬜ |
| S045 | [Kaggle — Reddit crypto sentiment](https://www.kaggle.com/datasets/shisha01/reddit-crypto-sentiment-and-market-trend-dataset) | sentiment | Reddit crypto sentiment + market trend | Kaggle acct | Kaggle download | free | `data/raw/` (loader) | `source_id`, `dataset_slug`, `version` | ⚠️ Kaggle + license — check | FREE | A004 | ⬜ |
