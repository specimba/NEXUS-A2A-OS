"""Read-only GROSS/Grok state prechecks for NexusClaw.

This module provides cheap sentinel primitives. It does not modify Grok state,
GROSS evidence files, firewall state, or queue contents.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
import subprocess


MATERIAL_QUEUE_BYTES = 100 * 1024 * 1024


@dataclass(frozen=True)
class FileMarker:
    path: str
    modified_at: str
    size_bytes: int

    def to_dict(self) -> dict[str, str | int]:
        return {
            "path": self.path,
            "modified_at": self.modified_at,
            "size_bytes": self.size_bytes,
        }


@dataclass(frozen=True)
class GrossSentinelSnapshot:
    grok_process_running: bool
    upload_queue_file_count: int
    upload_queue_bytes: int
    newest_win_native_run: FileMarker | None
    newest_gross_report: FileMarker | None
    newest_downloads_evidence: FileMarker | None
    pcap_ready: bool
    sysmon_ready: bool
    firewall_ready: bool
    material_change: bool
    decision: str

    def to_dict(self) -> dict[str, object]:
        return {
            "grok_process_running": self.grok_process_running,
            "upload_queue_file_count": self.upload_queue_file_count,
            "upload_queue_bytes": self.upload_queue_bytes,
            "newest_win_native_run": self.newest_win_native_run.to_dict() if self.newest_win_native_run else None,
            "newest_gross_report": self.newest_gross_report.to_dict() if self.newest_gross_report else None,
            "newest_downloads_evidence": self.newest_downloads_evidence.to_dict() if self.newest_downloads_evidence else None,
            "pcap_ready": self.pcap_ready,
            "sysmon_ready": self.sysmon_ready,
            "firewall_ready": self.firewall_ready,
            "material_change": self.material_change,
            "decision": self.decision,
        }


def should_read_deep_gross_files(
    *,
    grok_process_running: bool,
    upload_queue_bytes: int,
    win_native_run_recent: bool,
    new_evidence_report: bool,
    capture_process_exit: bool = False,
) -> bool:
    """Return whether expensive CSV/log reads are justified."""

    if grok_process_running:
        return True
    if upload_queue_bytes >= MATERIAL_QUEUE_BYTES:
        return True
    if win_native_run_recent or new_evidence_report or capture_process_exit:
        return True
    return False


def collect_gross_sentinel_snapshot(
    *,
    gross_root: Path = Path("D:/GROSS"),
    grok_root: Path | None = None,
    downloads_root: Path | None = None,
    now: datetime | None = None,
    previous_evidence_check: datetime | None = None,
) -> GrossSentinelSnapshot:
    """Collect a bounded read-only snapshot for GROSS material-change checks."""

    current_time = _aware_utc(now or datetime.now(timezone.utc))
    grok_base = grok_root or (Path.home() / ".grok")
    downloads = downloads_root or (Path.home() / "Downloads")

    queue_count, queue_bytes = _count_files(grok_base / "upload_queue")
    newest_run = _newest_marker(gross_root / "runs", ["win-native-*"], directories=True)
    newest_gross_report = _newest_marker(gross_root, ["*GROSS*", "*grok*", "*.md", "*.txt"], max_candidates=500)
    newest_downloads_evidence = _newest_marker(downloads, ["*GROSS*", "*grok*", "*NEXUS*"], max_candidates=500)

    win_native_run_recent = _marker_is_recent(newest_run, current_time, minutes=30)
    new_evidence_report = _marker_after(newest_gross_report, previous_evidence_check) or _marker_after(
        newest_downloads_evidence,
        previous_evidence_check,
    )
    process_running = _is_process_running("grok.exe")
    material_change = should_read_deep_gross_files(
        grok_process_running=process_running,
        upload_queue_bytes=queue_bytes,
        win_native_run_recent=win_native_run_recent,
        new_evidence_report=new_evidence_report,
    )

    return GrossSentinelSnapshot(
        grok_process_running=process_running,
        upload_queue_file_count=queue_count,
        upload_queue_bytes=queue_bytes,
        newest_win_native_run=newest_run,
        newest_gross_report=newest_gross_report,
        newest_downloads_evidence=newest_downloads_evidence,
        pcap_ready=_has_any(gross_root, ["*.pcap", "*.pcapng"], max_candidates=300),
        sysmon_ready=_has_any(gross_root, ["*sysmon*", "*Sysmon*"], max_candidates=300),
        firewall_ready=_has_any(gross_root, ["*firewall*", "*Firewall*", "*wfplwfs*"], max_candidates=300),
        material_change=material_change,
        decision="NOTIFY" if material_change else "DONT_NOTIFY",
    )


def _count_files(path: Path) -> tuple[int, int]:
    if not path.exists():
        return 0, 0
    count = 0
    total = 0
    for item in path.rglob("*"):
        if not item.is_file():
            continue
        count += 1
        try:
            total += item.stat().st_size
        except OSError:
            continue
    return count, total


def _newest_marker(
    root: Path,
    patterns: list[str],
    *,
    directories: bool = False,
    max_candidates: int = 200,
) -> FileMarker | None:
    if not root.exists():
        return None

    newest: tuple[float, Path, int] | None = None
    checked = 0
    for pattern in patterns:
        for item in root.glob(pattern):
            if checked >= max_candidates:
                break
            checked += 1
            if directories != item.is_dir() and not (not directories and item.is_file()):
                continue
            try:
                stat = item.stat()
            except OSError:
                continue
            size = 0 if item.is_dir() else stat.st_size
            if newest is None or stat.st_mtime > newest[0]:
                newest = (stat.st_mtime, item, size)
    if newest is None:
        return None
    modified = datetime.fromtimestamp(newest[0], timezone.utc).isoformat()
    return FileMarker(path=str(newest[1]), modified_at=modified, size_bytes=newest[2])


def _has_any(root: Path, patterns: list[str], *, max_candidates: int) -> bool:
    if not root.exists():
        return False
    checked = 0
    for pattern in patterns:
        for _ in root.glob(pattern):
            checked += 1
            if checked > max_candidates:
                return True
            return True
    return False


def _marker_is_recent(marker: FileMarker | None, now: datetime, *, minutes: int) -> bool:
    if marker is None:
        return False
    try:
        modified = datetime.fromisoformat(marker.modified_at)
    except ValueError:
        return False
    return _aware_utc(modified) >= now - timedelta(minutes=minutes)


def _marker_after(marker: FileMarker | None, threshold: datetime | None) -> bool:
    if marker is None or threshold is None:
        return False
    try:
        modified = datetime.fromisoformat(marker.modified_at)
    except ValueError:
        return False
    return _aware_utc(modified) > _aware_utc(threshold)


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _is_process_running(process_name: str) -> bool:
    try:
        proc = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {process_name}"],
            capture_output=True,
            text=True,
            check=False,
            timeout=3,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return process_name.lower() in proc.stdout.lower()
