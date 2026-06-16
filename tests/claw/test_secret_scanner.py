"""tests/claw/test_secret_scanner.py — Secret scanner unit tests."""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from nexus_os.claw.security.secret_scanner import (
    ScanAction,
    ScanResult,
    SecretScanner,
)


def _make_scanner(action: ScanAction = ScanAction.BLOCK) -> SecretScanner:
    return SecretScanner(action=action)


# ── detection tests ────────────────────────────────────────────────────


def test_scan_detects_api_key() -> None:
    scanner = _make_scanner()
    result = scanner.scan("my key is sk-proj-AcR3TkN0b8WXqYzL5mPv7JhF2DgS1")
    assert result.detected
    assert "api_key_generic" in result.matched_patterns


def test_scan_detects_jwt() -> None:
    jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3j3kI1YKiDP6t"
    scanner = _make_scanner()
    result = scanner.scan(f"token={jwt}")
    assert result.detected
    assert "jwt" in result.matched_patterns


def test_scan_detects_aws_key() -> None:
    scanner = _make_scanner()
    result = scanner.scan("AWS_ACCESS_KEY=AKIAIOSFODNN7EXAMPLE")
    assert result.detected
    assert "aws_access_key" in result.matched_patterns


def test_scan_detects_github_token() -> None:
    scanner = _make_scanner()
    result = scanner.scan("token=ghp_abcdefghijklmnopqrstuvwxyzABCDEFGHIJ")
    assert result.detected
    assert "github_token" in result.matched_patterns


def test_scan_detects_private_key() -> None:
    scanner = _make_scanner()
    pem = "-----BEGIN PRIVATE KEY-----\nMIIBVAIBADANBgkqhkiG9w0BAQEFAASCAT4"
    result = scanner.scan(pem)
    assert result.detected
    assert "private_key_pem" in result.matched_patterns


def test_scan_detects_connection_string() -> None:
    scanner = _make_scanner()
    result = scanner.scan("postgres://user:password@localhost:5432/mydb")
    assert result.detected
    assert "connection_string" in result.matched_patterns


# ── action tests ───────────────────────────────────────────────────────


def test_scan_block_action() -> None:
    scanner = _make_scanner(ScanAction.BLOCK)
    result = scanner.scan("secret=sk-abc1234567890123456789012345678")
    assert result.detected
    assert result.action == ScanAction.BLOCK
    assert result.redacted_text is None


def test_scan_redact_action() -> None:
    scanner = _make_scanner(ScanAction.REDACT)
    text = "my key is sk-proj-AcR3TkN0b8WXqYzL5mPv7Jh"
    result = scanner.scan(text)
    assert result.detected
    assert result.action == ScanAction.REDACT
    assert result.redacted_text is not None
    assert "***" in result.redacted_text
    assert result.redacted_text != text


def test_scan_warn_action() -> None:
    scanner = _make_scanner(ScanAction.WARN)
    result = scanner.scan("password=supersecret123!")
    assert result.detected
    assert result.action == ScanAction.WARN
    assert result.redacted_text is None


# ── edge cases ─────────────────────────────────────────────────────────


def test_scan_clean_text_passes() -> None:
    scanner = _make_scanner()
    result = scanner.scan("The quick brown fox jumps over the lazy dog.")
    assert not result.detected
    assert result.match_count == 0


def test_scan_mixed_content() -> None:
    scanner = _make_scanner(ScanAction.BLOCK)
    text = "Safe text here. My token is ghp_abcdefghijklmnopqrstuvwxyzABCDEFGHIJ. More safe text."
    result = scanner.scan(text)
    assert result.detected
    assert result.match_count >= 1


def test_scan_empty_string() -> None:
    scanner = _make_scanner()
    result = scanner.scan("")
    assert not result.detected


def test_scan_multiple_matches() -> None:
    scanner = _make_scanner()
    text = "AWS=AKIAIOSFODNN7EXAMPLE and GitHub=ghp_abcdefghijklmnopqrstuvwxyzABCDEFGHIJ"
    result = scanner.scan(text)
    assert result.detected
    assert result.match_count >= 2


def test_scan_result_bool() -> None:
    clean = ScanResult(detected=False, action=ScanAction.WARN)
    dirty = ScanResult(detected=True, action=ScanAction.BLOCK, matched_patterns=["api_key_generic"], match_count=1)
    assert not clean
    assert dirty


def test_scan_action_enum_values() -> None:
    assert ScanAction.BLOCK.value == "block"
    assert ScanAction.REDACT.value == "redact"
    assert ScanAction.WARN.value == "warn"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__])
