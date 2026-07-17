"""Tests for lifecycle and MEDDPICC modules."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "mcp-framework" / "servers"))

from lib.lifecycle import lifecycle_for_deal_stage, partner_goal_for_lifecycle
from lib.meddpicc import parse_meddpicc_input, recommend_meddpicc_gaps
import cisco_content as cc
import partner_ops as po


class TestLifecycle:
    def test_stage_mapping(self):
        assert lifecycle_for_deal_stage(10) == "analyze"
        assert lifecycle_for_deal_stage(50) == "land"
        assert partner_goal_for_lifecycle("land") == "Thought Leader"

    def test_get_content_matrix_analyze(self):
        result = cc.get_content_matrix(cx_lifecycle="analyze")
        data = __import__("json").loads(result)
        assert data["count"] >= 1
        assert data["entries"][0]["partner_goal"] == "Strategic Consultant"

    def test_get_lifecycle_guide(self):
        data = __import__("json").loads(cc.get_lifecycle_guide())
        assert "journey_steps" in data
        assert len(data["journey_steps"]) == 9

    def test_lifecycle_view(self):
        data = __import__("json").loads(po.lifecycle_view())
        assert "by_lifecycle" in data


class TestMeddpicc:
    def test_parse_meddpicc(self):
        parsed = parse_meddpicc_input("Metrics: Reduce MTTR 30%\nChampion: CISO delegate")
        assert parsed["metrics"] == "Reduce MTTR 30%"
        assert "CISO" in parsed["champion"]

    def test_gaps_for_analyze(self):
        gaps = recommend_meddpicc_gaps({}, "analyze", ["alert fatigue"])
        assert gaps["complete_for_stage"] is False
        assert any(g["field"] == "metrics" for g in gaps["gaps"])
