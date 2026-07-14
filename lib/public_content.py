"""Public Cisco content only — no credentials or tokens required."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
PUBLIC_CONTENT_PATH = ROOT / "fixtures" / "public_content.json"


def _load() -> dict[str, Any]:
    with open(PUBLIC_CONTENT_PATH) as f:
        return json.load(f)


def get_proof_point(
    topic: str,
    product: str | None = None,
    max_age_days: int = 365,
) -> dict[str, Any] | None:
    """Return a publicly citeable proof point, or None if unavailable."""
    data = _load()
    point = data.get("proof_points", {}).get(topic)
    if not point or point.get("classification") != "Public":
        return None
    if product and point.get("product") != product:
        return None
    if point.get("age_days", 0) > max_age_days:
        return None
    return {**point, "origin": "public"}


def get_product_summary(product: str) -> dict[str, Any] | None:
    """Return public product description from cisco.com portfolio pages."""
    data = _load()
    summary = data.get("product_summaries", {}).get(product)
    if not summary:
        return None
    return {**summary, "product": product, "origin": "public"}


def list_public_products() -> list[str]:
    data = _load()
    return sorted(data.get("product_summaries", {}).keys())


def get_competitive(competitor: str, motion: str | None = None) -> dict[str, Any] | None:
    data = _load()
    entry = data.get("competitive", {}).get(competitor)
    if not entry or entry.get("classification") != "Public":
        return None
    if motion and entry.get("motion") != motion:
        return None
    return {**entry, "origin": "public"}


def list_competitors() -> list[str]:
    data = _load()
    return sorted(data.get("competitive", {}).keys())


def get_offer(offer_type: str, product: str | None = None) -> dict[str, Any] | None:
    data = _load()
    entry = data.get("offers", {}).get(offer_type)
    if not entry or entry.get("classification") != "Public":
        return None
    result = {**entry, "origin": "public"}
    if product:
        result["product"] = product
    return result
