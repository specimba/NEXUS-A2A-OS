"""Read-only disk hygiene inventory for NEXUS operator workflows.

The scanner is intentionally conservative: it never deletes, moves, opens
files for content, or follows reparse points. It produces evidence that a
human/operator workflow can use before approving cleanup or migration.
"""

from __future__ import annotations

import heapq
import os
import platform
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


GIB = 1024 ** 3
MIB = 1024 ** 2
FILE_ATTRIBUTE_REPARSE_POINT = 0x400


def _is_reparse_stat(stat_result: os.stat_result) -> bool:
    attrs = getattr(stat_result, "st_file_attributes", 0)
    return bool(attrs & FILE_ATTRIBUTE_REPARSE_POINT)


@dataclass(frozen=True)
class PathSummary:
    path: str
    size_bytes: int
    files: int
    dirs: int
    errors: int
    latest_write: float | None
    category: str
    risk: str
    recommendation: str

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "size_gib": round(self.size_bytes / GIB, 3),
            "size_bytes": self.size_bytes,
            "files": self.files,
            "dirs": self.dirs,
            "errors": self.errors,
            "latest_write": _format_ts(self.latest_write),
            "category": self.category,
            "risk": self.risk,
            "recommendation": self.recommendation,
        }


@dataclass(frozen=True)
class FileCandidate:
    path: str
    size_bytes: int
    modified: float
    category: str
    risk: str
    recommendation: str

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "size_gib": round(self.size_bytes / GIB, 3),
            "size_bytes": self.size_bytes,
            "modified": _format_ts(self.modified),
            "category": self.category,
            "risk": self.risk,
            "recommendation": self.recommendation,
        }


@dataclass(frozen=True)
class DriveAccounting:
    drive: str
    total_bytes: int
    used_bytes: int
    free_bytes: int
    visible_bytes: int | None = None
    visible_scan_errors: int = 0
    source: str = "shutil.disk_usage"
    warning: str | None = None

    @property
    def hidden_gap_bytes(self) -> int | None:
        if self.visible_bytes is None:
            return None
        return self.used_bytes - self.visible_bytes

    def to_dict(self) -> dict:
        hidden_gap = self.hidden_gap_bytes
        return {
            "drive": self.drive,
            "total_gib": round(self.total_bytes / GIB, 3),
            "used_gib": round(self.used_bytes / GIB, 3),
            "free_gib": round(self.free_bytes / GIB, 3),
            "total_bytes": self.total_bytes,
            "used_bytes": self.used_bytes,
            "free_bytes": self.free_bytes,
            "visible_gib": None if self.visible_bytes is None else round(self.visible_bytes / GIB, 3),
            "visible_bytes": self.visible_bytes,
            "hidden_gap_gib": None if hidden_gap is None else round(hidden_gap / GIB, 3),
            "hidden_gap_bytes": hidden_gap,
            "visible_scan_errors": self.visible_scan_errors,
            "source": self.source,
            "warning": self.warning,
        }


@dataclass(frozen=True)
class CleanupReadiness:
    path: str
    size_bytes: int
    category: str
    risk: str
    cleanup_class: str
    requires_confirmation: bool
    protected: bool
    reason: str

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "size_gib": round(self.size_bytes / GIB, 3),
            "size_bytes": self.size_bytes,
            "category": self.category,
            "risk": self.risk,
            "cleanup_class": self.cleanup_class,
            "requires_confirmation": self.requires_confirmation,
            "protected": self.protected,
            "reason": self.reason,
        }


def _format_ts(ts: float | None) -> str | None:
    if ts is None:
        return None
    return time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(ts))


