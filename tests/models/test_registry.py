"""tests/models/test_registry.py — Model Provider Registry Tests"""

import json
import os
import tempfile
import pytest
from nexus_os.models.registry import (
    ModelRegistry,
    ModelEntry,
    DomainConfig,
    ProviderInfo,
    LocalModelInfo,
    get_registry,
)


@pytest.fixture
def registry():
    return ModelRegistry()


@pytest.fixture
def sample_json():
    data = {
        "domains": {
            "code": {
                "description": "Code generation",
                "primary": [
                    {"model": "osman-coder", "provider": "ollama", "tier": 40, "latency_ms": 50, "cost_per_1m": 0, "status": "local"},
                    {"model": "Codestral", "provider": "codestral", "tier": 53, "latency_ms": 464, "cost_per_1m": 2.0, "status": "up"},
                ],
                "fallback_chain": ["osman-coder", "Codestral", "GPT OSS 20B"],
                "recommended_for": ["implementation", "debugging"],
            },
            "fast": {
                "description": "Hot path",
                "primary": [
                    {"model": "Bonsai 4B IQ1_S", "provider": "ollama", "tier": 40, "latency_ms": 15, "cost_per_1m": 0, "status": "local"},
                ],
                "fallback_chain": ["Bonsai 4B", "osman-fast"],
                "recommended_for": ["hot_path"],
                "requirement": {"max_latency_ms": 100, "prefer_local": True},
            },
        },
        "providers": {
            "ollama": {"models": 15, "status": "local"},
            "codestral": {"models": 1, "status": "healthy"},
        },
        "local_models": {
            "count": 2,
            "models": [
                {"name": "osman-coder", "size_gb": 4.7, "latency_ms": 50, "specialty": "code"},
                {"name": "Bonsai-4B-IQ1_S", "size_gb": 0.9, "latency_ms": 15, "specialty": "edge"},
            ],
            "total_size_gb": 5.6,
            "zero_cost": True,
            "always_available": True,
        },
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        path = f.name
    yield path
    os.unlink(path)


class TestModelEntry:
    def test_from_dict(self):
        entry = ModelEntry.from_dict({"model": "gpt-4o", "provider": "openai", "tier": 90, "latency_ms": 500, "cost_per_1m": 5.0, "status": "up"})
        assert entry.name == "gpt-4o"
        assert entry.provider == "openai"
        assert entry.tier == 90
        assert entry.latency_ms == 500

    def test_from_dict_defaults(self):
        entry = ModelEntry.from_dict({"model": "test"})
        assert entry.provider == "unknown"
        assert entry.tier == 0

    def test_to_dict(self):
        entry = ModelEntry("test", "ollama", 50, 100, 1.0, "up")
        d = entry.to_dict()
        assert d["name"] == "test"
        assert d["provider"] == "ollama"
        assert d["tier"] == 50


class TestDomainConfig:
    def test_from_dict(self):
        cfg = DomainConfig.from_dict({
            "description": "test",
            "primary": [{"model": "m1", "provider": "p1", "tier": 50, "latency_ms": 100, "cost_per_1m": 1.0}],
            "fallback_chain": ["m1", "m2"],
            "recommended_for": ["test"],
        })
        assert cfg.description == "test"
        assert len(cfg.primary) == 1
        assert cfg.fallback_chain == ["m1", "m2"]

    def test_from_dict_requirement(self):
        cfg = DomainConfig.from_dict({
            "description": "test",
            "requirement": {"max_latency_ms": 100, "prefer_local": True},
        })
        assert cfg.requirement == {"max_latency_ms": 100, "prefer_local": True}


class TestProviderInfo:
    def test_provider_info(self):
        p = ProviderInfo("test", models=["m1"], status="healthy")
        assert p.name == "test"
        assert p.models == ["m1"]
        assert p.status == "healthy"
        assert p.priority == 999

    def test_to_dict(self):
        p = ProviderInfo("test", priority=50)
        d = p.to_dict()
        assert d["name"] == "test"
        assert d["priority"] == 50


class TestModelRegistryLoad:
    def test_load_empty(self, registry):
        assert registry.list_domains() == []
        assert registry.list_models() == []

    def test_load_from_json(self, registry, sample_json):
        registry.load(sample_json)
        assert len(registry.list_domains()) == 2
        assert len(registry.list_models()) == 3
        assert len(registry.list_providers()) == 2

    def test_load_from_json_domains(self, registry, sample_json):
        registry.load(sample_json)
        code = registry.get_domain("code")
        assert code is not None
        assert code.description == "Code generation"
        assert len(code.primary) == 2
        assert code.primary[0].name == "osman-coder"
        assert code.fallback_chain == ["osman-coder", "Codestral", "GPT OSS 20B"]

    def test_load_from_json_providers(self, registry, sample_json):
        registry.load(sample_json)
        ollama = registry.get_provider("ollama")
        assert ollama is not None
        assert ollama.status == "local"

    def test_load_from_json_local_models(self, registry, sample_json):
        registry.load(sample_json)
        local = registry.list_local_models()
        assert len(local) == 2
        osman = registry.get_local_model("osman-coder")
        assert osman is not None
        assert osman.size_gb == 4.7


class TestModelRegistryRegistration:
    def test_register_provider(self, registry):
        p = registry.register_provider("test_provider", models=["m1"], base_url="http://test", priority=10, status="healthy")
        assert p.name == "test_provider"
        assert registry.get_provider("test_provider") is p
        assert p.priority == 10

    def test_register_provider_update(self, registry):
        registry.register_provider("p1", models=["m1"])
        p2 = registry.register_provider("p1", models=["m2"], priority=5)
        assert "m1" in p2.models
        assert "m2" in p2.models
        assert p2.priority == 5

    def test_register_model(self, registry):
        entry = registry.register_model("test-model", "ollama", tier=70, latency_ms=100, cost_per_1m=2.0, status="up")
        assert registry.get_model("test-model") is entry
        assert entry.provider == "ollama"
        # Provider should be auto-created
        assert registry.get_provider("ollama") is not None

    def test_register_model_updates_provider(self, registry):
        registry.register_provider("p1", models=["m1"])
        registry.register_model("m2", "p1")
        p = registry.get_provider("p1")
        assert "m2" in p.models

    def test_register_domain(self, registry):
        models = [ModelEntry("m1", "p1", 50, 100, 1.0)]
        cfg = registry.register_domain("test_domain", "test", models=models, fallback_chain=["m1", "m2"])
        assert registry.get_domain("test_domain") is cfg
        assert cfg.description == "test"
        assert registry.get_model("m1") is not None

    def test_register_local_model(self, registry):
        info = registry.register_local_model("test-local", 2.5, 30, "fast")
        assert registry.get_local_model("test-local") is info
        assert info.specialty == "fast"

    def test_register_provider_invalid_status(self, registry):
        p = registry.register_provider("test", status="invalid_status")
        assert p.status == "unknown"


class TestModelRegistrySelection:
    def test_select_model_basic(self, registry, sample_json):
        registry.load(sample_json)
        model = registry.select_model("code")
        assert model is not None
        # Codestral (tier 53) > osman-coder (tier 40)
        assert model.name == "Codestral"

    def test_select_model_prefer_local(self, registry, sample_json):
        registry.load(sample_json)
        model = registry.select_model("code", prefer_local=True)
        assert model is not None
        assert model.name == "osman-coder"
        assert model.status == "local"

    def test_select_model_min_tier(self, registry, sample_json):
        registry.load(sample_json)
        model = registry.select_model("code", min_tier=50)
        assert model is not None
        assert model.tier >= 50
        assert model.name == "Codestral"

    def test_select_model_max_cost(self, registry, sample_json):
        registry.load(sample_json)
        model = registry.select_model("code", max_cost=1.0)
        assert model is not None
        assert model.cost_per_1m <= 1.0
        assert model.name == "osman-coder"

    def test_select_model_unknown_domain(self, registry):
        model = registry.select_model("nonexistent")
        assert model is None

    def test_select_model_fast_requirements(self, registry, sample_json):
        registry.load(sample_json)
        model = registry.select_model("fast")
        assert model is not None
        assert model.latency_ms <= 50  # Local preference should pick Bonsai


class TestModelRegistrySearch:
    def test_search_by_name(self, registry, sample_json):
        registry.load(sample_json)
        results = registry.search_models(query="coder")
        assert len(results) >= 1
        assert any("coder" in m.name.lower() for m in results)

    def test_search_by_provider(self, registry, sample_json):
        registry.load(sample_json)
        results = registry.search_models(provider="ollama")
        assert len(results) >= 1
        assert all(m.provider == "ollama" for m in results)

    def test_search_by_tier(self, registry, sample_json):
        registry.load(sample_json)
        results = registry.search_models(min_tier=50)
        assert len(results) >= 1
        assert all(m.tier >= 50 for m in results)

    def test_search_by_status(self, registry, sample_json):
        registry.load(sample_json)
        results = registry.search_models(status="local")
        assert all(m.status == "local" for m in results)

    def test_search_no_results(self, registry, sample_json):
        registry.load(sample_json)
        results = registry.search_models(query="zzz_nonexistent_123")
        assert results == []

    def test_search_sorted_by_tier(self, registry, sample_json):
        registry.load(sample_json)
        results = registry.search_models()
        tiers = [m.tier for m in results]
        assert tiers == sorted(tiers, reverse=True)


class TestModelRegistryGetFallback:
    def test_get_fallback_chain(self, registry, sample_json):
        registry.load(sample_json)
        chain = registry.get_fallback_chain("code")
        assert chain == ["osman-coder", "Codestral", "GPT OSS 20B"]

    def test_get_fallback_chain_missing(self, registry):
        assert registry.get_fallback_chain("missing") == []


class TestModelRegistryList:
    def test_list_providers_sorted(self, registry, sample_json):
        registry.load(sample_json)
        providers = registry.list_providers()
        # Both have priority 999 (default from JSON load)
        assert len(providers) == 2

    def test_list_models(self, registry, sample_json):
        registry.load(sample_json)
        models = registry.list_models()
        assert len(models) == 3

    def test_list_domains(self, registry, sample_json):
        registry.load(sample_json)
        domains = registry.list_domains()
        assert sorted(domains) == sorted(["code", "fast"])


class TestModelRegistryStats:
    def test_get_stats(self, registry, sample_json):
        registry.load(sample_json)
        stats = registry.get_stats()
        assert stats["domains"] == 2
        assert stats["providers"] == 2
        assert stats["models"] == 3
        assert stats["local_models"] == 2

    def test_get_stats_empty(self, registry):
        stats = registry.get_stats()
        assert stats["domains"] == 0
        assert stats["loaded_from"] is None


class TestModelRegistrySerialization:
    def test_to_json(self, registry, sample_json):
        registry.load(sample_json)
        output = registry.to_json()
        data = json.loads(output)
        assert "domains" in data
        assert "code" in data["domains"]
        assert data["model_count"] == 3

    def test_load_default_nonexistent(self):
        registry = ModelRegistry.load_default()
        # It may or may not find the file depending on CWD
        assert isinstance(registry, ModelRegistry)


class TestModelRegistryIntegration:
    def test_singleton_consistent(self):
        r1 = get_registry()
        r2 = get_registry()
        assert r1 is r2

    def test_full_lifecycle(self, registry, sample_json):
        registry.load(sample_json)
        # Register a new provider
        registry.register_provider("new-provider", models=["new-model"], base_url="http://new", priority=1, status="healthy")
        # Register a new model
        registry.register_model("new-model", "new-provider", tier=99, latency_ms=200)
        # Select best for code
        model = registry.select_model("code")
        assert model is not None
        # Search new model
        results = registry.search_models(query="new")
        assert len(results) >= 1
        # Check stats
        stats = registry.get_stats()
        assert stats["providers"] >= 3
        assert stats["models"] >= 4
