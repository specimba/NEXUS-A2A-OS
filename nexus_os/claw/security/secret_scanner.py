"""High-confidence secret / credential scanner for CLAW data flows.

Scans text for secret patterns and supports three response actions:
  - BLOCK — reject the write entirely
  - REDACT — replace matched secrets with a placeholder
  - WARN — log a warning but allow the write to proceed
"""

from __future__ import annotations

import enum
import logging
import re
from typing import Iterator

logger = logging.getLogger(__name__)


class ScanAction(enum.Enum):
    BLOCK = "block"
    REDACT = "redact"
    WARN = "warn"


class ScanResult:
    """Result of scanning a piece of text for secrets."""

    def __init__(
        self,
        *,
        detected: bool,
        action: ScanAction,
        matched_patterns: list[str] = None,
        redacted_text: str | None = None,
        match_count: int = 0,
    ) -> None:
        self.detected = detected
        self.action = action
        self.matched_patterns = matched_patterns or []
        self.redacted_text = redacted_text
        self.match_count = match_count

    def __bool__(self) -> bool:
        return self.detected


# ── pattern tuples: (name, compiled_regex) ──────────────────────────────

_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("api_key_generic", re.compile(r"\b(sk-[\w-]{20,}|pk-[\w-]{20,}|[A-Za-z0-9]{32,64})\b")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
    ("aws_access_key", re.compile(r"\b(AKIA[0-9A-Z]{16}|ASIA[0-9A-Z]{16})\b")),
    ("github_token", re.compile(r"\b(ghp_|ghu_|ghs_|ghr_|gho_)[A-Za-z0-9_]{36,}\b")),
    ("slack_token", re.compile(r"\b(xox[baprs]-[0-9A-Za-z-]{10,})\b")),
    ("discord_token", re.compile(r"\b([MN][A-Za-z\d]{23}\.[A-Za-z\d]{6}\.[A-Za-z\d-]{27})\b")),
    ("telegram_bot_token", re.compile(r"\b(\d{8,10}:[A-Za-z0-9_-]{35,})\b")),
    ("private_key_pem", re.compile(r"-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----")),
    ("connection_string", re.compile(r"\b\w+://\w+:\w+@[\w.-]+:\d+/\w+\b")),
    ("password_field", re.compile(r"\b(password|passwd|pwd|secret)\s*[:=]\s*\S+", re.IGNORECASE)),
    ("bearer_token", re.compile(r"\bBearer\s+[A-Za-z0-9_-]{20,}\b")),
    ("generic_secret", re.compile(r"\b(secret|token|key|credential)\s*['\"]?=\s*['\"][A-Za-z0-9_\-]{16,}['\"]", re.IGNORECASE)),
]


class SecretScanner:
    """Scans text for high-confidence secret patterns."""

    ACTION_KEYWORD = "secret_scan_action"

    def __init__(self, action: ScanAction = ScanAction.BLOCK) -> None:
        self._action = action

    @property
    def action(self) -> ScanAction:
        return self._action

    @action.setter
    def action(self, value: ScanAction) -> None:
        self._action = value

    def scan(self, text: str) -> ScanResult:
        """Analyse *text* for secret patterns and return a ``ScanResult``."""
        matches: list[tuple[str, str]] = []
        for name, pattern in _PATTERNS:
            for m in pattern.finditer(text):
                matches.append((name, m.group()))

        if not matches:
            return ScanResult(detected=False, action=self._action)

        matched_names = list({n for n, _ in matches})
        redacted = text
        for _, raw in matches:
            redacted = redacted.replace(raw, "***")

        return ScanResult(
            detected=True,
            action=self._action,
            matched_patterns=matched_names,
            redacted_text=redacted if self._action == ScanAction.REDACT else None,
            match_count=len(matches),
        )

    def iter_scan(self, texts: Iterator[str]) -> Iterator[ScanResult]:
        """Lazily scan an iterator of text chunks."""
        for text in texts:
            yield self.scan(text)
