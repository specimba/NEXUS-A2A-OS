"""Incremental grounding scanner and supervisor."""

from __future__ import annotations

import hashlib
import os
import time
from pathlib import Path
from typing import Any, Iterable

from .models import GroundingEvent, GroundingLifecycle
from .papers import build_paper_card
from .store import GroundingStore


EXCLUDED_PARTS = {
    ".git",
    ".nexus_pi",
    ".kilo",
    ".pytest_cache",
    ".ruff_cache",
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
    "tests_tmp",
    "unsloth_compiled_cache",
}
SENSITIVE_NAMES = {".env", "cookies", "login data", "web data"}
SENSITIVE_SUFFIXES = {".key", ".pem", ".pfx", ".p12"}
_PRIOR_STATE_UNSET = object()


def default_source_roots() -> dict[str, Path]:
    """Resolve operator golden roots on Windows home or WSL /mnt/c mounts."""
    home = Path.home()
    candidates_by_id: dict[str, list[Path]] = {
        "archivist": [
            home / "Downloads" / "ARCHIVIST",
            Path("/mnt/c/Users/speci.000/Downloads/ARCHIVIST"),
            Path(os.environ["USERPROFILE"]) / "Downloads" / "ARCHIVIST"
            if os.environ.get("USERPROFILE")
            else None,
        ],
        "nexuslogs": [
            home / "Downloads" / "NEXUSlogs",
            Path("/mnt/c/Users/speci.000/Downloads/NEXUSlogs"),
            Path(os.environ["USERPROFILE"]) / "Downloads" / "NEXUSlogs"
            if os.environ.get("USERPROFILE")
            else None,
        ],
        "papers": [
            home / "Downloads" / "ARCHIVIST" / "PAPERS",
            Path("/mnt/c/Users/speci.000/Downloads/ARCHIVIST/PAPERS"),
            Path(os.environ["USERPROFILE"]) / "Downloads" / "ARCHIVIST" / "PAPERS"
            if os.environ.get("USERPROFILE")
            else None,
        ],
        "nexus": [
            home / "Documents" / "NEXUS",
            Path("/mnt/c/Users/speci.000/Documents/NEXUS"),
            Path(os.environ["USERPROFILE"]) / "Documents" / "NEXUS"
            if os.environ.get("USERPROFILE")
            else None,
        ],
    }
    roots: dict[str, Path] = {}
    for source_id, candidates in candidates_by_id.items():
        chosen: Path | None = None
        for candidate in candidates:
            if candidate is None:
                continue
            if candidate.exists():
                chosen = candidate
                break
            if chosen is None:
                chosen = candidate  # first non-null as display fallback
        roots[source_id] = chosen if chosen is not None else home / source_id
    return roots


def is_excluded_part(part: str) -> bool:
    lowered = str(part).casefold()
    return lowered in EXCLUDED_PARTS or lowered.startswith("pytest-cache-files-")


def is_sensitive_or_excluded(path: Path) -> bool:
    if any(is_excluded_part(part) for part in path.parts):
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


def iter_source_files(
    root: Path,
    *,
    excluded_roots: Iterable[Path] = (),
    scan_errors: list[str] | None = None,
) -> Iterable[Path]:
    """Yield eligible files without descending into excluded/unsafe trees.

    ``Path.rglob`` cannot prune before descent, so a nominally incremental
    scan still walked node_modules, worktrees, denied pytest caches, and nested
    source roots.  This scandir walk rejects those directories first, does not
    follow symlinks/reparse points, and contains per-directory failures.
    """
    root = Path(root)

    def key(path: Path) -> str:
        return os.path.normcase(os.path.abspath(os.fspath(path)))

    excluded_keys = {key(Path(path)) for path in excluded_roots}
    stack = [root]
    while stack:
        directory = stack.pop()
        try:
            with os.scandir(directory) as iterator:
                entries = sorted(iterator, key=lambda entry: entry.name.casefold())
        except OSError:
            if scan_errors is not None:
                scan_errors.append(str(directory))
            continue
        child_directories: list[Path] = []
        for entry in entries:
            if is_excluded_part(entry.name):
                continue
            path = Path(entry.path)
            if key(path) in excluded_keys:
                continue
            try:
                if entry.is_symlink():
                    continue
                if entry.is_dir(follow_symlinks=False):
                    child_directories.append(path)
                    continue
                if not entry.is_file(follow_symlinks=False):
                    continue
            except OSError:
                if scan_errors is not None:
                    scan_errors.append(str(path))
                continue
            try:
                policy_path = path.relative_to(root)
            except ValueError:
                policy_path = Path(path.name)
            if not is_sensitive_or_excluded(policy_path):
                yield path
        stack.extend(reversed(child_directories))


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
            if delay_seconds <= 0:
                return first
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
        prior_state: dict[str, Any] | None | object = _PRIOR_STATE_UNSET,
        known_file: bool = False,
    ) -> GroundingEvent | None:
        """Ingest without re-checking KAIJU. Internal only — callers must have
        already passed the write gate (e.g. reconcile checks once per batch)."""
        path = Path(path)
        root = self.roots.get(source_id)
        try:
            policy_path = path.relative_to(root) if root else Path(path.name)
        except ValueError:
            policy_path = Path(path.name)
        if (not known_file and not path.is_file()) or is_sensitive_or_excluded(policy_path):
            return None
        stat = self._stable_stat(path, stability_delay_seconds)
        if stat is None:
            return None
        prior = (
            self.store.file_state(path) if prior_state is _PRIOR_STATE_UNSET else prior_state
        )
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
        scan_errors: list[str] = []
        cards: list[dict[str, object]] = []
        snapshotter = getattr(self.store, "file_state_snapshot", None)
        prior_states = snapshotter() if callable(snapshotter) else None
        resolved_roots: dict[str, Path] = {}
        for source_id, root in self.roots.items():
            try:
                resolved_roots[source_id] = root.resolve(strict=False)
            except OSError:
                resolved_roots[source_id] = root.absolute()
        for source_id, root in self.roots.items():
            if not root.exists():
                skipped_roots.append(str(root))
                continue
            resolved_root = resolved_roots[source_id]
            nested_roots = []
            for other_id, other_root in resolved_roots.items():
                if other_id == source_id or other_root == resolved_root:
                    continue
                try:
                    if other_root.is_relative_to(resolved_root):
                        nested_roots.append(other_root)
                except (OSError, ValueError):
                    continue
            for path in iter_source_files(
                root,
                excluded_roots=nested_roots,
                scan_errors=scan_errors,
            ):
                discovered += 1
                event = self._ingest_path_authorized(
                    source_id,
                    path,
                    stability_delay_seconds=stability_delay_seconds,
                    known_file=True,
                    prior_state=(
                        prior_states.get(str(path))
                        if prior_states is not None
                        else _PRIOR_STATE_UNSET
                    ),
                )
                if event:
                    ingested += 1
                    if prior_states is not None:
                        prior_states[str(path)] = {
                            "size": event.size,
                            "mtime_ns": event.mtime_ns,
                            "content_hash": event.content_hash,
                            "last_event_id": event.event_id,
                        }
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
            "scan_errors": len(set(scan_errors)),
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
