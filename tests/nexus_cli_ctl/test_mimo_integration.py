"""Wipe-guard tests for the mimo integration (full-audit CRITICAL finding:
the JSONC comment stripper split every line on '//', truncating 'http://'
URLs, so the whole config failed to parse — and the empty-config fallback
was then written back to disk by the 5-minute daemon sync cycle)."""
from __future__ import annotations

import json

import pytest

from nexus_cli_ctl.integrations.mimo.mimo_integration import (
    MimoConfig,
    strip_jsonc_comments,
)

JSONC_WITH_URLS = """{
  // user comment — must survive stripping
  "providers": {
    "nexus-god-relay": {
      /* block comment */
      "options": {
        "baseURL": "http://127.0.0.1:7355/v1",
        "apiKey": "k//eep-this" // trailing comment
      }
    }
  }
}
"""


@pytest.fixture
def mimo(tmp_path, monkeypatch):
    cfg_path = tmp_path / "mimocode.jsonc"
    monkeypatch.setattr(MimoConfig, "MIMO_CONFIG_PATH", cfg_path)
    return cfg_path


# --- strip_jsonc_comments -------------------------------------------------

def test_strip_preserves_urls_and_string_slashes():
    cfg = json.loads(strip_jsonc_comments(JSONC_WITH_URLS))
    opts = cfg["providers"]["nexus-god-relay"]["options"]
    assert opts["baseURL"] == "http://127.0.0.1:7355/v1"
    assert opts["apiKey"] == "k//eep-this"


def test_strip_removes_line_and_block_comments():
    stripped = strip_jsonc_comments(JSONC_WITH_URLS)
    assert "user comment" not in stripped
    assert "block comment" not in stripped
    assert "trailing comment" not in stripped


def test_strip_handles_escaped_quotes():
    text = '{"a": "say \\"hi\\" // not a comment", "b": 1} // real comment'
    cfg = json.loads(strip_jsonc_comments(text))
    assert cfg["a"] == 'say "hi" // not a comment'
    assert cfg["b"] == 1


# --- load/save round-trip -------------------------------------------------

def test_config_with_urls_round_trips(mimo):
    mimo.write_text(JSONC_WITH_URLS, encoding="utf-8")
    m = MimoConfig()
    assert not m._load_failed
    base = m.config["providers"]["nexus-god-relay"]["options"]["baseURL"]
    assert base == "http://127.0.0.1:7355/v1"

    assert m._save_config() is True
    reloaded = json.loads(mimo.read_text(encoding="utf-8"))
    assert reloaded["providers"]["nexus-god-relay"]["options"]["baseURL"] == base
    # backup of the pre-write content kept
    bak = mimo.with_name(mimo.name + ".nexus-sync.bak")
    assert bak.read_text(encoding="utf-8") == JSONC_WITH_URLS


def test_unparseable_config_is_never_overwritten(mimo):
    broken = '{ "providers": { broken'
    mimo.write_text(broken, encoding="utf-8")
    m = MimoConfig()
    assert m._load_failed
    m.config["providers"]["injected"] = {}
    assert m._save_config() is False
    assert mimo.read_text(encoding="utf-8") == broken  # byte-identical


def test_missing_config_starts_fresh_and_saves(mimo):
    m = MimoConfig()
    assert not m._load_failed
    assert m.configure_nexus_god_relay() is True
    cfg = json.loads(mimo.read_text(encoding="utf-8"))
    assert "nexus-god-relay" in cfg["providers"]
