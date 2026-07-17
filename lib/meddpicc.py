"""MEDDPICC qualification helpers for discovery and proposal workflows."""

from __future__ import annotations

import re
from typing import Any

MEDDPICC_FIELDS = [
    "metrics",
    "economic_buyer",
    "decision_criteria",
    "decision_process",
    "paper_process",
    "identify_pain",
    "champion",
    "competition",
]

FIELD_LABELS = {
    "metrics": "Metrics",
    "economic_buyer": "Economic Buyer",
    "decision_criteria": "Decision Criteria",
    "decision_process": "Decision Process",
    "paper_process": "Paper Process",
    "identify_pain": "Identify Pain",
    "champion": "Champion",
    "competition": "Competition",
}

DISCOVERY_QUESTIONS: dict[str, str] = {
    "metrics": "Which KPIs or metrics define success for this initiative in the next 12 months?",
    "economic_buyer": "Who has financial authority to sign — and what strategic outcome do they care about?",
    "decision_criteria": "What technical and business criteria will the evaluation team score against?",
    "decision_process": "What are the validation milestones and who must align before purchase?",
    "paper_process": "What procurement, legal, or security review steps apply before PO?",
    "identify_pain": "What happens if this problem is not solved in the next two quarters?",
    "champion": "Who inside the account will advocate for this solution — and what do they need to win?",
    "competition": "What alternatives or status quo are you being measured against?",
}

STAGE_FOCUS: dict[str, list[str]] = {
    "analyze": ["metrics", "identify_pain"],
    "place": ["decision_criteria", "competition", "economic_buyer"],
    "land": ["economic_buyer", "decision_process", "identify_pain"],
    "adopt": ["metrics", "identify_pain", "champion"],
    "expand": ["metrics", "identify_pain", "champion"],
    "renew": ["champion", "metrics", "competition"],
}


def parse_meddpicc_input(text: str) -> dict[str, str]:
    """Parse 'Metrics: ... Economic Buyer: ...' or line-per-field input."""
    out: dict[str, str] = {}
    if not text or text.strip().lower() in ("skip", "skip meddpicc", "none"):
        return out

    aliases = {
        "metrics": "metrics",
        "metric": "metrics",
        "economic buyer": "economic_buyer",
        "eb": "economic_buyer",
        "decision criteria": "decision_criteria",
        "criteria": "decision_criteria",
        "decision process": "decision_process",
        "process": "decision_process",
        "paper process": "paper_process",
        "paper": "paper_process",
        "pain": "identify_pain",
        "identify pain": "identify_pain",
        "champion": "champion",
        "competition": "competition",
        "competitor": "competition",
    }

    for line in text.splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        key_part, _, val = line.partition(":")
        key = aliases.get(key_part.strip().lower())
        if key and val.strip():
            out[key] = val.strip()
    return out


def meddpicc_questions(lifecycle_stage: str = "analyze") -> list[str]:
    focus = STAGE_FOCUS.get(lifecycle_stage, STAGE_FOCUS["analyze"])
    return [DISCOVERY_QUESTIONS[f] for f in focus if f in DISCOVERY_QUESTIONS]


def recommend_meddpicc_gaps(
    meddpicc: dict[str, str] | None,
    lifecycle_stage: str = "analyze",
    pain_points: list[str] | None = None,
) -> dict[str, Any]:
    data = meddpicc or {}
    focus = STAGE_FOCUS.get(lifecycle_stage, STAGE_FOCUS["analyze"])
    gaps = []
    for field in focus:
        if not data.get(field):
            if field == "identify_pain" and pain_points:
                continue
            gaps.append({
                "field": field,
                "label": FIELD_LABELS[field],
                "question": DISCOVERY_QUESTIONS[field],
            })

    filled = {k: v for k, v in data.items() if v}
    return {
        "lifecycle_stage": lifecycle_stage,
        "focus_fields": focus,
        "filled": filled,
        "gaps": gaps,
        "complete_for_stage": len(gaps) == 0,
        "guidance": (
            "SE objective: align technical proof to business metrics and decision criteria — "
            "not a feature tour. Fill gaps before executive or RFP milestones."
        ),
    }


def format_meddpicc_section(meddpicc: dict[str, str]) -> str:
    if not meddpicc:
        return "Not captured"
    lines = []
    for key in MEDDPICC_FIELDS:
        if meddpicc.get(key):
            lines.append(f"- **{FIELD_LABELS[key]}:** {meddpicc[key]}")
    return "\n".join(lines) if lines else "Not captured"
