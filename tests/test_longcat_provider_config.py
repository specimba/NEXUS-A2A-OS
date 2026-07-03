from __future__ import annotations

import json
from pathlib import Path

from nexus_os.bridge.secrets import PROVIDER_CONFIG
from upload.config import FALLBACK_CHAINS, PROVIDERS
from upload.gateway import ModelRelayGateway
from upload.longcat_lanes import LONGCAT_LANES, resolve_longcat_key
from upload.models_registry import ModelsRegistry
from nexus_os.model_relay.provider_budget import ProviderBudgetLedger
from upload.quota_guard import QuotaGuard


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


def test_longcat_provider_is_registered_across_python_layers():
    assert PROVIDER_CONFIG["longcat"]["base_url"] == "https://api.longcat.chat/openai/v1"
    assert "NEXUS_LONGCAT_API_KEY" in PROVIDER_CONFIG["longcat"]["key_env_order"]
    assert PROVIDERS["longcat"]["chat_path"] == "/chat/completions"
    assert PROVIDERS["longcat"]["auth_type"] == "bearer"
    assert "LongCat-2.0" in FALLBACK_CHAINS["reasoning"]
    assert "LongCat-2.0" in FALLBACK_CHAINS["research"]
    assert "LongCat-2.0-Preview" not in FALLBACK_CHAINS["reasoning"]


def test_longcat_models_expose_teacher_eval_capabilities():
    registry = ModelsRegistry()
    models = {model.model_id: model for model in registry.get_by_provider("longcat")}

    assert "longcat/LongCat-2.0" in models
    assert "longcat/LongCat-2.0-Preview" not in models
    assert models["longcat/LongCat-2.0"].context_window == 1_000_000
    assert models["longcat/LongCat-2.0"].supports_function_calling


def test_longcat_quota_is_initialized(tmp_path):
    ledger = ProviderBudgetLedger(tmp_path / "quota.sqlite3")
    quota = QuotaGuard(budget_ledger=ledger).get_quota("longcat")

    assert quota is not None
    assert quota.quota_type == "tokens"
    assert quota.daily_limit is None
    assert quota.budget_verified is False
    assert quota.is_exhausted is True


def test_longcat_lane_key_resolution_prefers_surface_specific_key(monkeypatch):
    monkeypatch.setenv("LONGCAT_API_KEY", "compat-token")
    monkeypatch.setenv("NEXUS_LONGCAT_API_KEY", "canonical-token")
    monkeypatch.setenv("LONGCAT_OPENCODE_API_KEY", "opencode-token")

    assert LONGCAT_LANES["opencode"].default_model == "LongCat-2.0"
    assert resolve_longcat_key("opencode").env_var == "LONGCAT_OPENCODE_API_KEY"
    assert resolve_longcat_key("opencode").value == "opencode-token"
    assert resolve_longcat_key("kilocode").env_var == "NEXUS_LONGCAT_API_KEY"


def test_gateway_sends_longcat_bearer_auth(monkeypatch, tmp_path):
    captured = {}

    def fake_post(url, headers, json, timeout):
        captured.update({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return _Response()

    monkeypatch.setenv("NEXUS_LONGCAT_API_KEY", "lc-token")
    monkeypatch.setattr("requests.post", fake_post)

    gateway = ModelRelayGateway(ProviderBudgetLedger(tmp_path / "quota.sqlite3"))
    result = gateway._call_provider(
        "longcat/LongCat-2.0",
        "longcat",
        [{"role": "user", "content": "ping"}],
        {"max_tokens": 8, "temperature": 0},
    )

    assert result["success"] is True
    assert captured["url"] == "https://api.longcat.chat/openai/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer lc-token"
    assert captured["json"]["model"] == "LongCat-2.0"


def test_gateway_reports_longcat_429_retry_signal(monkeypatch, tmp_path):
    def fake_post(url, headers, json, timeout):
        return _Response(429, {"Retry-After": "60"})

    monkeypatch.setenv("NEXUS_LONGCAT_API_KEY", "lc-token")
    monkeypatch.setattr("requests.post", fake_post)

    gateway = ModelRelayGateway(ProviderBudgetLedger(tmp_path / "quota.sqlite3"))
    result = gateway._call_provider(
        "longcat/LongCat-2.0",
        "longcat",
        [{"role": "user", "content": "ping"}],
        {"max_tokens": 8, "temperature": 0},
    )

    assert result["success"] is False
    assert result["quota_signal"] == "rate_limited"
    assert result["retry_after"] == "60"


def test_longcat_adapter_manifests_are_secret_free_and_tool_disabled():
    root = Path("nexus_os/bridge/provider_adapters/longcat")
    for path in root.glob("*.json"):
        text = path.read_text(encoding="utf-8")
        assert "ak_" not in text
        data = json.loads(text)
        if "capabilities" in data:
            assert data["capabilities"]["tools"] is False
        assert "NEXUS_LONGCAT_API_KEY" in text or "LONGCAT_" in text

