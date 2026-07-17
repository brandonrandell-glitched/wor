import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "mcp_servers"))

from _mcp_base import run_server

from lib.gtm_tools import extract_pain_points, recommend_products

TOOLS = [
    {
        "name": "extract_pain_points",
        "description": "Extract customer pain points from infrastructure and context.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "current_infrastructure": {"type": "string"},
                "industry": {"type": "string"},
                "organization_size": {"type": "string"},
            },
            "required": ["current_infrastructure"],
        },
    },
    {
        "name": "recommend_products",
        "description": "Recommend Cisco technologies based on confirmed pain points.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "pain_points": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "existing_technologies": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": ["pain_points"],
        },
    },
]

USE_LIVE = False


def handler(name, args):
    if USE_LIVE:
        raise NotImplementedError("Live proposal tools disabled.")
    if name == "extract_pain_points":
        return extract_pain_points(
            args["current_infrastructure"],
            args.get("industry"),
            args.get("organization_size"),
        )
    if name == "recommend_products":
        return recommend_products(
            args["pain_points"],
            args.get("existing_technologies"),
        )
    return {"error": f"Unknown tool: {name}"}


if __name__ == "__main__":
    run_server(TOOLS, handler, server_name="proposal-tools")
