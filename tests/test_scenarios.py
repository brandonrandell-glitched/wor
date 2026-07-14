"""Additional scenario and integration tests."""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agents.proposal_assistant import Phase, ProposalAssistant
from story_library.generator import generate_proposal


CUSTOMER = "Acme Financial Services"


class TestScenarios:
    def test_blank_customer_full_flow(self):
        a = ProposalAssistant()
        a.start("New Prospect Corp")
        steps = [
            "skip",  # industry
            "skip",  # org size
            "Legacy firewalls and manual VPN management",
            "use",  # pain points
            "all",  # technologies
            "Schedule discovery workshop",
            "skip",  # deal id
            "English",
            "word",
            "short",
            "yes",
        ]
        resp = None
        for step in steps:
            resp = a.process_input(step)
        assert resp.done
        assert resp.json_output["Customer Account Name"] == "New Prospect Corp"
        assert resp.json_output["Proposal Form Length"] == "short"

    def test_ppt_format_skips_form_length(self):
        a = ProposalAssistant()
        a.start("New Prospect Corp")
        steps = [
            "skip",
            "skip",
            "Cloud-first with basic firewall",
            "use",
            "all",
            "Send follow-up email",
            "skip",
            "English",
            "ppt",
            "yes",
        ]
        resp = None
        for step in steps:
            resp = a.process_input(step)
        assert resp.json_output["Proposal Output Format"] == "ppt"
        assert "Proposal Form Length" not in resp.json_output

    def test_deal_batch_more(self):
        a = ProposalAssistant()
        a.start(CUSTOMER)
        a.process_input("use")
        a.process_input("use")
        a.process_input("Next steps")
        a.collected.pop("deal_id", None)
        a.post_infra_index = 1
        a.phase = Phase.GREETING
        resp = a._advance_post_infra()
        assert resp.phase == Phase.DEAL_SELECT
        resp = a.process_input("more")
        assert resp.phase == Phase.DEAL_SELECT
        assert "OPP-2024" in resp.message

    def test_pain_points_replace(self):
        a = ProposalAssistant()
        a.start("New Prospect Corp")
        a.process_input("skip")
        a.process_input("skip")
        a.process_input("Legacy firewalls and endpoint gaps")
        a.process_input("replace")
        resp = a.process_input("Manual patching delays, No central logging")
        assert "Manual patching delays" in a.collected["customer_pain_points"]


class TestProposalGenerator:
    def test_generate_word_proposal(self, tmp_path):
        data = {
            "Customer Account Name": "Acme Financial Services",
            "Industry": "Financial Services",
            "Organization Size": "5000-10000",
            "Current Infrastructure": "Hybrid cloud",
            "Customer Pain Points": "Slow incident detection, Alert fatigue",
            "Cisco Technologies to be Proposed": ["Cisco XDR", "Cisco Secure Access"],
            "Next Steps": "Schedule briefing",
            "DEAL ID": "OPP-2025-78432",
            "Language": "English",
            "Proposal Output Format": "word",
            "Proposal Form Length": "long",
        }
        path = generate_proposal(data, output_dir=tmp_path)
        assert path.suffix == ".docx"
        assert path.exists()

    def test_generate_ppt_proposal(self, tmp_path):
        data = {
            "Customer Account Name": "Acme Financial Services",
            "Customer Pain Points": "Alert fatigue",
            "Cisco Technologies to be Proposed": ["Cisco XDR"],
            "Next Steps": "Demo",
            "DEAL ID": "OPP-1",
            "Language": "English",
            "Proposal Output Format": "ppt",
        }
        path = generate_proposal(data, output_dir=tmp_path)
        assert path.suffix == ".pptx"
        assert path.exists()

    def test_proof_points_included_when_available(self, tmp_path):
        data = {
            "Customer Account Name": "Test Corp",
            "Customer Pain Points": "Zero trust gap",
            "Cisco Technologies to be Proposed": ["Cisco Secure Access", "Cisco XDR"],
            "Next Steps": "Workshop",
            "DEAL ID": "OPP-1",
            "Language": "English",
            "Proposal Output Format": "word",
            "Proposal Form Length": "long",
        }
        path = generate_proposal(data, output_dir=tmp_path)
        from zipfile import ZipFile
        with ZipFile(path) as zf:
            xml = zf.read("word/document.xml").decode("utf-8")
        assert "Proof Points" in xml
        assert "78%" in xml or "prioritizing faster" in xml


class TestMCPIntegration:
    def test_salesforce_mcp_tools_list(self):
        import subprocess

        proc = subprocess.run(
            ["python3", str(ROOT / "mcp_servers" / "salesforce_mcp.py")],
            input='{"jsonrpc":"2.0","id":1,"method":"tools/list"}\n',
            capture_output=True,
            text=True,
            timeout=5,
            cwd=str(ROOT),
        )
        result = json.loads(proc.stdout.strip())
        names = [t["name"] for t in result["result"]["tools"]]
        assert "get_customer_context" in names
        assert "suggest_opportunities" in names

    def test_proposal_tools_extract(self):
        import subprocess

        call = json.dumps({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "extract_pain_points",
                "arguments": {
                    "current_infrastructure": "legacy on-prem firewalls and fragmented endpoint protection"
                },
            },
        })
        proc = subprocess.run(
            ["python3", str(ROOT / "mcp_servers" / "proposal_tools_mcp.py")],
            input=call + "\n",
            capture_output=True,
            text=True,
            timeout=5,
            cwd=str(ROOT),
        )
        result = json.loads(proc.stdout.strip())
        pain_points = result["result"]["pain_points"]
        assert len(pain_points) > 0
