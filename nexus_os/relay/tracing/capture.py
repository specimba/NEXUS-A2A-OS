"""Trace capture middleware for NEXUS-Relay integration.

Provides a tiny side-channel that model_relay.py can call without restructuring
its existing call sites. The integration is intentionally additive:
existing callers receive new behavior only if they opt-in via:
    `from nexus_os.relay.tracing.capture import record_response`
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from nexus_os.relay.tracing.record import TraceWriter
from nexus_os.relay.tracing.scrub import (
    scrub_text,
    scrub_messages,
    looks_classified,
)
from nexus_os.relay.tracing.schema import (
    TraceRecord,
    ModelAttempt,
)


_HOME = Path(os.environ.get("NEXUS_REASONS_DB", Path.home() / ".nexus" / "reasons_db"))
_WRITER: TraceWriter | None = None


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
) -> None | str:
    """Capture one provider response into the trace DB.

    Returns the new trace_id on persistence, or None if the response was
    classified as containing raw credentials and was discarded.
    """
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

    message_clean = scrub_text(raw_message)
    reasoning_clean = scrub_text(raw_reasoning) if raw_reasoning else None
    if looks_classified(message_clean) or looks_classified(reasoning_clean or ""):
        return None

    request_clean = _scrubbed_request(request_payload)
    subject_hash = _request_subject(request_clean)

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
    )
    try:
        writer = _writer()
        writer.append(record)
    except (OSError, ValueError, RuntimeError):
        return None
    return record.trace_id


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
