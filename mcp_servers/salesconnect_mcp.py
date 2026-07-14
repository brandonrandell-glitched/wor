import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "mcp_servers"))

from _mcp_base import run_server
from lib.public_content import get_competitive, get_offer, get_proof_point

TOOLS = [
  {"name": "get_proof_point", "description": "Public Cisco proof stat. Cite-or-null.",
   "inputSchema": {"type": "object", "properties": {
      "topic": {"type": "string"}, "product": {"type": "string"},
      "max_age_days": {"type": "integer", "default": 365}}, "required": ["topic"]}},
  {"name": "search_competitive", "description": "Public competitive positioning (PAN/Zscaler/Fortinet).",
   "inputSchema": {"type": "object", "properties": {
      "competitor": {"type": "string"}, "motion": {"type": "string"}}, "required": ["competitor"]}},
  {"name": "get_offer_detail", "description": "Public Cisco offer scope overview.",
   "inputSchema": {"type": "object", "properties": {
      "offer_type": {"type": "string"}, "product": {"type": "string"}}, "required": ["offer_type"]}}
]

def handler(name, args):
    if name == "get_proof_point":
        r = get_proof_point(
            args["topic"],
            product=args.get("product"),
            max_age_days=args.get("max_age_days", 365),
        )
        if not r:
            return {"value": None, "reason": "cite-or-null / not publicly available"}
        return r
    if name == "search_competitive":
        r = get_competitive(args["competitor"], motion=args.get("motion"))
        if not r:
            return {"value": None, "reason": "No public competitive content for this competitor"}
        return r
    if name == "get_offer_detail":
        r = get_offer(args["offer_type"], product=args.get("product"))
        if not r:
            return {"value": None, "reason": "No public offer content for this offer type"}
        return r
    return {"error": f"Unknown tool: {name}"}

if __name__ == "__main__":
    run_server(TOOLS, handler)
