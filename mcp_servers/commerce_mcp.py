"""Commerce / renewal fixture MCP — license and renewal context (no live CCW)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "mcp_servers"))

from _mcp_base import run_server

import json

COMMERCE_FIXTURE = ROOT / "fixtures" / "commerce_renewals.json"


def _load() -> dict:
    with open(COMMERCE_FIXTURE, encoding="utf-8") as f:
        return json.load(f)


def get_renewal_context(customer_account: str) -> dict:
    data = _load()
    acct = data.get("accounts", {}).get(customer_account)
    if not acct:
        needle = customer_account.strip().lower()
        for name, entry in data.get("accounts", {}).items():
            if needle in name.lower():
                acct = entry
                break
    if not acct:
        return {"found": False, "reason": f"No renewal data for '{customer_account}'"}
    return {"found": True, "data": acct}


def suggest_license_bundle(customer_account: str, motion: str = "") -> dict:
    data = _load()
    ctx = get_renewal_context(customer_account)
    if not ctx.get("found"):
        return ctx
    bundles = data.get("license_bundles", {})
    acct = ctx["data"]
    at_risk = any(c.get("status") == "renewal_at_risk" for c in acct.get("contracts", []))
    if at_risk or "renew" in motion.lower():
        key = "renewal-protection"
    else:
        key = "security-expansion"
    bundle = bundles.get(key, {})
    return {
        "customer_account": customer_account,
        "recommended_bundle": key,
        "bundle": bundle,
        "contracts": acct.get("contracts", []),
        "value_realization": acct.get("value_realization", []),
        "guidance": "Use Champion and Metrics from MEDDPICC when presenting renewal case to Economic Buyer.",
    }


def list_renewals_due(within_days: int = 90) -> dict:
    data = _load()
    due = []
    for name, acct in data.get("accounts", {}).items():
        for c in acct.get("contracts", []):
            days = c.get("days_to_renewal", 999)
            if days <= within_days:
                due.append({
                    "customer": name,
                    "contract_id": c.get("contract_id"),
                    "product_family": c.get("product_family"),
                    "days_to_renewal": days,
                    "status": c.get("status"),
                    "annual_value_cad": c.get("annual_value_cad"),
                })
    due.sort(key=lambda x: x["days_to_renewal"])
    return {"count": len(due), "within_days": within_days, "renewals": due}


TOOLS = [
    {
        "name": "get_renewal_context",
        "description": "Renewal and license context for an account from fixture data (contracts, attach candidates, value realization).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "customer_account": {"type": "string"},
            },
            "required": ["customer_account"],
        },
    },
    {
        "name": "suggest_license_bundle",
        "description": "Suggest a license/attach bundle for renewal or expansion based on account contracts and motion.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "customer_account": {"type": "string"},
                "motion": {"type": "string", "description": "Optional motion hint, e.g. 'renewal', 'expand'."},
            },
            "required": ["customer_account"],
        },
    },
    {
        "name": "list_renewals_due",
        "description": "List contracts approaching renewal within N days (fixture data).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "within_days": {"type": "integer", "default": 90},
            },
        },
    },
]


def handler(name, args):
    if name == "get_renewal_context":
        return get_renewal_context(args["customer_account"])
    if name == "suggest_license_bundle":
        return suggest_license_bundle(args["customer_account"], args.get("motion", ""))
    if name == "list_renewals_due":
        return list_renewals_due(args.get("within_days", 90))
    return {"error": f"Unknown tool: {name}"}


if __name__ == "__main__":
    run_server(TOOLS, handler, server_name="commerce")
