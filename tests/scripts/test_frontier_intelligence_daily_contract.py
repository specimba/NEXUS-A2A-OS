"""Contract checks for the bounded frontier-intelligence scheduled job."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "nexus_frontier_intelligence_daily.ps1"
SHELL = shutil.which("pwsh") or shutil.which("powershell")


def test_daily_job_uses_shared_writable_runtime_state_and_clean_boolean_results():
    text = SCRIPT.read_text(encoding="utf-8")

    assert "Join-Path $repo 'logs\\runtime-state'" in text
    assert "NEXUS_RUNTIME_STATE_ROOT" in text
    assert "Write-Host $line" in text
    assert "Write-Output $line" not in text
    assert "$catalogOk = Invoke-PythonLogged" in text
    assert "$arenaOk = Invoke-PythonLogged" in text
    assert "if (-not $arenaOk) { $ok = $false }" in text
    assert "frontier_intelligence_status.json" in text
    assert "evidence_sidecar_accepted" in text
    # Discovery/evidence refresh must not mutate or depend on every CLI
    # configuration.  7356 projects the live relay manifest directly.
    assert "client manifest sync skipped: this evidence job never mutates CLI configuration" in text
    assert "-m', 'nexusctl.model_sync', '--refresh'" not in text
    # The scheduled job and its recovery path share the repo-local raw cache;
    # a transient public-board failure may replay only a still-fresh snapshot.
    assert "'--cache-dir', (Join-Path $arenaRoot 'raw')" in text
    assert "cached LMArena evidence replay" in text
    assert "--offline" in text
    # Native stderr is diagnostic text; the launcher must make its boolean
    # decision from python's exit code rather than terminate on a warning.
    assert "$priorErrorActionPreference = $ErrorActionPreference" in text
    assert "$ErrorActionPreference = 'Continue'" in text
    assert "$exitCode = $LASTEXITCODE" in text
    # 7356 is Node-based; write the status sidecar without a Windows
    # PowerShell UTF-8 BOM so JSON.parse accepts a valid refresh report.
    assert "[System.IO.File]::WriteAllText" in text
    assert "[System.Text.UTF8Encoding]::new($false)" in text


@pytest.mark.skipif(SHELL is None, reason="PowerShell unavailable")
def test_daily_job_whatif_parses_without_profile_or_network_writes():
    result = subprocess.run(
        [SHELL, "-NoProfile", "-File", str(SCRIPT), "-WhatIf"],
        cwd=REPO,
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "logs\\runtime-state" in result.stdout
    assert "candidate-only delta" in result.stdout
