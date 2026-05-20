# Medallion Data Lake

A three-layer data lake implementing the Bronze/Silver/Gold medallion architecture for progressive data refinement, from raw ingestion to business-ready analytics.

---

## Architecture

```
  Raw CSV Files
       │
       ▼
┌──────────────────┐
│   BRONZE Layer    │  Raw ingestion, append-only
│  (lake/bronze/)   │  + metadata (_ingested_at, _source, _row)
│  Format: JSONL    │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   SILVER Layer    │  Cleaned, validated, typed
│  (lake/silver/)   │  Currency normalization (→ USD)
│  + _rejected.jsonl│  Deduplication by txn_id
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│    GOLD Layer     │  Business aggregations
│  (lake/gold/)     │  • revenue_by_region.json
│  Format: JSON     │  • revenue_by_product.json
└──────────────────┘  • customer_summary.json
```

## Data Flow

| Stage | Input | Transforms | Output |
|---|---|---|---|
| **Bronze** | Raw CSV | Add metadata, preserve as-is | JSONL (1:1 with source rows) |
| **Silver** | Bronze JSONL | Type casting, null rejection, currency → USD, dedup | Clean JSONL + rejected JSONL |
| **Gold** | Silver JSONL | Aggregate by region/product/customer | Analytics-ready JSON |

## Quick Start

```bash
git clone <repo-url> && cd 09-medallion-datalake
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# run full pipeline
python main.py run --input data/raw --lake lake

# run specific stages
python main.py run --stages bronze
python main.py run --stages silver,gold
```

## Testing

```bash
pytest -v
```

**15 tests** — bronze ingestion, silver cleaning/validation/dedup, gold aggregation, and end-to-end pipeline.

## Project Structure

```
├── main.py              # CLI: run (with stage selection)
├── data/raw/
│   └── transactions_2025.csv  # 8 rows with intentional dirty data
├── src/
│   ├── config.py        # .env loader
│   ├── bronze.py        # Raw ingestion + metadata
│   ├── silver.py        # Clean, validate, normalize currency, dedup
│   └── gold.py          # Business aggregations (3 tables)
└── tests/
    └── test_layers.py   # 15 tests — all three layers
```
