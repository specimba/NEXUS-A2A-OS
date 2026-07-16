"""Static safety contract for the controlled SAGE Brain reload helper."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess


REPO_ROOT = Path(__file__).resolve().parents[2]
HELPER = REPO_ROOT / "scripts" / "restart_sage_brain_7352.ps1"


def _source() -> str:
    return HELPER.read_text(encoding="utf-8")


def test_restart_helper_is_valid_powershell_without_execution() -> None:
    environment = os.environ.copy()
    environment["NEXUS_TEST_POWERSHELL_FILE"] = str(HELPER)
    result = subprocess.run(
        [
            "pwsh",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            (
                "$tokens=$null; $errors=$null; "
                "[System.Management.Automation.Language.Parser]::ParseFile("
                "$env:NEXUS_TEST_POWERSHELL_FILE,[ref]$tokens,[ref]$errors) | Out-Null; "
                "if ($errors.Count -gt 0) { $errors | ForEach-Object { $_.Message }; exit 1 }"
            ),
        ],
        cwd=REPO_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_restart_helper_hard_pins_7352_and_requires_operator_key_file() -> None:
    source = _source()

    assert "SupportsShouldProcess = $true" in source
    assert "[string]$SageKeyFile" in source
    assert "[Parameter(Mandatory = $true)]" in source
    assert "$port = 7352" in source
    assert "SAGE_BRAIN_NONCANONICAL_PORT_REFUSED" in source
    assert "[int]$Port = 7352" not in source
    assert "SAGE_KEY_FILE_MUST_BE_OUTSIDE_REPO" in source
    assert "Remove-Item Env:NEXUS_SAGE_API_KEY" in source


def test_restart_helper_verifies_brain_contract_and_process_identity_before_stop() -> None:
    source = _source()

    assert "Get-NetTCPConnection -State Listen" in source
    assert "Get-CimInstance" in source
    assert "Test-SageBrainProcessRecord" in source
    assert "Test-SageBrainPublicHealth" in source
    assert "Test-SageAuthenticatedHealth" in source
    assert "SAGE_BRAIN_OWNERSHIP_CONTRACT_FAILED" in source
    assert "SAGE_BRAIN_UNOWNED_LISTENER_DETECTED" in source
    assert "SAGE_BRAIN_LISTENER_CHANGED_BEFORE_STOP" in source
    stop_command = "Stop-Process -Id $currentListener.ProcessId"
    assert source.index("if (-not (Test-SageBrainPublicHealth -Port $port))") < source.index(stop_command)
    assert source.index("Test-SageAuthenticatedHealth -Port $port -Key $sageKey") < source.index(stop_command)
    assert source.index("Test-SageBrainProcessRecord `") < source.index(stop_command)
    assert "taskkill" not in source.lower()


def test_restart_helper_reuses_hardened_launcher_and_only_checks_safe_health_routes() -> None:
    source = _source()

    assert "scripts\\start_sage_brain.ps1" in source
    assert "& $launcher @launchArguments" in source
    assert '"http://127.0.0.1:$Port/"' in source
    assert '"http://127.0.0.1:$Port/api/sage/v1/health"' in source
    assert "openapi.json" not in source
    assert "/model-cards" not in source
    assert "/jobs" not in source
    assert "$requestedWhatIf = [bool]$WhatIfPreference" in source
    dry_run_branch = "    if ($requestedWhatIf) {\n        [ordered]@{"
    assert dry_run_branch in source
    assert source.index(dry_run_branch) < source.index("& $launcher @launchArguments")
    assert source.index(dry_run_branch) < source.index("$sageKey = Read-ValidatedSageKey")
    assert "operator_file_resolved_not_read_for_whatif" in source
    assert "would_restart" in source


def test_restart_helper_never_writes_the_sage_key_to_output() -> None:
    source = _source()

    for line in source.splitlines():
        if any(command in line for command in ("Write-Host", "Write-Output", "Write-Error")):
            assert "$sageKey" not in line
    assert "$sageKey = $null" in source
