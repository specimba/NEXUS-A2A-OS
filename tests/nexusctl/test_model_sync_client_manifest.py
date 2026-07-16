"""Client-manifest contracts for governed ModelRelay sync.

These tests protect the distinction between a raw relay catalogue and the
canonical CLI-visible chat routes emitted by the Model Arena.
"""
from __future__ import annotations

import json
from pathlib import Path

from nexusctl import model_sync


def _card(
    *,
    route_id: str,
    label: str,
    provider: str,
    health: str,
    quality: float = 0.0,
    visible: bool = True,
    context: int = 131_072,
    thinking: bool = False,
) -> dict:
    return {
        "model_id": f"{provider}/{route_id}",
        "label": label,
        "provider_key": provider,
        "routing": {
            "cli_visible": visible,
            "eligible": visible,
            "cli_route_id": route_id,
        },
        "health": {"state": health, "raw_status": health, "last_checked_at": "2026-07-14T20:00:00Z"},
        "benchmarks": {"dimensions": {"quality": quality}},
        "registry": {
            "context_tokens": context,
            "max_output_tokens": 8192,
            "capabilities": {"thinking": thinking},
        },
        "runtime": {"context": "128k"},
    }


def test_arena_projection_deduplicates_by_cli_route_and_excludes_non_cli_cards():
    payload = {
        "models": [
            _card(
                route_id="glm-5.2",
                label="GLM 5.2",
                provider="nvidia",
                health="healthy",
                quality=0.71,
                thinking=True,
            ),
            _card(
                route_id="glm-5.2",
                label="GLM 5.2 stale copy",
                provider="ollama-cloud",
                health="unverified",
                quality=0.99,
            ),
            _card(
                route_id="image-only", label="Image-only", provider="modal", health="healthy", visible=False),
        ]
    }

    models = model_sync._project_arena_client_models(payload)

    assert [model["id"] for model in models] == ["glm-5.2"]
    assert models[0]["provider"] == "nvidia"
    assert models[0]["health"] == "healthy"
    assert models[0]["capabilities"] == {"thinking": True}


def test_fetch_live_state_prefers_versioned_client_manifest_over_raw_relay(monkeypatch):
    manifest = {
        "schema_version": 1,
        "contract": {"source": "nexus-model-arena-live-projection"},
        "models": [
            {
                "id": "glm-5.2",
                "label": "GLM 5.2",
                "provider": "nvidia",
                "health": {"state": "healthy", "last_checked_at": "2026-07-14T20:00:00Z"},
                "benchmarks": {"status": "evidence_backed", "dimensions": {"quality": 0.71}},
                "context_tokens": 1_048_576,
                "max_output_tokens": 8_192,
                "capabilities": {"thinking": True},
                "free": True,
            },
            {
                "id": "minimax-m3",
                "label": "MiniMax M3",
                "provider": "nvidia",
                "health": {"state": "unverified", "last_checked_at": None},
                "benchmarks": {"status": "evidence_backed", "dimensions": {"quality": 0.66}},
                "context_tokens": 1_048_576,
                "max_output_tokens": 8_192,
                "capabilities": {},
                "free": True,
            },
        ]
    }

    def fake_get(url: str, timeout: float = 8.0):
        del timeout
        if url.endswith("/god/lanes"):
            return {"lanes": [{"alias": "core", "description": "Core", "target": "glm-5.2"}]}
        if url == f"{model_sync.NODE_RELAY_URL}/api/models":
            return {"models": [{"modelId": "glm-5.2", "providerKey": "nvidia", "status": "up"}]}
        if url == f"{model_sync.NODE_RELAY_URL}/v1/models":
            return {"data": [{"id": "glm-5.2"}, {"id": "embedding-only"}]}
        if url == f"{model_sync.MODEL_ARENA_URL}/api/client-manifest":
            return manifest
        return {"data": []}

    monkeypatch.setattr(model_sync, "_http_get_json", fake_get)
    monkeypatch.setattr(model_sync, "MODELRELAY_CONFIG", Path("does-not-exist"))

    state = model_sync.fetch_live_state()

    assert state["model_catalog_source"] == "client_manifest"
    assert state["arena_cards_alive"] is True
    assert state["client_manifest_alive"] is True
    assert [model["id"] for model in state["models"]] == ["glm-5.2", "minimax-m3"]
    assert state["models"][1]["health"] == "unverified"


def test_client_manifest_projection_rejects_unversioned_or_wrong_source():
    assert model_sync._project_client_manifest_models({"models": [{"id": "glm-5.2"}]}) == []
    assert model_sync._project_client_manifest_models({
        "schema_version": 1,
        "contract": {"source": "static-catalogue"},
        "models": [{"id": "glm-5.2"}],
    }) == []


def test_pi_sync_preserves_existing_config_and_repairs_only_known_mirror_default(tmp_path):
    models_path = tmp_path / "models.json"
    extension_path = tmp_path / "nexus-modelrelay-mirror.ts"
    original = {
        "providers": {
            "custom": {"baseUrl": "https://example.invalid/v1", "api": "openai-completions", "models": []},
            "nexus-modelrelay": {"baseUrl": "http://localhost:7350/v1", "api": "openai-completions", "apiKey": "nexus", "models": []},
        }
    }
    models_path.write_text(json.dumps(original), encoding="utf-8")
    extension_path.write_text(
        'const baseUrl = (process.env.NEXUS_MODELRELAY_URL || "http://127.0.0.1:7352/v1").replace(/\\/$/, "");\n',
        encoding="utf-8",
    )
    state = {
        "model_catalog_source": "arena",
        "models": [
            {
                "id": "glm-5.2",
                "label": "GLM 5.2",
                "provider": "nvidia",
                "health": "healthy",
                "context_tokens": 1_048_576,
                "max_output_tokens": 8192,
                "capabilities": {"thinking": True},
            },
            {
                "id": "minimax-m3",
                "label": "MiniMax M3",
                "provider": "nvidia",
                "health": "unverified",
                "context_tokens": 1_048_576,
                "max_output_tokens": 8192,
                "capabilities": {},
            },
        ],
    }

    result = model_sync.sync_pi(
        state,
        {"config_path": str(models_path), "extension_path": str(extension_path)},
        dry_run=False,
    )

    assert result["ok"] is True
    assert result["model_count"] == 3
    assert result["mirror_extension"]["state"] == "updated"
    written = json.loads(models_path.read_text(encoding="utf-8"))
    assert written["providers"]["custom"] == original["providers"]["custom"]
    relay = written["providers"]["nexus-modelrelay"]
    assert relay["baseUrl"] == "http://127.0.0.1:7350/v1"
    assert relay["apiKey"] == "nexus"
    assert [model["id"] for model in relay["models"]] == ["auto-fastest", "glm-5.2", "minimax-m3"]
    assert relay["models"][1]["reasoning"] is True
    assert "http://127.0.0.1:7352/v1" not in extension_path.read_text(encoding="utf-8")
    assert "http://127.0.0.1:7350/v1" in extension_path.read_text(encoding="utf-8")
    assert models_path.with_name("models.json.nexus-sync.bak").exists()
    assert extension_path.with_name("nexus-modelrelay-mirror.ts.nexus-sync.bak").exists()
