"""
Partner Ops — partner book + deal pipeline + operating cadence for a
Cisco Canada Partner Security AE.

PUBLIC LENS: ships with fictional sample data only. On the internal
rebuild, replace servers/data/partner_ops.json with real partner data.

Stage vocabulary (from the T1 Sellers playbook):
  10 EARLY - 25 QUALIFIED - 50 EVALUATION - 75 NEGOTIATION - 90 CLOSE
Stuck rule: 30+ days at the same stage = quietly slipping.
"""
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Union

import sys
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.lifecycle import (
    enrich_deal_row,
    lifecycle_for_deal_stage,
    lifecycle_label,
    partner_goal_for_lifecycle,
    STAGE_TO_LIFECYCLE,
)

SERVER_NAME = "partner-ops"
DATA_PATH = Path(__file__).parent / "data" / "partner_ops.json"

STAGES = {10: "Early", 25: "Qualified", 50: "Evaluation",
          75: "Negotiation", 90: "Close"}
STUCK_DAYS = 30
TOUCH_OVERDUE_DAYS = 14

MOTION_PILLARS = {
    "security": [
        "xdr", "firewall", "risk advisory", "identity", "zero trust", "breach",
        "duo", "soc", "audit", "ai-ready security", "meteor", "segmentation",
    ],
    "networking": [
        "reignite", "meraki", "catalyst", "refresh", "networking", "campus", "branch",
    ],
    "data_center": ["nexus", "ucs", "intersight", "dc", "ai pod", "hypershield", "workload"],
    "collaboration": ["webex", "collab", "calling", "contact centre", "contact center"],
}


def _motion_pillar(motion: str) -> str:
    m = (motion or "").lower()
    for pillar, keywords in MOTION_PILLARS.items():
        if any(k in m for k in keywords):
            return pillar
    return "security"

def _load() -> dict:
    if DATA_PATH.exists():
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"partners": {}, "deals": []}

def _save(data: dict):
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")

def _slug(name: str) -> str:
    return "-".join(name.strip().lower().split())

def _find_partner(data: dict, name: str) -> Optional[str]:
    key = _slug(name)
    if key in data["partners"]:
        return key
    needle = name.strip().lower()
    hits = [k for k, p in data["partners"].items()
            if needle in p["name"].lower() or needle in k]
    return hits[0] if len(hits) == 1 else None

def _days_since(iso: str) -> int:
    try:
        return (datetime.now() - datetime.fromisoformat(iso)).days
    except Exception:
        return -1

# ---------------------------------------------------------------- partners

def upsert_partner(name: str, fields: Optional[dict] = None) -> str:
    data = _load()
    key = _find_partner(data, name) or _slug(name)
    p = data["partners"].get(key, {"name": name.strip(), "created_at": _now(),
                                   "touches": []})
    p.update(fields or {})
    p["updated_at"] = _now()
    data["partners"][key] = p
    _save(data)
    return json.dumps({"success": True, "partner": p["name"]})

def get_partner(name: str) -> str:
    data = _load()
    key = _find_partner(data, name)
    if not key:
        return json.dumps({"error": "Partner '{}' not found.".format(name),
                           "known": [p["name"] for p in data["partners"].values()]})
    p = data["partners"][key]
    deals = [d for d in data["deals"] if d["partner"] == key]
    return json.dumps({"partner": p, "deals": deals,
                       "open_pipeline": sum(d.get("acv", 0) for d in deals
                                            if d["stage"] < 90)},
                      ensure_ascii=False)

def list_partners() -> str:
    data = _load()
    out = []
    for key, p in data["partners"].items():
        last_touch = p["touches"][-1]["at"] if p.get("touches") else None
        deals = [d for d in data["deals"] if d["partner"] == key and d["stage"] < 90]
        out.append({
            "name": p["name"], "tier": p.get("tier", "?"),
            "path": p.get("path", "?"), "pvi": p.get("pvi"),
            "black_belt_pct": p.get("black_belt_pct"),
            "disti_rep": p.get("disti_rep", ""),
            "open_deals": len(deals),
            "open_pipeline": sum(d.get("acv", 0) for d in deals),
            "last_touch": last_touch,
            "touch_overdue": (last_touch is None
                              or _days_since(last_touch) > TOUCH_OVERDUE_DAYS),
        })
    return json.dumps({"count": len(out), "partners": out}, ensure_ascii=False)

