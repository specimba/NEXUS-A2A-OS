#!/usr/bin/env python3
# CANARY: bf304e7e3b842dc628df7483c9d94e30
"""
Shared guard for pausing heavy local model jobs while protected desktop
workloads such as Streamlabs OBS are active or freshly crashed.
"""

from __future__ import annotations

import os
import json
import re
import subprocess
import time
from pathlib import Path
from typing import Iterable


DEFAULT_PROTECTED_NAMES = (
    "Streamlabs OBS.exe",
    "obs64.exe",
    "obs-browser-page.exe",
    "crash-handler-process.exe",
    "crashhelper.exe",
    "crash-handler.exe",
)


def _env_flag(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def _slobs_root() -> Path:
    return Path(os.environ.get("APPDATA", "")) / "slobs-client"


def _windows_tasklist_names() -> set[str]:
    names: set[str] = set()
    try:
        result = subprocess.run(
            ["tasklist", "/fo", "csv", "/nh"],
            check=False,
            capture_output=True,
            text=True,
            timeout=8,
        )
    except Exception:
        result = None

    if result and result.returncode == 0:
        for line in result.stdout.splitlines():
            match = re.match(r'^"([^"]+)"', line.strip())
            if match:
                names.add(match.group(1).lower())

    if names:
        return names

    # Some locked-down desktop sessions deny tasklist. PowerShell Get-Process
    # still gives enough process names for a conservative protected-workload gate.
    try:
        fallback = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-Process | Select-Object -ExpandProperty ProcessName",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=8,
        )
    except Exception:
        return set()

    if fallback.returncode != 0:
        return set()

    for line in fallback.stdout.splitlines():
        name = line.strip().lower()
        if name:
            names.add(name)
            names.add(f"{name}.exe")
    return names


def protected_processes(names: Iterable[str] = DEFAULT_PROTECTED_NAMES) -> list[str]:
    running_names = _windows_tasklist_names()
    wanted = {name.lower() for name in names}
    return sorted(name for name in wanted if name in running_names)


def recent_streamlabs_crash(minutes: int = 20, slobs_root: Path | None = None) -> bool:
    root = slobs_root or _slobs_root()
    crash_log = root / "crash-handler.log"
    if not crash_log.exists():
        return False

    cutoff = time.time() - (minutes * 60)
    try:
        if crash_log.stat().st_mtime < cutoff:
            return False
        with crash_log.open("r", encoding="utf-8", errors="replace") as handle:
            tail = handle.readlines()[-160:]
    except OSError:
        return False

    markers = (
        "crashed_module_info",
        "Handling crash",
        "process died",
        "requested memory dump on crash",
    )
    return any(any(marker in line for marker in markers) for line in tail)


def protected_workload_status() -> dict[str, object]:
    if not _env_flag("NEXUS_PROTECTED_WORKLOAD_GATE", True):
        return {"should_pause": False, "reason": "disabled_by_env"}

    active = protected_processes()
    recent_crash_minutes = int(os.environ.get("NEXUS_RECENT_STREAMLABS_CRASH_MINUTES", "20"))
    recent_crash = recent_streamlabs_crash(minutes=recent_crash_minutes)
    reasons: list[str] = []
    if active:
        reasons.append("protected_process_active")
    if recent_crash:
        reasons.append(f"recent_streamlabs_crash_{recent_crash_minutes}m")

    return {
        "should_pause": bool(reasons),
        "reason": ",".join(reasons) if reasons else "clear",
        "active_processes": active,
        "recent_streamlabs_crash": recent_crash,
    }


def should_pause_for_protected_workload() -> bool:
    return bool(protected_workload_status()["should_pause"])


if __name__ == "__main__":
    print(json.dumps(protected_workload_status(), indent=2))
