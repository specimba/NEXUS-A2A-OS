"""nexus_os/user_profile/protocol.py — File organization protocol execution engine.

Implements the execution logic for tidyness rules: auto-clone, cleanup, index, organize.
All operations are logged to worklog and memory channels, and are designed to be:
  - Safe: originals are never modified, only cloned/moved with tracking
  - Auditable: every operation is logged with evidence
  - Reversible: clone operations are tracked, cleanup operations require backup
  - Governed: rules must be ENABLED before execution, DRAFT rules are advisory only
"""

from __future__ import annotations

import fnmatch
import logging
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from nexus_os.user_profile.preferences import (
    AutoCloneRule,
    CleanupRule,
    IndexRule,
    ProfileRuleSet,
    RuleStatus,
    FileScope,
    UserProfile,
)
from nexus_os.nexusclaw.worklog import WorklogSystem

logger = logging.getLogger("nexusclaw.user_profile.protocol")


@dataclass
class CloneOperation:
    """Record of a single file clone operation."""
    source: str
    destination: str
    success: bool
    error: Optional[str] = None
    bytes_copied: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "destination": self.destination,
            "success": self.success,
            "error": self.error,
            "bytes_copied": self.bytes_copied,
            "timestamp": self.timestamp,
        }


@dataclass
class RuleExecutionResult:
    """Result of executing a tidyness rule."""
    rule_id: str
    rule_type: str
    success: bool
    operations: List[CloneOperation] = field(default_factory=list)
    files_processed: int = 0
    files_skipped: int = 0
    errors: List[str] = field(default_factory=list)
    manifest_path: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "rule_type": self.rule_type,
            "success": self.success,
            "operations": [op.to_dict() for op in self.operations],
            "files_processed": self.files_processed,
            "files_skipped": self.files_skipped,
            "errors": self.errors,
            "manifest_path": self.manifest_path,
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms,
        }


