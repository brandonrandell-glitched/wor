#!/usr/bin/env python3
"""Merge a Salesforce-style JSON export into fixtures/real_customers.json."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib.data_sources import REAL_CUSTOMERS_FILE, fixtures_dir, init_real_data_files


def _normalize_record(raw: dict) -> dict:
    name = raw.get("customer_account") or raw.get("Customer Account Name") or raw.get("Account Name")
    if not name:
        raise ValueError("Record missing customer_account / Account Name")
    record = dict(raw)
    record["customer_account"] = name
    if "org_size" not in record and record.get("Organization Size"):
        record["org_size"] = record["Organization Size"]
    if "cisco_technologies_proposed" not in record and record.get("Cisco Technologies to be Proposed"):
        record["cisco_technologies_proposed"] = record["Cisco Technologies to be Proposed"]
    return record


def import_records(records: list[dict], target: Path | None = None) -> Path:
    init_real_data_files()
    path = target or (fixtures_dir() / REAL_CUSTOMERS_FILE)
    if path.exists():
        with open(path, encoding="utf-8") as f:
            blob = json.load(f)
    else:
        blob = {"_schema": "gtm-customers-v1", "_currency": "CAD", "customers": {}}

    customers = blob.setdefault("customers", {})
    for raw in records:
        record = _normalize_record(raw)
        customers[record["customer_account"]] = record

    path.write_text(json.dumps(blob, indent=2), encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Import customer JSON into real_customers.json")
    parser.add_argument("input_file", type=Path, help="JSON file: single account or {customers:{...}}")
    args = parser.parse_args()

    with open(args.input_file, encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        records = data
    elif "customers" in data:
        records = list(data["customers"].values())
    elif data.get("customer_account") or data.get("Account Name"):
        records = [data]
    else:
        print("Unrecognized JSON shape.", file=sys.stderr)
        return 1

    path = import_records(records)
    print(f"Imported {len(records)} account(s) into {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
