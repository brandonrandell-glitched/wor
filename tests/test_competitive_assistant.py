"""Tests for competitive brief assistant."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agents.competitive_assistant import CompetitiveAssistant

CUSTOMER = "Acme Financial Services"


class TestCompetitiveAssistant:
    def test_start_prefills_technologies(self):
        a = CompetitiveAssistant()
        resp = a.start(CUSTOMER)
        assert "use" in resp.message.lower() or "technologies" in resp.message.lower()

    def test_full_flow_produces_json(self):
        a = CompetitiveAssistant()
        a.start(CUSTOMER)
        resp = a.process_input("use")
        resp = a.process_input("all")
        resp = a.process_input("yes")
        assert resp.done
        assert resp.json_output["Competitors"]
        assert resp.json_output["Cisco Technologies to be Proposed"]
