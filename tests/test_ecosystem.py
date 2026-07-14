"""Tests for discovery and competitive document generation."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from story_library.competitive_brief import generate_competitive_brief
from story_library.discovery_brief import generate_discovery_brief

SAMPLE_DISCOVERY = {
    "Customer Account Name": "Acme Financial Services",
    "Industry": "Financial Services",
    "Organization Size": "5000+",
    "Current Infrastructure": "Hybrid cloud",
    "Customer Pain Points": "Alert fatigue, slow response",
    "Cisco Technologies to be Proposed": ["Cisco XDR", "Cisco Secure Access"],
    "Discovery Questions": ["What are your top outcomes?", "How do you measure success?"],
}

SAMPLE_COMPETITIVE = {
    "Customer Account Name": "Acme Financial Services",
    "Cisco Technologies to be Proposed": ["Cisco XDR"],
    "Competitors": ["Zscaler"],
}


class TestEcosystemGenerators:
    def test_generate_discovery_brief(self, tmp_path):
        path = generate_discovery_brief(SAMPLE_DISCOVERY, output_dir=tmp_path)
        assert path.exists()
        assert path.suffix == ".docx"

    def test_generate_competitive_brief(self, tmp_path):
        path = generate_competitive_brief(SAMPLE_COMPETITIVE, output_dir=tmp_path)
        assert path.exists()
        assert path.suffix == ".docx"
