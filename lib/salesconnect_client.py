"""SalesConnect data access — public content only."""

from __future__ import annotations

from typing import Any

from lib.public_content import get_proof_point as _get_public_proof_point


def get_proof_point(
    topic: str,
    access_token: str | None = None,
    product: str | None = None,
    max_age_days: int = 365,
) -> dict[str, Any] | None:
    """Return public proof points only. Tokens are ignored."""
    return _get_public_proof_point(topic, product=product, max_age_days=max_age_days)
