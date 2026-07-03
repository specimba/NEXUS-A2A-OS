from __future__ import annotations

from nexus_os.bridge.secrets import PROVIDER_CONFIG
from nexus_os.gmr.domain_mapping import DOMAIN_MAPPING
from upload.config import FALLBACK_CHAINS, PROVIDERS
from upload.gateway import ModelRelayGateway
from upload.intern_ai_lanes import INTERN_AI_LANES, resolve_intern_ai_key
from upload.models_registry import ModelsRegistry
from upload.quota_guard import QuotaGuard

from nexus_os.model_relay.provider_budget import ProviderBudgetLedger

class _Response:
    status_code = 200
    ok = True
    text = "{}"

    def json(self):
        return {
            "choices": [{"message": {"content": "OK"}}],
            "usage": {"total_tokens": 2},
        }


def test_internai_provider_is_registered_across_python_layers():
    assert PROVIDER_CONFIG["internai"]["base_url"] == "https://chat.intern-ai.org.cn/api/v1"
    assert PROVIDER_CONFIG["internai"]["rpm_limit"] == 30
    assert "INTERN_OPENCODE_API_KEY" in PROVIDER_CONFIG["internai"]["key_env_order"]
    assert PROVIDERS["internai"]["chat_path"] == "/chat/completions"
    assert PROVIDERS["internai"]["auth_type"] == "bearer"
    assert "intern-s2-preview" in FALLBACK_CHAINS["reasoning"]
    # Membership, not position: DOMAIN_MAPPING is now generated from the
    # canonical registry with locals-first ordering (SLM-team posture);
    # intern-s2 remains a reasoning-domain member via its reasoning role.
    reasoning_models = [e["model"] for e in DOMAIN_MAPPING["reasoning"]["primary"]]
    assert "intern-s2-preview" in reasoning_models
    assert DOMAIN_MAPPING["security"]["primary"][0]["provider"] == "internai"


def test_internai_models_expose_agent_capabilities():
    registry = ModelsRegistry()
    models = {model.model_id: model for model in registry.get_by_provider("internai")}

    assert {"internai/intern-s2-preview", "internai/intern-latest", "internai/internvl3.5-latest"} <= set(models)
    assert models["internai/intern-s2-preview"].context_window == 256000
    assert models["internai/intern-s2-preview"].supports_function_calling
    assert models["internai/internvl3.5-latest"].supports_vision


def test_internai_quota_is_initialized(tmp_path):
    ledger = ProviderBudgetLedger(tmp_path / "quota.sqlite3")
    quota = QuotaGuard(budget_ledger=ledger).get_quota("internai")

    assert quota is not None
    assert quota.quota_type == "tokens"
    assert quota.daily_limit is None
    assert quota.budget_verified is False
    assert quota.is_exhausted is True


def test_internai_lane_key_resolution_prefers_surface_specific_key(monkeypatch):
    monkeypatch.setenv("INTERN_API_KEY", "default-token")
    monkeypatch.setenv("INTERN_API_KEY_2", "shared-external-token")
    monkeypatch.setenv("INTERN_OPENCODE_API_KEY", "opencode-token")

    assert INTERN_AI_LANES["opencode"].default_model == "intern-s2-preview"
    assert resolve_intern_ai_key("opencode").env_var == "INTERN_OPENCODE_API_KEY"
    assert resolve_intern_ai_key("opencode").value == "opencode-token"
    assert resolve_intern_ai_key("kilocode").env_var == "INTERN_API_KEY_2"


def test_gateway_sends_internai_bearer_auth_and_thinking_mode(monkeypatch, tmp_path):
    captured = {}

    def fake_post(url, headers, json, timeout):
        captured.update({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return _Response()

    monkeypatch.setenv("INTERN_API_KEY", "test-intern-token")
    monkeypatch.setattr("requests.post", fake_post)

    gateway = ModelRelayGateway(ProviderBudgetLedger(tmp_path / "quota.sqlite3"))
    result = gateway._call_provider(
        "internai/intern-s2-preview",
        "internai",
        [{"role": "user", "content": "ping"}],
        {"max_tokens": 8, "temperature": 0, "stop": ["unused"]},
    )

    assert result["success"] is True
    assert captured["url"] == "https://chat.intern-ai.org.cn/api/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer test-intern-token"
    assert captured["json"]["model"] == "intern-s2-preview"
    assert captured["json"]["thinking_mode"] is True
    assert "stop" not in captured["json"]


def test_gateway_uses_internai_provider_lane_key(monkeypatch, tmp_path):
    captured = {}

    def fake_post(url, headers, json, timeout):
        captured.update({"headers": headers, "json": json})
        return _Response()

    monkeypatch.setenv("INTERN_API_KEY", "default-token")
    monkeypatch.setenv("INTERN_KILOCODE_API_KEY", "kilocode-token")
    monkeypatch.setattr("requests.post", fake_post)

    gateway = ModelRelayGateway(ProviderBudgetLedger(tmp_path / "quota.sqlite3"))
    result = gateway._call_provider(
        "internai/intern-s2-preview",
        "internai",
        [{"role": "user", "content": "ping"}],
        {"max_tokens": 8, "temperature": 0, "provider_lane": "kilocode"},
    )

    assert result["success"] is True
    assert captured["headers"]["Authorization"] == "Bearer kilocode-token"
    assert captured["json"]["thinking_mode"] is True
