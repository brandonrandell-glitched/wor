"""
SNI Scorer — the Secure Networking Index 30-Minute Readiness Audit as a
live tool. Run the audit in a Claude chat: ask the ten questions, score
live, and generate the Readiness Report package on the spot.

Structure (from the Architecture Audit Challenge motion):
  5 dimensions x 0-6 points = 0-30 total
  Tiers: At Risk (0-8) · Foundational (9-15) · Developing (16-23) · Advanced (24-30)
  Scores under 16 trigger a 90-minute Design Clinic.

NOTE: The ten questions below are a working draft in the official
structure (two per dimension, 0-3 points each). Replace with the official
Customer Audit Form wording via update via save-over of QUESTIONS in this
file, or keep as-is for partner-led sessions.
"""
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.market import MARKET

SERVER_NAME = "sni-scorer"
DATA_PATH = Path(__file__).parent / "data" / "sni_data.json"

DIMENSIONS = ["Branch Security", "Remote Access", "Cloud Visibility",
              "Identity Enforcement", "Net + Sec Convergence"]

# Two questions per dimension, each scored 0-3. DRAFT wording — swap in the
# official Customer Audit Form questions when available.
QUESTIONS = [
    {"id": 1, "dimension": "Branch Security",
     "question": "How is security enforced at your branch/site edges today?",
     "scoring": "0 = no dedicated edge security / EOL firewall. 1 = aging firewall, no active management. 2 = current firewall, basic policy hygiene. 3 = current firewall with managed policy, IPS, and regular rule reviews."},
    {"id": 2, "dimension": "Branch Security",
     "question": "When did you last review firewall rules and segmentation between sites?",
     "scoring": "0 = never / unknown. 1 = over two years ago. 2 = within the last year. 3 = scheduled reviews with documented changes."},
    {"id": 3, "dimension": "Remote Access",
     "question": "How do remote and hybrid users reach applications today?",
     "scoring": "0 = legacy VPN for everything, shared credentials exist. 1 = VPN with MFA. 2 = mix of VPN and ZTNA/SSE for some apps. 3 = ZTNA/SSE-first with posture checks."},
    {"id": 4, "dimension": "Remote Access",
     "question": "What breaks or generates tickets most often in remote access?",
     "scoring": "0 = frequent outages/complaints, no visibility into cause. 1 = known pain points, workarounds in place. 2 = occasional issues, monitored. 3 = stable, measured, user experience tracked."},
    {"id": 5, "dimension": "Cloud Visibility",
     "question": "How consistent is your security policy across cloud platforms (AWS/Azure/GCP/M365)?",
     "scoring": "0 = no cloud security posture visibility. 1 = per-platform native tools only, no unified view. 2 = partial central visibility. 3 = unified policy and posture view across clouds."},
    {"id": 6, "dimension": "Cloud Visibility",
     "question": "Do you know which SaaS and AI tools your users are actually using?",
     "scoring": "0 = no visibility into shadow IT/AI. 1 = anecdotal awareness only. 2 = discovery tooling in place, partially reviewed. 3 = continuous discovery with an approval workflow."},
    {"id": 7, "dimension": "Identity Enforcement",
     "question": "What stands between a stolen password and your applications?",
     "scoring": "0 = passwords only in places. 1 = MFA on some apps. 2 = MFA everywhere. 3 = MFA + device trust/posture + risk-based policies."},
    {"id": 8, "dimension": "Identity Enforcement",
     "question": "How quickly can you disable all access for a departing user or compromised account?",
     "scoring": "0 = manual, multi-system, days. 1 = documented process, hours. 2 = mostly centralised, under an hour. 3 = single-action deprovisioning, minutes."},
    {"id": 9, "dimension": "Net + Sec Convergence",
     "question": "Do your networking and security teams share tools, data, and planning?",
     "scoring": "0 = fully siloed teams and tooling. 1 = separate teams, occasional coordination. 2 = shared visibility, joint planning on projects. 3 = converged operating model and shared platform."},
    {"id": 10, "dimension": "Net + Sec Convergence",
     "question": "If an attacker got into your network today, how far could they move before you saw them?",
     "scoring": "0 = flat network, no internal detection. 1 = some segmentation, limited detection. 2 = segmented with monitored east-west traffic. 3 = policy-enforced segmentation with detection and response integrated."},
]

