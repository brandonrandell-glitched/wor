"""Tests for document export and i18n."""

import sys
from pathlib import Path
from zipfile import ZipFile

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from story_library.generator import generate_proposal
from story_library.i18n import labels_for


SAMPLE_DATA = {
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


class TestDocumentExport:
    def test_generate_docx(self, tmp_path):
        path = generate_proposal(SAMPLE_DATA, output_dir=tmp_path)
        assert path.suffix == ".docx"
        assert path.exists()
        with ZipFile(path) as zf:
            assert "word/document.xml" in zf.namelist()

    def test_generate_pptx(self, tmp_path):
        data = {**SAMPLE_DATA, "Proposal Output Format": "ppt"}
        path = generate_proposal(data, output_dir=tmp_path)
        assert path.suffix == ".pptx"
        assert path.exists()
        with ZipFile(path) as zf:
            assert "[Content_Types].xml" in zf.namelist()

    def test_german_labels(self, tmp_path):
        data = {**SAMPLE_DATA, "Language": "German"}
        path = generate_proposal(data, output_dir=tmp_path)
        with ZipFile(path) as zf:
            xml = zf.read("word/document.xml").decode("utf-8")
        assert "Zusammenfassung" in xml
        assert "Acme Financial Services" in xml

    def test_competitive_section_in_docx(self, tmp_path):
        path = generate_proposal(SAMPLE_DATA, output_dir=tmp_path)
        with ZipFile(path) as zf:
            xml = zf.read("word/document.xml").decode("utf-8")
        assert "Competitive Positioning" in xml
        assert "Zscaler" in xml

    def test_proof_points_in_docx(self, tmp_path):
        path = generate_proposal(SAMPLE_DATA, output_dir=tmp_path)
        with ZipFile(path) as zf:
            xml = zf.read("word/document.xml").decode("utf-8")
        assert "Proof Points" in xml
        assert "78%" in xml or "prioritizing faster" in xml


class TestI18n:
    @pytest.mark.parametrize(
        "language",
        ["English", "German", "French", "Spanish", "Italian", "Japanese", "Simplified Chinese"],
    )
    def test_all_languages_have_core_labels(self, language):
        labels = labels_for(language)
        for key in (
            "proposal_title",
            "executive_summary",
            "customer_context",
            "proposed_solution",
            "recommended_next_steps",
        ):
            assert labels[key]
