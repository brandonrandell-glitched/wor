"""Generate proposal documents from confirmed intake JSON."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from story_library.canada_context import prepend_market_sections
from story_library.exporters import export_docx, export_pptx
from story_library.i18n import labels_for

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output"

from lib.gtm_tools import PROOF_TOPICS_BY_PRODUCT
from lib.public_content import get_offer

SECURITY_TECHNOLOGIES = {
    "Cisco Secure Access",
    "Cisco XDR",
    "Cisco Secure Endpoint",
    "Cisco Firewall",
    "Cisco Umbrella",
}

DEFAULT_COMPETITORS = ["Zscaler", "Palo Alto Networks"]


def _slugify(text: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[-\s]+", "-", slug).strip("-")


def _format_value(value: Any, not_provided: str) -> str:
    if value is None or value == "" or value == [] or value == "Skipped":
        return not_provided
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    return str(value)


def _build_sections(data: dict[str, Any]) -> list[tuple[str, str]]:
    language = data.get("Language", "English")
    labels = labels_for(language)
    account = data.get("Customer Account Name", "")
    industry = data.get("Industry", "")
    org_size = data.get("Organization Size", "")
    infrastructure = data.get("Current Infrastructure", "")
    pain_points = data.get("Customer Pain Points", "")
    technologies = data.get("Cisco Technologies to be Proposed", [])
    next_steps = data.get("Next Steps", "")
    deal_id = data.get("DEAL ID", "")
    form_length = data.get("Proposal Form Length", "long")
    is_short = form_length == "short"

    sections: list[tuple[str, str]] = [
        (labels["executive_summary"], _executive_summary(labels, account, pain_points, technologies, is_short)),
        (labels["customer_context"], _customer_context(labels, account, industry, org_size, infrastructure)),
        (labels["business_challenges"], _business_challenges(pain_points, is_short)),
        (labels["proposed_solution"], _proposed_solution(technologies, is_short, labels)),
    ]

    proof_section = _proof_points(technologies, labels)
    if proof_section:
        sections.append((labels["proof_points"], proof_section))

    competitive = _competitive_positioning(technologies, labels, data.get("Competitors"))
    if competitive:
        sections.append((labels["competitive_positioning"], competitive))

    offer_section = _commercial_offer(data, technologies, labels)
    if offer_section:
        sections.append((labels.get("commercial_offer", "Commercial Offer"), offer_section))

    sections.extend([
        (labels["recommended_next_steps"], _format_value(next_steps, labels["not_provided"])),
        (labels["deal_reference"], _format_value(deal_id, labels["not_provided"])),
    ])

    meddpicc = data.get("MEDDPICC")
    if isinstance(meddpicc, dict) and meddpicc:
        from lib.meddpicc import format_meddpicc_section
        sections.append(("MEDDPICC Qualification", format_meddpicc_section(meddpicc)))
    gaps = data.get("MEDDPICC Gaps")
    if gaps:
        sections.append((
            "MEDDPICC Gaps",
            "\n".join(f"- {g}" for g in gaps) if isinstance(gaps, list) else str(gaps),
        ))
    if data.get("CX Lifecycle Stage"):
        sections.append(("CX Lifecycle Stage", str(data["CX Lifecycle Stage"])))

    return sections


def _executive_summary(
    labels: dict[str, str],
    account: str,
    pain_points: str,
    technologies: Any,
    is_short: bool,
) -> str:
    tech_list = _format_value(technologies, labels["not_provided"])
    template = labels["exec_short"] if is_short else labels["exec_long"]
    return template.format(
        account=account,
        pain_points=pain_points or labels["not_provided"],
        technologies=tech_list,
    )


def _customer_context(
    labels: dict[str, str],
    account: str,
    industry: str,
    org_size: str,
    infrastructure: str,
) -> str:
    return (
        f"{labels['account']}: {account}\n"
        f"{labels['industry']}: {_format_value(industry, labels['not_provided'])}\n"
        f"{labels['organization_size']}: {_format_value(org_size, labels['not_provided'])}\n"
        f"{labels['current_infrastructure']}: {_format_value(infrastructure, labels['not_provided'])}"
    )


def _business_challenges(pain_points: str, is_short: bool) -> str:
    points = [p.strip() for p in pain_points.split(",") if p.strip()]
    if not points:
        return ""
    limit = 3 if is_short else len(points)
    return "\n".join(f"- {p}" for p in points[:limit])


def _proposed_solution(technologies: Any, is_short: bool, labels: dict[str, str]) -> str:
    from lib.public_content import get_product_summary

    techs = technologies if isinstance(technologies, list) else [technologies]
    techs = [t for t in techs if t]
    if not techs:
        return labels["not_provided"]
    lines = []
    for tech in techs:
        public = get_product_summary(tech)
        if is_short:
            lines.append(f"- {tech}")
        elif public:
            lines.append(f"- **{tech}**: {public['summary']}")
        else:
            lines.append(f"- **{tech}**: {labels['solution_fallback']}")
    return "\n".join(lines)


def _proof_points(technologies: Any, labels: dict[str, str]) -> str:
    from lib.public_content import get_proof_point

    techs = technologies if isinstance(technologies, list) else [technologies]
    lines = []
    for tech in techs:
        topic = PROOF_TOPICS_BY_PRODUCT.get(tech)
        if not topic:
            continue
        point = get_proof_point(topic)
        if not point:
            continue
        lines.append(
            f"- {point['value']} ({labels['source']}: {point['source']}, {point['product']})"
        )
    return "\n".join(lines)


def _competitive_positioning(
    technologies: Any,
    labels: dict[str, str],
    competitors: Any = None,
) -> str:
    from lib.public_content import get_competitive

    techs = technologies if isinstance(technologies, list) else [technologies]
    if not any(t in SECURITY_TECHNOLOGIES for t in techs):
        return ""

    names = competitors if isinstance(competitors, list) and competitors else DEFAULT_COMPETITORS
    lines = []
    for competitor in names:
        entry = get_competitive(competitor)
        if not entry:
            continue
        lines.append(f"**vs {competitor}**")
        for point in entry.get("positioning", []):
            lines.append(f"- {point}")
        lines.append("")
    return "\n".join(lines).strip()


def _commercial_offer(data: dict[str, Any], technologies: Any, labels: dict[str, str]) -> str:
    techs = technologies if isinstance(technologies, list) else [technologies]
    if not any(t in SECURITY_TECHNOLOGIES for t in techs):
        return ""
    offer_type = data.get("Offer Type", "security-suite")
    offer = get_offer(offer_type)
    if not offer:
        return ""
    lines = [offer.get("scope", "")]
    if offer.get("economics"):
        lines.append(offer["economics"])
    return "\n".join(line for line in lines if line)


def generate_proposal(
    data: dict[str, Any],
    output_dir: Path | None = None,
) -> Path:
    """Generate a proposal file from confirmed intake JSON. Returns the output path."""
    out = output_dir or OUTPUT_DIR
    out.mkdir(parents=True, exist_ok=True)

    account = data.get("Customer Account Name", "proposal")
    fmt = data.get("Proposal Output Format", "word").lower()
    language = data.get("Language", "English")
    labels = labels_for(language)
    slug = _slugify(account)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    sections = prepend_market_sections(_build_sections(data), data.get("Industry", ""))

    if fmt == "ppt":
        filename = f"{slug}-{timestamp}.pptx"
        path = out / filename
        return export_pptx(account, sections, path, labels["proposal_title"])

    filename = f"{slug}-{timestamp}.docx"
    path = out / filename
    return export_docx(account, sections, path, labels["proposal_title"])