def classify_path(path: str) -> tuple[str, str, str]:
    """Classify cleanup risk from path shape only.

    The categories are intentionally broad and explain operator posture, not an
    authorization decision.
    """

    p = path.replace("/", "\\").lower()
    name = os.path.basename(p)

    if "\\windows\\" in p or p.endswith("\\windows") or name in {"pagefile.sys", "swapfile.sys", "hiberfil.sys"}:
        return ("system", "admin_only", "Do not delete manually; use Windows/system settings or admin diagnostics.")
    if "\\system volume information" in p:
        return ("system_shadow_storage", "admin_only", "Use elevated shadow-storage diagnostics; do not manual-delete.")
    if "\\.git\\objects" in p or "\\.git\\lfs\\objects" in p:
        return ("repo_git_storage", "high", "Review Git/LFS retention before pruning; never delete loose objects manually.")
    if "\\documents\\nexus\\models\\" in p or "\\documents\\nexus\\datasets\\" in p:
        return ("nexus_model_or_dataset", "high", "Move through NEXUS cold-storage policy, not ad-hoc deletion.")
    if "\\downloads\\nexuslogs" in p or "\\downloads\\archivist" in p:
        return ("nexus_evidence", "high", "Preserve unless source-carded and intentionally archived.")
    if "\\appdata\\local\\temp\\" in p or p.endswith("\\temp"):
        return ("temp", "medium", "Clean only when owning processes are stopped or file is stale.")
    if "\\npm-cache" in p or "\\_cacache" in p:
        return ("package_cache", "low", "Use package-manager-aware cache cleanup.")
    if "\\node_modules\\" in p or p.endswith("\\node_modules"):
        return ("global_tooling", "medium", "Uninstall retired global packages; do not delete active CLIs blindly.")
    if "\\.unsloth" in p:
        return ("ml_tool_cache", "medium", "Review for active training use; move or uninstall through tool workflow.")
    if "\\appdata\\local\\docker" in p or "\\.docker" in p:
        return ("docker_state", "high", "Use Docker-aware cleanup; do not delete VHDX while Docker/WSL is active.")
    if "\\appdata\\local\\wsl" in p or p.endswith(".vhdx"):
        return ("virtual_disk", "high", "Identify owner first; compact/move through WSL/Docker tooling.")
    if "\\chrome\\user data\\optguideondevicemodel" in p:
        return ("browser_on_device_model", "medium", "Candidate for browser feature/cache policy review.")
    if "\\downloads\\" in p:
        return ("downloads", "operator_review", "Personal/evidence mixed; sort by file, then approve explicit moves/deletes.")
    if p.startswith("c:\\myflaskai") or p.startswith("c:\\githubvs") or p.startswith("c:\\tmp"):
        return ("legacy_workspace", "medium", "Move to D: quarantine after operator approval.")
    if any(p.endswith(ext) for ext in (".gguf", ".safetensors", ".pth", ".onnx", ".parquet", ".arrow")):
        return ("model_or_dataset_file", "medium", "Check duplicate/canonical location before moving.")
    if any(p.endswith(ext) for ext in (".mp4", ".wav", ".zip", ".tar", ".cab", ".exe", ".iso")):
        return ("large_binary", "operator_review", "Review freshness and ownership before moving/deleting.")
    return ("general", "review", "Review owner, last-write time, and duplicate status.")


def summarize_path(path: Path) -> PathSummary:
    total = 0
    files = 0
    dirs = 0
    errors = 0
    latest: float | None = None

    if not path.exists():
        category, risk, recommendation = classify_path(str(path))
        return PathSummary(str(path), 0, 0, 0, 0, None, category, "missing", "Path does not exist.")

    try:
        if path.is_file():
            stat = path.stat()
            category, risk, recommendation = classify_path(str(path))
            return PathSummary(str(path), stat.st_size, 1, 0, 0, stat.st_mtime, category, risk, recommendation)
    except OSError:
        category, risk, recommendation = classify_path(str(path))
        return PathSummary(str(path), 0, 0, 0, 1, None, category, "unreadable", recommendation)

    stack = [str(path)]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    try:
                        entry_stat = entry.stat(follow_symlinks=False)
                        if entry.is_symlink() or _is_reparse_stat(entry_stat):
                            continue
                        if entry.is_dir(follow_symlinks=False):
                            dirs += 1
                            stack.append(entry.path)
                            modified = entry_stat.st_mtime
                            latest = modified if latest is None or modified > latest else latest
                        elif entry.is_file(follow_symlinks=False):
                            total += entry_stat.st_size
                            files += 1
                            latest = entry_stat.st_mtime if latest is None or entry_stat.st_mtime > latest else latest
                    except OSError:
                        errors += 1
        except OSError:
            errors += 1

    category, risk, recommendation = classify_path(str(path))
    return PathSummary(str(path), total, files, dirs, errors, latest, category, risk, recommendation)


