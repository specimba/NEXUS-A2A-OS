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
    schema_version: int = 1
    event_type: str = "observed"
    evidence_grade: str = "E0"
    lifecycle_state: str = GroundingLifecycle.DISCOVERED.value
    trace_id: str = field(default_factory=lambda: uuid4().hex)
    parent_event_id: str | None = None
    observed_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    event_id: str = field(default_factory=lambda: f"ge-{uuid4().hex}")
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.schema_version != 1:
            raise ValueError(f"Unsupported grounding schema: {self.schema_version}")
        if not self.event_id or not self.source_id or not self.path:
            raise ValueError("GroundingEvent identifiers and path are required")
        if self.size < 0 or self.mtime_ns < 0:
            raise ValueError("GroundingEvent size and mtime must be non-negative")
        if not self.content_hash or not self.source_kind:
            raise ValueError("GroundingEvent hash and source kind are required")

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
            "schema_version",
            "event_type",
            "evidence_grade",
            "lifecycle_state",
            "trace_id",
            "parent_event_id",
            "observed_at",
            "event_id",
            "metadata",
        }
        return cls(**{key: value for key, value in payload.items() if key in known})
