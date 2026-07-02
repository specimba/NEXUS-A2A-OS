"""Tests for nexus_os/security/secrets.py — central secret resolution.

Covers the audit P0 contract: env -> vault file -> ModelRelay apiKeys,
no committed fallbacks, hard-fail via require_secret.
"""
from __future__ import annotations

import json

import pytest

from nexus_os.security.secrets import MissingSecretError, get_secret, require_secret


@pytest.fixture
def isolated_stores(tmp_path, monkeypatch):
    """Point both file stores at empty temp locations and clear env."""
    vault = tmp_path / "secrets.json"
    relay = tmp_path / "modelrelay.json"
    monkeypatch.setenv("NEXUS_SECRETS_FILE", str(vault))
    monkeypatch.setenv("MODELRELAY_CONFIG", str(relay))
    monkeypatch.delenv("FAKEPROV_API_KEY", raising=False)
    return vault, relay


class TestResolutionOrder:
    def test_env_wins(self, isolated_stores, monkeypatch):
        vault, _ = isolated_stores
        vault.write_text(json.dumps({"FAKEPROV_API_KEY": "from-vault"}), encoding="utf-8")
        monkeypatch.setenv("FAKEPROV_API_KEY", "from-env")
        assert get_secret("FAKEPROV_API_KEY") == "from-env"

    def test_vault_file_second(self, isolated_stores):
        vault, relay = isolated_stores
        vault.write_text(json.dumps({"FAKEPROV_API_KEY": "from-vault"}), encoding="utf-8")
        relay.write_text(json.dumps({"apiKeys": {"fakeprov": "from-relay"}}), encoding="utf-8")
        assert get_secret("FAKEPROV_API_KEY") == "from-vault"

    def test_modelrelay_apikeys_third_with_derived_slug(self, isolated_stores):
        _, relay = isolated_stores
        relay.write_text(json.dumps({"apiKeys": {"fakeprov": "from-relay"}}), encoding="utf-8")
        assert get_secret("FAKEPROV_API_KEY") == "from-relay"

    def test_explicit_provider_slug(self, isolated_stores):
        _, relay = isolated_stores
        relay.write_text(
            json.dumps({"apiKeys": {"openai-compatible:baseten": "bt-key"}}), encoding="utf-8"
        )
        assert get_secret("BASETEN_API_KEY", provider="openai-compatible:baseten") == "bt-key"

    def test_default_when_nothing_found(self, isolated_stores):
        assert get_secret("FAKEPROV_API_KEY") == ""
        assert get_secret("FAKEPROV_API_KEY", default="sentinel") == "sentinel"


class TestRobustness:
    def test_missing_files_are_not_errors(self, isolated_stores):
        assert get_secret("FAKEPROV_API_KEY") == ""

    def test_malformed_vault_json_is_not_an_error(self, isolated_stores):
        vault, _ = isolated_stores
        vault.write_text("{not json", encoding="utf-8")
        assert get_secret("FAKEPROV_API_KEY") == ""

    def test_non_dict_apikeys_tolerated(self, isolated_stores):
        _, relay = isolated_stores
        relay.write_text(json.dumps({"apiKeys": ["not", "a", "dict"]}), encoding="utf-8")
        assert get_secret("FAKEPROV_API_KEY") == ""

    def test_name_without_api_key_suffix_has_no_slug(self, isolated_stores):
        _, relay = isolated_stores
        relay.write_text(json.dumps({"apiKeys": {"posthog": "ph-key"}}), encoding="utf-8")
        # POSTHOG_TOKEN cannot derive a slug -> relay store not consulted
        assert get_secret("POSTHOG_TOKEN") == ""


class TestHardFail:
    def test_require_secret_raises_and_names_no_value(self, isolated_stores):
        with pytest.raises(MissingSecretError) as exc:
            require_secret("FAKEPROV_API_KEY")
        assert "FAKEPROV_API_KEY" in str(exc.value)

    def test_require_secret_returns_value(self, isolated_stores, monkeypatch):
        monkeypatch.setenv("FAKEPROV_API_KEY", "present")
        assert require_secret("FAKEPROV_API_KEY") == "present"