def log_touch(partner: str, note: str) -> str:
    data = _load()
    key = _find_partner(data, partner)
    if not key:
        return json.dumps({"error": "Partner '{}' not found.".format(partner)})
    data["partners"][key]["touches"].append({"at": _now(), "note": note})
    data["partners"][key]["updated_at"] = _now()
    _save(data)
    return json.dumps({"success": True, "partner": data["partners"][key]["name"]})

# ---------------------------------------------------------------- deals

def upsert_deal(partner: str, deal: str, stage: int,
                motion: str = "", acv: Union[int, float] = 0,
                close_date: str = "", notes: str = "",
                cx_lifecycle: str = "") -> str:
    if stage not in STAGES:
        return json.dumps({"error": "Stage must be one of {}".format(sorted(STAGES))})
    data = _load()
    pkey = _find_partner(data, partner)
    if not pkey:
        return json.dumps({"error": "Partner '{}' not found. Create it first with upsert_partner.".format(partner)})

    dkey = _slug(deal)
    for d in data["deals"]:
        if d["key"] == dkey and d["partner"] == pkey:
            if d["stage"] != stage:
                d["stage_history"].append({"stage": stage, "at": _now()})
                d["stage"] = stage
            if motion:
                d["motion"] = motion
            if acv:
                d["acv"] = acv
            if close_date:
                d["close_date"] = close_date
            if notes:
                d["notes"] = notes
            lc = cx_lifecycle or lifecycle_for_deal_stage(stage)
            d["cx_lifecycle"] = lc
            d["partner_goal"] = partner_goal_for_lifecycle(lc)
            d["updated_at"] = _now()
            _save(data)
            return json.dumps({"success": True, "updated": d["name"],
                               "stage": "{} ({}%)".format(STAGES[stage], stage)})
    lc = cx_lifecycle or lifecycle_for_deal_stage(stage)
    d = {"key": dkey, "name": deal.strip(), "partner": pkey, "stage": stage,
         "motion": motion, "acv": acv, "close_date": close_date,
         "notes": notes, "cx_lifecycle": lc,
         "partner_goal": partner_goal_for_lifecycle(lc),
         "created_at": _now(), "updated_at": _now(),
         "stage_history": [{"stage": stage, "at": _now()}]}
    data["deals"].append(d)
    _save(data)
    return json.dumps({"success": True, "created": d["name"],
                       "stage": "{} ({}%)".format(STAGES[stage], stage)})

def pipeline_view(partner: str = "") -> str:
    data = _load()
    pkey = _find_partner(data, partner) if partner else None
    deals, total, weighted, stuck = [], 0, 0.0, []
    for d in data["deals"]:
        if pkey and d["partner"] != pkey:
            continue
        if d["stage"] >= 90:
            continue
        days_at_stage = _days_since(d["stage_history"][-1]["at"])
        is_stuck = days_at_stage > STUCK_DAYS
        pname = data["partners"].get(d["partner"], {}).get("name", d["partner"])
        row = {"deal": d["name"], "partner": pname,
               "stage": "{} ({}%)".format(STAGES[d["stage"]], d["stage"]),
               "cx_lifecycle": d.get("cx_lifecycle", lifecycle_for_deal_stage(d["stage"])),
               "cx_lifecycle_label": lifecycle_label(d.get("cx_lifecycle", lifecycle_for_deal_stage(d["stage"]))),
               "partner_goal": d.get("partner_goal", partner_goal_for_lifecycle(lifecycle_for_deal_stage(d["stage"]))),
               "motion": d.get("motion", ""), "acv": d.get("acv", 0),
               "close_date": d.get("close_date", ""),
               "days_at_stage": days_at_stage, "stuck": is_stuck}
        deals.append(row)
        total += d.get("acv", 0)
        weighted += d.get("acv", 0) * d["stage"] / 100.0
        if is_stuck:
            stuck.append(row)
    deals.sort(key=lambda r: -r["acv"])
    return json.dumps({
        "open_deals": len(deals), "total_pipeline": total,
        "weighted_pipeline": round(weighted),
        "stuck_deals": len(stuck),
        "stuck_rule": "30+ days at the same stage = quietly slipping",
        "deals": deals,
    }, ensure_ascii=False)