class FileOrganizationProtocol:
    """Execute tidyness rules with safety and governance.

    This is the engine that actually performs file operations based on user profile rules.
    It is designed to be safe:
      - Auto-clone: never modifies originals, only copies
      - Cleanup: requires backup before deletion (configurable)
      - All operations are logged and auditable
    """

    def __init__(self, worklog: Optional[WorklogSystem] = None) -> None:
        self.worklog = worklog or WorklogSystem()

    # ------------------------------------------------------------------
    # Auto-Clone Execution
    # ------------------------------------------------------------------

    def execute_clone_rule(self, rule: AutoCloneRule) -> RuleExecutionResult:
        """Execute an auto-clone rule: copy recent files from source to destination."""
        import time
        start = time.time()

        if rule.status != RuleStatus.ENABLED:
            return RuleExecutionResult(
                rule_id=rule.rule_id,
                rule_type="auto_clone",
                success=False,
                errors=[f"Rule {rule.rule_id} is not enabled (status={rule.status.value})"],
            )

        source_path = Path(rule.source_path)
        dest_path = Path(rule.destination_path)

        if not source_path.exists():
            return RuleExecutionResult(
                rule_id=rule.rule_id,
                rule_type="auto_clone",
                success=False,
                errors=[f"Source path does not exist: {source_path}"],
            )

        # Ensure destination exists
        dest_path.mkdir(parents=True, exist_ok=True)

        # Calculate time cutoff
        cutoff = datetime.now(timezone.utc) - timedelta(hours=rule.time_window_hours)

        # Find matching files
        matching_files = self._find_matching_files(
            source_path,
            rule.file_patterns,
            rule.exclude_patterns,
            cutoff if rule.file_scope == FileScope.RECENT_ONLY else None,
        )

        operations: List[CloneOperation] = []
        files_processed = 0
        files_skipped = 0
        errors: List[str] = []

        for src_file in matching_files:
            try:
                if rule.preserve_structure:
                    # Preserve relative path structure
                    rel_path = src_file.relative_to(source_path)
                    dest_file = dest_path / rel_path
                else:
                    dest_file = dest_path / src_file.name

                dest_file.parent.mkdir(parents=True, exist_ok=True)

                # Copy file (overwrite if newer)
                if dest_file.exists() and dest_file.stat().st_mtime >= src_file.stat().st_mtime:
                    files_skipped += 1
                    continue

                shutil.copy2(str(src_file), str(dest_file))
                bytes_copied = dest_file.stat().st_size

                operations.append(CloneOperation(
                    source=str(src_file),
                    destination=str(dest_file),
                    success=True,
                    bytes_copied=bytes_copied,
                ))
                files_processed += 1

            except Exception as e:
                error_msg = f"Failed to copy {src_file}: {e}"
                errors.append(error_msg)
                operations.append(CloneOperation(
                    source=str(src_file),
                    destination=str(dest_file) if 'dest_file' in locals() else "",
                    success=False,
                    error=error_msg,
                ))
                logger.warning(error_msg)

        # Generate manifest if requested
        manifest_path: Optional[str] = None
        if rule.create_manifest and files_processed > 0:
            manifest_path = self._generate_manifest(
                dest_path, rule, operations, files_processed, files_skipped, errors
            )

        # Log to worklog
        self._log_rule_execution(rule, files_processed, files_skipped, errors)

        duration_ms = (time.time() - start) * 1000

        return RuleExecutionResult(
            rule_id=rule.rule_id,
            rule_type="auto_clone",
            success=len(errors) == 0 or files_processed > 0,
            operations=operations,
            files_processed=files_processed,
            files_skipped=files_skipped,
            errors=errors,
            manifest_path=manifest_path,
            duration_ms=duration_ms,
        )

    def _find_matching_files(
        self,
        source_path: Path,
        patterns: List[str],
        exclude_patterns: List[str],
        cutoff: Optional[datetime] = None,
    ) -> List[Path]:
        """Find files matching patterns, excluding exclusions, optionally after cutoff."""
        matching: List[Path] = []

        # If no patterns specified, match all files
        if not patterns:
            patterns = ["*"]

        for pattern in patterns:
            for file_path in source_path.rglob(pattern):
                if not file_path.is_file():
                    continue

                # Check exclusions
                excluded = False
                for excl in exclude_patterns:
                    if fnmatch.fnmatch(str(file_path), excl) or file_path.match(excl):
                        excluded = True
                        break
                if excluded:
                    continue

                # Check time cutoff
                if cutoff is not None:
                    # Get modification time in UTC
                    mtime = datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc)
                    if mtime < cutoff:
                        continue

                matching.append(file_path)

        # Remove duplicates (same file matched by multiple patterns)
        seen: set = set()
        unique: List[Path] = []
        for fp in matching:
            if fp not in seen:
                seen.add(fp)
                unique.append(fp)

        return sorted(unique)

    def _generate_manifest(
        self,
        dest_path: Path,
        rule: AutoCloneRule,
        operations: List[CloneOperation],
        files_processed: int,
        files_skipped: int,
        errors: List[str],
    ) -> str:
        """Generate a MANIFEST.md file in the destination directory."""
        manifest_path = dest_path / "MANIFEST.md"

        manifest_content = f"""# Auto-Clone Manifest — {rule.name}

**Rule ID:** {rule.rule_id}
**Executed:** {datetime.now(timezone.utc).isoformat()}
**Source:** {rule.source_path}
**Destination:** {rule.destination_path}
**Time Window:** {rule.time_window_hours} hours

---

## Summary

| Metric | Value |
|--------|-------|
| Files Processed | {files_processed} |
| Files Skipped | {files_skipped} |
| Errors | {len(errors)} |
| Total Operations | {len(operations)} |

---

## Cloned Files

| Source | Destination | Size | Status |
|--------|-------------|------|--------|
"""
        for op in operations:
            status = "OK" if op.success else f"ERROR: {op.error}"
            size_str = f"{op.bytes_copied} B" if op.bytes_copied > 0 else "-"
            manifest_content += f"| `{op.source}` | `{op.destination}` | {size_str} | {status} |\n"

        if errors:
            manifest_content += "\n## Errors\n\n"
            for err in errors:
                manifest_content += f"- {err}\n"

        manifest_content += f"\n---\n*Auto-generated by NEXUS OS User Profile Preference Protocol*\n"

        manifest_path.write_text(manifest_content, encoding="utf-8")
        return str(manifest_path)

    # ------------------------------------------------------------------
    # Cleanup Execution (Placeholder — requires explicit enable for safety)
    # ------------------------------------------------------------------

    def execute_cleanup_rule(self, rule: CleanupRule) -> RuleExecutionResult:
        """Execute a cleanup rule. Currently returns advisory only (safety-first)."""
        if rule.status != RuleStatus.ENABLED:
            return RuleExecutionResult(
                rule_id=rule.rule_id,
                rule_type="cleanup",
                success=False,
                errors=[f"Rule {rule.rule_id} is not enabled (status={rule.status.value})"],
            )

        # Safety check: cleanup rules require explicit user confirmation
        # In v1, cleanup is report-only (dry-run)
        return RuleExecutionResult(
            rule_id=rule.rule_id,
            rule_type="cleanup",
            success=True,  # Dry-run success
            files_processed=0,
            errors=["Cleanup rules are currently dry-run only. Review required before execution."],
        )

    # ------------------------------------------------------------------
    # Index Execution (Placeholder — integrates with ARCHIVIST)
    # ------------------------------------------------------------------

    def execute_index_rule(self, rule: IndexRule) -> RuleExecutionResult:
        """Execute an index rule. Currently returns advisory only."""
        if rule.status != RuleStatus.ENABLED:
            return RuleExecutionResult(
                rule_id=rule.rule_id,
                rule_type="index",
                success=False,
                errors=[f"Rule {rule.rule_id} is not enabled (status={rule.status.value})"],
            )

        # In v1, index rules are advisory (suggest files for ARCHIVIST processing)
        source_path = Path(rule.source_path)
        if not source_path.exists():
            return RuleExecutionResult(
                rule_id=rule.rule_id,
                rule_type="index",
                success=False,
                errors=[f"Source path does not exist: {source_path}"],
            )

        cutoff = datetime.now(timezone.utc) - timedelta(hours=rule.time_window_hours)
        matching_files = self._find_matching_files(
            source_path,
            rule.file_patterns,
            [],
            cutoff,
        )

        return RuleExecutionResult(
            rule_id=rule.rule_id,
            rule_type="index",
            success=True,
            files_processed=0,  # Advisory only in v1
            errors=[f"Index advisory: {len(matching_files)} files match criteria. Submit to ARCHIVIST import stage for processing."],
        )

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def _log_rule_execution(
        self,
        rule: AutoCloneRule,
        files_processed: int,
        files_skipped: int,
        errors: List[str],
    ) -> None:
        """Log rule execution to worklog."""
        try:
            self.worklog.log_task(
                agent_id="nexusclaw-user-profile",
                task_id=rule.rule_id,
                intent=f"execute_clone_rule:{rule.name}",
                status="ok" if not errors else "partial",
                duration_ms=0.0,
                evidence=[f"Processed: {files_processed}, Skipped: {files_skipped}, Errors: {len(errors)}"],
                metadata={
                    "rule_type": "auto_clone",
                    "source_path": rule.source_path,
                    "destination_path": rule.destination_path,
                    "files_processed": files_processed,
                    "files_skipped": files_skipped,
                    "errors": errors,
                },
            )
        except Exception as e:
            logger.warning("Failed to log rule execution to worklog: %s", e)
