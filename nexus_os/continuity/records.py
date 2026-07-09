"""Append-only continuity ledger for agent and browser-AI runs.

The ledger is intentionally simple JSONL. It is the durable handoff substrate
for "what changed, what was verified, and what should happen next" without
rewriting canonical docs or old `.nexus_pi` state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterable, Mapping


SCHEMA_VERSION = "nexus.continuity.run.v1"


class ProgressClass(str, Enum):
    NOOP_RECAP = "NOOP_RECAP"
    ADVISORY_ONLY = "ADVISORY_ONLY"
    EVIDENCE_DELTA = "EVIDENCE_DELTA"
    IMPLEMENTED_DELTA = "IMPLEMENTED_DELTA"
    VERIFIED_DELTA = "VERIFIED_DELTA"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_ledger_path() -> Path:
    configured = os.environ.get("NEXUS_CONTINUITY_LEDGER")
    if configured:
        return Path(configured)
    local = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / ".nexus")))
    return local / "NEXUS" / "continuity" / "runs.jsonl"


def stable_fingerprint(*parts: str) -> str:
    digest = hashlib.sha256()
    for part in parts:
        digest.update(part.encode("utf-8", errors="replace"))
        digest.update(b"\0")
    return "sha256:" + digest.hexdigest()


def classify_progress(
    *,
    input_fingerprint: str | None,
    output_fingerprint: str | None,
    artifact_paths: Iterable[str] = (),
    tests: Iterable[str] = (),
    provider_calls: int = 0,
    blocker: str | None = None,
    implemented: bool = False,
    advisory_only: bool = False,
) -> ProgressClass:
    artifacts = tuple(p for p in artifact_paths if p)
    test_rows = tuple(t for t in tests if t)
    if test_rows:
        return ProgressClass.VERIFIED_DELTA
    if implemented or artifacts:
        return ProgressClass.IMPLEMENTED_DELTA
    if advisory_only or blocker:
        return ProgressClass.ADVISORY_ONLY
    if provider_calls > 0:
        return ProgressClass.EVIDENCE_DELTA
    if input_fingerprint and output_fingerprint and input_fingerprint != output_fingerprint:
        return ProgressClass.EVIDENCE_DELTA
    return ProgressClass.NOOP_RECAP


@dataclass(frozen=True)
class ContinuityRunRecord:
    run_id: str
    agent_id: str
    source_lane: str
    input_fingerprint: str | None = None
    output_fingerprint: str | None = None
    progress_class: str = ProgressClass.NOOP_RECAP.value
    artifact_paths: tuple[str, ...] = ()
    tests: tuple[str, ...] = ()
    provider_calls: int = 0
    quota_reserved: int = 0
    blocker: str | None = None
    next_action: str | None = None
    started_at: str = field(default_factory=utc_now)
    completed_at: str | None = None
    memory_routes: tuple[str, ...] = ("EPISODIC", "TASK", "META")
    schema: str = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "run_id": self.run_id,
            "agent_id": self.agent_id,
            "source_lane": self.source_lane,
            "input_fingerprint": self.input_fingerprint,
            "output_fingerprint": self.output_fingerprint,
            "progress_class": self.progress_class,
            "artifact_paths": list(self.artifact_paths),
            "tests": list(self.tests),
            "provider_calls": self.provider_calls,
            "quota_reserved": self.quota_reserved,
            "blocker": self.blocker,
            "next_action": self.next_action,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "memory_routes": list(self.memory_routes),
        }

    @classmethod
    def from_mapping(cls, item: Mapping[str, Any]) -> "ContinuityRunRecord":
        run_id = str(item.get("run_id", ""))
        if not run_id:
            raise ValueError("ContinuityRunRecord.from_mapping: run_id must be non-empty")
        return cls(
            run_id=run_id,
            agent_id=str(item.get("agent_id", "")),
            source_lane=str(item.get("source_lane", "")),
            input_fingerprint=item.get("input_fingerprint"),
            output_fingerprint=item.get("output_fingerprint"),
            progress_class=str(item.get("progress_class", ProgressClass.NOOP_RECAP.value)),
            artifact_paths=tuple(str(v) for v in item.get("artifact_paths", []) or ()),
            tests=tuple(str(v) for v in item.get("tests", []) or ()),
            provider_calls=int(item.get("provider_calls", 0) or 0),
            quota_reserved=int(item.get("quota_reserved", 0) or 0),
            blocker=item.get("blocker"),
            next_action=item.get("next_action"),
            started_at=str(item.get("started_at", "")),
            completed_at=item.get("completed_at"),
            memory_routes=tuple(str(v) for v in item.get("memory_routes", []) or ("EPISODIC", "TASK", "META")),
            schema=str(item.get("schema", SCHEMA_VERSION)),
        )


def append_record(record: ContinuityRunRecord, path: str | Path | None = None) -> Path:
    ledger = Path(path) if path else default_ledger_path()
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record.to_dict(), sort_keys=True, separators=(",", ":")) + "\n")
    return ledger


def read_records(path: str | Path | None = None, *, limit: int | None = None) -> tuple[list[ContinuityRunRecord], dict[str, Any]]:
    ledger = Path(path) if path else default_ledger_path()
    meta: dict[str, Any] = {"path": str(ledger), "exists": ledger.exists(), "corrupt_tail": False, "errors": []}
    if not ledger.exists():
        return [], meta
    records: list[ContinuityRunRecord] = []
    with ledger.open("r", encoding="utf-8") as handle:
        if limit is not None:
            from collections import deque
            line_iter: Iterable = deque(handle, maxlen=limit)
        else:
            line_iter = handle
        for index, line in enumerate(line_iter, start=1):
            if not line.strip():
                continue
            try:
                records.append(ContinuityRunRecord.from_mapping(json.loads(line)))
            except (json.JSONDecodeError, ValueError) as exc:
                meta["corrupt_tail"] = True
                meta["errors"].append({"line": index, "error": str(exc)})
    return records, meta


def summarize_records(records: Iterable[ContinuityRunRecord]) -> dict[str, Any]:
    rows = list(records)
    progress_counts: dict[str, int] = {}
    provider_calls = 0
    blockers: dict[str, int] = {}
    for record in rows:
        progress_counts[record.progress_class] = progress_counts.get(record.progress_class, 0) + 1
        provider_calls += record.provider_calls
        if record.blocker:
            blockers[record.blocker] = blockers.get(record.blocker, 0) + 1
    return {
        "record_count": len(rows),
        "progress_counts": progress_counts,
        "provider_calls": provider_calls,
        "blockers": blockers,
        "last_record": rows[-1].to_dict() if rows else None,
    }


def records_since(records: Iterable[ContinuityRunRecord], *, hours: float) -> list[ContinuityRunRecord]:
    threshold = datetime.now(timezone.utc) - timedelta(hours=hours)
    selected: list[ContinuityRunRecord] = []
    for record in records:
        stamp = record.completed_at or record.started_at
        try:
            parsed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        except ValueError:
            continue
        if parsed >= threshold:
            selected.append(record)
    return selected


def legacy_state_refs(repo_root: Path | None = None) -> list[dict[str, Any]]:
    roots = []
    if repo_root:
        roots.append(repo_root / ".nexus_pi" / "state")
    roots.append(Path.home() / ".nexus_pi" / "state")
    refs: list[dict[str, Any]] = []
    seen: set[str] = set()
    for root in roots:
        if str(root) in seen:
            continue
        seen.add(str(root))
        if not root.exists():
            refs.append({"path": str(root), "exists": False, "files": []})
            continue
        files = [
            {
                "path": str(path),
                "size": path.stat().st_size,
                "mtime": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat().replace("+00:00", "Z"),
            }
            for path in sorted(root.glob("*.json"))
        ]
        refs.append({"path": str(root), "exists": True, "files": files})
    return refs
