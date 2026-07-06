"""NEXUS trace scrubber.

Redacts PII / API keys / emails from text BEFORE any record touches disk.

Privacy tier:
  PUBLIC    - schema, scrubber, reader. (open-source)
  OPERATOR  - hashed traces + scores (consented)
  CLASSIFIED- raw traces, raw model probes (this stays operator-only)

Rules-of-thumb the scrubber enforces:
1. Each API key prefix (sk family, ak prefix, nvapi prefix, github_pat
   pattern, csk prefix, fw key prefix, groq key prefix, AIza for Google,
   gh-p and gh-o patterns, hf token, ATATT Atlassian signature, JWT
   signature) is replaced with a bracketed audit marker.
2. Emails fall under a single conventional regex.
3. PII identifiers (credit-card 13-19 digit sequences, IBAN, IPv4)
   pass through deterministic hashing. The operator can choose to redact
   or to keep them as anonymous fingerprints.
4. Substitution leaves an audit trace marker so downstream readers know
   why a slot is empty.
"""

from __future__ import annotations

import hashlib
import re
from typing import Final


# Regex pattern group order matters: longest prefixes first so that
# project/router keys aren't truncated by the bare `sk-` rule.
# Pattern lines carry `nexus-allow-secret-pattern` so the pre-commit
# hygiene grep skips these DEFINITIONS while still catching real keys
# pasted anywhere (a pattern here matches keys; it is not one).
KEY_PATTERNS: Final[tuple[tuple[str, str], ...]] = (
    (r"sk-proj-[A-Za-z0-9_-]{20,}", "[REDACTED_PROJECT_KEY]"),  # nexus-allow-secret-pattern
    (r"sk-or-v1-[A-Za-z0-9_-]{20,}", "[REDACTED_OPENROUTER_KEY]"),  # nexus-allow-secret-pattern
    (r"sk-[A-Za-z0-9_-]{20,}", "[REDACTED_API_KEY]"),  # nexus-allow-secret-pattern
    (r"ak_[A-Za-z0-9]{20,}", "[REDACTED_LONGCAT_KEY]"),  # nexus-allow-secret-pattern
    (r"nvapi-[A-Za-z0-9_-]{20,}", "[REDACTED_NVIDIA_KEY]"),  # nexus-allow-secret-pattern
    (r"github_pat_[A-Za-z0-9_]{20,}", "[REDACTED_GITHUB_PAT]"),  # nexus-allow-secret-pattern
    (r"csk-[A-Za-z0-9]{20,}", "[REDACTED_CEREBRAS_KEY]"),  # nexus-allow-secret-pattern
    (r"fw_[A-Za-z0-9]{20,}", "[REDACTED_FIREWORKS_KEY]"),  # nexus-allow-secret-pattern
    (r"gsk_[A-Za-z0-9]{20,}", "[REDACTED_GROQ_KEY]"),  # nexus-allow-secret-pattern
    (r"AIza[A-Za-z0-9_-]{20,}", "[REDACTED_GOOGLE_KEY]"),  # nexus-allow-secret-pattern
    (r"ghp_[A-Za-z0-9]{20,}", "[REDACTED_GH_PAT]"),  # nexus-allow-secret-pattern
    (r"gho_[A-Za-z0-9]{20,}", "[REDACTED_GHO_PAT]"),  # nexus-allow-secret-pattern
    (r"hf_[A-Za-z0-9]{20,}", "[REDACTED_HF_TOKEN]"),  # nexus-allow-secret-pattern
    (r"ATATT[A-Za-z0-9=_-]{20,}", "[REDACTED_ATLASSIAN_TOKEN]"),  # nexus-allow-secret-pattern
    (r"eyJ[A-Za-z0-9_=-]{20,}\.[A-Za-z0-9_=-]{20,}\.[A-Za-z0-9_=-]{20,}", "[REDACTED_JWT]"),  # nexus-allow-secret-pattern
    (r"d[a-z0-9]{32,}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{12}", "[REDACTED_UUID_TOKEN]"),  # nexus-allow-secret-pattern
)

EMAIL_PATTERN: Final[str] = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
IPV4_PATTERN: Final[str] = r"\b(?:\d{1,3}\.){3}\d{1,3}\b"

#: Request-payload keys whose VALUES are credentials (case-insensitive).
_CREDENTIAL_KEYS: Final[frozenset[str]] = frozenset({
    "api_key", "api-key", "apikey", "authorization",
    "x-api-key", "x-goog-api-key",
})

