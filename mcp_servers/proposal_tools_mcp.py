import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "mcp_servers"))

from _mcp_base import run_server

from lib.gtm_tools import (
    extract_pain_points,
    meddpicc_gaps,
    recommend_platform_story,
    recommend_products,
)

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
    {
        "name": "recommend_platform_story",
        "description": (
            "Recommendations mapped by pillar with story_mode routing: security-only, "
            "security-led, or pillar-first. Pass entry_pillar when inbound is networking, "
            "data-center, or collaboration — not security."
        ),
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
                "entry_pillar": {
                    "type": "string",
                    "description": "How the deal entered: security (default), networking, data-center, collaboration.",
                    "default": "security",
                },
            },
            "required": ["pain_points"],
        },
    },
    {
        "name": "meddpicc_gaps",
        "description": (
            "Return MEDDPICC qualification gaps for a lifecycle stage (analyze, place, land, "
            "adopt, expand, renew) with suggested discovery questions."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "meddpicc": {
                    "type": "object",
                    "description": "Captured MEDDPICC fields, e.g. {metrics, economic_buyer, champion}",
                },
                "lifecycle_stage": {
                    "type": "string",
                    "default": "analyze",
                },
                "pain_points": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
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
    if name == "recommend_platform_story":
        return recommend_platform_story(
            args["pain_points"],
            args.get("existing_technologies"),
            args.get("entry_pillar", "security"),
        )
    if name == "meddpicc_gaps":
        return meddpicc_gaps(
            args.get("meddpicc"),
            args.get("lifecycle_stage", "analyze"),
            args.get("pain_points"),
        )
    return {"error": f"Unknown tool: {name}"}


if __name__ == "__main__":
    run_server(TOOLS, handler, server_name="proposal-tools")
