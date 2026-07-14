"""Tests for discovery prep assistant."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agents.discovery_assistant import DiscoveryAssistant

CUSTOMER = "Acme Financial Services"


def _complete_discovery(assistant: DiscoveryAssistant) -> dict:
    resp = assistant.start(CUSTOMER)
    while resp.awaiting_input and not resp.done:
        if resp.phase == "pain_points_confirm":
            resp = assistant.process_input("use")
        elif resp.phase == "technologies_confirm":
            resp = assistant.process_input("all")
        elif resp.phase == "review":
            resp = assistant.process_input("yes")
        elif resp.phase == "intake":
            resp = assistant.process_input("skip")
        else:
            resp = assistant.process_input("yes")
    return resp.json_output or {}


class TestDiscoveryAssistant:
    def test_start_prefills_acme(self):
        a = DiscoveryAssistant()
        resp = a.start(CUSTOMER)
        assert a.collected.get("industry") == "Financial Services"
        assert resp.phase in ("intake", "pain_points_confirm")

    def test_full_flow_produces_json(self):
        output = _complete_discovery(DiscoveryAssistant())
        assert output["Customer Account Name"] == CUSTOMER
        assert output["Discovery Questions"]
        assert output["Cisco Technologies to be Proposed"]
