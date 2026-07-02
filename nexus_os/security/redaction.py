"""Central secret redaction for NEXUS OS (roadmap P1-10).

Operator directive 2026-07-02: the free-tier provider keys are NOT rotated —
they are the live routing substrate. The compensating control is redaction:
anything that leaves process memory for a durable or visible surface (log
lines, ARCHIVIST dossiers, exported payloads) passes through :func:`redact`.

Two layers, both fail-toward-redacting:

1. **Value-based** — every secret value currently resolvable from the same
   sources :mod:`nexus_os.security.secrets` uses (``*_API_KEY``/``*_TOKEN``/
   ``*_SECRET`` env vars, ``~/.nexus/secrets.json``, ``~/.modelrelay.json``
   apiKeys) is replaced wherever it appears.
2. **Pattern-based** — key-shaped strings (nvapi-, sk-, hf_, ghp_, Bearer,
   Slack xox, Google AIza, JWTs) are replaced even when no store knows them.

Values are never logged, not even at DEBUG.
"""
from __future__ import annotations

import logging
import os
import re
import time
from typing import Any, Dict, List, Pattern

from nexus_os.security.secrets import _modelrelay_config_path, _read_json, _vault_path

__all__ = [
    "redact",
    "redact_obj",
    "known_secret_values",
    "RedactionFilter",
    "install_log_redaction",
]

REDACTED = "[REDACTED:{label}]"

#: Secret values shorter than this are ignored for value-based redaction —
#: replacing 4-char strings everywhere would shred ordinary text.
MIN_SECRET_LENGTH = 8

#: Env var names that look secret-bearing.
_ENV_NAME_RE = re.compile(r"(API_?KEY|TOKEN|SECRET|PASSWORD|PASSKEY)", re.IGNORECASE)

#: Key-shaped token patterns (label, compiled regex).
_PATTERNS: List[tuple[str, Pattern[str]]] = [
    ("nvidia", re.compile(r"nvapi-[A-Za-z0-9_-]{20,}")),
    ("openai-style", re.compile(r"sk-[A-Za-z0-9_-]{20,}")),
    ("huggingface", re.compile(r"hf_[A-Za-z0-9]{20,}")),
    ("github", re.compile(r"(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}")),
    ("github-pat", re.compile(r"github_pat_[A-Za-z0-9_]{20,}")),
    ("slack", re.compile(r"xox[bapr]-[A-Za-z0-9-]{10,}")),
    ("google", re.compile(r"AIza[0-9A-Za-z_-]{30,}")),
    ("jwt", re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
    ("bearer", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{16,}")),
]

_CACHE_TTL_S = 60.0
_cache_values: Dict[str, str] = {}
_cache_at: float = 0.0


def known_secret_values(refresh: bool = False) -> Dict[str, str]:
    """Map of live secret value -> label, from every source get_secret reads.

    Cached for a minute — the redactor sits on hot logging paths. Lookup
    failures contribute nothing (a missing store must not disable the
    pattern layer).
    """
    global _cache_values, _cache_at
    now = time.time()
    if not refresh and _cache_values and (now - _cache_at) < _CACHE_TTL_S:
        return _cache_values

    values: Dict[str, str] = {}
    try:
        for name, val in os.environ.items():
            if _ENV_NAME_RE.search(name) and isinstance(val, str) and len(val) >= MIN_SECRET_LENGTH:
                values[val] = f"env:{name}"
    except Exception:  # pragma: no cover - environ access is near-infallible
        pass
    try:
        for name, val in _read_json(_vault_path()).items():
            if isinstance(val, str) and len(val) >= MIN_SECRET_LENGTH:
                values[val] = f"vault:{name}"
    except Exception:
        pass
    try:
        api_keys = _read_json(_modelrelay_config_path()).get("apiKeys", {})
        if isinstance(api_keys, dict):
            for slug, val in api_keys.items():
                if isinstance(val, str) and len(val) >= MIN_SECRET_LENGTH:
                    values[val] = f"apiKeys:{slug}"
    except Exception:
        pass

    _cache_values, _cache_at = values, now
    return values


def redact(text: str) -> str:
    """Replace every known secret value and key-shaped token in *text*."""
    if not text:
        return text
    out = str(text)
    # Longest values first so overlapping secrets can't leave fragments.
    for value, label in sorted(known_secret_values().items(), key=lambda kv: -len(kv[0])):
        if value in out:
            out = out.replace(value, REDACTED.format(label=label))
    for label, pattern in _PATTERNS:
        out = pattern.sub(REDACTED.format(label=label), out)
    return out


def redact_obj(obj: Any) -> Any:
    """Recursively redact strings inside dicts/lists/tuples (payload-safe)."""
    if isinstance(obj, str):
        return redact(obj)
    if isinstance(obj, dict):
        return {k: redact_obj(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [redact_obj(v) for v in obj]
    if isinstance(obj, tuple):
        return tuple(redact_obj(v) for v in obj)
    return obj


class RedactionFilter(logging.Filter):
    """Logging filter that redacts the fully-formatted message.

    Attach to handlers (filters on handlers see every record they emit):
        for h in logging.getLogger().handlers:
            h.addFilter(RedactionFilter())
    """

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:
            return True
        redacted = redact(message)
        if redacted != message:
            record.msg = redacted
            record.args = ()
        return True


def install_log_redaction(logger: logging.Logger | None = None) -> None:
    """Attach a RedactionFilter to every handler of *logger* (default root).

    Idempotent — repeated calls do not stack filters.
    """
    target = logger or logging.getLogger()
    for handler in target.handlers:
        if not any(isinstance(f, RedactionFilter) for f in handler.filters):
            handler.addFilter(RedactionFilter())
