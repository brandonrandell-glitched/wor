"""Unified GTM tool layer — shared by agents and MCP servers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from lib.public_content import (
    get_competitive,
    get_offer,
    get_proof_point,
    get_product_summary,
    list_competitors,
)

ROOT = Path(__file__).resolve().parent.parent
SALESFORCE_FIXTURE = ROOT / "fixtures" / "salesforce_customer.json"
TOOLS_FIXTURE = ROOT / "fixtures" / "proposal_tools_data.json"

PROOF_TOPICS_BY_PRODUCT = {
    "Cisco Secure Access": "zero-trust-adoption",
    "Cisco XDR": "deployment-speed",
    "Cisco Networking": "secure-networking",
    "Cisco Firewall": "secure-networking",
}


def _strip_internal(data: Any) -> Any:
    if isinstance(data, dict):
        return {k: _strip_internal(v) for k, v in data.items() if k != "savm_id"}
    if isinstance(data, list):
        return [_strip_internal(item) for item in data]
    return data


def get_customer_context(customer_account: str) -> dict[str, Any] | None:
    if not SALESFORCE_FIXTURE.exists():
        return None
    with open(SALESFORCE_FIXTURE) as f:
        data = json.load(f)
    if data.get("customer_account") != customer_account:
        return None
    return _strip_internal(data)


def suggest_opportunities(
    customer_account: str,
    batch_offset: int = 0,
    batch_size: int = 10,
) -> dict[str, Any]:
    data = get_customer_context(customer_account)
    if not data:
        return {"opportunities": [], "total": 0, "has_more": False}
    all_opps = data.get("opportunities", [])
    batch = all_opps[batch_offset : batch_offset + batch_size]
    return {
        "opportunities": batch,
        "total": len(all_opps),
        "has_more": batch_offset + batch_size < len(all_opps),
        "next_offset": batch_offset + batch_size if batch_offset + batch_size < len(all_opps) else None,
    }


def extract_pain_points(
    current_infrastructure: str,
    industry: str | None = None,
    organization_size: str | None = None,
) -> dict[str, Any]:
    with open(TOOLS_FIXTURE) as f:
        data = json.load(f)

    text = current_infrastructure.lower()
    if industry:
        text += " " + industry.lower()
    if organization_size:
        text += " " + organization_size.lower()

    found = []
    for pattern in data["pain_point_patterns"]:
        if any(kw in text for kw in pattern["keywords"]):
            found.extend(pattern["pain_points"])

    seen: set[str] = set()
    unique = []
    for pp in found:
        if pp not in seen:
            seen.add(pp)
            unique.append(pp)

    return {"pain_points": unique, "count": len(unique)}


def recommend_products(
    pain_points: list[str],
    existing_technologies: list[str] | None = None,
) -> dict[str, Any]:
    with open(TOOLS_FIXTURE) as f:
        data = json.load(f)

    recs = set(existing_technologies or [])
    mapping = data["product_recommendations"]

    for pp in pain_points:
        for product in mapping.get(pp, []):
            recs.add(product)

    if not recs:
        recs = set(data["default_recommendations"])

    return {"recommendations": sorted(recs), "count": len(recs)}


def recommend_platform_story(
    pain_points: list[str],
    existing_technologies: list[str] | None = None,
    entry_pillar: str = "security",
) -> dict[str, Any]:
    """Product map by pillar with narrative mode based on entry pillar."""
    with open(TOOLS_FIXTURE) as f:
        data = json.load(f)

    pillars: dict[str, set[str]] = {
        "security": set(),
        "networking": set(),
        "data_center": set(),
        "collaboration": set(),
    }
    pull = data.get("platform_pull_through", {})
    for pp in pain_points:
        entry = pull.get(pp, {})
        for pillar, products in entry.items():
            key = pillar if pillar != "data_center" else "data_center"
            if key in pillars:
                pillars[key].update(products)

    entry = (entry_pillar or "security").strip().lower().replace("_", "-")
    if entry in ("data-center", "datacenter"):
        entry = "data-center"

    sec_recs = recommend_products(pain_points, existing_technologies)
    pillars["security"].update(sec_recs["recommendations"])

    thread = "security-led"

    if entry == "security":
        story_mode = "security-led"
        if any("east-west" in p or "segmentation" in p.lower() for p in pain_points):
            thread = data.get("platform_threads", {}).get("refresh", thread)
        elif any("shadow" in p.lower() or "cloud" in p.lower() for p in pain_points):
            thread = data.get("platform_threads", {}).get("ai", thread)
        guidance = (
            "Default security-led. Expand to networking, DC, and collab when customer names "
            "refresh, sprawl, hybrid pain, or AI plans. Switch to security-only when sponsor "
            "is CISO-only, budget is a security line-item, or deal is Qualified on a named "
            "security motion."
        )
    elif entry in ("networking", "data-center", "collaboration"):
        story_mode = "pillar-first"
        thread = {"networking": "network-first", "data-center": "dc-first",
                  "collaboration": "collab-first"}.get(entry, thread)
        guidance = (
            f"Answer as {entry} SME first — lead with products in by_pillar for that pillar. "
            "Pivot to security or other pillars only when segmentation, compliance, identity, "
            "or isolation pain surfaces."
        )
    else:
        story_mode = "security-led"
        guidance = "Lead with security; expand pillars when pain points open the thread."

    result: dict[str, Any] = {
        "entry_pillar": entry,
        "story_mode": story_mode,
        "narrative_thread": thread,
        "by_pillar": {k: sorted(v) for k, v in pillars.items()},
        "guidance": guidance,
        "routing": {
            "stay_security_only_when": [
                "CISO or security lead is sole sponsor",
                "Budget is a security line-item",
                "Deal is Qualified on a named security motion",
            ],
            "expand_from_security_when": [
                "Customer names network or campus refresh",
                "Platform sprawl (SaaS, collab, or cloud)",
                "Hybrid workforce or access pain",
                "AI or GPU plans surfacing",
            ],
            "pillar_first_pivot_when": [
                "Segmentation, identity, or policy raised in a network call",
                "Compliance, fraud, or data handling raised in collab",
                "Workload isolation or shadow AI raised in DC",
            ],
        },
    }
    if story_mode == "pillar-first":
        pkey = "data_center" if entry == "data-center" else entry
        result["lead_products"] = result["by_pillar"].get(pkey, [])
    elif story_mode == "security-only":
        result["lead_products"] = result["by_pillar"].get("security", [])
    else:
        result["lead_products"] = result["by_pillar"].get("security", [])

    return result


def proof_point_for_product(product: str) -> dict[str, Any] | None:
    topic = PROOF_TOPICS_BY_PRODUCT.get(product)
    if not topic:
        return None
    return get_proof_point(topic, product=product)


def competitive_for_competitors(competitors: list[str]) -> list[dict[str, Any]]:
    results = []
    for name in competitors:
        entry = get_competitive(name)
        if entry:
            results.append(entry)
    return results


def offer_for_type(offer_type: str = "security-suite") -> dict[str, Any] | None:
    return get_offer(offer_type)


def discovery_questions(pain_points: list[str], industry: str | None = None) -> list[str]:
    questions = [
        "What are your top three security outcomes for the next 12 months?",
        "How do you measure success for detection, response, and access control today?",
        "Which teams own policy definition versus day-to-day operations?",
    ]
    if industry:
        questions.insert(0, f"What industry-specific compliance or risk drivers are shaping {industry} priorities?")
    for pp in pain_points[:3]:
        questions.append(f"How is '{pp}' impacting operations and business risk today?")
    questions.append(
        "If we solve the security gap first, what infrastructure refresh or platform "
        "decision is already on your calendar this year?"
    )
    return questions


def meddpicc_gaps(
    meddpicc: dict[str, str] | None,
    lifecycle_stage: str = "analyze",
    pain_points: list[str] | None = None,
) -> dict[str, Any]:
    from lib.meddpicc import recommend_meddpicc_gaps
    return recommend_meddpicc_gaps(meddpicc, lifecycle_stage, pain_points)
