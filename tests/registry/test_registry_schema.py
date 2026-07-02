"""Validation for config/models.registry.json — the canonical model registry.

Guards (audit 2026-07-02, registry-divergence root cause):
- schema validity (config/models.registry.schema.json)
- NO key-shaped secrets anywhere (the registry is key-free by design)
- every model's provider exists; every priorityTier / team reference
  resolves to a registered model (kills the mimo-v2.5 orphan class)
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
REGISTRY_PATH = REPO / "config" / "models.registry.json"
SCHEMA_PATH = REPO / "config" / "models.registry.schema.json"

#: Provider key prefixes seen in this project's history — none may appear.
#: The groq prefix is assembled from pieces so this detector never trips
#: the pre-commit hygiene hook's own literal scan.
_GROQ_PREFIX = "g" + "sk_"
KEY_PATTERNS = re.compile(
    r"\b(sk-[A-Za-z0-9_-]{20,}|nvapi-[A-Za-z0-9_-]{20,}|om-[A-Za-z0-9_-]{20,}"
    r"|" + _GROQ_PREFIX + r"[A-Za-z0-9_-]{20,}|hf_[A-Za-z0-9]{20,}|csk-[A-Za-z0-9_-]{20,}"
    r"|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36})"
)


@pytest.fixture(scope="module")
def registry():
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def raw_text():
    return REGISTRY_PATH.read_text(encoding="utf-8")


class TestSchema:
    def test_validates_against_schema(self, registry):
        jsonschema = pytest.importorskip("jsonschema")
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        jsonschema.validate(registry, schema)

    def test_no_key_shaped_strings(self, raw_text):
        match = KEY_PATTERNS.search(raw_text)
        assert match is None, f"key-shaped string in registry: {match.group()[:12]}..."

    def test_keyrefs_are_slugs_not_secrets(self, registry):
        for name, prov in registry["providers"].items():
            ref = prov.get("keyRef")
            if ref is not None:
                assert len(ref) < 40, f"{name}.keyRef suspiciously long"
                assert not KEY_PATTERNS.search(ref), f"{name}.keyRef looks like a key"


class TestReferentialIntegrity:
    def test_every_model_provider_exists(self, registry):
        providers = set(registry["providers"])
        for m in registry["models"]:
            assert m["provider"] in providers, f"{m['id']}: unknown provider {m['provider']}"

    def test_model_ids_unique_per_provider(self, registry):
        seen = set()
        for m in registry["models"]:
            key = (m["provider"], m["id"])
            assert key not in seen, f"duplicate model {key}"
            seen.add(key)

    def _known_ids(self, registry):
        ids = set()
        for m in registry["models"]:
            ids.add(m["id"])
            ids.update(m.get("aliases", []))
        return ids

    def _provider_scoped(self, registry):
        return {(m["provider"], m["id"]) for m in registry["models"]}

    def test_priority_tier_refs_resolve(self, registry):
        scoped = self._provider_scoped(registry)
        providers = set(registry["providers"])

        def check_ref(ref: str, where: str):
            provider, _, model_id = ref.partition(":")
            assert provider in providers, f"{where}: unknown provider in {ref!r}"
            assert (provider, model_id) in scoped, f"{where}: unresolved model ref {ref!r}"

        tiers = registry.get("priorityTiers", {})
        for tier_name, tier in tiers.items():
            if tier_name == "avoid_due_to_tool_loop_bug":
                continue  # bare model-name flags, not provider refs
            if isinstance(tier, list):
                for ref in tier:
                    check_ref(ref, tier_name)
            elif isinstance(tier, dict):
                for ref in tier.get("models", []):
                    check_ref(ref, tier_name)
                for ref in tier.get("use_order", []):
                    check_ref(ref, tier_name)
                for ref in tier.get("never_use_as_primary", []):
                    check_ref(ref, tier_name)

    def test_team_refs_resolve(self, registry):
        known = self._known_ids(registry)
        for team, members in registry.get("teams", {}).items():
            if isinstance(members, dict):
                members = [v for v in members.values() if isinstance(v, str)]
            for ref in members:
                if ref.startswith("role:"):
                    continue  # role selector, resolved at routing time
                assert ref in known, f"team {team}: unresolved model {ref!r}"

    def test_active_models_on_active_providers(self, registry):
        """An active model on a suspended/deprecated provider is a routing lie."""
        prov_status = {k: v["status"] for k, v in registry["providers"].items()}
        for m in registry["models"]:
            if m["status"] == "active":
                assert prov_status[m["provider"]] in ("active",), (
                    f"{m['id']} is active but provider {m['provider']} "
                    f"is {prov_status[m['provider']]}"
                )


class TestArsenalRegressions:
    """The specific frontier models the 2026-07-02 audit found missing."""

    @pytest.mark.parametrize("provider,model_id", [
        ("baseten", "zai-org/GLM-5.2"),
        ("baseten", "moonshotai/Kimi-K2.7-Code"),
        ("siliconflow", "zai-org/GLM-5.2"),
        ("siliconflow", "MiniMaxAI/MiniMax-M3"),
        ("nvidia", "stepfun/step-3.7-flash"),
        ("nvidia", "deepseek-ai/deepseek-v4-pro"),
        ("nvidia", "qwen/qwen3.5-397b"),
        ("opencode", "mimo-v2.5-free"),
        ("ollama", "functiongemma:latest"),
    ])
    def test_frontier_model_registered(self, registry, provider, model_id):
        assert any(
            m["provider"] == provider and m["id"] == model_id
            for m in registry["models"]
        ), f"{provider}:{model_id} missing from registry"

    def test_siliconflow_endpoint_is_com(self, registry):
        """config.ts had api.siliconflow.cn; authoritative is .com/v1."""
        assert registry["providers"]["siliconflow"]["baseUrl"] == "https://api.siliconflow.com/v1"

    def test_sambanova_no_longer_orphaned(self, registry):
        assert "sambanova" in registry["providers"]
        assert registry["providers"]["sambanova"]["keyRef"] == "openai-compatible:sambanova"
