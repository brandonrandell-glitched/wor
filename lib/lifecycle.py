"""Customer lifecycle (LAND/ADOPT/EXPAND/RENEW) and deal-stage mapping."""

from __future__ import annotations

from typing import Any

# Partner-ops deal stage (10–90) → CX lifecycle short id
STAGE_TO_LIFECYCLE: dict[int, str] = {
    10: "analyze",
    25: "place",
    50: "land",
    75: "adopt",
    90: "renew",
}

LIFECYCLE_LABELS: dict[str, str] = {
    "analyze": "ANALYZE / NEED",
    "place": "PLACE / EVALUATE",
    "land": "LAND / SELECT / ALIGN",
    "adopt": "ADOPT / ONBOARD / IMPLEMENT",
    "expand": "EXPAND / OPTIMIZE",
    "renew": "RENEW / RECOMMEND / ADVOCATE",
}

PARTNER_GOALS: dict[str, str] = {
    "analyze": "Strategic Consultant",
    "place": "Trusted Advisor",
    "land": "Thought Leader",
    "adopt": "Reliable Operator",
    "expand": "Strategic Services Partner",
    "renew": "Trusted Partner",
}


def lifecycle_for_deal_stage(stage: int) -> str:
    return STAGE_TO_LIFECYCLE.get(stage, "analyze")


def lifecycle_label(lifecycle_id: str) -> str:
    return LIFECYCLE_LABELS.get(lifecycle_id, lifecycle_id)


def partner_goal_for_lifecycle(lifecycle_id: str) -> str:
    return PARTNER_GOALS.get(lifecycle_id, "")


def enrich_deal_row(deal: dict[str, Any]) -> dict[str, Any]:
    """Add cx_lifecycle and partner_goal from deal stage if not set."""
    lc = deal.get("cx_lifecycle") or lifecycle_for_deal_stage(deal.get("stage", 10))
    out = dict(deal)
    out["cx_lifecycle"] = lc
    out["cx_lifecycle_label"] = lifecycle_label(lc)
    out["partner_goal"] = deal.get("partner_goal") or partner_goal_for_lifecycle(lc)
    return out
