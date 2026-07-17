"""Resolve demo vs real fixture paths and load customer account data."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent

DEMO_CUSTOMER_FILE = ROOT / "fixtures" / "salesforce_customer.json"
REAL_CUSTOMERS_FILE = "real_customers.json"
REAL_PARTNER_OPS_FILE = "real_partner_ops.json"
REAL_COMMERCE_FILE = "real_commerce_renewals.json"
DEMO_PARTNER_OPS = ROOT / "mcp-framework" / "servers" / "data" / "partner_ops.json"
DEMO_COMMERCE = ROOT / "fixtures" / "commerce_renewals.json"
TEMPLATES_DIR = ROOT / "fixtures" / "templates"


def fixtures_dir() -> Path:
    override = os.environ.get("GTM_FIXTURES_DIR", "").strip()
    if override:
        path = Path(override)
        path.mkdir(parents=True, exist_ok=True)
        return path
    return ROOT / "fixtures"


def data_mode() -> str:
    """demo | real | auto — auto prefers real files when present."""
    mode = os.environ.get("GTM_DATA_MODE", "auto").strip().lower()
    if mode not in {"demo", "real", "auto"}:
        return "auto"
    return mode


def _real_path(filename: str) -> Path:
    return fixtures_dir() / filename


def using_real_customers() -> bool:
    mode = data_mode()
    real_file = _real_path(REAL_CUSTOMERS_FILE)
    if mode == "demo":
        return False
    if mode == "real":
        return real_file.exists()
    return real_file.exists()


def customers_file() -> Path | None:
    real_file = _real_path(REAL_CUSTOMERS_FILE)
    if using_real_customers():
        return real_file
    if DEMO_CUSTOMER_FILE.exists():
        return DEMO_CUSTOMER_FILE
    return None


def partner_ops_path() -> Path:
    mode = data_mode()
    real_file = _real_path(REAL_PARTNER_OPS_FILE)
    if mode == "demo":
        return DEMO_PARTNER_OPS
    if mode == "real":
        return real_file if real_file.exists() else DEMO_PARTNER_OPS
    return real_file if real_file.exists() else DEMO_PARTNER_OPS


def commerce_path() -> Path:
    mode = data_mode()
    real_file = _real_path(REAL_COMMERCE_FILE)
    if mode == "demo":
        return DEMO_COMMERCE
    if mode == "real":
        return real_file if real_file.exists() else DEMO_COMMERCE
    return real_file if real_file.exists() else DEMO_COMMERCE


def _load_customers_blob() -> dict[str, Any]:
    path = customers_file()
    if not path or not path.exists():
        return {"customers": {}}

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    if "customers" in data and isinstance(data["customers"], dict):
        return data

    if data.get("customer_account"):
        name = data["customer_account"]
        return {"customers": {name: data}, "_single_demo": True}

    return {"customers": {}}


def list_customer_accounts() -> list[dict[str, str]]:
    blob = _load_customers_blob()
    entries = []
    source = "real" if using_real_customers() else "demo"
    for name, record in sorted(blob.get("customers", {}).items()):
        entries.append({
            "name": name,
            "industry": record.get("industry", ""),
            "source": source,
        })
    return entries


def get_customer_record(customer_account: str) -> dict[str, Any] | None:
    blob = _load_customers_blob()
    customers = blob.get("customers", {})
    if customer_account in customers:
        return dict(customers[customer_account])

    needle = customer_account.strip().lower()
    hits = [
        rec for name, rec in customers.items()
        if needle in name.lower()
    ]
    if len(hits) == 1:
        return dict(hits[0])
    return None


def data_status() -> dict[str, Any]:
    real_partners = _real_path(REAL_PARTNER_OPS_FILE)
    real_commerce = _real_path(REAL_COMMERCE_FILE)
    mode = data_mode()
    accounts = list_customer_accounts()
    return {
        "mode": mode,
        "effective": "real" if using_real_customers() else "demo",
        "fixtures_dir": str(fixtures_dir()),
        "customers_file": str(customers_file()) if customers_file() else None,
        "customer_count": len(accounts),
        "real_files": {
            "customers": real_customers.exists(),
            "partner_ops": real_partners.exists(),
            "commerce": real_commerce.exists(),
        },
        "partner_ops_path": str(partner_ops_path()),
        "commerce_path": str(commerce_path()),
    }


def init_real_data_files(force: bool = False) -> list[str]:
    """Create gitignored real_*.json from templates. Returns paths created."""
    import shutil

    created: list[str] = []
    out_dir = fixtures_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    template_dir = TEMPLATES_DIR
    mapping = {
        REAL_CUSTOMERS_FILE: "customers.template.json",
        REAL_PARTNER_OPS_FILE: "partner_ops.template.json",
        REAL_COMMERCE_FILE: "commerce_renewals.template.json",
    }
    for dest_name, template_name in mapping.items():
        dest = out_dir / dest_name
        if dest.exists() and not force:
            continue
        template = template_dir / template_name
        if template.exists():
            shutil.copy(template, dest)
            created.append(str(dest))
        elif dest_name == REAL_CUSTOMERS_FILE and DEMO_CUSTOMER_FILE.exists():
            with open(DEMO_CUSTOMER_FILE, encoding="utf-8") as f:
                demo = json.load(f)
            payload = {
                "_schema": "gtm-customers-v1",
                "_currency": "CAD",
                "_notice": "Seeded from demo — replace with your accounts.",
                "customers": {demo["customer_account"]: demo},
            }
            dest.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            created.append(str(dest))
    return created
