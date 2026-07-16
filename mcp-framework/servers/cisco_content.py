"""
Cisco Content Engine — audience profiles, messaging library, prompt vault,
and asset registry for Cisco Canada partner-enablement content.

The core motion: master content -> audience-specific derivatives.
`build_brief` assembles everything Claude needs to draft a deliverable
in one call: audience profile + relevant messaging + style/format prompts
+ related assets.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

SERVER_NAME = "cisco-content"
DATA_PATH = Path(__file__).parent / "data" / "cisco_content.json"

EMPTY = {"audiences": {}, "messaging": [], "prompts": {}, "assets": []}

def _load() -> dict:
    if DATA_PATH.exists():
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return dict(EMPTY)

def _save(data: dict):
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")

def _slug(name: str) -> str:
    return "-".join(name.strip().lower().split())

# ---------------------------------------------------------------- audiences

def get_audiences(name: Optional[str] = None) -> str:
    data = _load()
    if name is None:
        return json.dumps({
            "count": len(data["audiences"]),
            "audiences": [
                {"key": k, "label": a.get("label", k)}
                for k, a in data["audiences"].items()
            ],
        }, ensure_ascii=False)
    key = _slug(name)
    if key not in data["audiences"]:
        needle = name.strip().lower()
        hits = [k for k, a in data["audiences"].items()
                if needle in k or needle in a.get("label", "").lower()]
        if len(hits) == 1:
            key = hits[0]
        else:
            return json.dumps({"error": "Audience '{}' not found.".format(name),
                               "known": list(data["audiences"].keys())})
    return json.dumps({"key": key, "profile": data["audiences"][key]},
                      ensure_ascii=False)

def upsert_audience(name: str, profile: dict) -> str:
    data = _load()
    key = _slug(name)
    existing = data["audiences"].get(key, {})
    existing.update(profile)
    existing["updated_at"] = _now()
    data["audiences"][key] = existing
    _save(data)
    return json.dumps({"success": True, "key": key})

# ---------------------------------------------------------------- messaging

def find_messaging(query: str = "", category: Optional[str] = None,
                   audience: Optional[str] = None) -> str:
    q = query.strip().lower()
    data = _load()
    hits = []
    for m in data["messaging"]:
        if category and m.get("category") != category:
            continue
        if audience and audience not in (m.get("audiences") or []) \
                and m.get("audiences"):
            continue
        blob = " ".join([m.get("topic", ""), m.get("content", ""),
                         m.get("category", "")]).lower()
        if q and q not in blob:
            continue
        hits.append(m)
    cats = sorted(set(m.get("category", "") for m in data["messaging"]))
    return json.dumps({"count": len(hits), "categories_available": cats,
                       "results": hits}, ensure_ascii=False)

def add_messaging(category: str, topic: str, content: str,
                  audiences: Optional[list] = None) -> str:
    data = _load()
    entry = {"category": category, "topic": topic, "content": content,
             "audiences": audiences or [], "added_at": _now()}
    data["messaging"].append(entry)
    _save(data)
    return json.dumps({"success": True, "total_messaging": len(data["messaging"])})

# ---------------------------------------------------------------- prompts

def get_prompt(name: Optional[str] = None) -> str:
    data = _load()
    if name is None:
        return json.dumps({"prompts": [
            {"name": k, "notes": v.get("notes", "")}
            for k, v in data["prompts"].items()
        ]}, ensure_ascii=False)
    key = _slug(name)
    if key not in data["prompts"]:
        needle = name.strip().lower()
        hits = [k for k in data["prompts"] if needle in k]
        if len(hits) == 1:
            key = hits[0]
        else:
            return json.dumps({"error": "Prompt '{}' not found.".format(name),
                               "known": list(data["prompts"].keys())})
    return json.dumps({"name": key, "prompt": data["prompts"][key]},
                      ensure_ascii=False)

def save_prompt(name: str, prompt: str, notes: str = "") -> str:
    data = _load()
    key = _slug(name)
    prev = data["prompts"].get(key)
    entry = {"text": prompt, "notes": notes, "updated_at": _now(),
             "version": (prev.get("version", 1) + 1) if prev else 1}
    if prev:
        entry["previous_version"] = prev.get("text", "")
    data["prompts"][key] = entry
    _save(data)
    return json.dumps({"success": True, "name": key,
                       "version": entry["version"]})

# ---------------------------------------------------------------- assets

def register_asset(title: str, asset_type: str, audience: str = "",
                   status: str = "final", location: str = "drive",
                   link: str = "", derived_from: str = "",
                   campaign: str = "") -> str:
    data = _load()
    asset = {"title": title, "type": asset_type, "audience": audience,
             "status": status, "location": location, "link": link,
             "derived_from": derived_from, "campaign": campaign,
             "registered_at": _now()}
    # Update if same title exists
    for i, a in enumerate(data["assets"]):
        if a["title"].lower() == title.lower():
            data["assets"][i] = asset
            _save(data)
            return json.dumps({"success": True, "updated": title})
    data["assets"].append(asset)
    _save(data)
    return json.dumps({"success": True, "registered": title,
                       "total_assets": len(data["assets"])})

def list_assets(query: str = "", campaign: str = "",
                audience: str = "") -> str:
    q = query.strip().lower()
    data = _load()
    hits = []
    for a in data["assets"]:
        if campaign and campaign.lower() not in a.get("campaign", "").lower():
            continue
        if audience and audience.lower() not in a.get("audience", "").lower():
            continue
        blob = " ".join([a.get("title", ""), a.get("type", ""),
                         a.get("campaign", ""), a.get("audience", "")]).lower()
        if q and q not in blob:
            continue
        hits.append(a)
    return json.dumps({"count": len(hits), "assets": hits}, ensure_ascii=False)

# ---------------------------------------------------------------- build_brief

def build_brief(audience: str, deliverable: str, topic: str = "") -> str:
    """Assemble the full drafting context for one deliverable."""
    data = _load()

    aud = json.loads(get_audiences(audience))
    if "error" in aud:
        return json.dumps(aud)

    relevant = json.loads(find_messaging(query=topic))["results"] if topic \
        else data["messaging"]
    # Filter to messaging tagged for this audience (untagged = universal)
    key = aud["key"]
    relevant = [m for m in relevant
                if not m.get("audiences") or key in m["audiences"]]

    style = data["prompts"].get("style-guide", {}).get("text", "")
    fmt_key = _slug(deliverable)
    fmt_hits = [k for k in data["prompts"] if fmt_key in k or k in fmt_key]
    fmt = data["prompts"][fmt_hits[0]]["text"] if fmt_hits else ""

    related = [a for a in data["assets"]
               if not topic or topic.lower() in
               " ".join([a.get("title", ""), a.get("campaign", "")]).lower()]

    return json.dumps({
        "instruction": ("Draft the deliverable using ALL of the context below. "
                        "Follow the style guide exactly. Pull source material "
                        "from related_assets links where needed."),
        "deliverable": deliverable,
        "topic": topic,
        "audience": aud,
        "messaging": relevant,
        "style_guide": style,
        "format_prompt": fmt,
        "related_assets": related,
    }, ensure_ascii=False)

# ---------------------------------------------------------------- MCP exports

TOOLS = [
    {
        "name": "build_brief",
        "description": (
            "START HERE for any content task. Assembles the complete drafting "
            "context for a Cisco partner-content deliverable: audience profile, "
            "relevant messaging, style guide, format prompt, and related assets. "
            "Use when asked to create/adapt a deck, playbook, one-pager, or any "
            "partner content."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "audience": {"type": "string", "description": "Target audience, e.g. 'tier1-leadership', 't1-sellers', 'tier2-partners', 'disti-teams', 'customer-facing'."},
                "deliverable": {"type": "string", "description": "Deliverable type, e.g. 'deck', 'playbook', 'one-pager', 'objection-handler'."},
                "topic": {"type": "string", "description": "Optional topic/campaign filter, e.g. 'firewall seeding', 'audit'."},
            },
            "required": ["audience", "deliverable"],
        },
    },
    {
        "name": "get_audiences",
        "description": "List all audience profiles, or get one full profile by name (partial match OK).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Audience name. Omit to list all."},
            },
        },
    },
    {
        "name": "upsert_audience",
        "description": "Create or update an audience profile (tone, priorities, lead_with, avoid, format_preferences).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Audience name/key."},
                "profile": {"type": "object", "description": "Profile fields to set/merge, e.g. {label, who, tone, lead_with, priorities, avoid, format_preferences}."},
            },
            "required": ["name", "profile"],
        },
    },
    {
        "name": "find_messaging",
        "description": "Search the messaging library: plays, partner paths, competitive positions, objection/response pairs, proof points, incentives, market forces.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Text to search for. Empty returns all (filtered by category/audience)."},
                "category": {"type": "string", "description": "Optional: play, path, competitive, objection, proof-point, incentive, market-force, cadence."},
                "audience": {"type": "string", "description": "Optional audience key filter."},
            },
        },
    },
    {
        "name": "add_messaging",
        "description": "Add a messaging entry after creating new content — value props, objection responses, proof points — so it's reusable in every future deliverable.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "play, path, competitive, objection, proof-point, incentive, market-force, or cadence."},
                "topic": {"type": "string", "description": "Short topic label."},
                "content": {"type": "string", "description": "The messaging content."},
                "audiences": {"type": "array", "items": {"type": "string"}, "description": "Audience keys this applies to. Empty = universal."},
            },
            "required": ["category", "topic", "content"],
        },
    },
    {
        "name": "get_prompt",
        "description": "List saved adaptation/style prompts, or fetch one by name (partial match OK). Includes 'style-guide' — Brandon's writing voice.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Prompt name. Omit to list all."},
            },
        },
    },
    {
        "name": "save_prompt",
        "description": "Save or update a reusable adaptation prompt (versioned — the previous text is kept).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Prompt name, e.g. 'deck-from-master'."},
                "prompt": {"type": "string", "description": "The prompt text."},
                "notes": {"type": "string", "description": "Optional usage notes."},
            },
            "required": ["name", "prompt"],
        },
    },
    {
        "name": "register_asset",
        "description": "Register a content asset (master or derivative) in the registry after creating or discovering one.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Asset title."},
                "asset_type": {"type": "string", "description": "master-doc, deck, playbook, one-pager, objection-handler, proposal, pdf."},
                "audience": {"type": "string", "description": "Target audience key."},
                "status": {"type": "string", "description": "draft, review, or final.", "default": "final"},
                "location": {"type": "string", "description": "drive, cisco, or local.", "default": "drive"},
                "link": {"type": "string", "description": "URL or file path."},
                "derived_from": {"type": "string", "description": "Title of the master this derives from."},
                "campaign": {"type": "string", "description": "Campaign/programme, e.g. 'secure-networking-index-audit'."},
            },
            "required": ["title", "asset_type"],
        },
    },
    {
        "name": "list_assets",
        "description": "Search the asset registry — masters, derivatives, status, locations, links. Use to answer 'what content exists / what's missing for X'.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Text filter on title/type/campaign."},
                "campaign": {"type": "string", "description": "Filter by campaign."},
                "audience": {"type": "string", "description": "Filter by audience."},
            },
        },
    },
]

TOOL_HANDLERS = {
    "build_brief": lambda a: build_brief(a["audience"], a["deliverable"], a.get("topic", "")),
    "get_audiences": lambda a: get_audiences(a.get("name")),
    "upsert_audience": lambda a: upsert_audience(a["name"], a["profile"]),
    "find_messaging": lambda a: find_messaging(a.get("query", ""), a.get("category"), a.get("audience")),
    "add_messaging": lambda a: add_messaging(a["category"], a["topic"], a["content"], a.get("audiences")),
    "get_prompt": lambda a: get_prompt(a.get("name")),
    "save_prompt": lambda a: save_prompt(a["name"], a["prompt"], a.get("notes", "")),
    "register_asset": lambda a: register_asset(
        a["title"], a["asset_type"], a.get("audience", ""), a.get("status", "final"),
        a.get("location", "drive"), a.get("link", ""), a.get("derived_from", ""),
        a.get("campaign", "")),
    "list_assets": lambda a: list_assets(a.get("query", ""), a.get("campaign", ""), a.get("audience", "")),
}
