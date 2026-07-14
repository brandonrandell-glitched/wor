import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _mcp_base import run_server
from _paths import ROOT

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
FIXTURE_PATH = ROOT / "fixtures" / "proposal_tools_data.json"


def _load_fixture():
    with open(FIXTURE_PATH) as f:
        return json.load(f)


def _extract_pain_points(current_infrastructure, industry=None, organization_size=None):
    if USE_LIVE:
        raise NotImplementedError("Live proposal tools disabled. Using public pattern fixtures.")

    data = _load_fixture()
    text = current_infrastructure.lower()
    if industry:
        text += " " + industry.lower()
    if organization_size:
        text += " " + organization_size.lower()

    found = []
    for pattern in data["pain_point_patterns"]:
        if any(kw in text for kw in pattern["keywords"]):
            found.extend(pattern["pain_points"])

    seen = set()
    unique = []
    for pp in found:
        if pp not in seen:
            seen.add(pp)
            unique.append(pp)

    return {"pain_points": unique, "count": len(unique)}


def _recommend_products(pain_points, existing_technologies=None):
    if USE_LIVE:
        raise NotImplementedError("Live proposal tools disabled. Using public pattern fixtures.")

    data = _load_fixture()
    recs = set(existing_technologies or [])
    mapping = data["product_recommendations"]

    for pp in pain_points:
        for product in mapping.get(pp, []):
            recs.add(product)

    if not recs:
        recs = set(data["default_recommendations"])

    return {"recommendations": sorted(recs), "count": len(recs)}


def handler(name, args):
    if name == "extract_pain_points":
        return _extract_pain_points(
            args["current_infrastructure"],
            args.get("industry"),
            args.get("organization_size"),
        )
    if name == "recommend_products":
        return _recommend_products(
            args["pain_points"],
            args.get("existing_technologies"),
        )
    return {"error": f"Unknown tool: {name}"}


if __name__ == "__main__":
    run_server(TOOLS, handler)
