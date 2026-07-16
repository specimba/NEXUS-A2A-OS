"""Partner direct-provider projection contracts for ``nexusctl model-sync``.

Legacy ModelRelay records remain useful as historical adapter data, but they
are never evidence that a partner endpoint is active.  Client sync may only
project a partner from an active, canonical OpenAI-compatible endpoint record.
"""
from __future__ import annotations

import copy
import json

from nexusctl import model_sync


def _state(*, endpoint: dict | None = None) -> dict:
    providers: dict = {
        "longcat": {
            "baseUrl": "https://api.longcat.chat/openai",
            "models": ["LongCat-2.0-Preview"],
        },
        "internai": {
            "baseUrl": "https://chat.intern-ai.org.cn/api/v1",
            "models": ["intern-retired-preview"],
        },
    }
    if endpoint is not None:
        providers["openai-compatible:longcat"] = endpoint
    return {
        "lanes": [],
        "models": [],
        "modelrelay_config": {
            "apiKeys": {
                "longcat": "legacy-key-must-not-be-projected",
                "openai-compatible:longcat": "canonical-key",
            },
            "providers": providers,
        },
    }


def test_partner_projection_ignores_retired_legacy_models_in_favor_of_active_endpoint():
    state = _state(endpoint={
        "baseUrl": "https://api.longcat.chat/openai/v1",
        "modelId": "LongCat-2.0",
        "enabled": True,
        "models": ["LongCat-2.0-Preview"],
    })
    original = copy.deepcopy(state)

    entries = model_sync._build_relay_provider_entries(state)

    assert state == original  # projection never registers or activates endpoints
    assert set(entries["longcat"]["models"]) == {"LongCat-2.0"}
    assert entries["longcat"]["models"]["LongCat-2.0"]["name"] == "LongCat LongCat-2.0"
    assert entries["longcat"]["options"] == {
        "baseURL": "https://api.longcat.chat/openai/v1",
        "apiKey": "canonical-key",
    }
    assert "Preview" not in json.dumps(entries)


def test_partner_projection_does_not_use_legacy_record_or_key_when_canonical_endpoint_missing():
    entries = model_sync._build_relay_provider_entries(_state())

    assert "longcat" not in entries
    assert "internai" not in entries
    assert "direct-openai-compatible-longcat" not in entries
    assert "direct-openai-compatible-internai" not in entries


def test_partner_projection_requires_active_canonical_endpoint_and_model_mapping():
    staged = _state(endpoint={
        "baseUrl": "https://api.longcat.chat/openai/v1",
        "modelId": "LongCat-2.0",
        "enabled": False,
    })
    wrong_model = _state(endpoint={
        "baseUrl": "https://api.longcat.chat/openai/v1",
        "modelId": "LongCat-2.0-Preview",
        "enabled": True,
    })

    assert "longcat" not in model_sync._build_relay_provider_entries(staged)
    assert "longcat" not in model_sync._build_relay_provider_entries(wrong_model)


def test_partner_projection_uses_modelrelay_active_default_but_not_legacy_models():
    state = _state()
    state["modelrelay_config"]["providers"]["openai-compatible:internai"] = {
        "baseUrl": "https://chat.intern-ai.org.cn/api/v1",
        "modelId": "intern-latest",
        # ModelRelay itself treats omitted enabled as active.
    }
    state["modelrelay_config"]["apiKeys"]["openai-compatible:internai"] = "intern-key"

    entries = model_sync._build_relay_provider_entries(state)

    assert set(entries["internai"]["models"]) == {"intern-latest"}
    assert entries["internai"]["options"]["apiKey"] == "intern-key"
    assert "intern-retired-preview" not in json.dumps(entries)


def test_kilo_does_not_add_partner_credential_from_legacy_record(tmp_path):
    path = tmp_path / "auth.json"
    path.write_text("{}", encoding="utf-8")

    result = model_sync.sync_kilo(_state(), {"config_path": str(path)}, dry_run=False)

    assert result["ok"] is True
    assert result["providers_added"] == ["modelrelaygod"]
    assert json.loads(path.read_text(encoding="utf-8")) == {
        "modelrelaygod": {"type": "api", "key": "nexus-relay"}
    }
