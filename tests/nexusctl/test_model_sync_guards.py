"""Wipe-guard tests for nexusctl model-sync.

Historically a parse failure could overwrite a user config with only sync
output. Cline now has a stricter boundary: this module may report the tracked
project MCP contract but must never read or write Cline's user-owned inference
settings.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from nexusctl import model_sync
from nexusctl.model_sync import (
    _backup_before_write,
    _read_json_config_guarded,
    sync_cline,
    sync_kilo,
    sync_mimo,
    sync_opencode,
)

EMPTY_STATE = {"lanes": [], "models": [], "modelrelay_config": {}}

JSONC_SETTINGS = """{
    // user's editor comment — must survive any sync
    "editor.fontSize": 14,
    "workbench.colorTheme": "Default Dark+",
}
"""


def _target(path):
    return {"config_path": str(path)}


# --- _read_json_config_guarded -------------------------------------------

def test_guarded_read_missing_file_is_fresh_start(tmp_path):
    cfg, refuse = _read_json_config_guarded(tmp_path / "absent.json")
    assert cfg == {} and refuse is None


def test_guarded_read_strict_json(tmp_path):
    p = tmp_path / "ok.json"
    p.write_text('{"model": "x"}', encoding="utf-8")
    cfg, refuse = _read_json_config_guarded(p)
    assert cfg == {"model": "x"} and refuse is None


@pytest.mark.parametrize("text", [JSONC_SETTINGS, "{ broken", '"just a string"', "[1, 2]"])
def test_guarded_read_refuses_non_roundtrippable(tmp_path, text):
    p = tmp_path / "cfg.json"
    p.write_text(text, encoding="utf-8")
    cfg, refuse = _read_json_config_guarded(p)
    assert cfg is None and refuse


# --- handlers refuse to overwrite what they can't parse -------------------

@pytest.mark.parametrize("handler,tid", [
    (sync_opencode, "opencode"),
    (sync_mimo, "mimo"),
    (sync_kilo, "kilo"),
])
def test_handler_never_wipes_unparseable_config(tmp_path, handler, tid):
    p = tmp_path / "settings.json"
    p.write_text(JSONC_SETTINGS, encoding="utf-8")
    result = handler(EMPTY_STATE, _target(p), dry_run=False)
    assert result["ok"] is False
    assert "refusing to overwrite" in result["reason"]
    assert p.read_text(encoding="utf-8") == JSONC_SETTINGS  # byte-identical


# --- successful writes: merge preserved + backup kept ---------------------

def test_opencode_merge_preserves_user_config_and_backs_up(tmp_path):
    p = tmp_path / "opencode.json"
    original = {"model": "my/choice", "provider": {"mine": {"note": "keep"}}, "theme": "dark"}
    p.write_text(json.dumps(original), encoding="utf-8")

    result = sync_opencode(EMPTY_STATE, _target(p), dry_run=False)
    assert result["ok"] is True

    cfg = json.loads(p.read_text(encoding="utf-8"))
    assert cfg["model"] == "my/choice"          # user's default untouched
    assert cfg["theme"] == "dark"               # unrelated keys survive
    assert cfg["provider"]["mine"] == {"note": "keep"}
    assert "nexus-god-relay" in cfg["provider"]

    bak = tmp_path / "opencode.json.nexus-sync.bak"
    assert json.loads(bak.read_text(encoding="utf-8")) == original


def test_cline_sync_is_project_mcp_only_and_never_mutates_legacy_settings(tmp_path):
    p = tmp_path / "settings.json"
    original = json.dumps({"editor.fontSize": 14})
    p.write_text(original, encoding="utf-8")

    result = sync_cline(EMPTY_STATE, _target(p), dry_run=False)

    assert result["ok"] is True
    assert result["mode"] == "project_mcp_contract_only"
    assert result["providers_added"] == []
    assert result["inference"] == {
        "status": "not_inspected",
        "configuration_owner": "user",
        "requirements": ["openai_compatible_base_url", "bearer", "model_id"],
    }
    assert Path(result["path"]).name == "mcp.json"
    assert p.read_text(encoding="utf-8") == original
    assert not (tmp_path / "settings.json.nexus-sync.bak").exists()


def test_cline_inventory_target_is_repo_contract_not_legacy_vscode_settings():
    target = next(item for item in model_sync.CLI_TARGETS if item["id"] == "cline")

    assert target["config_path"] == model_sync.CLINE_PROJECT_MCP_CONFIG
    assert target["config_format"] == "cline-project-mcp-contract"
    assert target["config_scope"] == "repository"
    assert target["inference_configuration"] == "user_owned"
    assert "AppData" not in str(target["config_path"])


def test_dry_run_writes_nothing(tmp_path):
    p = tmp_path / "opencode.json"
    p.write_text('{"model": "keep"}', encoding="utf-8")
    result = sync_opencode(EMPTY_STATE, _target(p), dry_run=True)
    assert result["ok"] is True and result["dry_run"] is True
    assert p.read_text(encoding="utf-8") == '{"model": "keep"}'
    assert not (tmp_path / "opencode.json.nexus-sync.bak").exists()


def test_backup_before_write_rolls(tmp_path):
    p = tmp_path / "cfg.json"
    p.write_text("v1", encoding="utf-8")
    _backup_before_write(p)
    p.write_text("v2", encoding="utf-8")
    _backup_before_write(p)
    assert (tmp_path / "cfg.json.nexus-sync.bak").read_text(encoding="utf-8") == "v2"


# --- sync_hermes YAML nesting (P3-5: entries must be CHILDREN of providers:) ---

def _ready_hermes_probe():
    return {
        "ok": True,
        "reason": "ready",
        "auth_enforced": True,
        "anonymous_status": 401,
        "authenticated_status": 200,
        "models": [model_sync.HERMES_PRIMARY_MODEL, "nexus-resilient"],
    }


@pytest.fixture(autouse=True)
def _ready_hermes_target_key(monkeypatch):
    from nexusctl import model_sync

    monkeypatch.setattr(
        model_sync,
        "probe_hermes_target_key_env",
        lambda *args, **kwargs: {
            "ok": True,
            "reason": "ready",
            "source": "hermes_env_file",
            "secure_permissions": True,
        },
    )



def _hermes_sync(tmp_path, initial_text, monkeypatch):
    import yaml
    from nexusctl import model_sync

    monkeypatch.setattr(
        model_sync,
        "probe_modelrelay_for_target",
        lambda *args, **kwargs: _ready_hermes_probe(),
    )
    p = tmp_path / "config.yaml"
    p.write_text(initial_text, encoding="utf-8")
    result = model_sync.sync_hermes(EMPTY_STATE, _target(p), dry_run=False)
    assert result["ok"] is True, result
    cfg = yaml.safe_load(p.read_text(encoding="utf-8"))
    return cfg


def test_hermes_nests_under_empty_providers_map(tmp_path, monkeypatch):
    cfg = _hermes_sync(tmp_path, "model: something\nproviders: {}\n", monkeypatch)
    assert "modelrelay" in cfg["providers"]
    assert cfg["providers"]["modelrelay"]["base_url"].startswith("http")
    assert cfg["providers"]["modelrelay"]["key_env"] == "NEXUS_MODELRELAY_API_KEY"
    assert "api_key" not in cfg["providers"]["modelrelay"]
    assert "modelrelay" not in cfg
    assert cfg["model"] == "something"


def test_hermes_replaces_existing_managed_block_in_place(tmp_path, monkeypatch):
    import yaml
    from nexusctl import model_sync

    monkeypatch.setattr(
        model_sync,
        "probe_modelrelay_for_target",
        lambda *args, **kwargs: _ready_hermes_probe(),
    )
    p = tmp_path / "config.yaml"
    p.write_text("model: keep\nproviders: {}\n", encoding="utf-8")
    model_sync.sync_hermes(EMPTY_STATE, _target(p), dry_run=False)
    first = p.read_text(encoding="utf-8")
    model_sync.sync_hermes(EMPTY_STATE, _target(p), dry_run=False)
    cfg = yaml.safe_load(p.read_text(encoding="utf-8"))
    assert "modelrelay" in cfg["providers"]
    assert "modelrelay" not in cfg
    assert first.count("# === nexusctl model-sync providers") == 1
    assert p.read_text(encoding="utf-8").count("# === nexusctl model-sync providers") == 1


def test_hermes_appends_providers_key_when_absent(tmp_path, monkeypatch):
    cfg = _hermes_sync(tmp_path, "model: bare\n", monkeypatch)
    assert "modelrelay" in cfg["providers"]
    assert "modelrelay" not in cfg
    assert cfg["model"] == "bare"


def test_hermes_repairs_prefix_bug_top_level_block(tmp_path, monkeypatch):
    # A config written by the pre-fix emitter: managed block at column 0,
    # provider ids as TOP-LEVEL keys and no providers: parent.
    broken = (
        "model: keep\n"
        "# === nexusctl model-sync providers (managed) ===\n"
        "nexus_god_relay:\n"
        "  name: 'old'\n"
        "  base_url: 'http://old'\n"
        "  api_key: ''\n"
        "  models:\n"
        "    'x': 'x'\n"
        "# === end nexusctl managed ===\n"
    )
    cfg = _hermes_sync(tmp_path, broken, monkeypatch)
    assert "modelrelay" in cfg["providers"]
    assert "nexus_god_relay" not in cfg
