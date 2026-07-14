"""Tests for public content (no credentials)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib.public_content import (
    get_competitive,
    get_offer,
    get_product_summary,
    get_proof_point,
    list_competitors,
    list_public_products,
)


class TestPublicContent:
    def test_public_proof_point_only(self):
        point = get_proof_point("zero-trust-adoption")
        assert point is not None
        assert point["classification"] == "Public"
        assert point["origin"] == "public"

    def test_internal_or_confidential_excluded(self):
        assert get_proof_point("margin-guidance") is None

    def test_product_summary(self):
        summary = get_product_summary("Cisco XDR")
        assert summary is not None
        assert "public_url" in summary
        assert "Extended detection" in summary["summary"]

    def test_list_products(self):
        products = list_public_products()
        assert "Cisco Secure Access" in products
        assert "Cisco XDR" in products

    def test_competitive_content(self):
        entry = get_competitive("Zscaler")
        assert entry is not None
        assert len(entry["positioning"]) >= 2
        assert entry["classification"] == "Public"

    def test_competitive_list(self):
        competitors = list_competitors()
        assert "Palo Alto Networks" in competitors

    def test_offer_content(self):
        offer = get_offer("security-suite")
        assert offer is not None
        assert "scope" in offer
