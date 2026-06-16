"""NEXUSCLAW worklog integration.

V0 writes directly to the 8-channel memory manager, keeps an honest in-memory
ARCHIVIST handoff queue, and only mutates markdown audit files when explicitly
enabled by the caller.
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from uuid import uuid4

from nexus_os.vault.memory_channels import MemoryChannelManager, get_manager


@dataclass
class WorklogSinkResult:
    """Result for one worklog sink write."""

    sink: str
    success: bool
    detail: str
    error: Optional[str] = None
    records_written: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sink": self.sink,
            "success": self.success,
            "detail": self.detail,
            "error": self.error,
            "records_written": self.records_written,
        }


@dataclass
class WorklogEntry:
    """Single agent worklog entry."""

    timestamp: str
    agent_id: str
    task_id: str
    intent: str
    status: str
    duration_ms: float
    evidence: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    entry_id: str = field(default_factory=lambda: str(uuid4()))

    def to_markdown_line(self) -> str:
        return (
            f"- `{self.timestamp}` | **{self.agent_id}** | "
            f"{self.intent} -> `{self.status}` | "
            f"{self.duration_ms:.0f}ms | {self.task_id}"
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "timestamp": self.timestamp,
            "agent_id": self.agent_id,
            "task_id": self.task_id,
            "intent": self.intent,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "evidence": self.evidence,
            "metadata": self.metadata,
        }


class WorklogSystem:
    """Governed worklog fan-out for NEXUSCLAW.

    Default construction never writes AGENTS.md/SKILLS.md/SOUL.md. Markdown
    writes require ``markdown_enabled=True`` and a caller-provided repo root,
    keeping daemon/unit-test paths from mutating canonical docs by accident.
    """

    def __init__(
        self,
        memory_channels: Optional[MemoryChannelManager] = None,
        repo_root: Optional[Path] = None,
        markdown_enabled: bool = False,
        memory_trust_score: float = 100.0,
        archivist_queue_enabled: bool = True,
    ) -> None:
        self.memory_channels = memory_channels or get_manager()
        self.repo_root = Path(repo_root) if repo_root is not None else Path.cwd()
        self.markdown_enabled = markdown_enabled
        self.memory_trust_score = memory_trust_score
        self.archivist_queue_enabled = archivist_queue_enabled
        self._entries: List[WorklogEntry] = []
        self._archivist_queue: List[Dict[str, Any]] = []
        self._lock = threading.RLock()

    def log_task(
        self,
        agent_id: str,
        task_id: str,
        intent: str,
        status: str,
        duration_ms: float,
        evidence: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> WorklogEntry:
        """Record a task action and expose every sink result in metadata."""
        with self._lock:
            entry = WorklogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                agent_id=agent_id,
                task_id=task_id,
                intent=intent,
                status=status,
                duration_ms=duration_ms,
                evidence=evidence or [],
                metadata=dict(metadata or {}),
            )

            sink_results: List[WorklogSinkResult] = []
            sink_results.extend(self._write_to_memory(entry))
            sink_results.append(self._queue_for_archivist(entry))
            sink_results.extend(self._append_to_markdown(entry))

            entry.metadata["sink_results"] = [result.to_dict() for result in sink_results]
            entry.metadata["all_sinks_ok"] = all(result.success for result in sink_results)
            self._entries.append(entry)
            return entry

    def queue_depth(self) -> int:
        """Return the number of records waiting for ARCHIVIST handoff."""
        with self._lock:
            return len(self._archivist_queue)

    def get_archivist_queue(self, clear_processed: bool = False) -> List[Dict[str, Any]]:
        """Return and optionally drain the V0 in-memory ARCHIVIST queue.

        When ``clear_processed=True``, atomically returns the queue and clears it,
        preventing unbounded growth. Default ``False`` preserves backward compatibility.
        """
        with self._lock:
            snapshot = list(self._archivist_queue)
            if clear_processed:
                self._archivist_queue.clear()
            return snapshot

    def get_recent(self, n: int = 10) -> List[WorklogEntry]:
        """Return the N most recent worklog entries."""
        with self._lock:
            return self._entries[-n:]

    def to_json(self) -> str:
        """Serialize all entries to JSON."""
        with self._lock:
            return json.dumps([entry.to_dict() for entry in self._entries], indent=2)

    def _write_to_memory(self, entry: WorklogEntry) -> List[WorklogSinkResult]:
        """Write directly to EPISODIC, TASK, and META memory channels."""

        token_count = int(entry.metadata.get("token_count", 0) or 0)
        return [
            self._call_memory_sink(
                "memory:episodic",
                self.memory_channels.append_episodic,
                agent_id=entry.agent_id,
                content=entry.to_markdown_line(),
                outcome=entry.status,
                duration_ms=entry.duration_ms,
                token_count=token_count,
                trace_id=entry.entry_id,
                project_id=entry.metadata.get("project_id"),
            ),
            self._call_memory_sink(
                "memory:task",
                self.memory_channels.append_task,
                agent_id=entry.agent_id,
                task_id=entry.task_id,
                task_status=entry.status,
                content=entry.intent,
                trust_score=self.memory_trust_score,
                trace_id=entry.entry_id,
            ),
            self._call_memory_sink(
                "memory:meta",
                self.memory_channels.append_meta,
                agent_id=entry.agent_id,
                meta_type="worklog_status",
                meta_value=1.0
                if entry.status.lower() in {"ok", "success", "complete", "completed"}
                else 0.0,
                content=f"{entry.intent} -> {entry.status}",
                trust_score=self.memory_trust_score,
                trace_id=entry.entry_id,
            ),
        ]

    def _call_memory_sink(self, sink: str, fn: Any, **kwargs: Any) -> WorklogSinkResult:
        try:
            record = fn(**kwargs)
        except Exception as exc:
            return WorklogSinkResult(
                sink=sink,
                success=False,
                detail="memory write failed",
                error=f"{type(exc).__name__}: {exc}",
            )

        if record is None:
            return WorklogSinkResult(
                sink=sink,
                success=False,
                detail="memory write denied or returned no record",
            )
        return WorklogSinkResult(
            sink=sink,
            success=True,
            detail="memory write accepted",
            records_written=1,
        )

    def _queue_for_archivist(self, entry: WorklogEntry) -> WorklogSinkResult:
        """Queue worklog evidence for a future real ARCHIVIST adapter."""

        if not self.archivist_queue_enabled:
            return WorklogSinkResult(
                sink="archivist:v0_queue",
                success=True,
                detail="deferred by config",
            )

        self._archivist_queue.append(
            {
                "queued_at": datetime.now(timezone.utc).isoformat(),
                "source": "nexusclaw.worklog",
                "status": "queued_in_memory",
                "record": entry.to_dict(),
            }
        )
        return WorklogSinkResult(
            sink="archivist:v0_queue",
            success=True,
            detail="queued in memory",
            records_written=1,
        )

    def _append_to_markdown(self, entry: WorklogEntry) -> List[WorklogSinkResult]:
        if not self.markdown_enabled:
            return [
                WorklogSinkResult(
                    sink="markdown",
                    success=True,
                    detail="disabled",
                )
            ]

        targets = (
            ("AGENTS.md", "## Agent Worklog"),
            ("SKILLS.md", "## Skill Worklog"),
            ("SOUL.md", "## Soul Worklog"),
        )
        return [
            self._append_to_file(self.repo_root / filename, entry, section)
            for filename, section in targets
        ]

    def _append_to_file(
        self,
        file_path: Path,
        entry: WorklogEntry,
        section: str,
    ) -> WorklogSinkResult:
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            if file_path.exists():
                lines = file_path.read_text(encoding="utf-8").splitlines()
                created_file = False
            else:
                lines = [f"# {file_path.stem}", ""]
                created_file = True

            lower_section = section.casefold()
            section_index = self._find_section(lines, lower_section)
            created_section = section_index is None

            if section_index is None:
                if lines and lines[-1].strip():
                    lines.extend(["", section, ""])
                else:
                    lines.extend([section, ""])
                insert_at = len(lines)
            else:
                insert_at = section_index + 1
                while insert_at < len(lines) and not lines[insert_at].strip():
                    insert_at += 1

            lines.insert(insert_at, entry.to_markdown_line())
            file_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

            if created_file:
                detail = "created file and appended"
            elif created_section:
                detail = "created section and appended"
            else:
                detail = "appended"
            return WorklogSinkResult(
                sink=f"markdown:{file_path.name}",
                success=True,
                detail=detail,
                records_written=1,
            )
        except Exception as exc:
            return WorklogSinkResult(
                sink=f"markdown:{file_path.name}",
                success=False,
                detail="markdown append failed",
                error=f"{type(exc).__name__}: {exc}",
            )

    def _find_section(self, lines: Iterable[str], lower_section: str) -> Optional[int]:
        for index, line in enumerate(lines):
            if line.strip().casefold() == lower_section:
                return index
        return None


# Singleton instance
_worklog_instance: Optional[WorklogSystem] = None


def get_worklog(
    memory_channels: Optional[MemoryChannelManager] = None,
    repo_root: Optional[Path] = None,
    markdown_enabled: bool = False,
    memory_trust_score: float = 100.0,
    archivist_queue_enabled: bool = True,
) -> WorklogSystem:
    """Get the singleton WorklogSystem instance."""
    global _worklog_instance
    if _worklog_instance is None:
        _worklog_instance = WorklogSystem(
            memory_channels=memory_channels,
            repo_root=repo_root,
            markdown_enabled=markdown_enabled,
            memory_trust_score=memory_trust_score,
            archivist_queue_enabled=archivist_queue_enabled,
        )
    return _worklog_instance
