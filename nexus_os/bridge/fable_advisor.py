"""Root-supplied Fable-5 advice normalization for the NEXUS SAGE boundary.

This module intentionally has no external process, tool, job-store, route, or
governor side effect.  A trusted root process may deliberately materialize a
bounded advisory receipt; downstream governance remains mandatory.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Any

from nexus_os.security import TerminalSanitizer


ROOT_ACTOR_ID = "nexus-root"
MAX_ADVICE_CHARS = 12_000
_TASK_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,95}$")
_SECRET_ASSIGNMENT = re.compile(
    r"\b(?:api[-_ ]?key|access[-_ ]?token|refresh[-_ ]?token|"
    r"client[-_ ]?secret|password|passwd|authorization)\b"
    r"\s*(?:=|:)\s*(?:bearer\s+)?[^\s,;\"'}]{6,}",
    re.IGNORECASE,
)
_VENDOR_TOKEN = re.compile(
    r"\b(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|"
    r"hf_[A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9-]{20,}|"
    r"AIza[A-Za-z0-9_-]{20,})\b"
)
_PLAN_DECISION = re.compile(r"\bPLAN_(?:APPROVED|REVISE)\b")

# There is deliberately no external advisor invocation in this boundary.
EXTERNAL_FABLE_INVOCATION_ENABLED = False


def build_root_supplied_fable_advisory(
    *,
    actor_id: str,
    task_id: str,
    advice_text: str,
) -> dict[str, Any]:
    """Return a redacted, advisory-only Fable receipt for one root call.

    ``actor_id`` is a trusted in-process identity from the root coordinator,
    not an API claim.  This helper is intentionally unreferenced by the SAGE
    HTTP routes and cannot set approval, execution, or gateway mode.
    """

    if actor_id != ROOT_ACTOR_ID:
        raise PermissionError("root authorization required")
    if not isinstance(task_id, str) or not _TASK_ID.fullmatch(task_id):
        raise ValueError("task_id must be a bounded safe identifier")
    if not isinstance(advice_text, str) or not advice_text.strip():
        raise ValueError("advice_text must be a non-empty string")
    if len(advice_text) > MAX_ADVICE_CHARS:
        raise ValueError(f"advice_text must be at most {MAX_ADVICE_CHARS} characters")

    sanitized = TerminalSanitizer.sanitize(unicodedata.normalize("NFKC", advice_text))
    redacted = _redact_advice(sanitized)
    raw_digest = hashlib.sha256(advice_text.encode("utf-8")).hexdigest()

    return {
        "schema": "nexus.sage-fable-advisory.v1",
        "task_id": task_id,
        "source": "root-supplied-fable5",
        "source_authority": "root_advisory_only",
        "advice_sha256": raw_digest,
        "advice_excerpt": redacted,
        "advice_chars": len(redacted),
        "redaction_applied": redacted != sanitized,
        "proposal_only": True,
        "execution_allowed": False,
        "approval_state": "pending",
        "human_approved": False,
        "mode": "observe_only",
        "advisor_decision_accepted": False,
        "governor_required": True,
        "automatic_invocation": False,
        "job_created": False,
        "operator_next_step": "Root may attach this receipt to a separately governed proposal.",
    }


def _redact_advice(value: str) -> str:
    """Return one bounded plain-text excerpt without credentials or verdicts."""

    redacted = _SECRET_ASSIGNMENT.sub("[REDACTED_SECRET]", value)
    redacted = _VENDOR_TOKEN.sub("[REDACTED_SECRET]", redacted)
    redacted = _PLAN_DECISION.sub("[ADVISORY_DECISION_REDACTED]", redacted)
    return " ".join(redacted.split())[:MAX_ADVICE_CHARS]