def top_files(paths: Iterable[Path], *, min_size_mib: int = 100, limit: int = 100) -> tuple[list[FileCandidate], dict]:
    if limit <= 0:
        return [], {"scanned_files": 0, "errors": 0, "skipped": "limit_zero"}

    threshold = min_size_mib * MIB
    heap: list[tuple[int, float, str]] = []
    scanned = 0
    errors = 0

    for root in paths:
        if not root.exists():
            continue
        stack = [str(root)]
        while stack:
            current = stack.pop()
            try:
                current_stat = os.stat(current, follow_symlinks=False)
                if os.path.islink(current) or _is_reparse_stat(current_stat):
                    continue
                if os.path.isfile(current):
                    scanned += 1
                    if current_stat.st_size >= threshold:
                        row = (current_stat.st_size, current_stat.st_mtime, current)
                        if len(heap) < limit:
                            heapq.heappush(heap, row)
                        elif row[0] > heap[0][0]:
                            heapq.heapreplace(heap, row)
                    continue
                with os.scandir(current) as entries:
                    for entry in entries:
                        try:
                            entry_stat = entry.stat(follow_symlinks=False)
                            if entry.is_symlink() or _is_reparse_stat(entry_stat):
                                continue
                            if entry.is_dir(follow_symlinks=False):
                                stack.append(entry.path)
                            elif entry.is_file(follow_symlinks=False):
                                scanned += 1
                                if entry_stat.st_size >= threshold:
                                    row = (entry_stat.st_size, entry_stat.st_mtime, entry.path)
                                    if len(heap) < limit:
                                        heapq.heappush(heap, row)
                                    elif row[0] > heap[0][0]:
                                        heapq.heapreplace(heap, row)
                        except OSError:
                            errors += 1
            except OSError:
                errors += 1

    files = []
    for size, modified, path in sorted(heap, reverse=True):
        category, risk, recommendation = classify_path(path)
        files.append(FileCandidate(path, size, modified, category, risk, recommendation))
    return files, {"scanned_files": scanned, "errors": errors}


def default_targets(home: Path | None = None) -> list[Path]:
    home = home or Path.home()
    targets = [
        home / "AppData" / "Local",
        home / "AppData" / "Roaming",
        home / "Downloads",
        home / "Documents",
        home / ".cache",
        home / ".local",
        home / ".unsloth",
        home / ".ollama",
        Path("C:/MyFlaskAI"),
        Path("C:/tmp"),
        Path("C:/GitHubVs"),
    ]
    return targets


def root_system_files() -> list[Path]:
    if platform.system().lower() != "windows":
        return []
    return [Path("C:/pagefile.sys"), Path("C:/swapfile.sys"), Path("C:/hiberfil.sys")]


def _default_drive_labels() -> list[str]:
    if platform.system().lower() == "windows":
        return ["C:", "D:"]
    anchor = Path.cwd().anchor or "/"
    return [anchor]


def _drive_root(label: str) -> Path:
    if platform.system().lower() == "windows":
        normalized = label.rstrip("\\/")
        if len(normalized) == 1:
            normalized = f"{normalized}:"
        return Path(f"{normalized}\\")
    return Path(label)


