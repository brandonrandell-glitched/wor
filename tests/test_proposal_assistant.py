"""Tests for the proposal-building assistant."""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agents.proposal_assistant import (
    Phase,
    ProposalAssistant,
    SUMMARY_ORDER,
)
from lib.gtm_tools import extract_pain_points, recommend_products, suggest_opportunities


CUSTOMER = "Acme Financial Services"
UNKNOWN_CUSTOMER = "New Prospect Corp"


@pytest.fixture
def assistant():
    a = ProposalAssistant()
    a.start(CUSTOMER)
    return a


@pytest.fixture
def blank_assistant():
    a = ProposalAssistant()
    a.start(UNKNOWN_CUSTOMER)
    return a


class TestToolFunctions:
    def test_extract_pain_points_finds_matches(self):
        result = extract_pain_points(
            "Hybrid cloud with legacy on-prem firewalls and fragmented endpoint protection",
            industry="Financial Services",
        )
        assert result["count"] > 0
        assert isinstance(result["pain_points"], list)

    def test_recommend_products_from_pain_points(self):
        pain_points = [
            "Slow incident detection and response times",
            "Alert fatigue from disconnected security consoles",
        ]
        result = recommend_products(pain_points)
        assert "Cisco XDR" in result["recommendations"]

    def test_suggest_opportunities_batches(self):
        result = suggest_opportunities(CUSTOMER, batch_offset=0, batch_size=10)
        assert len(result["opportunities"]) == 10
        assert result["has_more"] is True

        result2 = suggest_opportunities(CUSTOMER, batch_offset=10, batch_size=10)
        assert len(result2["opportunities"]) == 2
        assert result2["has_more"] is False

    def test_suggest_opportunities_no_savm_id(self):
        result = suggest_opportunities(CUSTOMER)
        for opp in result["opportunities"]:
            assert "savm_id" not in opp


class TestConversationFlow:
    def test_greeting_shows_prefilled_data(self, assistant):
        a = ProposalAssistant()
        resp = a.start(CUSTOMER)
        assert CUSTOMER in resp.message
        assert "Financial Services" in resp.message

    def test_skip_optional_industry(self, blank_assistant):
        blank_assistant.process_input("skip")
        assert "industry" in blank_assistant.skipped

    def test_pain_points_extraction_triggered(self, blank_assistant):
        blank_assistant.process_input("skip")  # industry
        blank_assistant.process_input("skip")  # org size
        resp = blank_assistant.process_input(
            "Hybrid cloud with legacy on-prem firewalls and fragmented endpoint protection"
        )
        assert resp.phase == Phase.PAIN_POINTS_CONFIRM
        assert resp.tool_call is not None
        assert resp.tool_call["tool"] == "extract_pain_points"

    def test_full_flow_to_json(self, assistant):
        steps = [
            "use",
            "use",
            "Schedule executive briefing and technical deep-dive",
            "yes",
            "skip",
            "yes",
        ]
        resp = None
        for step in steps:
            resp = assistant.process_input(step)
        assert resp.done is True
        assert resp.json_output is not None
        assert resp.json_output["Customer Account Name"] == CUSTOMER
        assert resp.json_output["DEAL ID"] == "OPP-2025-78432"
        assert isinstance(resp.json_output["Cisco Technologies to be Proposed"], list)

    def test_summary_field_order(self, assistant):
        steps = ["use", "use", "Follow up next week", "yes", "skip"]
        for step in steps:
            resp = assistant.process_input(step)
        assert resp.phase == Phase.REVIEW
        labels = [label for _, label in SUMMARY_ORDER]
        assert list(resp.summary.keys()) == labels

    def test_review_edit_before_confirm(self, assistant):
        steps = ["use", "use", "Initial next steps", "yes", "skip"]
        for step in steps:
            resp = assistant.process_input(step)
        resp = assistant.process_input("update next steps to schedule demo")
        assert resp.phase == Phase.REVIEW
        assert "schedule demo" in resp.summary["Next Steps"]

    def test_off_topic_redirect(self):
        msg = ProposalAssistant.redirect_off_topic("the weather")
        assert "weather" in msg
        assert "proposal building" in msg.lower()

    def test_no_savm_id_in_json(self, assistant):
        steps = ["use", "use", "Next steps here", "yes", "skip", "yes"]
        resp = None
        for step in steps:
            resp = assistant.process_input(step)
        output_str = json.dumps(resp.json_output)
        assert "savm_id" not in output_str
        assert "SAVM" not in output_str


class TestValidation:
    def test_invalid_language_rejected(self, blank_assistant):
        blank_assistant.process_input("skip")
        blank_assistant.process_input("skip")
        blank_assistant.process_input("Legacy firewalls")
        blank_assistant.process_input("use")
        blank_assistant.process_input("all")
        blank_assistant.process_input("Follow up next week")
        blank_assistant.process_input("skip")
        resp = blank_assistant.process_input("Klingon")
        assert "valid language" in resp.message.lower()

    def test_invalid_format_rejected(self, blank_assistant):
        blank_assistant.process_input("skip")
        blank_assistant.process_input("skip")
        blank_assistant.process_input("Legacy firewalls")
        blank_assistant.process_input("use")
        blank_assistant.process_input("all")
        blank_assistant.process_input("Follow up next week")
        blank_assistant.process_input("skip")
        blank_assistant.process_input("English")
        resp = blank_assistant.process_input("pdf")
        assert "word" in resp.message.lower() or "ppt" in resp.message.lower()