TIERS = [(0, 8, "At Risk"), (9, 15, "Foundational"),
         (16, 23, "Developing"), (24, 30, "Advanced")]
CLINIC_THRESHOLD = 16  # under 16 triggers the Design Clinic

ACTIONS = {
    "Branch Security": "Firewall rule hygiene review and edge refresh assessment — candidate for the Secure Networking play (firewall seeding, TCF pricing at refresh).",
    "Remote Access": "ZTNA/SSE pilot for the highest-friction user group — Zero Trust Access play (Umbrella to Secure Access at the 50-seat threshold).",
    "Cloud Visibility": "Unified cloud posture review including shadow AI discovery — Cloud play; AI Defense assessment where shadow AI surfaced.",
    "Identity Enforcement": "Identity hardening sprint: MFA coverage gaps, device trust, rapid deprovisioning — Identity play (Duo, lowest-friction entry).",
    "Net + Sec Convergence": "Segmentation and convergence workshop mapping east-west visibility gaps — Segmentation play built on the firewall as policy enforcement point.",
}

SPRINT_TARGETS = {"accounts_targeted": 15, "audit_sessions": "6-8",
                  "qualified_opportunities": "3-4", "design_clinics": 2,
                  "duration": "10 weeks"}

def _load() -> dict:
    if DATA_PATH.exists():
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {"assessments": []}
    data.setdefault("market", MARKET)
    return data

def _save(data: dict):
    data.setdefault("market", MARKET)
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def _tier(total: int) -> str:
    for lo, hi, name in TIERS:
        if lo <= total <= hi:
            return name
    return "Unknown"

# ---------------------------------------------------------------- tools

def get_questionnaire() -> str:
    return json.dumps({
        "title": "Secure Networking Index — 30-Minute Readiness Audit",
        "market": MARKET,
        "how_to_run": ("Ask the ten questions conversationally. Score each 0-3 "
                       "using the scoring guide. Keep it vendor-agnostic — no "
                       "product names in the room. Score live; the customer "
                       "keeps the output. Frame outcomes for Canadian buyers "
                       "(PHIPA, PIPEDA, OSFI, FINTRAC where relevant); CAD "
                       "commercial context only."),
        "dimensions": DIMENSIONS,
        "questions": QUESTIONS,
        "tiers": [{"range": "{}-{}".format(lo, hi), "tier": name}
                  for lo, hi, name in TIERS],
        "design_clinic_trigger": "Total score under {}".format(CLINIC_THRESHOLD),
    }, ensure_ascii=False)

def score_assessment(customer: str, answers: list, notes: str = "",
                     partner: str = "") -> str:
    if len(answers) != 10:
        return json.dumps({"error": "Need exactly 10 answers (0-3 each), got {}.".format(len(answers))})
    if any((not isinstance(a, int)) or a < 0 or a > 3 for a in answers):
        return json.dumps({"error": "Each answer must be an integer 0-3."})

    dims = {}
    for q, a in zip(QUESTIONS, answers):
        dims[q["dimension"]] = dims.get(q["dimension"], 0) + a
    total = sum(dims.values())
    tier = _tier(total)
    ranked = sorted(dims.items(), key=lambda kv: kv[1])
    top_gaps = [d for d, s in ranked[:3] if s < 5]
    recommended = [{"gap": d, "score": dims[d], "action": ACTIONS[d]}
                   for d in top_gaps]

    assessment = {
        "customer": customer, "partner": partner, "at": datetime.now().isoformat(timespec="seconds"),
        "answers": answers, "dimension_scores": dims, "total": total,
        "tier": tier, "design_clinic": total < CLINIC_THRESHOLD,
        "recommended_actions": recommended, "notes": notes,
    }
    data = _load()
    data["assessments"].append(assessment)
    _save(data)

    return json.dumps({
        "customer": customer,
        "total": "{}/30".format(total),
        "tier": tier,
        "dimension_scores": {d: "{}/6".format(s) for d, s in dims.items()},
        "design_clinic": ("TRIGGERED - book the 90-minute Design Clinic"
                          if total < CLINIC_THRESHOLD else "Not triggered"),
        "recommended_actions": recommended,
        "next_step": ("Generate the Readiness Report (deliver within 24 hrs): "
                      "scored dimensions, prioritised gaps, three actions, and "
                      "the architectural next step with a date on it. "
                      "Vendor-agnostic; the customer keeps it."),
    }, ensure_ascii=False)

