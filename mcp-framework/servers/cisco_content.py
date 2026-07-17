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
MATRIX_PATH = Path(__file__).parent / "data" / "network_security_content_matrix.json"

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
                   audience: Optional[str] = None,
                   pillar: Optional[str] = None) -> str:
    q = query.strip().lower()
    data = _load()
    hits = []
    for m in data["messaging"]:
        if category and m.get("category") != category:
            continue
        if pillar and m.get("pillar") != pillar and m.get("pillar") != "cross-pillar":
            continue
        if audience and audience not in (m.get("audiences") or []) \
                and m.get("audiences"):
            continue
        blob = " ".join([m.get("topic", ""), m.get("content", ""),
                         m.get("category", ""), m.get("pillar", "")]).lower()
        if q and q not in blob:
            continue
        hits.append(m)
    cats = sorted(set(m.get("category", "") for m in data["messaging"]))
    pillars = sorted(set(m.get("pillar", "") for m in data["messaging"] if m.get("pillar")))
    return json.dumps({"count": len(hits), "categories_available": cats,
                       "pillars_available": pillars, "results": hits},
                      ensure_ascii=False)

def add_messaging(category: str, topic: str, content: str,
                  audiences: Optional[list] = None,
                  pillar: str = "") -> str:
    data = _load()
    entry = {"category": category, "topic": topic, "content": content,
             "audiences": audiences or [], "added_at": _now()}
    if pillar:
        entry["pillar"] = pillar
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


def _load_matrix() -> dict:
    if MATRIX_PATH.exists():
        with open(MATRIX_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"entries": [], "journey_steps": [], "foundations": {}}


def get_content_matrix(cx_lifecycle: str = "", partner_goal: str = "") -> str:
    """Return content matrix row: assets, actions, MEDDPICC focus, certifications."""
    matrix = _load_matrix()
    entries = matrix.get("entries", [])
    lc = _slug(cx_lifecycle) if cx_lifecycle else ""
    pg = partner_goal.strip().lower()

    hits = list(entries)
    if lc:
        hits = [e for e in hits if e.get("cx_lifecycle_short") == lc or e.get("id") == lc]
    if pg:
        hits = [e for e in hits if pg in e.get("partner_goal", "").lower()]

    return json.dumps({
        "count": len(hits),
        "entries": hits,
        "available_lifecycle_stages": [e.get("cx_lifecycle_short") for e in entries],
        "available_partner_goals": [e.get("partner_goal") for e in entries],
    }, ensure_ascii=False)


def get_lifecycle_guide() -> str:
    """Return full CX lifecycle spine, journey steps, and stage→deal mappings."""
    matrix = _load_matrix()
    data = _load()
    platform = data.get("platform", {})
    return json.dumps({
        "headline": "LAND → ADOPT → EXPAND → RENEW with ANALYZE and PLACE foundations",
        "foundations": matrix.get("foundations", {}),
        "lifecycle_stages": matrix.get("entries", []),
        "journey_steps": matrix.get("journey_steps", []),
        "deal_stage_map": {
            "10 Early": "analyze",
            "25 Qualified": "place",
            "50 Evaluation": "land",
            "75 Negotiation": "adopt",
            "90 Close": "renew",
        },
        "platform_threads": platform.get("threads", []),
        "usage": "Call get_content_matrix(cx_lifecycle='analyze') for assets/actions/certs at each stage.",
    }, ensure_ascii=False)


def get_platform_story(pillar: str = "", entry_pillar: str = "") -> str:
    """Return the one-Cisco platform model with routing for entry pillar."""
    data = _load()
    platform = data.get("platform", {})
    if not platform:
        return json.dumps({"error": "Platform model not configured."})

    entry = _slug(entry_pillar) if entry_pillar else platform.get("entry_pillar", "security")
    if not entry:
        entry = "security"

    routing = platform.get("routing", {})
    threads = platform.get("threads", [])
    pillars = platform.get("pillars", {})

    out = {
        "headline": platform.get("headline"),
        "story_principle": platform.get("story_principle"),
        "entry_pillar": entry,
        "routing": routing,
        "pillars": pillars,
        "threads": threads,
        "recommended_story_mode": _recommended_story_mode(entry, routing),
        "usage": (
            "security-only: CISO-only / security budget / qualified security motion. "
            "security-led: default inbound security with platform expansion on signals. "
            "pillar-first: network/DC/collab inbound — SME answer first, pivot when earned. "
            "pillar-deep: security opened the door; go deep on one pillar. "
            "Call build_platform_brief for a full drafting package."
        ),
    }

    pkey = _slug(pillar) if pillar else entry
    if pkey and pkey in pillars:
        out["pillar_focus"] = pillars[pkey]
        pivot_topic = {
            "networking": "Network-first pivot to platform",
            "data-center": "DC-first pivot to platform",
            "collaboration": "Collab-first pivot to platform",
            "security": "When to stay security-only",
        }.get(pkey)
        if pivot_topic:
            hits = json.loads(find_messaging(query=pivot_topic))["results"]
            out["pivot_messaging"] = hits[:3] if hits else []
        else:
            out["pivot_messaging"] = json.loads(
                find_messaging(pillar=pkey, category="platform-thread"))["results"]

    thread_id = {
        "networking": "network-first",
        "data-center": "dc-first",
        "collaboration": "collab-first",
    }.get(entry)
    if thread_id:
        out["entry_thread"] = next((t for t in threads if t.get("id") == thread_id), None)

    return json.dumps(out, ensure_ascii=False)