def _visible_roots_size(paths: Iterable[Path]) -> tuple[int, int]:
    total = 0
    errors = 0
    for path in paths:
        summary = summarize_path(path)
        total += summary.size_bytes
        errors += summary.errors
    return total, errors


def collect_drive_accounting(
    *,
    drives: Iterable[str] | None = None,
    visible_roots: dict[str, Iterable[Path]] | None = None,
) -> list[DriveAccounting]:
    """Collect drive-level accounting without deleting or requiring admin tools.

    `visible_roots` is optional because full root traversal can be expensive.
    When provided, the report can compare filesystem-used bytes with visible
    logical bytes and surface hidden allocation gaps before cleanup is proposed.
    """

    rows: list[DriveAccounting] = []
    for label in drives or _default_drive_labels():
        root = _drive_root(str(label))
        drive_label = root.drive.upper() if root.drive else str(root)
        try:
            usage = shutil.disk_usage(root)
        except OSError as exc:
            rows.append(
                DriveAccounting(
                    drive=drive_label,
                    total_bytes=0,
                    used_bytes=0,
                    free_bytes=0,
                    warning=f"drive_unavailable: {exc}",
                )
            )
            continue

        visible_bytes = None
        visible_errors = 0
        if visible_roots and drive_label in visible_roots:
            visible_bytes, visible_errors = _visible_roots_size(visible_roots[drive_label])

        rows.append(
            DriveAccounting(
                drive=drive_label,
                total_bytes=usage.total,
                used_bytes=usage.used,
                free_bytes=usage.free,
                visible_bytes=visible_bytes,
                visible_scan_errors=visible_errors,
            )
        )
    return rows


def visible_roots_for_drives(drives: Iterable[str] | None = None) -> dict[str, list[Path]]:
    """Return first-level visible roots per drive for optional deep accounting."""

    roots: dict[str, list[Path]] = {}
    for label in drives or _default_drive_labels():
        root = _drive_root(str(label))
        drive_label = root.drive.upper() if root.drive else str(root)
        try:
            roots[drive_label] = [entry for entry in root.iterdir()]
        except OSError:
            roots[drive_label] = [root]
    return roots


def analyze_drive_accounting(
    rows: Iterable[DriveAccounting | dict],
    *,
    previous_report: dict | None = None,
    hidden_gap_threshold_gib: float = 25.0,
    free_delta_threshold_gib: float = 50.0,
) -> list[dict]:
    findings: list[dict] = []
    hidden_threshold = int(hidden_gap_threshold_gib * GIB)
    delta_threshold = int(free_delta_threshold_gib * GIB)

    previous_by_drive = {}
    if previous_report:
        for row in previous_report.get("drive_accounting", []):
            drive = row.get("drive")
            if drive:
                previous_by_drive[drive] = row

    for raw in rows:
        row = raw if isinstance(raw, dict) else raw.to_dict()
        drive = row.get("drive")
        if not drive:
            continue

        hidden_gap = row.get("hidden_gap_bytes")
        if isinstance(hidden_gap, int):
            if hidden_gap >= hidden_threshold:
                findings.append(
                    {
                        "severity": "warning",
                        "type": "hidden_space_unexplained",
                        "drive": drive,
                        "delta_gib": round(hidden_gap / GIB, 3),
                        "message": (
                            "Filesystem-used bytes exceed scanned visible bytes. "
                            "Run admin/VSS/USN diagnostics before deleting visible project or model files."
                        ),
                    }
                )
            elif hidden_gap <= -hidden_threshold:
                findings.append(
                    {
                        "severity": "info",
                        "type": "visible_logical_exceeds_allocated",
                        "drive": drive,
                        "delta_gib": round(hidden_gap / GIB, 3),
                        "message": (
                            "Visible logical file sizes exceed allocated drive usage; sparse/compressed files "
                            "or deduplicated/cache layouts may be involved."
                        ),
                    }
                )

        previous = previous_by_drive.get(drive)
        if previous:
            current_free = row.get("free_bytes")
            previous_free = previous.get("free_bytes")
            if isinstance(current_free, int) and isinstance(previous_free, int):
                free_delta = current_free - previous_free
                if abs(free_delta) >= delta_threshold:
                    direction = "increased" if free_delta > 0 else "decreased"
                    finding = {
                        "severity": "info" if free_delta > 0 else "warning",
                        "type": "material_free_space_delta",
                        "drive": drive,
                        "direction": direction,
                        "delta_gib": round(free_delta / GIB, 3),
                        "message": (
                            "Free-space changed materially since baseline. "
                            "Classify the cause before making cleanup decisions."
                        ),
                    }
                    current_visible = row.get("visible_bytes")
                    previous_visible = previous.get("visible_bytes")
                    if isinstance(current_visible, int) and isinstance(previous_visible, int):
                        visible_delta = current_visible - previous_visible
                        finding["visible_delta_gib"] = round(visible_delta / GIB, 3)
                        if free_delta > 0 and abs(visible_delta) < abs(free_delta) * 0.25:
                            finding["type"] = "hidden_allocation_release_likely"
                            finding["message"] = (
                                "Free space increased while scanned visible bytes stayed comparatively stable. "
                                "Investigate VSS, Windows Update cleanup, virtual disks, sparse files, or cache compaction."
                            )
                    findings.append(finding)

    return findings


