import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "mcp_servers"))

from _mcp_base import run_server

from lib.gtm_tools import get_customer_context, suggest_opportunities

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


def handler(name, args):
    if name == "get_customer_context":
        result = get_customer_context(args["customer_account"])
        if not result:
            return {"found": False, "reason": "No customer data available for this account"}
        return {"found": True, "data": result}
    if name == "suggest_opportunities":
        if USE_LIVE:
            raise NotImplementedError("Live Salesforce connector disabled.")
        return suggest_opportunities(
            args["customer_account"],
            args.get("batch_offset", 0),
            args.get("batch_size", 10),
        )
    return {"error": f"Unknown tool: {name}"}


if __name__ == "__main__":
    run_server(TOOLS, handler, server_name="salesforce")