def platform_view(partner: str = "") -> str:
    """Open pipeline grouped by pillar — security entry vs platform pull-through."""
    data = _load()
    pkey = _find_partner(data, partner) if partner else None
    by_pillar: dict = {p: [] for p in MOTION_PILLARS}
    for d in data["deals"]:
        if pkey and d["partner"] != pkey:
            continue
        if d["stage"] >= 90:
            continue
        pillar = _motion_pillar(d.get("motion", ""))
        pname = data["partners"].get(d["partner"], {}).get("name", d["partner"])
        by_pillar[pillar].append({
            "deal": d["name"], "partner": pname, "motion": d.get("motion", ""),
            "acv": d.get("acv", 0),
            "stage": "{} ({}%)".format(STAGES[d["stage"]], d["stage"]),
        })
    entry = by_pillar.get("security", [])
    pull = []
    for p in ("networking", "data_center", "collaboration"):
        pull.extend(by_pillar.get(p, []))
    return json.dumps({
        "headline": "Security opens the door; platform pull-through compounds.",
        "entry_pillar_deals": len(entry),
        "pull_through_deals": len(pull),
        "by_pillar": {k: v for k, v in by_pillar.items() if v},
        "guidance": (
            "Lead partner conversations with security motions. "
            "Flag pull-through deals where disti can thread network, DC, or collab "
            "on the same customer."
        ),
    }, ensure_ascii=False)


def lifecycle_view(partner: str = "") -> str:
    """Pipeline grouped by CX lifecycle stage (ANALYZE→RENEW)."""
    data = _load()
    pkey = _find_partner(data, partner) if partner else None
    by_lifecycle: dict = {k: [] for k in STAGE_TO_LIFECYCLE.values()}
    by_lifecycle["expand"] = []

    for d in data["deals"]:
        if pkey and d["partner"] != pkey:
            continue
        if d["stage"] >= 90:
            continue
        enriched = enrich_deal_row(d)
        pname = data["partners"].get(d["partner"], {}).get("name", d["partner"])
        lc = enriched["cx_lifecycle"]
        if lc not in by_lifecycle:
            by_lifecycle[lc] = []
        by_lifecycle[lc].append({
            "deal": d["name"],
            "partner": pname,
            "stage": STAGES[d["stage"]],
            "partner_goal": enriched["partner_goal"],
            "motion": d.get("motion", ""),
            "acv": d.get("acv", 0),
        })

    return json.dumps({
        "headline": "Customer lifecycle view — ANALYZE through RENEW",
        "by_lifecycle": {k: v for k, v in by_lifecycle.items() if v},
        "stage_mapping": {str(k): v for k, v in STAGE_TO_LIFECYCLE.items()},
        "next_step": "Call cisco-content get_content_matrix(cx_lifecycle=...) for stage-specific assets and actions.",
    }, ensure_ascii=False)


# ---------------------------------------------------------------- cadence