def _cleanup_readiness_for(category: str, risk: str) -> tuple[str, bool, bool, str]:
    if risk == "admin_only" or category in {"system", "system_shadow_storage"}:
        return (
            "admin_diagnostic",
            False,
            True,
            "Do not delete manually; use elevated system diagnostics or OS-supported cleanup.",
        )
    if category in {
        "nexus_evidence",
        "nexus_model_or_dataset",
        "repo_git_storage",
        "docker_state",
        "virtual_disk",
    } or risk == "high":
        return (
            "protected_or_tool_managed",
            False,
            True,
            "Protected or tool-managed surface; inventory and owner-specific procedure required first.",
        )
    if category in {"package_cache", "temp", "browser_on_device_model"}:
        return (
            "ready_with_confirmation",
            True,
            False,
            "Likely reclaimable after owner/process check and explicit operator confirmation.",
        )
    if category in {
        "downloads",
        "legacy_workspace",
        "large_binary",
        "model_or_dataset_file",
        "ml_tool_cache",
        "global_tooling",
    }:
        return (
            "review_then_confirm",
            True,
            False,
            "Mixed-value content; rank by freshness/duplicates before approved move or delete.",
        )
    return (
        "needs_owner_review",
        True,
        False,
        "Unknown value; identify owner, freshness, and duplicate status before action.",
    )


def build_cleanup_readiness(summaries: Iterable[PathSummary]) -> dict:
    rows: list[CleanupReadiness] = []
    for summary in summaries:
        cleanup_class, requires_confirmation, protected, reason = _cleanup_readiness_for(
            summary.category,
            summary.risk,
        )
        rows.append(
            CleanupReadiness(
                path=summary.path,
                size_bytes=summary.size_bytes,
                category=summary.category,
                risk=summary.risk,
                cleanup_class=cleanup_class,
                requires_confirmation=requires_confirmation,
                protected=protected,
                reason=reason,
            )
        )

    buckets: dict[str, dict] = {}
    for row in rows:
        bucket = buckets.setdefault(row.cleanup_class, {"count": 0, "size_bytes": 0, "size_gib": 0.0})
        bucket["count"] += 1
        bucket["size_bytes"] += row.size_bytes
        bucket["size_gib"] = round(bucket["size_bytes"] / GIB, 3)

    return {
        "buckets": buckets,
        "rows": [row.to_dict() for row in sorted(rows, key=lambda item: item.size_bytes, reverse=True)],
        "estimated_confirmation_reclaim_gib": round(
            sum(row.size_bytes for row in rows if row.requires_confirmation and not row.protected) / GIB,
            3,
        ),
        "protected_gib": round(sum(row.size_bytes for row in rows if row.protected) / GIB, 3),
    }


