"""Grounding event models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


class GroundingLifecycle(str, Enum):
    DISCOVERED = "discovered"
    CLASSIFIED = "classified"
    SOURCE_CARDED = "source_carded"
    RECONCILED = "reconciled"
    REJECTED = "rejected"
    QUEUED = "queued"


@dataclass(frozen=True)
class GroundingEvent:
    source_id: str
    path: str
    size: int
    mtime_ns: int
    content_hash: str
    source_kind: str
    evidence_grade: str = "E0"
    lifecycle_state: str = GroundingLifecycle.DISCOVERED.value
    trace_id: str = field(default_factory=lambda: uuid4().hex)
    parent_event_id: str | None = None
    observed_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    event_id: str = field(default_factory=lambda: f"ge-{uuid4().hex}")
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "GroundingEvent":
        known = {
            "source_id",
            "path",
            "size",
            "mtime_ns",
            "content_hash",
            "source_kind",
            "evidence_grade",
            "lifecycle_state",
            "trace_id",
            "parent_event_id",
            "observed_at",
            "event_id",
            "metadata",
        }
        return cls(**{key: value for key, value in payload.items() if key in known})
