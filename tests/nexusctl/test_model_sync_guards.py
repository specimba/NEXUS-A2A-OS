"""Wipe-guard tests for nexusctl model-sync (full-audit finding: a parse
failure used to fall through to ``cfg = {}`` and then OVERWRITE the user's
config file with only the sync output — worst case the entire VS Code
settings.json). The scheduled NexusModelSync4h task runs this unattended
every 4 hours, so these paths must hard-fail instead of destroying data.
"""
from __future__ import annotations

import json

import pytest

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
    (sync_cline, "cline"),
])
def test_handler_never_wipes_unparseable_config(tmp_path, handler, tid):
    p = tmp_path / "settings.json"
    p.write_text(JSONC_SETTINGS, encoding="utf-8")
    result = handler(EMPTY_STATE, _target(p), dry_run=False)
    assert result["ok"] is False
    assert "refusing to overwrite" in result["reason"]
    assert p.read_text(encoding="utf-8") == JSONC_SETTINGS  # byte-identical


def test_cline_missing_settings_reports_not_found(tmp_path):
    result = sync_cline(EMPTY_STATE, _target(tmp_path / "nope.json"), dry_run=False)
    assert result["ok"] is False and "not found" in result["reason"]


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


def test_cline_merge_keeps_existing_settings(tmp_path):
    p = tmp_path / "settings.json"
    p.write_text(json.dumps({"editor.fontSize": 14}), encoding="utf-8")
    result = sync_cline(EMPTY_STATE, _target(p), dry_run=False)
    assert result["ok"] is True
    cfg = json.loads(p.read_text(encoding="utf-8"))
    assert cfg["editor.fontSize"] == 14
    assert "nexus-god-relay" in cfg["cline.apiProviders"]


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
