"""tests/claw/test_exceptions.py — NEXUSCLAW error hierarchy."""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from nexus_os.claw.exceptions import (
    CLINotFoundError,
    ClawError,
    ConfigIntegrityError,
    LockError,
    ParseError,
    PolicyDeniedError,
    PolicyError,
    PolicyNotApprovedError,
    RetryableError,
    SecretDetectedError,
    SubprocessError,
    SubprocessTimeoutError,
    UnsupportedAgentError,
)


def test_claw_error_base() -> None:
    err = ClawError("something went wrong", component="retry")
    assert err.message == "something went wrong"
    assert err.context["component"] == "retry"


def test_subprocess_error_attributes() -> None:
    err = SubprocessError("command failed", command="ls /nonexistent", stderr="No such file", stdout="", returncode=1)
    assert isinstance(err, ClawError)
    assert err.context["command"] == "ls /nonexistent"
    assert err.context["returncode"] == 1
    assert err.context["stderr"] == "No such file"


def test_subprocess_timeout_error() -> None:
    err = SubprocessTimeoutError("timeout", command="sleep 100", timeout=30.0)
    assert isinstance(err, SubprocessError)
    assert err.context["timeout"] == 30.0


def test_cli_not_found_error() -> None:
    err = CLINotFoundError("docker not on PATH", command="docker")
    assert isinstance(err, SubprocessError)


def test_parse_error() -> None:
    err = ParseError("unexpected JSON structure", raw_output="{broken")
    assert isinstance(err, ClawError)
    assert err.context["raw_output"] == "{broken"


def test_retryable_error_http_429() -> None:
    err = RetryableError("rate limited", http_status=429, retry_after=5.0)
    assert isinstance(err, ClawError)
    assert err.context["http_status"] == 429
    assert err.context["retry_after"] == 5.0


def test_retryable_error_http_503() -> None:
    err = RetryableError("service unavailable", http_status=503)
    assert err.context["http_status"] == 503


def test_non_retryable_not_instance() -> None:
    err = ParseError("syntax error")
    assert not isinstance(err, RetryableError)


def test_policy_denied_error() -> None:
    err = PolicyDeniedError("blocked by sandbox policy", policy="openclaw-sandbox", host="evil.com")
    assert isinstance(err, PolicyError)
    assert isinstance(err, ClawError)


def test_policy_not_approved_error() -> None:
    err = PolicyNotApprovedError("needs human approval", host="internal-tool.corp")
    assert isinstance(err, PolicyError)


def test_config_integrity_error() -> None:
    err = ConfigIntegrityError("openclaw.json hash mismatch", expected="abc123", actual="def456")
    assert isinstance(err, ClawError)
    assert err.context["expected"] == "abc123"


def test_secret_detected_error() -> None:
    err = SecretDetectedError("API key found in output", pattern="api_key_generic")
    assert isinstance(err, ClawError)
    assert err.context["pattern"] == "api_key_generic"


def test_lock_error_timeout() -> None:
    err = LockError("could not acquire lock within 60s", lock_path="/tmp/test.lock", timeout_ms=60000)
    assert isinstance(err, ClawError)
    assert err.context["timeout_ms"] == 60000


def test_unsupported_agent_error() -> None:
    err = UnsupportedAgentError("unknown runtime: wasm", runtime="wasm")
    assert isinstance(err, ClawError)


def test_error_inheritance_matrix() -> None:
    """Every concrete error is a ClawError."""
    all_errors = [
        ClawError,
        SubprocessError,
        SubprocessTimeoutError,
        CLINotFoundError,
        ParseError,
        RetryableError,
        PolicyError,
        PolicyDeniedError,
        PolicyNotApprovedError,
        ConfigIntegrityError,
        SecretDetectedError,
        LockError,
        UnsupportedAgentError,
    ]
    for err_cls in all_errors:
        assert issubclass(err_cls, ClawError), f"{err_cls.__name__} not subclass of ClawError"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__])