def _recommended_story_mode(entry: str, routing: dict) -> str:
    if entry == "security":
        return "security-led"
    if entry in ("networking", "data-center", "collaboration"):
        return "pillar-first"
    return "security-led"


def _filter_audience(msgs: list, aud_key: str) -> list:
    return [m for m in msgs if not m.get("audiences") or aud_key in m["audiences"]]


def build_platform_brief(audience: str, deliverable: str, topic: str = "",
                         pillar: str = "", story_mode: str = "security-led") -> str:
    """Platform brief with security-only, security-led, pillar-first, or pillar-deep modes."""
    data = _load()
    platform = data.get("platform", {})

    aud = json.loads(get_audiences(audience))
    if "error" in aud:
        return json.dumps(aud)

    mode = story_mode.strip().lower()
    valid_modes = ("security-only", "security-led", "pillar-first", "pillar-deep")
    if mode not in valid_modes:
        return json.dumps({"error": f"story_mode must be one of: {', '.join(valid_modes)}"})

    key = aud["key"]
    pkey = _slug(pillar) if pillar else ""
    routing = platform.get("routing", {})

    security_msgs = _filter_audience(
        json.loads(find_messaging(category="play"))["results"], key)
    if topic:
        topic_hits = json.loads(find_messaging(query=topic))["results"]
        security_msgs = topic_hits + [m for m in security_msgs if m not in topic_hits]

    platform_threads = _filter_audience(
        json.loads(find_messaging(category="platform-thread"))["results"], key)

    pull_through = []
    if mode not in ("security-only", "pillar-first"):
        for p in ("networking", "data-center", "collaboration"):
            pull_through.extend(json.loads(find_messaging(pillar=p, category="play"))["results"])
    elif mode == "pillar-first" and pkey:
        pull_through = []  # optional pivot only via pivot_messaging

    pillar_msgs: list = []
    pivot_msgs: list = []
    entry_pillar = "security"

    if mode == "security-only":
        pivot_msgs = _filter_audience(
            [m for m in platform_threads if m.get("topic") == "When to stay security-only"],
            key)
        entry_pillar = "security"

    elif mode == "pillar-deep":
        if not pkey:
            return json.dumps({"error": "pillar-deep requires pillar (security, networking, data-center, collaboration)."})
        pillar_msgs = json.loads(find_messaging(pillar=pkey))["results"]
        if not pillar_msgs:
            pillar_msgs = json.loads(find_messaging(query=pillar))["results"]
        entry_pillar = "security"

    elif mode == "pillar-first":
        if not pkey or pkey == "security":
            return json.dumps({"error": "pillar-first requires pillar: networking, data-center, or collaboration."})
        pillar_msgs = json.loads(find_messaging(pillar=pkey, category="play"))["results"]
        pillar_msgs += json.loads(find_messaging(pillar=pkey, category="platform-thread"))["results"]
        pivot_map = {
            "networking": "Network-first pivot to platform",
            "data-center": "DC-first pivot to platform",
            "collaboration": "Collab-first pivot to platform",
        }
        pivot_msgs = json.loads(find_messaging(query=pivot_map.get(pkey, "")))["results"]
        entry_pillar = pkey

    style = data["prompts"].get("style-guide", {}).get("text", "")
    narrative_key = {
        "security-only": "security-only",
        "security-led": "platform-story",
        "pillar-first": "pillar-first",
        "pillar-deep": "pillar-deep-dive",
    }[mode]
    narrative = data["prompts"].get(narrative_key, {}).get("text", "")

    fmt_key = _slug(deliverable)
    fmt_hits = [k for k in data["prompts"] if fmt_key in k or k in fmt_key]
    fmt = data["prompts"][fmt_hits[0]]["text"] if fmt_hits else ""

    related = [a for a in data["assets"]
               if not topic or topic.lower() in
               " ".join([a.get("title", ""), a.get("campaign", "")]).lower()]

    instructions = {
        "security-only": (
            "Stay security-only per routing.security_only. No networking, DC, or collab pull-through. "
            "SME depth on the security motion in flight."
        ),
        "security-led": (
            "Draft security-first. Use platform threads only where the customer or partner "
            "opened the door — expand on refresh, sprawl, hybrid, or AI signals."
        ),
        "pillar-first": (
            f"Answer as {pkey} SME first — sizing, architecture, economics. "
            "Optional platform pivot only when routing.pillar_first_pivot_when signals appear."
        ),
        "pillar-deep": (
            f"Security opened the door; go deep on '{pkey}'. "
            "Tie back to security trigger; use THE RETURN if platform thread is in flight."
        ),
    }

    pillar_profile = platform.get("pillars", {}).get(pkey, {}) if pkey else {}

    return json.dumps({
        "instruction": instructions[mode],
        "story_mode": mode,
        "entry_pillar": entry_pillar,
        "deliverable": deliverable,
        "topic": topic,
        "audience": aud,
        "routing": routing,
        "platform": {
            "headline": platform.get("headline"),
            "story_principle": platform.get("story_principle"),
            "threads": platform.get("threads", []),
            "pillar_profile": pillar_profile,
        },
        "security_messaging": security_msgs[:20] if mode != "pillar-first" else [],
        "platform_threads": platform_threads if mode == "security-led" else [],
        "pull_through_plays": pull_through,
        "pillar_content": pillar_msgs,
        "pivot_messaging": pivot_msgs,
        "style_guide": style,
        "narrative_prompt": narrative,
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
        "name": "build_platform_brief",
        "description": (
            "Platform narrative drafting context for Tier 2 / disti. Story modes: "
            "'security-led' (default — expand on refresh/sprawl/hybrid/AI signals), "
            "'security-only' (CISO-only, security budget, qualified security motion), "
            "'pillar-first' + pillar (network/DC/collab inbound — SME answer first, optional pivot), "
            "'pillar-deep' + pillar (security opened door; SME depth on one pillar)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "audience": {"type": "string", "description": "Target audience, e.g. 'tier2-partners', 'disti-teams'."},
                "deliverable": {"type": "string", "description": "deck, playbook, one-pager, objection-handler."},
                "topic": {"type": "string", "description": "Optional topic filter, e.g. 'audit', 'campus refresh'."},
                "pillar": {"type": "string", "description": "Required for pillar-first/deep: networking, data-center, collaboration, security."},
                "story_mode": {"type": "string", "description": "security-led (default), security-only, pillar-first, or pillar-deep.", "default": "security-led"},
            },
            "required": ["audience", "deliverable"],
        },
    },
    {
        "name": "get_content_matrix",
        "description": (
            "Return the Network Security Architecture content matrix for a CX lifecycle stage "
            "or partner goal: Cisco assets, partner actions, MEDDPICC focus, certifications, "
            "and recommended MCP tools."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "cx_lifecycle": {"type": "string", "description": "analyze, place, land, adopt, expand, renew"},
                "partner_goal": {"type": "string", "description": "e.g. Strategic Consultant, Thought Leader"},
            },
        },
    },
    {
        "name": "get_lifecycle_guide",
        "description": (
            "Return the full customer lifecycle spine (ANALYZE→RENEW), 9-step journey, "
            "deal-stage mapping, and platform threads."
        ),
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_platform_story",
        "description": (
            "Return the one-Cisco platform model with routing rules. Use entry_pillar when "
            "the first conversation is networking, data-center, or collaboration — not security. "
            "Optional pillar focus for pivot lines and SME depth."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "pillar": {"type": "string", "description": "Optional focus: networking, data-center, collaboration, security."},
                "entry_pillar": {"type": "string", "description": "How the deal entered: security (default), networking, data-center, collaboration."},
            },
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
                "category": {"type": "string", "description": "Optional: play, path, platform-thread, competitive, objection, proof-point, incentive, market-force, cadence, framework."},
                "audience": {"type": "string", "description": "Optional audience key filter."},
                "pillar": {"type": "string", "description": "Optional pillar filter: security, networking, data-center, collaboration, cross-pillar."},
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
                "pillar": {"type": "string", "description": "Optional: security, networking, data-center, collaboration, cross-pillar."},
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
    "build_platform_brief": lambda a: build_platform_brief(
        a["audience"], a["deliverable"], a.get("topic", ""),
        a.get("pillar", ""), a.get("story_mode", "security-led")),
    "get_content_matrix": lambda a: get_content_matrix(
        a.get("cx_lifecycle", ""), a.get("partner_goal", "")),
    "get_lifecycle_guide": lambda a: get_lifecycle_guide(),
    "get_platform_story": lambda a: get_platform_story(
        a.get("pillar", ""), a.get("entry_pillar", "")),
    "get_audiences": lambda a: get_audiences(a.get("name")),
    "upsert_audience": lambda a: upsert_audience(a["name"], a["profile"]),
    "find_messaging": lambda a: find_messaging(
        a.get("query", ""), a.get("category"), a.get("audience"), a.get("pillar")),
    "add_messaging": lambda a: add_messaging(
        a["category"], a["topic"], a["content"], a.get("audiences"), a.get("pillar", "")),
    "get_prompt": lambda a: get_prompt(a.get("name")),
    "save_prompt": lambda a: save_prompt(a["name"], a["prompt"], a.get("notes", "")),
    "register_asset": lambda a: register_asset(
        a["title"], a["asset_type"], a.get("audience", ""), a.get("status", "final"),
        a.get("location", "drive"), a.get("link", ""), a.get("derived_from", ""),
        a.get("campaign", "")),
    "list_assets": lambda a: list_assets(a.get("query", ""), a.get("campaign", ""), a.get("audience", "")),
}
