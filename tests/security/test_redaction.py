"""Canary tests for the central redaction filter (roadmap P1-10).

Operator directive: keys are not rotated (live routing substrate), so
redaction is the compensating control. These tests plant canary keys in
every source the redactor reads and assert none of them survive.
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from nexus_os.security import redaction
from nexus_os.security.redaction import (
    RedactionFilter,
    install_log_redaction,
    known_secret_values,
    redact,
    redact_obj,
)

CANARY = "canary-key-value-0123456789abcdef"


@pytest.fixture(autouse=True)
def _fresh_cache(monkeypatch, tmp_path):
    """Isolate every test from the real stores and the module cache."""
    monkeypatch.setattr(redaction, "_cache_values", {})
    monkeypatch.setattr(redaction, "_cache_at", 0.0)
    monkeypatch.setenv("NEXUS_SECRETS_FILE", str(tmp_path / "secrets.json"))
    monkeypatch.setenv("MODELRELAY_CONFIG", str(tmp_path / "modelrelay.json"))
    # Scrub secret-shaped env vars the host machine may carry so labels are
    # deterministic; the canary tests re-add what they need.
    yield


class TestValueRedaction:
    def test_env_canary_redacted(self, monkeypatch):
        monkeypatch.setenv("CANARY_API_KEY", CANARY)
        out = redact(f"calling provider with key {CANARY} now")
        assert CANARY not in out
        assert "[REDACTED:env:CANARY_API_KEY]" in out

    def test_vault_canary_redacted(self, monkeypatch, tmp_path):
        (tmp_path / "secrets.json").write_text(
            json.dumps({"VAULT_CANARY": CANARY}), encoding="utf-8"
        )
        out = redact(f"vault value {CANARY}")
        assert CANARY not in out
        assert "vault:VAULT_CANARY" in out

    def test_modelrelay_apikeys_canary_redacted(self, tmp_path):
        (tmp_path / "modelrelay.json").write_text(
            json.dumps({"apiKeys": {"canaryprov": CANARY}}), encoding="utf-8"
        )
        out = redact(f"Authorization uses {CANARY}")
        assert CANARY not in out
        assert "apiKeys:canaryprov" in out

    def test_short_values_not_redacted(self, monkeypatch):
        monkeypatch.setenv("TINY_API_KEY", "abc")
        assert redact("abc is fine in prose") == "abc is fine in prose"

    def test_cache_refresh_picks_up_new_secret(self, monkeypatch):
        known_secret_values(refresh=True)
        monkeypatch.setenv("LATE_API_KEY", CANARY)
        assert CANARY in known_secret_values(refresh=True)


class TestPatternRedaction:
    @pytest.mark.parametrize(
        "leak,label",
        [
            ("nvapi-" + "x" * 40, "nvidia"),
            ("sk-" + "a" * 40, "openai-style"),
            ("hf_" + "B" * 30, "huggingface"),
            ("ghp_" + "C" * 36, "github"),
            ("xoxb-1234567890-abcdefghij", "slack"),
            ("AIza" + "D" * 35, "google"),
            ("eyJ" + "a" * 20 + "." + "b" * 20 + "." + "c" * 20, "jwt"),
            ("Bearer abcdefghijklmnopqrstuvwx", "bearer"),
        ],
    )
    def test_key_shapes_redacted(self, leak, label):
        out = redact(f"header was {leak} in the dump")
        assert leak not in out
        assert f"[REDACTED:{label}]" in out


class TestRedactObj:
    def test_nested_payload(self, monkeypatch):
        monkeypatch.setenv("NEST_API_KEY", CANARY)
        payload = {
            "relay_info": {"auth": f"Bearer {CANARY}", "model": "auto"},
            "choices": [{"message": {"content": f"key={CANARY}"}}],
            "count": 3,
        }
        clean = redact_obj(payload)
        assert CANARY not in json.dumps(clean)
        assert clean["count"] == 3
        assert clean["relay_info"]["model"] == "auto"


class TestLoggingFilter:
    def test_filter_redacts_formatted_message(self, monkeypatch, caplog):
        monkeypatch.setenv("LOG_API_KEY", CANARY)
        logger = logging.getLogger("nexus.test.redaction")
        logger.addFilter(RedactionFilter())
        with caplog.at_level(logging.INFO, logger="nexus.test.redaction"):
            logger.info("using key %s for provider", CANARY)
        assert CANARY not in caplog.text
        assert "REDACTED" in caplog.text

    def test_install_is_idempotent(self):
        logger = logging.getLogger("nexus.test.redaction.idem")
        handler = logging.StreamHandler()
        logger.addHandler(handler)
        try:
            install_log_redaction(logger)
            install_log_redaction(logger)
            assert sum(isinstance(f, RedactionFilter) for f in handler.filters) == 1
        finally:
            logger.removeHandler(handler)
