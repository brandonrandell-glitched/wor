"""Tests for cross-workflow handoffs."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agents.competitive_assistant import CompetitiveAssistant
from agents.discovery_assistant import DiscoveryAssistant
from agents.proposal_assistant import ProposalAssistant
from agents.router import GTMRouter
from lib.handoff import discovery_to_handoff, merge_handoff_for

CUSTOMER = "Acme Financial Services"

DISCOVERY_JSON = {
    "Customer Account Name": CUSTOMER,
    "Industry": "Financial Services",
    "Organization Size": "5000-10000",
    "Current Infrastructure": "Hybrid cloud with legacy on-prem firewalls",
    "Customer Pain Points": "Slow incident detection, Alert fatigue",
    "Cisco Technologies to be Proposed": ["Cisco Secure Access", "Cisco XDR", "Cisco Duo"],
    "MEDDPICC": {"metrics": "Reduce MTTR 50%"},
    "CX Lifecycle Stage": "analyze",
}

COMPETITIVE_JSON = {
    "Customer Account Name": CUSTOMER,
    "Cisco Technologies to be Proposed": ["Cisco Secure Access", "Cisco XDR"],
    "Competitors": ["Palo Alto Networks", "Fortinet"],
}


class TestHandoffMapping:
    def test_discovery_to_handoff_maps_fields(self):
        handoff = discovery_to_handoff(DISCOVERY_JSON)
        assert handoff["industry"] == "Financial Services"
        assert len(handoff["customer_pain_points"]) == 2
        assert "Cisco Duo" in handoff["cisco_technologies"]
        assert handoff["meddpicc"]["metrics"] == "Reduce MTTR 50%"

    def test_merge_for_proposal_includes_competitors(self):
        prior = [
            {"workflow": "discovery", "json": DISCOVERY_JSON},
            {"workflow": "competitive", "json": COMPETITIVE_JSON},
        ]
        merged = merge_handoff_for("proposal", prior)
        assert "discovery" in merged["_handoff_sources"]
        assert "competitive" in merged["_handoff_sources"]
        assert merged["competitors"] == ["Palo Alto Networks", "Fortinet"]


class TestAssistantHandoff:
    def test_competitive_skips_technology_step_from_discovery(self):
        handoff = merge_handoff_for(
            "competitive",
            [{"workflow": "discovery", "json": DISCOVERY_JSON}],
        )
        a = CompetitiveAssistant()
        resp = a.start(CUSTOMER, handoff=handoff)
        assert resp.phase == "competitors"
        assert "Cisco Duo" in resp.message

    def test_proposal_carries_pain_points_and_competitors(self):
        prior = [
            {"workflow": "discovery", "json": DISCOVERY_JSON},
            {"workflow": "competitive", "json": COMPETITIVE_JSON},
        ]
        handoff = merge_handoff_for("proposal", prior)
        a = ProposalAssistant()
        resp = a.start(CUSTOMER, handoff=handoff)
        assert "Continuing from prior workflow" in resp.message
        assert a.collected.get("customer_pain_points")
        assert a.collected.get("competitors") == ["Palo Alto Networks", "Fortinet"]


class TestRouterContinue:
    def test_continue_discovery_to_competitive(self):
        router = GTMRouter()
        d = DiscoveryAssistant()
        d.start(CUSTOMER)
        while not d._final_json:
            if d.phase == "pain_points_confirm":
                d.process_input("use")
            elif d.phase == "technologies_confirm":
                d.process_input("all")
            elif d.phase == "meddpicc_capture":
                d.process_input("skip")
            elif d.phase == "review":
                d.process_input("yes")
            else:
                d.process_input("skip")
        router._sessions["s1"] = {
            "workflow": "discovery",
            "assistant": d,
            "customer_account": CUSTOMER,
            "prior_outputs": [],
        }
        opts = router.get_continue_options("s1")
        assert any(o["id"] == "competitive" for o in opts)
        resp = router.continue_workflow("s1", "competitive", "s2")
        assert resp.workflow == "competitive"
        assert resp.phase == "competitors"
