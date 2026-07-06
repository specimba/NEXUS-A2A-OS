"""NEXUS trace schema definitions.

Per-attempt and per-record dataclasses. Compatibility-only with model_relay.py
return shape; consumers should never read raw provider bytes through this
module — scrub.py is the bypass-proof per-record sanitizer.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any


def uuid_v7() -> str:
    """Generate a UUIDv7-like time-ordered identifier.

    The shape is time_ms-hex + random_hex padded to RFC 4122 v4-like form.
    Not strict RFC v7, but sortable and unique-enough for trace keys.
    """
    ts_ms = int(time.time() * 1000)
    rand_hi = uuid.uuid4().hex[:12]
    rand_lo = uuid.uuid4().bytes[:6].hex()
    return f"{ts_ms:013x}-{rand_hi}-{rand_lo}"


@dataclass
class ModelAttempt:
    """One provider/model/api attempt within a session turn."""
    provider: str
    model_id: str
    temperature: float = 0.0
    max_tokens: int | None = None
    reasoning_content: str | None = None
    message_content: str | None = None
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    finish_reason: str | None = None
    latency_ms: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    outcome: str = "unknown"
    evaluator_score: float | None = None

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TraceRecord:
    """One NEXUS-call's full footprint."""
    trace_id: str = field(default_factory=uuid_v7)
    ts: float = field(default_factory=time.time)
    session_id: str | None = None
    domain: str = "general"
    difficulty: str = "medium"
    tags: list[str] = field(default_factory=list)
    request_subject: str = "scrubbed"
    models_tried: list[ModelAttempt] = field(default_factory=list)
    outcome: str = "pending"
    anonymization: str = "applied"
    notes: list[str] = field(default_factory=list)
    # FI-T schema fields (defaults keep pre-existing JSONL readable)
    prompt_hash: str = ""  # sha256 of the full SCRUBBED message concat
    hallucination_verdict: dict[str, Any] | None = None
    license_class: str = "unknown"  # permissive|restricted|unknown — unknown never trains
    generation_lineage: str = "organic"  # organic|synthetic|distilled — collapse guard
    redaction_flags: list[str] = field(default_factory=list)
    dedup_cluster_id: str | None = None

    def to_json(self) -> dict[str, Any]:
        out = asdict(self)
        out["models_tried"] = [m.to_json() for m in self.models_tried]
        return out

    @staticmethod
    def from_json(payload: dict[str, Any]) -> "TraceRecord":
        attempts = [
            ModelAttempt(**a) for a in payload.pop("models_tried", [])
        ]
        base = {k: v for k, v in payload.items() if k != "models_tried"}
        return TraceRecord(models_tried=attempts, **base)


def encode_line(record: TraceRecord) -> bytes:
    """Single-line JSON for append-only JSONL storage."""
    return (json.dumps(record.to_json(), ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
