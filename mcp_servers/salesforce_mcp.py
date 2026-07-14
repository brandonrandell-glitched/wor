import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _mcp_base import run_server
from _paths import ROOT

TOOLS = [
    {
        "name": "get_customer_context",
        "description": "Load customer account data and previous proposal preferences.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "customer_account": {"type": "string"},
            },
            "required": ["customer_account"],
        },
    },
    {
        "name": "suggest_opportunities",
        "description": "Suggest deal opportunities for a customer in batches of 10.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "customer_account": {"type": "string"},
                "batch_offset": {"type": "integer", "default": 0},
                "batch_size": {"type": "integer", "default": 10},
            },
            "required": ["customer_account"],
        },
    },
]

USE_LIVE = False
FIXTURE_PATH = ROOT / "fixtures" / "salesforce_customer.json"


def _load_fixture():
    with open(FIXTURE_PATH) as f:
        return json.load(f)


def _strip_internal_fields(data):
    if isinstance(data, dict):
        return {k: _strip_internal_fields(v) for k, v in data.items() if k != "savm_id"}
    if isinstance(data, list):
        return [_strip_internal_fields(item) for item in data]
    return data


def _fetch_customer_context(customer_account):
    if not USE_LIVE:
        data = _load_fixture()
        if data.get("customer_account") != customer_account:
            return None
        return _strip_internal_fields(data)
    raise NotImplementedError("Live Salesforce connector disabled. Using demo scenario fixtures.")


def _fetch_opportunities(customer_account, batch_offset, batch_size):
    if not USE_LIVE:
        data = _load_fixture()
        if data.get("customer_account") != customer_account:
            return {"opportunities": [], "total": 0, "has_more": False}
        all_opps = data.get("opportunities", [])
        batch = all_opps[batch_offset : batch_offset + batch_size]
        return {
            "opportunities": _strip_internal_fields(batch),
            "total": len(all_opps),
            "has_more": batch_offset + batch_size < len(all_opps),
            "next_offset": batch_offset + batch_size if batch_offset + batch_size < len(all_opps) else None,
        }
    raise NotImplementedError("Live Salesforce connector disabled. Using demo scenario fixtures.")


def handler(name, args):
    if name == "get_customer_context":
        result = _fetch_customer_context(args["customer_account"])
        if not result:
            return {"found": False, "reason": "No customer data available for this account"}
        return {"found": True, "data": result}
    if name == "suggest_opportunities":
        return _fetch_opportunities(
            args["customer_account"],
            args.get("batch_offset", 0),
            args.get("batch_size", 10),
        )
    return {"error": f"Unknown tool: {name}"}


if __name__ == "__main__":
    run_server(TOOLS, handler)
