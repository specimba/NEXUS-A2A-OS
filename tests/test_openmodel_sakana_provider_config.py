from __future__ import annotations

import json
from pathlib import Path

from nexus_os.bridge.secrets import PROVIDER_CONFIG
from upload.config import FALLBACK_CHAINS, PROVIDERS
from upload.gateway import ModelRelayGateway
from upload.models_registry import ModelsRegistry
from upload.openmodel_lanes import OPENMODEL_LANES, resolve_openmodel_key
from upload.quota_guard import QuotaGuard
from upload.sakana_lanes import SAKANA_LANES, resolve_sakana_key


class _Response:
    def __init__(self, status_code=200, headers=None):
        self.status_code = status_code
        self.headers = headers or {}
        self.text = "{}"

    def json(self):
        return {
            "choices": [{"message": {"content": "OK"}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }


def test_openmodel_and_sakana_registered_across_python_layers():
    assert PROVIDER_CONFIG["openmodel"]["base_url"] == "https://api.openmodel.ai"
    assert "NEXUS_OPENMODEL_API_KEY" in PROVIDER_CONFIG["openmodel"]["key_env_order"]
    assert PROVIDERS["openmodel"]["chat_path"] == "/v1/chat/completions"
    assert PROVIDERS["sakana"]["base_url"] == "https://api.sakana.ai/v1"
    assert PROVIDERS["sakana"]["chat_path"] == "/chat/completions"
    assert "deepseek-v4-flash-free" in FALLBACK_CHAINS["code"]
    assert "fugu" in FALLBACK_CHAINS["reasoning"]


def test_models_registry_contains_new_free_provider_models():
    registry = ModelsRegistry()
    openmodel = {model.model_id: model for model in registry.get_by_provider("openmodel")}
    sakana = {model.model_id: model for model in registry.get_by_provider("sakana")}

    assert "openmodel/deepseek-v4-flash-free" in openmodel
    assert openmodel["openmodel/deepseek-v4-flash-free"].supports_function_calling
    assert "sakana/fugu" in sakana
    assert "sakana/fugu-ultra" in sakana
    assert sakana["sakana/fugu"].context_window == 1_000_000


def test_quota_guard_initializes_new_provider_lanes():
    quota = QuotaGuard()

    assert quota.get_quota("openmodel") is not None
    assert quota.get_quota("sakana") is not None
    assert quota.get_quota("openmodel").daily_limit == 1000
    assert quota.get_quota("sakana").daily_limit == 200


def test_lane_key_resolution_prefers_surface_specific_keys(monkeypatch):
    monkeypatch.setenv("NEXUS_OPENMODEL_API_KEY", "openmodel-default")
    monkeypatch.setenv("OPENMODEL_OPENCODE_API_KEY", "openmodel-opencode")
    monkeypatch.setenv("NEXUS_SAKANA_API_KEY", "sakana-default")
    monkeypatch.setenv("SAKANA_VERIFIER_API_KEY", "sakana-verifier")

    assert OPENMODEL_LANES["opencode"].default_model == "deepseek-v4-flash-free"
    assert resolve_openmodel_key("opencode").env_var == "OPENMODEL_OPENCODE_API_KEY"
    assert resolve_openmodel_key("modelrelay").env_var == "NEXUS_OPENMODEL_API_KEY"
    assert SAKANA_LANES["verifier"].default_model == "fugu-ultra"
    assert resolve_sakana_key("verifier").env_var == "SAKANA_VERIFIER_API_KEY"
    assert resolve_sakana_key("hermes").env_var == "NEXUS_SAKANA_API_KEY"


def test_gateway_sends_new_provider_bearer_auth(monkeypatch):
    captured = []

    def fake_post(url, headers, json, timeout):
        captured.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return _Response()

    monkeypatch.setenv("NEXUS_OPENMODEL_API_KEY", "om-token")
    monkeypatch.setenv("NEXUS_SAKANA_API_KEY", "sakana-token")
    monkeypatch.setattr("requests.post", fake_post)

    gateway = ModelRelayGateway()
    openmodel_result = gateway._call_provider(
        "openmodel/deepseek-v4-flash-free",
        "openmodel",
        [{"role": "user", "content": "ping"}],
        {"max_tokens": 8, "temperature": 0},
    )
    sakana_result = gateway._call_provider(
        "sakana/fugu",
        "sakana",
        [{"role": "user", "content": "ping"}],
        {"max_tokens": 8, "temperature": 0},
    )

    assert openmodel_result["success"] is True
    assert sakana_result["success"] is True
    assert captured[0]["url"] == "https://api.openmodel.ai/v1/chat/completions"
    assert captured[0]["headers"]["Authorization"] == "Bearer om-token"
    assert captured[0]["json"]["model"] == "deepseek-v4-flash-free"
    assert captured[1]["url"] == "https://api.sakana.ai/v1/chat/completions"
    assert captured[1]["headers"]["Authorization"] == "Bearer sakana-token"
    assert captured[1]["json"]["model"] == "fugu"


def test_gateway_reports_429_cooldown_for_new_providers(monkeypatch):
    def fake_post(url, headers, json, timeout):
        return _Response(429, {"Retry-After": "120"})

    monkeypatch.setenv("NEXUS_OPENMODEL_API_KEY", "om-token")
    monkeypatch.setattr("requests.post", fake_post)

    result = ModelRelayGateway()._call_provider(
        "openmodel/deepseek-v4-flash-free",
        "openmodel",
        [{"role": "user", "content": "ping"}],
        {"max_tokens": 8, "temperature": 0},
    )

    assert result["success"] is False
    assert result["quota_signal"] == "rate_limited"
    assert result["retry_after"] == "120"


def test_new_provider_adapter_manifests_are_secret_free_and_tool_disabled():
    for root in [Path("nexus_os/bridge/provider_adapters/openmodel"), Path("nexus_os/bridge/provider_adapters/sakana")]:
        for path in root.glob("*.json"):
            text = path.read_text(encoding="utf-8")
            assert "ak_" not in text
            assert "om-" not in text
            assert "fish_" not in text
            data = json.loads(text)
            assert data["capabilities"]["tools"] is False
            assert data["requestRules"]["backgroundPolling"] is False
