"""Incremental grounding scanner and supervisor."""

from __future__ import annotations

import hashlib
import os
import time
from pathlib import Path
from typing import Iterable

from .models import GroundingEvent, GroundingLifecycle
from .papers import build_paper_card
from .store import GroundingStore


EXCLUDED_PARTS = {
    ".git",
    ".nexus_pi",
    ".kilo",
    ".nexus-worktrees",
    ".venv",
    "backups",
    "models",
    "scratch",
    "upload",
    "venv",
    ".tmp",
    "__pycache__",
    "node_modules",
    ".next",
    "vendor",
}
SENSITIVE_NAMES = {".env", "cookies", "login data", "web data"}
SENSITIVE_SUFFIXES = {".key", ".pem", ".pfx", ".p12"}


def default_source_roots() -> dict[str, Path]:
    home = Path.home()
    return {
        "archivist": home / "Downloads" / "ARCHIVIST",
        "nexuslogs": home / "Downloads" / "NEXUSlogs",
        "papers": home / "Downloads" / "ARCHIVIST" / "PAPERS",
        "nexus": home / "Documents" / "NEXUS",
    }


def is_sensitive_or_excluded(path: Path) -> bool:
    lowered_parts = {part.casefold() for part in path.parts}
    if lowered_parts & EXCLUDED_PARTS:
        return True
    if path.name.casefold() in SENSITIVE_NAMES:
        return True
    return path.suffix.casefold() in SENSITIVE_SUFFIXES


def source_kind(path: Path) -> str:
    suffix = path.suffix.casefold()
    if suffix == ".pdf":
        return "paper"
    if suffix in {".txt", ".log"}:
        return "agent_log"
    if suffix in {".py", ".ts", ".tsx", ".js", ".ps1"}:
        return "code"
    if suffix in {".md", ".rst"}:
        return "documentation"
    if suffix in {".json", ".jsonl", ".csv", ".parquet"}:
        return "data"
    return "artifact"


