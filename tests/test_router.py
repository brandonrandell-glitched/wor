"""Tests for GTM workflow router."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agents.router import GTMRouter

CUSTOMER = "Acme Financial Services"


class TestGTMRouter:
    def test_list_workflows(self):
        router = GTMRouter()
        workflows = router.list_workflows()
        ids = {w["id"] for w in workflows}
        assert ids == {"proposal", "discovery", "competitive"}

    def test_start_proposal(self):
        router = GTMRouter()
        resp = router.start("proposal", CUSTOMER, "s1")
        assert resp.workflow == "proposal"
        assert CUSTOMER in resp.message

    def test_start_discovery(self):
        router = GTMRouter()
        resp = router.start("discovery", CUSTOMER, "s2")
        assert resp.workflow == "discovery"

    def test_unknown_workflow_raises(self):
        router = GTMRouter()
        try:
            router.start("unknown", CUSTOMER, "s3")
            assert False, "expected ValueError"
        except ValueError:
            pass
