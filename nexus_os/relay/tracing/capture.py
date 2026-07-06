"""Trace capture middleware for NEXUS-Relay integration.

Provides a tiny side-channel that model_relay.py can call without restructuring
its existing call sites. The integration is intentionally additive:
existing callers receive new behavior only if they opt-in via:
    `from nexus_os.relay.tracing.capture import record_response`
"""

from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger("nexus.relay.tracing.capture")

_DISABLED_REASON: str | None = None
_DISABLED_WARNED = False
try:
    from nexus_os.relay.tracing.record import TraceWriter
    from nexus_os.relay.tracing.scrub import (
        scrub_text,
        scrub_text_with_flags,
        scrub_messages,
        looks_classified,
    )
    from nexus_os.relay.tracing.schema import (
        TraceRecord,
        ModelAttempt,
    )
except ImportError as exc:  # missing optional dep must NEVER silently
    _DISABLED_REASON = str(exc)  # brick capture with no trace in the logs


def _warn_disabled_once() -> None:
    global _DISABLED_WARNED
    if not _DISABLED_WARNED:
        logger.warning(
            "trace capture DISABLED: %s — traces are not being recorded",
            _DISABLED_REASON,
        )
        _DISABLED_WARNED = True


_HOME = Path(os.environ.get("NEXUS_REASONS_DB", Path.home() / ".nexus" / "reasons_db"))
_WRITER: "TraceWriter | None" = None


def _writer() -> TraceWriter:
    """Lazy singleton TraceWriter under $NEXUS_REASONS_DB or default."""
    global _WRITER
    if _WRITER is None:
        _WRITER = TraceWriter(base_dir=_HOME)
    return _WRITER


def reset_writer_for_tests(target: Path | None) -> None:
    """Test-only: monkey-patch the singleton writer's base directory."""
    global _WRITER
    if _WRITER is not None:
        _WRITER.close()
    _WRITER = TraceWriter(base_dir=target or _HOME)


def close_writer_for_tests() -> None:
    global _WRITER
    if _WRITER is not None:
        _WRITER.close()
        _WRITER = None


def record_response(
    *,
    provider: str,
    model_id: str,
    request_payload: dict[str, Any] | None,
    response_payload: dict[str, Any] | None,
    latency_ms: int,
    temperature: float | None,
    outcome: str = "ok",
    session_id: str | None = None,
    domain: str = "general",
    difficulty: str = "medium",
    tags: list[str] | None = None,
    cost_usd: float = 0.0,
    hallucination_verdict: dict[str, Any] | None = None,
) -> None | str:
    """Capture one provider response into the trace DB.

    Returns the new trace_id on persistence, or None if the response was
    classified as containing raw credentials and was discarded.
    """
    if _DISABLED_REASON is not None:
        _warn_disabled_once()
        return None
    if response_payload is None:
        return None
    choices = response_payload.get("choices") or []
    if not choices:
        return None
    first = choices[0]
    msg = first.get("message") or {}
    raw_message = msg.get("content") or ""
    raw_reasoning = msg.get("reasoning_content") or ""
    tool_calls = msg.get("tool_calls") or []
    finish_reason = first.get("finish_reason") or ""
    usage = response_payload.get("usage") or {}
    prompt_tokens = int(usage.get("prompt_tokens") or 0)
    completion_tokens = int(usage.get("completion_tokens") or 0)
    total_tokens = int(
        usage.get("total_tokens")
        or (prompt_tokens + completion_tokens)
    )

    message_clean, message_flags = scrub_text_with_flags(raw_message)
    if raw_reasoning:
        reasoning_clean, reasoning_flags = scrub_text_with_flags(raw_reasoning)
    else:
        reasoning_clean, reasoning_flags = None, []
    if looks_classified(message_clean) or looks_classified(reasoning_clean or ""):
        return None

    request_clean = _scrubbed_request(request_payload)
    subject_hash = _request_subject(request_clean)
    # Request-side redactions dirty the record too — the prompt is half
    # of any future training pair.
    request_flags: list[str] = []
    if request_payload and isinstance(request_payload.get("messages"), list):
        for m in request_payload["messages"]:
            if isinstance(m, dict) and isinstance(m.get("content"), str):
                request_flags.extend(scrub_text_with_flags(m["content"])[1])
    redaction_flags = sorted(set(message_flags) | set(reasoning_flags) | set(request_flags))

    evaluator_score = None
    if hallucination_verdict:
        try:
            evaluator_score = float(hallucination_verdict.get("risk_score"))
        except (TypeError, ValueError):
            evaluator_score = None

    attempt = ModelAttempt(
        provider=provider,
        model_id=model_id,
        temperature=float(temperature or 0.0),
        max_tokens=(request_clean or {}).get("max_tokens"),
        reasoning_content=reasoning_clean,
        message_content=message_clean,
        tool_calls=[
            scrub_messages(tc if isinstance(tc, list) else [tc])
            for tc in tool_calls
        ],
        finish_reason=finish_reason,
        latency_ms=latency_ms,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        cost_usd=cost_usd,
        outcome=outcome,
        evaluator_score=evaluator_score,
    )
    record = TraceRecord(
        session_id=session_id,
        domain=domain,
        difficulty=difficulty,
        tags=list(tags or []),
        request_subject=subject_hash,
        models_tried=[attempt],
        outcome=outcome,
        anonymization="applied",
        prompt_hash=_prompt_hash(request_clean),
        hallucination_verdict=hallucination_verdict,
        redaction_flags=redaction_flags,
    )
    try:
        writer = _writer()
        writer.append(record)
    except (OSError, ValueError, RuntimeError):
        return None
    return record.trace_id


def _prompt_hash(request_clean: dict[str, Any] | None) -> str:
    """sha256 over the full SCRUBBED message concat — dedup/join key."""
    if not request_clean or "messages" not in request_clean:
        return ""
    parts = []
    for m in request_clean["messages"] or []:
        if isinstance(m, dict):
            parts.append(str(m.get("role", "")))
            parts.append(str(m.get("content", "")))
    if not parts:
        return ""
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()


def _scrubbed_request(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if payload is None:
        return None
    if "messages" in payload:
        return {
            **payload,
            "messages": scrub_messages(payload["messages"]),
        }
    return payload


def _request_subject(payload: dict[str, Any] | None) -> str:
    """A short, anonymous summary of the request.

    Used as a LIKE-searchable field. We never include full bodies.
    """
    if not payload or "messages" not in payload:
        return "scrubbed"
    body = payload["messages"][-1].get("content") if payload["messages"] else ""
    if not isinstance(body, str):
        return "scrubbed"
    cleaned = scrub_text(body).strip()
    return cleaned[:200] if cleaned else "scrubbed"
