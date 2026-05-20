import csv
import json
import pytest
from pathlib import Path
from src.bronze import ingest
from src.silver import refine, clean_record
from src.gold import aggregate


@pytest.fixture
def lake(tmp_path):
    return tmp_path / "lake"


@pytest.fixture
def raw_dir(tmp_path):
    d = tmp_path / "raw"
    d.mkdir()
    csv_file = d / "test.csv"
    csv_file.write_text(
        "txn_id,customer_id,product_name,quantity,price,currency,region,timestamp\n"
        "T1,C1,Widget,10,29.99,USD,US-East,2025-03-15T10:00:00\n"
        "T2,C2,Gadget,5,49.99,EUR,EU-West,2025-03-16T11:00:00\n"
        "T3,,Widget,3,29.99,USD,US-East,2025-03-17T12:00:00\n"
        "T4,C1,Widget,INVALID,29.99,USD,US-East,2025-03-18T13:00:00\n"
        "T5,C3,Gadget,2,49.99,GBP,EU-West,2025-03-19T14:00:00\n"
    )
    return d


class TestBronze:
    def test_ingests_all_rows(self, raw_dir, lake):
        result = ingest(raw_dir, lake)
        assert result["records"] == 5
        assert result["files"] == 1

    def test_creates_jsonl(self, raw_dir, lake):
        ingest(raw_dir, lake)
        files = list((lake / "bronze").glob("*.jsonl"))
        assert len(files) == 1

    def test_adds_metadata(self, raw_dir, lake):
        ingest(raw_dir, lake)
        with open(lake / "bronze" / "test.jsonl") as f:
            record = json.loads(f.readline())
        assert "_ingested_at" in record
        assert "_source_file" in record
        assert "_row_number" in record


class TestSilverClean:
    def test_valid_record(self):
        r = clean_record({"txn_id": "T1", "customer_id": "C1", "product_name": "W", "quantity": "10", "price": "29.99", "currency": "USD", "region": "US", "timestamp": "2025-03-15T10:00:00"})
        assert r["quantity"] == 10
        assert r["price_usd"] == 29.99
        assert r["total_usd"] == 299.9

    def test_eur_conversion(self):
        r = clean_record({"txn_id": "T2", "customer_id": "C2", "product_name": "G", "quantity": "5", "price": "49.99", "currency": "EUR", "region": "EU", "timestamp": "2025-03-16T11:00:00"})
        assert r["price_usd"] == round(49.99 * 1.08, 2)

    def test_missing_customer_rejected(self):
        assert clean_record({"quantity": "1", "price": "10", "customer_id": "", "timestamp": "2025-01-01T00:00:00"}) is None

    def test_invalid_quantity_rejected(self):
        assert clean_record({"quantity": "INVALID", "price": "10", "customer_id": "C1", "timestamp": "2025-01-01T00:00:00"}) is None

    def test_bad_date_rejected(self):
        assert clean_record({"quantity": "1", "price": "10", "customer_id": "C1", "timestamp": "bad"}) is None


class TestSilverRefine:
    def test_produces_clean_output(self, raw_dir, lake):
        ingest(raw_dir, lake)
        result = refine(lake)
        assert result["output_records"] == 3
        assert result["rejected"] == 2

    def test_creates_rejected_file(self, raw_dir, lake):
        ingest(raw_dir, lake)
        refine(lake)
        rejected = list((lake / "silver").glob("*_rejected.jsonl"))
        assert len(rejected) == 1


class TestGold:
    def test_generates_aggregations(self, raw_dir, lake):
        ingest(raw_dir, lake)
        refine(lake)
        result = aggregate(lake)
        assert result["tables"] == 3

    def test_revenue_by_region(self, raw_dir, lake):
        ingest(raw_dir, lake)
        refine(lake)
        aggregate(lake)
        data = json.loads((lake / "gold" / "revenue_by_region.json").read_text())
        assert len(data) > 0
        assert all("revenue_usd" in r for r in data)

    def test_customer_summary(self, raw_dir, lake):
        ingest(raw_dir, lake)
        refine(lake)
        aggregate(lake)
        data = json.loads((lake / "gold" / "customer_summary.json").read_text())
        assert len(data) > 0
        assert all("total_spent_usd" in r for r in data)

    def test_end_to_end_pipeline(self, raw_dir, lake):
        ingest(raw_dir, lake)
        refine(lake)
        result = aggregate(lake)
        assert result["source_records"] == 3