def whats_due(cadence: str = "weekly") -> str:
    data = _load()
    c = cadence.strip().lower()
    flags = []
    for key, p in data["partners"].items():
        last = p["touches"][-1]["at"] if p.get("touches") else None
        if last is None or _days_since(last) > TOUCH_OVERDUE_DAYS:
            flags.append("{}: no touch in {} days".format(
                p["name"], _days_since(last) if last else "(never)"))
    pipe = json.loads(pipeline_view())
    for row in pipe["deals"]:
        if row["stuck"]:
            flags.append("{} ({}): {} days at {}".format(
                row["deal"], row["partner"], row["days_at_stage"], row["stage"]))

    checklists = {
        "weekly": ["Pipeline scrub - three deals minimum: where is each one stuck?",
                   "Deal-reg review - every qualified opportunity registered before the customer call",
                   "Trial Console check - at-risk trials get an SE on the call by Friday",
                   "Five+ discovery calls with a security trigger question",
                   "PAM/disti sync booked with top three deals named"],
        "monthly": ["Black Belt completion review - flag slippage early, not at quarter-end",
                    "PVI score read - PXP partner-side, DPV disti-side, same numbers both sides",
                    "Pipeline coverage check - three-month forward view, gap analysis where coverage isn't there"],
        "quarterly": ["Joint plan review - Cisco / disti / partner: PVI movement, motion velocity, capability gaps",
                      "Investment alignment - MDF and program funds against named motions, not the catalogue",
                      "Cohort planning - Black Belt / FireJumper SE cohorts next quarter, resourcing committed",
                      "QBR decks - run qbr_package per Tier 1 partner"],
    }
    if c not in checklists:
        return json.dumps({"error": "cadence must be weekly, monthly, or quarterly"})
    return json.dumps({"cadence": c, "checklist": checklists[c],
                       "attention_flags": flags}, ensure_ascii=False)

def qbr_package(partner: str) -> str:
    data = _load()
    key = _find_partner(data, partner)
    if not key:
        return json.dumps({"error": "Partner '{}' not found.".format(partner)})
    p = data["partners"][key]
    deals = [d for d in data["deals"] if d["partner"] == key]
    closed = [d for d in deals if d["stage"] >= 90]
    open_deals = [d for d in deals if d["stage"] < 90]
    motions = sorted(set(d.get("motion", "") for d in deals if d.get("motion")))
    return json.dumps({
        "partner": p,
        "quarter_snapshot": {
            "pvi": p.get("pvi"),
            "black_belt_pct": p.get("black_belt_pct"),
            "motions_in_flight": motions,
            "open_pipeline": sum(d.get("acv", 0) for d in open_deals),
            "closed_this_period": sum(d.get("acv", 0) for d in closed),
            "open_deals": [{"name": d["name"], "stage": STAGES[d["stage"]],
                            "acv": d.get("acv", 0)} for d in open_deals],
            "recent_touches": p.get("touches", [])[-5:],
        },
        "next_step": ("Call cisco-content build_platform_brief(audience='tier1-leadership', "
                      "deliverable='deck', topic='QBR', story_mode='security-led') and draft "
                      "the QBR deck from this snapshot in Brandon's voice."),
    }, ensure_ascii=False)

# ---------------------------------------------------------------- MCP exports

