"""Tests for demo vs real data source resolution."""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import data_sources
from lib.gtm_tools import get_customer_context, list_customers


@pytest.fixture
def real_customers_file(tmp_path, monkeypatch):
    monkeypatch.setenv("GTM_FIXTURES_DIR", str(tmp_path))
    monkeypatch.setenv("GTM_DATA_MODE", "real")
    path = tmp_path / "real_customers.json"
    payload = {
        "customers": {
            "Maple Credit Union": {
                "customer_account": "Maple Credit Union",
                "industry": "Financial Services",
                "org_size": "500-1000",
                "current_infrastructure": "Meraki branches, ASA HQ",
                "cisco_technologies_proposed": ["Cisco Secure Access"],
                "opportunities": [],
            }
        }
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


class TestDataSources:
    def test_demo_mode_uses_acme(self, monkeypatch):
        monkeypatch.setenv("GTM_DATA_MODE", "demo")
        ctx = get_customer_context("Acme Financial Services")
        assert ctx is not None
        assert ctx["industry"] == "Financial Services"

    def test_real_mode_loads_custom_accounts(self, real_customers_file):
        ctx = get_customer_context("Maple Credit Union")
        assert ctx is not None
        assert ctx["org_size"] == "500-1000"
        accounts = list_customers()
        assert any(a["name"] == "Maple Credit Union" for a in accounts)

    def test_init_real_data_files(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GTM_FIXTURES_DIR", str(tmp_path))
        created = data_sources.init_real_data_files()
        assert (tmp_path / "real_customers.json").exists()
        assert len(created) >= 1
