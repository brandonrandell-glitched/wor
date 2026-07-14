"""Tests for shared GTM tools."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib.gtm_tools import (
    competitive_for_competitors,
    discovery_questions,
    extract_pain_points,
    get_customer_context,
    offer_for_type,
    recommend_products,
    suggest_opportunities,
)

CUSTOMER = "Acme Financial Services"


class TestGTMContext:
    def test_get_customer_context_strips_savm_id(self):
        ctx = get_customer_context(CUSTOMER)
        assert ctx is not None
        assert "savm_id" not in ctx
        for opp in ctx.get("opportunities", []):
            assert "savm_id" not in opp

    def test_get_customer_context_unknown(self):
        assert get_customer_context("Unknown Corp") is None


class TestGTMTools:
    def test_extract_pain_points(self):
        result = extract_pain_points(
            "Hybrid cloud with legacy on-prem firewalls and fragmented endpoint protection",
            industry="Financial Services",
        )
        assert result["count"] > 0

    def test_recommend_products(self):
        pains = [
            "Slow incident detection and response times",
            "Alert fatigue from disconnected security consoles",
        ]
        result = recommend_products(pains)
        assert "Cisco XDR" in result["recommendations"]

    def test_suggest_opportunities_batches(self):
        result = suggest_opportunities(CUSTOMER, batch_offset=0, batch_size=10)
        assert len(result["opportunities"]) == 10
        assert result["has_more"] is True

    def test_discovery_questions(self):
        questions = discovery_questions(["Alert fatigue"], "Financial Services")
        assert any("compliance" in q.lower() or "industry" in q.lower() for q in questions)

    def test_competitive_for_competitors(self):
        entries = competitive_for_competitors(["Zscaler"])
        assert len(entries) == 1
        assert entries[0]["classification"] == "Public"

    def test_offer_for_type(self):
        offer = offer_for_type("security-suite")
        assert offer is not None
        assert offer["classification"] == "Public"
