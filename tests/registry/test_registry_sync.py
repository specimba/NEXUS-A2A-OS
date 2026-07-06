"""Drift and consumer-sync tests for the generated registry artifacts.

Proves that config/models.registry.json and its four generated consumers
(Node config.generated.ts, quota limits, Chimera cloud profiles, Ollama
map) agree — and that the Python runtime actually consumes them.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
REGISTRY = json.loads((REPO / "config" / "models.registry.json").read_text(encoding="utf-8"))


class TestDrift:
    def test_artifacts_in_sync_with_registry(self):
        """Byte-equality drift gate: regenerating must be a no-op."""
        result = subprocess.run(
            [sys.executable, str(REPO / "scripts" / "gen_model_registry.py"), "--check"],
            capture_output=True, text=True, cwd=REPO, timeout=60,
        )
        assert result.returncode == 0, f"artifacts stale:\n{result.stdout}\n{result.stderr}"


class TestQuotaConsumer:
    def test_context_clamp_covers_frontier_models(self):
        from nexus_os.relay.quota import KNOWN_CONTEXT_LIMITS

        for model_id in (
            "zai-org/GLM-5.2",
            "moonshotai/Kimi-K2.7-Code",
            "deepseek-ai/DeepSeek-V4-Flash",
            "deepseek-ai/deepseek-v4-pro",
            "stepfun-ai/step-3.7-flash",
            "MiniMaxAI/MiniMax-M3",
            "Qwen/Qwen3-235B-A22B",
        ):
            assert model_id in KNOWN_CONTEXT_LIMITS, f"no context clamp for {model_id}"

    def test_collisions_resolve_conservatively(self):
        """Legacy said minimax-m3=524288, registry says 1048576 — the
        smaller window must win so the clamp never overshoots."""
        from nexus_os.relay.quota import KNOWN_CONTEXT_LIMITS

        assert KNOWN_CONTEXT_LIMITS["minimaxai/minimax-m3"] == 524288

    def test_clamp_still_works_end_to_end(self):
        from nexus_os.relay.quota import max_completion_budget

        budget = max_completion_budget("zai-org/GLM-5.2", input_tokens=1000)
        assert budget is not None and budget > 0


class TestChimeraConsumer:
    def test_retired_api_models_gone(self):
        from nexus_os.twave.chimera_router_v2 import DEFAULT_PROFILES

        names = {p.name for p in DEFAULT_PROFILES}
        assert "gpt-4-turbo" not in names
        assert "claude-3-5-sonnet" not in names

    def test_generated_frontier_profiles_present(self):
        from nexus_os.twave.chimera_router_v2 import DEFAULT_PROFILES, Tier

        cloud = {p.name for p in DEFAULT_PROFILES if p.tier == Tier.CLOUD}
        assert "zai-org/GLM-5.2" in cloud            # siliconflow, chat-verified live
        assert "deepseek-ai/DeepSeek-V4-Flash" in cloud
        # Kimi-K2.7-Code's only lane (baseten) is suspended (0 credit,
        # operator 2026-07-02) — a dead frontier must NOT linger in the
        # routable cloud tier.
        assert "moonshotai/Kimi-K2.7-Code" not in cloud

    def test_local_hand_authored_profiles_survive(self):
        from nexus_os.twave.chimera_router_v2 import DEFAULT_PROFILES

        names = {p.name for p in DEFAULT_PROFILES}
        assert "functiongemma-270m" in names
        assert "qwen2.5-7b-instruct-q4_k_m" in names


class TestOllamaConsumer:
    def test_generated_map_reaches_relay(self):
        from nexus_os.relay.ollama_map_generated import OLLAMA_MODEL_MAP

        assert OLLAMA_MODEL_MAP.get("functiongemma-270m") == "functiongemma:latest"
        assert OLLAMA_MODEL_MAP.get("VibeThinker-3B") == "vibethinker-3b"

    def test_cloud_models_listed(self):
        from nexus_os.relay.ollama_map_generated import OLLAMA_CLOUD_MODELS

        assert "minimax-m3:cloud" in OLLAMA_CLOUD_MODELS
        assert "qwen3-coder:480b" in OLLAMA_CLOUD_MODELS


class TestGeneratedTs:
    def test_ts_contains_baseten_frontiers(self):
        ts = (REPO / "src" / "lib" / "modelrelay" / "config.generated.ts").read_text(encoding="utf-8")
        assert "baseten/zai-org/GLM-5.2" in ts
        assert "baseten/moonshotai/Kimi-K2.7-Code" in ts
        assert "nvidia/stepfun-ai/step-3.7-flash" in ts

    def test_ts_marks_zai_deprecated(self):
        ts = (REPO / "src" / "lib" / "modelrelay" / "config.generated.ts").read_text(encoding="utf-8")
        assert '"zai"' in ts.split("DEPRECATED_PROVIDERS")[1].split("\n")[0]


class TestDomainMappingConsumer:
    def test_generated_entries_are_role_compatible_and_active(self):
        """Every generated domain entry must carry a role matching its
        domain and be registry-active on an active provider."""
        from nexus_os.gmr.domain_mapping_generated import GENERATED_DOMAIN_MAPPING

        DOMAIN_ROLES = {
            "code": ("code",), "reasoning": ("reasoning",),
            "research": ("frontier",), "fast": ("fast",),
            "security": ("judge", "guard"), "general": ("frontier",),
        }
        by_id = {}
        for m in REGISTRY["models"]:
            by_id.setdefault(m["id"], []).append(m)
        prov_status = {k: v["status"] for k, v in REGISTRY["providers"].items()}

        for domain, cfg in GENERATED_DOMAIN_MAPPING.items():
            for entry in cfg["primary"]:
                candidates = [
                    m for m in by_id.get(entry["model"], [])
                    if m["provider"] == entry["provider"]
                ]
                assert candidates, f"{domain}: {entry['model']} not in registry"
                m = candidates[0]
                assert m["status"] == "active"
                assert prov_status[m["provider"]] == "active"
                assert any(r in m.get("roles", []) for r in DOMAIN_ROLES[domain]), (
                    f"{domain}: {m['id']} roles {m.get('roles')} lack {DOMAIN_ROLES[domain]}"
                )

    def test_merged_mapping_keeps_locals_and_gains_frontiers(self):
        from nexus_os.gmr.domain_mapping import DOMAIN_MAPPING

        code_models = [e["model"] for e in DOMAIN_MAPPING["code"]["primary"]]
        assert "osman-coder" in code_models
        # Family-level assertion: the domain list dedups per model FAMILY,
        # so whichever provider's GLM-5.2 id wins the tier race satisfies it.
        assert any("glm-5.2" in m.lower() for m in code_models)
        # stale display-string literals must be gone
        for domain in DOMAIN_MAPPING.values():
            for e in domain["primary"]:
                assert e["model"] != "Trinity Large Preview"
                assert e["model"] != "GLM 5"

    def test_fast_lane_locals_lead(self):
        from nexus_os.gmr.domain_mapping import DOMAIN_MAPPING

        first = DOMAIN_MAPPING["fast"]["primary"][0]
        assert first["status"] == "local"