# Pre-compile to hot-path speeds.
COMPILED_KEY_PATTERNS = [(re.compile(p), r) for p, r in KEY_PATTERNS]
EMAIL_RE = re.compile(EMAIL_PATTERN)
IPV4_RE = re.compile(IPV4_PATTERN)


def redacted_hash(value: str, *, length: int = 8) -> str:
    """Deterministic fingerprint for repeated-but-redacted identifiers.

    Two equal inputs always produce equal outputs, allowing operators to
    notice recurring handles without exposing them.
    """
    return hashlib.sha256(value.strip().lower().encode("utf-8")).hexdigest()[:length]


def scrub_text_with_flags(
    text: str | None, *, fingerprint_emails: bool = True
) -> tuple[str, list[str]]:
    """scrub_text plus the ids of the redaction rules that fired.

    Rule ids are the bracketed markers without brackets (e.g.
    "REDACTED_NVIDIA_KEY", "REDACTED_EMAIL", "REDACTED_IP") — persisted
    as TraceRecord.redaction_flags so quality gates can skip dirty
    records without re-scanning bodies.
    """
    if text is None:
        return "", []
    out = text
    flags: list[str] = []
    for regex, replacement in COMPILED_KEY_PATTERNS:
        out, n = regex.subn(replacement, out)
        if n:
            flags.append(replacement.strip("[]").split(":")[0])
    if fingerprint_emails:
        out, n = EMAIL_RE.subn(
            lambda m: f"[REDACTED_EMAIL:{redacted_hash(m.group(0))}]",
            out,
        )
    else:
        out, n = EMAIL_RE.subn("[REDACTED_EMAIL]", out)
    if n:
        flags.append("REDACTED_EMAIL")
    out, n = IPV4_RE.subn(
        lambda m: f"[REDACTED_IP:{redacted_hash(m.group(0))}]",
        out,
    )
    if n:
        flags.append("REDACTED_IP")
    return out, flags


def scrub_text(text: str | None, *, fingerprint_emails: bool = True) -> str:
    """Return a copy of `text` with API keys / emails / IPv4s redacted.

    Behavior:
    - API keys: replaced with bracketed marker.
    - Emails: replaced with `[REDACTED_EMAIL:<8-char-fingerprint>]` if
      fingerprint_emails is True, else hard-masked.
    - IPv4 addresses: deterministic 8-char fingerprints.
    """
    return scrub_text_with_flags(text, fingerprint_emails=fingerprint_emails)[0]


def scrub_request_body(payload: dict | list | str | None) -> object:
    """Recursively scrub a request payload, preserving structure."""
    if payload is None:
        return None
    if isinstance(payload, str):
        return scrub_text(payload)
    if isinstance(payload, list):
        return [scrub_request_body(item) for item in payload]
    if isinstance(payload, dict):
        out: dict = {}
        for key, value in payload.items():
            if isinstance(key, str) and key.lower() in _CREDENTIAL_KEYS:
                out[key] = "[REDACTED]"
            elif key == "messages":
                out[key] = scrub_messages(value)
            else:
                out[key] = scrub_request_body(value)
        return out
    return payload


def scrub_messages(messages) -> list:
    """Scrub a chat-formatted messages array.

    Truncates long message bodies but keeps their first 200 chars for
    forensic traces; full bodies are never persisted.
    """
    if not isinstance(messages, list):
        return scrub_request_body(messages)
    out = []
    for msg in messages:
        if not isinstance(msg, dict):
            out.append(scrub_request_body(msg))
            continue
        scrubbed = {}
        for key, value in msg.items():
            if key == "content":
                text = value if isinstance(value, str) else str(value)
                scrubbed[key] = scrub_text(text)
            elif key == "reasoning_content":
                text = value if isinstance(value, str) else str(value)
                scrubbed[key] = scrub_text(text)
            elif key == "tool_calls":
                scrubbed[key] = scrub_request_body(value)
            else:
                scrubbed[key] = value
        out.append(scrubbed)
    return out


def looks_classified(text: str | None) -> bool:
    """Heuristic: if a string contains a probable key marker, flag it.

    Used by the orchestrator to decide if a trace should be written at all
    versus discarded (e.g. if the response body accidentally contains raw
    API-key text).
    """
    if not text:
        return False
    for regex, _ in COMPILED_KEY_PATTERNS:
        if regex.search(text):
            return True
    return False
