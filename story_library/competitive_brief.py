"""Generate competitive briefs from confirmed JSON."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lib.gtm_tools import competitive_for_competitors
from story_library.canada_context import prepend_market_sections
from story_library.exporters import export_docx

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output"


def _slugify(text: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[-\s]+", "-", slug).strip("-")


def _format_list(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value if item)
    return str(value) if value else "Not provided"


def _competitive_sections(competitors: list[str]) -> list[tuple[str, str]]:
    sections = []
    for entry in competitive_for_competitors(competitors):
        name = entry.get("competitor", "Competitor")
        lines = [f"Motion: {entry.get('motion', 'N/A')}"]
        for point in entry.get("positioning", []):
            lines.append(f"- {point}")
        sections.append((f"vs {name}", "\n".join(lines)))
    return sections


def generate_competitive_brief(
    data: dict[str, Any],
    output_dir: Path | None = None,
) -> Path:
    out = output_dir or OUTPUT_DIR
    out.mkdir(parents=True, exist_ok=True)

    account = data.get("Customer Account Name", "competitive")
    technologies = data.get("Cisco Technologies to be Proposed", [])
    competitors = data.get("Competitors", [])
    slug = _slugify(account)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    path = out / f"{slug}-competitive-{timestamp}.docx"

    sections = [
        ("Account", account),
        ("Cisco Technologies in Scope", _format_list(technologies)),
        ("Competitors", _format_list(competitors)),
    ]
    sections.extend(_competitive_sections(competitors))
    sections = prepend_market_sections(sections)
    return export_docx(account, sections, path, "Competitive Brief")