TOOLS = [
    {
        "name": "upsert_partner",
        "description": "Create or update a partner record: tier (1/2), path (A-Meraki/B-Catalyst/C-Practice-build), pvi score, black_belt_pct, disti_rep, notes.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Partner name."},
                "fields": {"type": "object", "description": "Fields to merge, e.g. {tier, path, pvi, black_belt_pct, disti_rep, notes}."},
            },
            "required": ["name"],
        },
    },
    {
        "name": "get_partner",
        "description": "Full partner record with deals and open pipeline. Partial name match OK.",
        "inputSchema": {
            "type": "object",
            "properties": {"name": {"type": "string", "description": "Partner name."}},
            "required": ["name"],
        },
    },
    {
        "name": "list_partners",
        "description": "Partner book overview: tier, path, PVI, open pipeline, last touch, overdue flags. Use for 'how's my patch?'",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "log_touch",
        "description": "Record a partner interaction (call, meeting, email) so overdue-touch tracking works.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "partner": {"type": "string", "description": "Partner name."},
                "note": {"type": "string", "description": "What happened."},
            },
            "required": ["partner", "note"],
        },
    },
    {
        "name": "upsert_deal",
        "description": "Create or update a deal. Stage vocabulary: 10 Early, 25 Qualified, 50 Evaluation, 75 Negotiation, 90 Close. Stage changes are history-tracked for stuck-deal detection.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "partner": {"type": "string", "description": "Partner name (must exist)."},
                "deal": {"type": "string", "description": "Deal name."},
                "stage": {"type": "integer", "description": "10, 25, 50, 75, or 90."},
                "motion": {"type": "string", "description": "Named motion: Reignite Firewall, Project Meteor, Breach Protection by XDR, AI-Ready Security, or a play name."},
                "acv": {"type": "number", "description": "Deal value in CAD."},
                "close_date": {"type": "string", "description": "Expected close date YYYY-MM-DD."},
                "notes": {"type": "string", "description": "Context notes."},
                "cx_lifecycle": {"type": "string", "description": "Optional: analyze, place, land, adopt, expand, renew. Inferred from stage if omitted."},
            },
            "required": ["partner", "deal", "stage"],
        },
    },
    {
        "name": "lifecycle_view",
        "description": (
            "Open pipeline grouped by CX lifecycle stage (ANALYZE→RENEW) and partner goal persona. "
            "Use with get_content_matrix for stage-specific playbooks."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"partner": {"type": "string", "description": "Optional partner filter."}},
        },
    },
    {
        "name": "pipeline_view",
        "description": "Open pipeline: total, weighted value, days-at-stage, stuck deals (30+ days at stage). Optionally filter by partner. Use for pipeline reviews and forecasts.",
        "inputSchema": {
            "type": "object",
            "properties": {"partner": {"type": "string", "description": "Optional partner filter."}},
        },
    },
    {
        "name": "platform_view",
        "description": (
            "Open pipeline grouped by pillar (security entry vs networking / data centre / "
            "collaboration pull-through). Use to see where the one-Cisco platform story is "
            "compounding across a partner book."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"partner": {"type": "string", "description": "Optional partner filter."}},
        },
    },
    {
        "name": "whats_due",
        "description": "The operating cadence checklist (weekly pipeline scrub / monthly PVI read / quarterly joint plan) plus live attention flags: overdue partner touches and stuck deals. Use for 'what's on my plate' and morning briefings.",
        "inputSchema": {
            "type": "object",
            "properties": {"cadence": {"type": "string", "description": "weekly, monthly, or quarterly.", "default": "weekly"}},
        },
    },
    {
        "name": "qbr_package",
        "description": "Assemble a partner's QBR data package: PVI, capability, motions in flight, pipeline, closed business, recent touches — ready to draft the QBR deck via cisco-content build_brief.",
        "inputSchema": {
            "type": "object",
            "properties": {"partner": {"type": "string", "description": "Partner name."}},
            "required": ["partner"],
        },
    },
]

TOOL_HANDLERS = {
    "upsert_partner": lambda a: upsert_partner(a["name"], a.get("fields")),
    "get_partner": lambda a: get_partner(a["name"]),
    "list_partners": lambda a: list_partners(),
    "log_touch": lambda a: log_touch(a["partner"], a["note"]),
    "upsert_deal": lambda a: upsert_deal(
        a["partner"], a["deal"], a["stage"], a.get("motion", ""),
        a.get("acv", 0), a.get("close_date", ""), a.get("notes", ""),
        a.get("cx_lifecycle", "")),
    "pipeline_view": lambda a: pipeline_view(a.get("partner", "")),
    "lifecycle_view": lambda a: lifecycle_view(a.get("partner", "")),
    "platform_view": lambda a: platform_view(a.get("partner", "")),
    "whats_due": lambda a: whats_due(a.get("cadence", "weekly")),
    "qbr_package": lambda a: qbr_package(a["partner"]),
}
