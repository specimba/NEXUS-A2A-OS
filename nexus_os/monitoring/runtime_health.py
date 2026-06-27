"""Report-only Windows runtime pressure diagnostics."""

from __future__ import annotations

import json
import os
import platform
import subprocess
from typing import Any


def assess_runtime_health(snapshot: dict[str, Any]) -> dict[str, Any]:
    chrome = snapshot.get("chrome", {})
    memory = snapshot.get("memory", {})
    disk = snapshot.get("disk", {})
    sessions = snapshot.get("session_recovery", {})

    private_gb = float(chrome.get("private_gb", 0.0))
    top_private_mb = float(chrome.get("top_private_mb", 0.0))
    available_mb = float(memory.get("available_mb", 0.0))
    commit_pct = float(memory.get("commit_pct", 0.0))
    disk_max_mbps = float(disk.get("max_mbps", 0.0))

    findings: list[dict[str, Any]] = []
    if private_gb >= 16 or available_mb < 2048 or commit_pct >= 90:
        findings.append({
            "severity": "critical",
            "code": "browser_memory_pressure",
            "message": "Chrome memory pressure can force paging and system-wide stalls.",
        })
    elif private_gb >= 10 or top_private_mb >= 3072 or available_mb < 4096:
        findings.append({
            "severity": "warning",
            "code": "browser_memory_growth",
            "message": "One or more Chrome processes have unusually high private memory.",
        })

    if disk_max_mbps >= 250:
        findings.append({
            "severity": "warning",
            "code": "disk_spike_observed",
            "message": "Short sampling observed high aggregate disk throughput.",
        })

    restore_ready = bool(sessions.get("ready"))
    restart_recommended = any(
        item["code"] in {"browser_memory_pressure", "browser_memory_growth"}
        for item in findings
    )
    if restart_recommended and not restore_ready:
        findings.append({
            "severity": "critical",
            "code": "restart_without_recovery",
            "message": "Do not terminate Chrome until session recovery artifacts exist.",
        })

    severity_order = {"ok": 0, "warning": 1, "critical": 2}
    status = "ok"
    for finding in findings:
        if severity_order[finding["severity"]] > severity_order[status]:
            status = finding["severity"]

    return {
        "status": status,
        "findings": findings,
        "restart_recommended": restart_recommended and restore_ready,
        "automatic_restart_performed": False,
        "thresholds": {
            "chrome_private_warning_gb": 10,
            "chrome_private_critical_gb": 16,
            "top_process_private_warning_mb": 3072,
            "available_memory_warning_mb": 4096,
            "available_memory_critical_mb": 2048,
            "commit_critical_pct": 90,
            "disk_spike_warning_mbps": 250,
        },
    }


def collect_windows_runtime_snapshot(sample_seconds: int = 3) -> dict[str, Any]:
    if platform.system() != "Windows":
        return {
            "status": "unsupported",
            "reason": "runtime doctor currently supports Windows only",
        }

    script = rf"""
$ErrorActionPreference = 'SilentlyContinue'
$samples = Get-Counter '\Memory\Available MBytes','\Memory\% Committed Bytes In Use','\PhysicalDisk(_Total)\Disk Bytes/sec','\GPU Engine(*)\Utilization Percentage' -SampleInterval 1 -MaxSamples {max(1, sample_seconds)}
$chrome = @(Get-Process chrome)
$gpu = @{{}}
foreach ($sample in $samples.CounterSamples) {{
  if ($sample.InstanceName -match 'pid_(\d+)' -and $sample.Path -match 'gpu engine') {{
    $id = $Matches[1]
    if (-not $gpu.ContainsKey($id)) {{ $gpu[$id] = 0.0 }}
    if ($sample.CookedValue -gt $gpu[$id]) {{ $gpu[$id] = $sample.CookedValue }}
  }}
}}
$topGpu = $gpu.GetEnumerator() | Sort-Object Value -Descending | Select-Object -First 1
$sessionPath = Join-Path $env:LOCALAPPDATA 'Google\Chrome\User Data\Default\Sessions'
$sessionFiles = @(Get-ChildItem -LiteralPath $sessionPath -File | Where-Object {{ $_.Name -match '^(Session|Tabs)_' }})
$newest = $sessionFiles | Sort-Object LastWriteTime -Descending | Select-Object -First 1
$available = ($samples.CounterSamples | Where-Object {{ $_.Path -match 'available mbytes$' }} | Select-Object -Last 1).CookedValue
$commit = ($samples.CounterSamples | Where-Object {{ $_.Path -match '% committed bytes in use$' }} | Select-Object -Last 1).CookedValue
$diskMax = ($samples.CounterSamples | Where-Object {{ $_.Path -match 'disk bytes/sec$' }} | Measure-Object CookedValue -Maximum).Maximum
$topChrome = $chrome | Sort-Object PrivateMemorySize64 -Descending | Select-Object -First 1
[ordered]@{{
  chrome = [ordered]@{{
    process_count = $chrome.Count
    working_set_gb = [math]::Round((($chrome | Measure-Object WorkingSet64 -Sum).Sum / 1GB), 2)
    private_gb = [math]::Round((($chrome | Measure-Object PrivateMemorySize64 -Sum).Sum / 1GB), 2)
    top_private_pid = $topChrome.Id
    top_private_mb = [math]::Round(($topChrome.PrivateMemorySize64 / 1MB), 1)
    highest_gpu_pid = if ($topGpu) {{ [int]$topGpu.Name }} else {{ $null }}
    highest_gpu_pct = if ($topGpu) {{ [math]::Round($topGpu.Value, 2) }} else {{ 0.0 }}
  }}
  memory = [ordered]@{{
    available_mb = [math]::Round($available, 0)
    commit_pct = [math]::Round($commit, 2)
  }}
  disk = [ordered]@{{
    sample_seconds = {max(1, sample_seconds)}
    max_mbps = [math]::Round(($diskMax / 1MB), 2)
  }}
  session_recovery = [ordered]@{{
    ready = ($sessionFiles.Count -ge 2)
    file_count = $sessionFiles.Count
    newest_write = if ($newest) {{ $newest.LastWriteTime.ToString('o') }} else {{ $null }}
    total_mb = [math]::Round((($sessionFiles | Measure-Object Length -Sum).Sum / 1MB), 2)
  }}
}} | ConvertTo-Json -Depth 5 -Compress
"""
    try:
        proc = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
            check=False,
            timeout=sample_seconds + 10,
            env=os.environ.copy(),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "unavailable", "reason": str(exc)}

    if proc.returncode != 0 or not proc.stdout.strip():
        return {
            "status": "unavailable",
            "reason": proc.stderr.strip() or f"collector_exit_{proc.returncode}",
        }
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        return {"status": "unavailable", "reason": f"invalid_collector_json: {exc}"}


def build_runtime_health_report(sample_seconds: int = 3) -> dict[str, Any]:
    snapshot = collect_windows_runtime_snapshot(sample_seconds=sample_seconds)
    if snapshot.get("status") in {"unsupported", "unavailable"}:
        return snapshot
    return {
        **assess_runtime_health(snapshot),
        "snapshot": snapshot,
        "report_only": True,
        "protected_processes": ["chrome", "obs64", "Streamlabs OBS"],
    }
