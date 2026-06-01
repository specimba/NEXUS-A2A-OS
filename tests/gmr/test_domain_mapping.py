"""tests/gmr/test_domain_mapping.py — Domain mapping structure validation"""
import pytest

from nexus_os.gmr.domain_mapping import DOMAIN_MAPPING


class TestDomainMapping:
    EXPECTED_DOMAINS = ["code", "reasoning", "research", "fast", "security", "general"]

    def test_all_expected_domains_present(self):
        for domain in self.EXPECTED_DOMAINS:
            assert domain in DOMAIN_MAPPING, f"Missing domain: {domain}"

    def test_each_domain_has_primary_and_fallback(self):
        for domain, data in DOMAIN_MAPPING.items():
            assert "primary" in data, f"{domain} missing 'primary'"
            assert "fallback_chain" in data, f"{domain} missing 'fallback_chain'"
            assert isinstance(data["primary"], list)
            assert isinstance(data["fallback_chain"], list)

    def test_primary_entries_have_required_fields(self):
        required = {"model", "provider", "tier", "latency_ms", "cost_per_1m", "status"}
        for domain, data in DOMAIN_MAPPING.items():
            for entry in data["primary"]:
                missing = required - set(entry.keys())
                assert not missing, f"{domain}/{entry.get('model', '?')} missing: {missing}"

    def test_code_domain_has_local_primary(self):
        code_models = DOMAIN_MAPPING["code"]["primary"]
        local_models = [m for m in code_models if m["cost_per_1m"] == 0]
        assert len(local_models) >= 1

    def test_fast_domain_all_local(self):
        fast_models = DOMAIN_MAPPING["fast"]["primary"]
        for m in fast_models:
            assert m["cost_per_1m"] == 0, f"{m['model']} is not free in fast domain"

    def test_fallback_chains_non_empty(self):
        for domain, data in DOMAIN_MAPPING.items():
            assert len(data["fallback_chain"]) > 0, f"{domain} has empty fallback_chain"