def content_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class GroundingService:
    def __init__(
        self,
        store: GroundingStore | None = None,
        roots: dict[str, Path] | None = None,
        agent_id: str = "grounding_service",
        project_id: str = "default",
        intent: str = "run incremental grounding scan, retrieve files, delete tombstones, and update grounding database",
        clearance: str = "maintainer",
    ) -> None:
        self.store = store or GroundingStore()
        self.roots = default_source_roots() if roots is None else roots
        self.agent_id = agent_id
        self.project_id = project_id
        self.intent = intent
        self.clearance = clearance

    def check_kaiju_authorization(self, action: str) -> None:
        """KAIJU gate checking. Raises PermissionError if denied/held."""
        from nexus_os.governor.kaiju_auth import KaijuAuthorizer, AuthRequest, ScopeLevel, ImpactLevel, ClearanceLevel, Decision
        
        authorizer = KaijuAuthorizer()
        
        scope_enum = ScopeLevel.CROSS_PROJECT
        impact_enum = ImpactLevel.MEDIUM if action in ("write", "delete", "ingest") else ImpactLevel.LOW
        
        try:
            clearance_enum = ClearanceLevel(self.clearance)
        except ValueError:
            # Hard-fail default: an unrecognized clearance must never be
            # silently upgraded to a privileged level.
            raise PermissionError(
                f"KAIJU authorization denied for action '{action}': "
                f"unknown clearance {self.clearance!r}"
            )

        req = AuthRequest(
            agent_id=self.agent_id,
            project_id=self.project_id,
            action=action,
            scope=scope_enum,
            intent=self.intent,
            impact=impact_enum,
            clearance=clearance_enum,
        )
        result = authorizer.authorize(req)
        if result.decision != Decision.ALLOW:
            raise PermissionError(f"KAIJU authorization denied for action '{action}': {result.reason}")

    def _stable_stat(self, path: Path, delay_seconds: float) -> os.stat_result | None:
        try:
            first = path.stat()
            if delay_seconds:
                time.sleep(delay_seconds)
            second = path.stat()
        except (FileNotFoundError, OSError):
            return None
        if (first.st_size, first.st_mtime_ns) != (second.st_size, second.st_mtime_ns):
            return None
        return second

    def ingest_path(
        self,
        source_id: str,
        path: Path,
        *,
        stability_delay_seconds: float = 2.0,
    ) -> GroundingEvent | None:
        self.check_kaiju_authorization("write")
        return self._ingest_path_authorized(
            source_id, path, stability_delay_seconds=stability_delay_seconds
        )

    def _ingest_path_authorized(
        self,
        source_id: str,
        path: Path,
        *,
        stability_delay_seconds: float = 2.0,
    ) -> GroundingEvent | None:
        """Ingest without re-checking KAIJU. Internal only — callers must have
        already passed the write gate (e.g. reconcile checks once per batch)."""
        path = Path(path)
        root = self.roots.get(source_id)
        try:
            policy_path = path.relative_to(root) if root else Path(path.name)
        except ValueError:
            policy_path = Path(path.name)
        if not path.is_file() or is_sensitive_or_excluded(policy_path):
            return None
        stat = self._stable_stat(path, stability_delay_seconds)
        if stat is None:
            return None
        prior = self.store.file_state(path)
        if prior and prior["size"] == stat.st_size and prior["mtime_ns"] == stat.st_mtime_ns:
            return None

        digest = content_hash(path)
        if prior and prior["content_hash"] == digest:
            return None
        event = GroundingEvent(
            source_id=source_id,
            path=str(path),
            size=stat.st_size,
            mtime_ns=stat.st_mtime_ns,
            content_hash=digest,
            source_kind=source_kind(path),
            lifecycle_state=GroundingLifecycle.CLASSIFIED.value,
            parent_event_id=prior["last_event_id"] if prior else None,
        )
        self.store.append(event)

        if event.source_kind == "paper":
            card = build_paper_card(path, event_id=event.event_id)
            self.store.append_card(card)
            card_event = GroundingEvent(
                source_id=source_id,
                path=str(path),
                size=stat.st_size,
                mtime_ns=stat.st_mtime_ns,
                content_hash=digest,
                source_kind="source_card",
                evidence_grade=card["evidence_grade"],
                lifecycle_state=GroundingLifecycle.SOURCE_CARDED.value,
                parent_event_id=event.event_id,
                trace_id=event.trace_id,
                metadata=card,
            )
            self.store.append(card_event)
        return event

    def ingest_delete(
        self,
        source_id: str,
        path: Path,
        *,
        old_path: Path | None = None,
    ) -> GroundingEvent | None:
        self.check_kaiju_authorization("delete")
        path = Path(path)
        prior = self.store.file_state(path)
        if prior is None:
            return None
        event = GroundingEvent(
            source_id=source_id,
            path=str(path),
            size=0,
            mtime_ns=0,
            content_hash=prior["content_hash"],
            source_kind="tombstone",
            evidence_grade="E1",
            lifecycle_state=GroundingLifecycle.RECONCILED.value,
            parent_event_id=prior["last_event_id"],
            metadata={"event_type": "rename" if old_path else "delete",
                      "old_path": str(old_path) if old_path else None},
        )
        self.store.append(event)

        self.store.forget_path(path)
        return event
    def reconcile(
        self,
        *,
        changed_only: bool = True,
        stability_delay_seconds: float = 0.0,
        max_files: int | None = None,
    ) -> dict[str, object]:
        self.check_kaiju_authorization("execute")
        self.check_kaiju_authorization("write")
        discovered = 0
        ingested = 0
        skipped_roots: list[str] = []
        cards: list[dict[str, object]] = []
        for source_id, root in self.roots.items():
            if not root.exists():
                skipped_roots.append(str(root))
                continue
            for path in root.rglob("*"):
                if not path.is_file():
                    continue
                discovered += 1
                event = self._ingest_path_authorized(
                    source_id,
                    path,
                    stability_delay_seconds=stability_delay_seconds,
                )
                if event:
                    ingested += 1
                    if event.source_kind == "paper":
                        cards.append(build_paper_card(path, event_id=event.event_id))
                if max_files and discovered >= max_files:
                    break
            if max_files and discovered >= max_files:
                break
        proposal = self.store.create_proposal(cards)
        return {
            "status": "ok",
            "changed_only": changed_only,
            "discovered": discovered,
            "ingested": ingested,
            "proposal": str(proposal) if proposal else None,
            "skipped_roots": skipped_roots,
            "store": self.store.status(),
        }

    def watch(self, poll_seconds: int = 30) -> None:
        """Continuously reconcile on every poll.

        Each pass is incremental (file-state manifest short-circuits
        unchanged files), giving the missed-event recovery semantics
        required of native directory watchers.
        """
        while True:
            self.reconcile(stability_delay_seconds=0.0)
            time.sleep(max(1, poll_seconds))
