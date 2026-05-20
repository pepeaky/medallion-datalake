"""Bronze layer — raw ingestion with metadata. No transformations, append-only."""

from __future__ import annotations
import csv
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("lake.bronze")


def ingest(input_dir: str | Path, lake_root: str | Path) -> dict:
    input_path = Path(input_dir)
    bronze_path = Path(lake_root) / "bronze"
    bronze_path.mkdir(parents=True, exist_ok=True)

    ingested = 0
    files_processed = 0

    for csv_file in sorted(input_path.glob("*.csv")):
        records = _read_raw(csv_file)
        output = bronze_path / f"{csv_file.stem}.jsonl"

        with open(output, "w") as f:
            for rec in records:
                f.write(json.dumps(rec) + "\n")

        ingested += len(records)
        files_processed += 1
        logger.info("Bronze: ingested %d records from %s", len(records), csv_file.name)

    return {"layer": "bronze", "files": files_processed, "records": ingested}


def _read_raw(filepath: Path) -> list[dict]:
    records = []
    ts = datetime.now(timezone.utc).isoformat()
    with open(filepath, newline="") as f:
        reader = csv.DictReader(f)
        for row_num, row in enumerate(reader, 1):
            records.append({
                "_ingested_at": ts,
                "_source_file": filepath.name,
                "_row_number": row_num,
                **row,
            })
    return records