def list_assessments(customer: str = "") -> str:
    data = _load()
    hits = [a for a in data["assessments"]
            if not customer or customer.lower() in a["customer"].lower()]
    return json.dumps({
        "count": len(hits),
        "assessments": [{"customer": a["customer"], "partner": a.get("partner", ""),
                         "at": a["at"], "total": a["total"], "tier": a["tier"],
                         "design_clinic": a["design_clinic"]} for a in hits],
    }, ensure_ascii=False)

def get_assessment(customer: str) -> str:
    data = _load()
    hits = [a for a in data["assessments"]
            if customer.lower() in a["customer"].lower()]
    if not hits:
        return json.dumps({"error": "No assessment found for '{}'.".format(customer)})
    return json.dumps(hits[-1], ensure_ascii=False)

def sprint_status() -> str:
    data = _load()
    sessions = len(data["assessments"])
    qualified = sum(1 for a in data["assessments"] if a["design_clinic"])
    return json.dumps({
        "targets_per_10_week_sprint": SPRINT_TARGETS,
        "actuals": {"audit_sessions_run": sessions,
                    "design_clinic_triggers": qualified},
        "note": ("Conservative baselines from a 15-account sprint. Partners who "
                 "personalise outreach and focus on their strongest verticals "
                 "convert higher."),
    }, ensure_ascii=False)

# ---------------------------------------------------------------- MCP exports

TOOLS = [
    {
        "name": "get_questionnaire",
        "description": "The Secure Networking Index 30-minute readiness audit: 10 questions across 5 dimensions with 0-3 scoring guides, tier bands, and how to run the session. Use when starting an audit with a customer or prepping a partner to run one.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "score_assessment",
        "description": "Score a completed audit: 10 answers (0-3 each) -> dimension scores, 0-30 total, tier (At Risk/Foundational/Developing/Advanced), Design Clinic trigger (<16), and three recommended actions mapped to Cisco Secure plays. Saves the assessment.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "customer": {"type": "string", "description": "Customer/organisation name."},
                "answers": {"type": "array", "items": {"type": "integer"}, "description": "Exactly 10 integers, 0-3, in question order."},
                "notes": {"type": "string", "description": "Session notes."},
                "partner": {"type": "string", "description": "Partner who ran the session."},
            },
            "required": ["customer", "answers"],
        },
    },
    {
        "name": "get_assessment",
        "description": "Retrieve the latest full assessment for a customer, including recommended actions — use to draft the Readiness Report.",
        "inputSchema": {
            "type": "object",
            "properties": {"customer": {"type": "string", "description": "Customer name (partial match)."}},
            "required": ["customer"],
        },
    },
    {
        "name": "list_assessments",
        "description": "List saved audit assessments with scores and clinic triggers, optionally filtered by customer.",
        "inputSchema": {
            "type": "object",
            "properties": {"customer": {"type": "string", "description": "Optional filter."}},
        },
    },
    {
        "name": "sprint_status",
        "description": "Audit-motion sprint scoreboard: sessions run and clinic triggers vs the 10-week targets (15 accounts, 6-8 sessions, 3-4 qualified, 2 clinics).",
        "inputSchema": {"type": "object", "properties": {}},
    },
]

TOOL_HANDLERS = {
    "get_questionnaire": lambda a: get_questionnaire(),
    "score_assessment": lambda a: score_assessment(
        a["customer"], a["answers"], a.get("notes", ""), a.get("partner", "")),
    "get_assessment": lambda a: get_assessment(a["customer"]),
    "list_assessments": lambda a: list_assessments(a.get("customer", "")),
    "sprint_status": lambda a: sprint_status(),
}