def cleanup_operator_protocol() -> dict:
    return {
        "mode": "diagnose_first_then_confirm",
        "rule": "When drive accounting shows hidden gaps or material free-space deltas, diagnose hidden/system allocation before deleting visible files.",
        "stop_rules": [
            "Do not delete or move NEXUS, GROSS, model, dataset, git, Docker, WSL, or evidence paths from this report alone.",
            "If free-space changed by >=50 GiB since baseline, run admin diagnostics before cleanup proposals.",
            "If filesystem-used bytes and visible scan bytes differ by >=25 GiB, classify VSS/virtual-disk/sparse/cache causes first.",
            "Every delete/move requires explicit operator approval listing exact paths and expected reclaim.",
        ],
        "admin_diagnostics": [
            "vssadmin list shadowstorage",
            "vssadmin list shadows",
            "fsutil volume diskfree C:",
            "fsutil volume diskfree D:",
            "Get-Volume",
            "Sysmon/EventLog delete/process check for the incident window",
        ],
    }


def build_hygiene_report(
    *,
    paths: Iterable[Path] | None = None,
    min_file_mib: int = 100,
    top_file_limit: int = 80,
    include_system_files: bool = True,
    include_drive_accounting: bool = True,
    drives: Iterable[str] | None = None,
    visible_roots: dict[str, Iterable[Path]] | None = None,
    previous_report: dict | None = None,
    hidden_gap_threshold_gib: float = 25.0,
    free_delta_threshold_gib: float = 50.0,
) -> dict:
    scan_paths = default_targets() if paths is None else list(paths)
    summaries = [summarize_path(path) for path in scan_paths]
    file_candidates, stats = top_files(scan_paths, min_size_mib=min_file_mib, limit=top_file_limit)

    system_summaries = [summarize_path(path) for path in root_system_files()] if include_system_files else []
    all_summaries = summaries + system_summaries
    reclaim_candidates = [
        item for item in file_candidates
        if item.risk in {"low", "medium", "operator_review"} and item.category not in {"nexus_evidence"}
    ]
    drive_rows = (
        collect_drive_accounting(drives=drives, visible_roots=visible_roots)
        if include_drive_accounting
        else []
    )
    drive_findings = analyze_drive_accounting(
        drive_rows,
        previous_report=previous_report,
        hidden_gap_threshold_gib=hidden_gap_threshold_gib,
        free_delta_threshold_gib=free_delta_threshold_gib,
    )

    return {
        "status": "ok",
        "mode": "read_only",
        "generated_at": _format_ts(time.time()),
        "safety": {
            "deletes": False,
            "moves": False,
            "follows_reparse_points": False,
            "requires_operator_approval_for_cleanup": True,
        },
        "summaries": [row.to_dict() for row in sorted(all_summaries, key=lambda row: row.size_bytes, reverse=True)],
        "top_files": [row.to_dict() for row in file_candidates],
        "drive_accounting": [row.to_dict() for row in drive_rows],
        "drive_findings": drive_findings,
        "cleanup_readiness": build_cleanup_readiness(all_summaries),
        "cleanup_operator_protocol": cleanup_operator_protocol(),
        "candidate_summary": {
            "reviewable_file_count": len(reclaim_candidates),
            "reviewable_file_gib": round(sum(row.size_bytes for row in reclaim_candidates) / GIB, 3),
            "admin_only_count": sum(1 for row in file_candidates if row.risk == "admin_only"),
            "high_risk_count": sum(1 for row in file_candidates if row.risk == "high"),
        },
        "scan_stats": stats,
        "admin_follow_up": [
            "Run elevated shadow-storage diagnostics when accessible space does not match used space.",
            "Inspect pagefile policy before changing C:/pagefile.sys.",
            "Use Docker/WSL tooling for VHDX compaction or migration; do not delete live VHDX files.",
        ],
    }
