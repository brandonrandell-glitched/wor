"""Generate discovery prep briefs from confirmed JSON."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from story_library.exporters import export_docx

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output"


def _slugify(text: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[-\s]+", "-", slug).strip("-")


def _format_list(value: Any) -> str:
    if isinstance(value, list):
        return "\n".join(f"- {item}" for item in value if item)
    return str(value) if value else "Not provided"


def generate_discovery_brief(
    data: dict[str, Any],
    output_dir: Path | None = None,
) -> Path:
    out = output_dir or OUTPUT_DIR
    out.mkdir(parents=True, exist_ok=True)

    account = data.get("Customer Account Name", "discovery")
    slug = _slugify(account)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    path = out / f"{slug}-discovery-{timestamp}.docx"

    sections = [
        ("Account Context", (
            f"Account: {account}\n"
            f"Industry: {data.get('Industry', 'Not provided')}\n"
            f"Organization Size: {data.get('Organization Size', 'Not provided')}\n"
            f"Current Infrastructure: {data.get('Current Infrastructure', 'Not provided')}"
        )),
        ("Customer Pain Points", data.get("Customer Pain Points", "Not provided")),
        (
            "Recommended Cisco Technologies",
            _format_list(data.get("Cisco Technologies to be Proposed", [])),
        ),
        (
            "Discovery Questions",
            _format_list(data.get("Discovery Questions", [])),
        ),
    ]
    return export_docx(account, sections, path, "Discovery Prep Brief")
