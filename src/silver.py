"""Silver layer — cleaned, validated, typed, deduplicated."""

from __future__ import annotations
import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("lake.silver")

EXCHANGE_RATES = {"USD": 1.0, "EUR": 1.08, "GBP": 1.27, "JPY": 0.0067, "CNY": 0.14}


def refine(lake_root: str | Path) -> dict:
    bronze_path = Path(lake_root) / "bronze"
    silver_path = Path(lake_root) / "silver"
    silver_path.mkdir(parents=True, exist_ok=True)

    total_in = 0
    total_out = 0
    total_rejected = 0

    for jsonl_file in sorted(bronze_path.glob("*.jsonl")):
        records = _load_jsonl(jsonl_file)
        total_in += len(records)

        clean, rejected = _clean_and_validate(records)
        deduped = _deduplicate(clean)
        total_out += len(deduped)
        total_rejected += len(rejected)

        output = silver_path / jsonl_file.name
        with open(output, "w") as f:
            for rec in deduped:
                f.write(json.dumps(rec) + "\n")

        rejected_path = silver_path / f"{jsonl_file.stem}_rejected.jsonl"
        if rejected:
            with open(rejected_path, "w") as f:
                for rec in rejected:
                    f.write(json.dumps(rec) + "\n")

        logger.info("Silver: %d → %d clean, %d rejected from %s", len(records), len(deduped), len(rejected), jsonl_file.name)

    return {"layer": "silver", "input_records": total_in, "output_records": total_out, "rejected": total_rejected}


def clean_record(record: dict) -> dict | None:
    try:
        quantity = int(record.get("quantity", ""))
        if quantity <= 0:
            return None
    except (ValueError, TypeError):
        return None

    try:
        price = float(record.get("price", ""))
        if price < 0:
            return None
    except (ValueError, TypeError):
        return None

    customer_id = (record.get("customer_id") or "").strip()
    if not customer_id:
        return None

    try:
        ts = datetime.fromisoformat(record.get("timestamp", ""))
    except (ValueError, TypeError):
        return None

    currency = record.get("currency", "USD")
    rate = EXCHANGE_RATES.get(currency, 1.0)
    price_usd = round(price * rate, 2)

    return {
        "txn_id": record.get("txn_id", "").strip(),
        "customer_id": customer_id,
        "product_name": (record.get("product_name") or "").strip(),
        "quantity": quantity,
        "price_original": price,
        "currency": currency,
        "price_usd": price_usd,
        "total_usd": round(price_usd * quantity, 2),
        "region": (record.get("region") or "Unknown").strip(),
        "timestamp": ts.isoformat(),
        "_source_file": record.get("_source_file"),
    }


def _clean_and_validate(records: list[dict]) -> tuple[list[dict], list[dict]]:
    clean, rejected = [], []
    for rec in records:
        result = clean_record(rec)
        if result:
            clean.append(result)
        else:
            rejected.append({**rec, "_rejection_reason": "validation_failed"})
    return clean, rejected


def _deduplicate(records: list[dict]) -> list[dict]:
    seen = set()
    deduped = []
    for rec in records:
        key = rec.get("txn_id")
        if key and key not in seen:
            seen.add(key)
            deduped.append(rec)
    return deduped


def _load_jsonl(path: Path) -> list[dict]:
    records = []
    with open(path) as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records
