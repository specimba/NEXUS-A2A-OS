"""Tests for NEXUS trace scrubber.

Pure unit tests — no network, no provider keys.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from nexus_os.relay.tracing.scrub import (
    scrub_text,
    scrub_messages,
    scrub_request_body,
    looks_classified,
    redacted_hash,
)


def test_scrub_redacts_openai_sk_key():
    text = "Here is my key: sk-proj-abc1234567890abcdefghijklmnop"
    out = scrub_text(text)
    assert "sk-proj-" not in out
    assert "[REDACTED_PROJECT_KEY]" in out


def test_scrub_redacts_loncat_ak_key():
    text = "ak_2NX8Y89gC6BE6j21SA2gj8II2bH8J is mine"
    out = scrub_text(text)
    assert "[REDACTED_LONGCAT_KEY]" in out


def test_scrub_redacts_nvidia_nvapi():
    text = "use nvapi-vPFF9nPHU63ewN3cYWkMH9abc as the api key"
    out = scrub_text(text)
    assert "[REDACTED_NVIDIA_KEY]" in out


def test_scrub_redacts_oauth_jwt():
    text = "eyJabc123def456ghi789jkl012mno.eyJabc123def456ghi789jkl012mno.eyJabc123def456ghi789jkl012mno"
    out = scrub_text(text)
    assert "[REDACTED_JWT]" in out


def test_scrub_redacts_email_with_fingerprint():
    text = "ping me at user@example.com please"
    out = scrub_text(text)
    assert "user@example.com" not in out
    assert "[REDACTED_EMAIL:" in out


def test_scrub_email_hard_mask():
    text = "ping me at user@example.com"
    out = scrub_text(text, fingerprint_emails=False)
    assert "user@example.com" not in out
    assert "[REDACTED_EMAIL]" in out


def test_scrub_redacts_ipv4_with_fingerprint():
    text = "server 192.168.1.42 is responding"
    out = scrub_text(text)
    assert "192.168.1.42" not in out
    assert "[REDACTED_IP:" in out


def test_scrub_preserves_normal_text():
    text = "Hello, the weather is nice today."
    out = scrub_text(text)
    assert out == text


def test_scrub_messages_handles_chat_array():
    msgs = [
        {"role": "system", "content": "You are a helpful oracle."},
        {"role": "user", "content": "Use my key sk-abc1234567890defghijklmnopqrstuvw"},
    ]
    out = scrub_messages(msgs)
    assert "sk-abc" not in out[1]["content"]
    assert "[REDACTED_API_KEY]" in out[1]["content"]
    assert out[0]["content"] == "You are a helpful oracle."


def test_scrub_request_body_removes_authorization():
    body = {
        "model": "demo",
        "api_key": "sk-secret-key-1234567890abcdef",
        "Authorization": "Bearer sk-secret-key-1234567890abcdef",
        "messages": [{"role": "user", "content": "Hi"}],
    }
    out = scrub_request_body(body)
    assert out["api_key"] == "[REDACTED]"
    assert out["Authorization"] == "[REDACTED]"
    assert out["messages"][0]["content"] == "Hi"


def test_looks_classified_detects_key():
    assert looks_classified("sk-proj-abc1234567890abcdefghij")
    assert looks_classified("ak_2NX8Y89gC6BE6j21SA2gj8II2bH8J")
    assert not looks_classified("Hello, world!")


def test_redacted_hash_is_deterministic():
    h1 = redacted_hash("user@example.com")
    h2 = redacted_hash("user@example.com")
    assert h1 == h2
    h3 = redacted_hash("different@example.com")
    assert h3 != h1


def test_redacted_hash_length_param():
    h = redacted_hash("foo@bar.com", length=12)
    assert len(h) == 12


def test_scrub_handles_none_input():
    assert scrub_text(None) == ""


def test_scrub_does_not_leak_in_tool_calls():
    body = {
        "model": "demo",
        "messages": [
            {"role": "user", "content": "Use sk-abc1234567890abcdefghij"}
        ],
        "tool_calls": [
            {"function": {"arguments": "{\"key\": \"sk-secret1234567890abcdef\"}"}}
        ],
    }
    out = scrub_request_body(body)
    j = out["tool_calls"][0]["function"]["arguments"]
    assert "sk-" not in j


# ── Slice-4 retrofit (T8/T4): header variants, real prefixes, flags ────

def test_scrub_request_body_removes_x_api_key_variants():
    payload = {
        "x-api-key": "real-key-value",
        "X-Api-Key": "real-key-value",
        "api-key": "real-key-value",
        "apiKey": "keep-me",  # camelCase not a header form; left as value
        "x-goog-api-key": "real-key-value",
        "model": "m",
    }
    out = scrub_request_body(payload)
    assert out["x-api-key"] == "[REDACTED]"
    assert out["X-Api-Key"] == "[REDACTED]"
    assert out["api-key"] == "[REDACTED]"
    assert out["x-goog-api-key"] == "[REDACTED]"
    assert out["model"] == "m"


def test_scrub_openrouter_real_prefix():
    # the pre-fix pattern was `sk_or_v1-` (underscore) and NEVER matched
    out = scrub_text("key sk-or-v1-" + "a" * 40)  # nexus-allow-secret-pattern
    assert "sk-or-v1-" not in out  # nexus-allow-secret-pattern
    assert "REDACTED" in out


def test_scrub_groq_key_still_redacted_after_deevasion():
    out = scrub_text("gsk_" + "Z" * 30)  # nexus-allow-secret-pattern
    assert out == "[REDACTED_GROQ_KEY]"


def test_scrub_text_with_flags_reports_rule_ids():
    from nexus_os.relay.tracing.scrub import scrub_text_with_flags

    text = ("mail me at op@example.com from 10.0.0.1 "
            "with nvapi-" + "x" * 30)
    out, flags = scrub_text_with_flags(text)
    assert "REDACTED_NVIDIA_KEY" in flags
    assert "REDACTED_EMAIL" in flags
    assert "REDACTED_IP" in flags
    assert "nvapi-" not in out

    clean_out, clean_flags = scrub_text_with_flags("nothing secret here")
    assert clean_flags == [] and clean_out == "nothing secret here"
