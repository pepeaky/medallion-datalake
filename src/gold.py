"""Gold layer — business-ready aggregations and analytics tables."""

from __future__ import annotations
import json
import logging
from collections import defaultdict
from pathlib import Path

logger = logging.getLogger("lake.gold")


def aggregate(lake_root: str | Path) -> dict:
    silver_path = Path(lake_root) / "silver"
    gold_path = Path(lake_root) / "gold"
    gold_path.mkdir(parents=True, exist_ok=True)

    records = _load_all_silver(silver_path)

    revenue_by_region = _agg_revenue_by_region(records)
    revenue_by_product = _agg_revenue_by_product(records)
    customer_summary = _agg_customer_summary(records)

    _write_json(gold_path / "revenue_by_region.json", revenue_by_region)
    _write_json(gold_path / "revenue_by_product.json", revenue_by_product)
    _write_json(gold_path / "customer_summary.json", customer_summary)

    logger.info("Gold: generated 3 aggregation tables from %d records", len(records))
    return {"layer": "gold", "source_records": len(records), "tables": 3}


def _agg_revenue_by_region(records: list[dict]) -> list[dict]:
    agg = defaultdict(lambda: {"revenue_usd": 0, "orders": 0, "units": 0})
    for r in records:
        region = r.get("region", "Unknown")
        agg[region]["revenue_usd"] += r.get("total_usd", 0)
        agg[region]["orders"] += 1
        agg[region]["units"] += r.get("quantity", 0)
    return [{"region": k, **v, "revenue_usd": round(v["revenue_usd"], 2)} for k, v in sorted(agg.items())]


def _agg_revenue_by_product(records: list[dict]) -> list[dict]:
    agg = defaultdict(lambda: {"revenue_usd": 0, "units_sold": 0})
    for r in records:
        product = r.get("product_name", "Unknown")
        agg[product]["revenue_usd"] += r.get("total_usd", 0)
        agg[product]["units_sold"] += r.get("quantity", 0)
    return [{"product": k, **v, "revenue_usd": round(v["revenue_usd"], 2)} for k, v in sorted(agg.items(), key=lambda x: -x[1]["revenue_usd"])]


def _agg_customer_summary(records: list[dict]) -> list[dict]:
    agg = defaultdict(lambda: {"total_spent_usd": 0, "orders": 0, "first_order": None, "last_order": None})
    for r in records:
        cid = r.get("customer_id")
        agg[cid]["total_spent_usd"] += r.get("total_usd", 0)
        agg[cid]["orders"] += 1
        ts = r.get("timestamp", "")
        if agg[cid]["first_order"] is None or ts < agg[cid]["first_order"]:
            agg[cid]["first_order"] = ts
        if agg[cid]["last_order"] is None or ts > agg[cid]["last_order"]:
            agg[cid]["last_order"] = ts

    return [
        {"customer_id": k, **v, "total_spent_usd": round(v["total_spent_usd"], 2)}
        for k, v in sorted(agg.items(), key=lambda x: -x[1]["total_spent_usd"])
    ]


def _load_all_silver(silver_path: Path) -> list[dict]:
    records = []
    for f in sorted(silver_path.glob("*.jsonl")):
        if "_rejected" in f.name:
            continue
        with open(f) as fh:
            for line in fh:
                if line.strip():
                    records.append(json.loads(line))
    return records


def _write_json(path: Path, data: list[dict]) -> None:
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
