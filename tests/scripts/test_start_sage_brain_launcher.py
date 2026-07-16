"""Static safety contract for the NEXUS SAGE Brain launcher."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess

from fastapi import FastAPI
from fastapi.testclient import TestClient

from nexus_os.sage_gateway import routes
from nexus_os.sage_gateway.security import SageBodyLimitMiddleware


REPO_ROOT = Path(__file__).resolve().parents[2]
LAUNCHER = REPO_ROOT / "scripts" / "start_sage_brain.ps1"


def _source() -> str:
    return LAUNCHER.read_text(encoding="utf-8")


def test_launcher_is_valid_powershell_without_execution() -> None:
    environment = os.environ.copy()
    environment["NEXUS_TEST_POWERSHELL_FILE"] = str(LAUNCHER)
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


def test_launcher_hard_pins_loopback_and_canonical_brain_port() -> None:
    source = _source()

    assert '[string]$BindAddress = "127.0.0.1"' in source
    assert 'if ($BindAddress -cne "127.0.0.1")' in source
    assert "[int]$Port = 7352" in source
    assert "if ($Port -ne 7352)" in source
    assert "Get-NetTCPConnection" in source
    assert "SAGE_BRAIN_PORT_IN_USE" in source
    assert source.index("Get-NetTCPConnection") < source.index("Start-Process")


def test_launcher_uses_only_an_out_of_repo_key_file() -> None:
    source = _source()

    assert "Resolve-Path -LiteralPath $SageKeyFile" in source
    assert "SAGE_KEY_FILE_MUST_BE_OUTSIDE_REPO" in source
    assert "$keyEntryPath.StartsWith($repoPrefix" in source
    assert "Remove-Item Env:NEXUS_SAGE_API_KEY" in source
    assert '"NEXUS_SAGE_API_KEY" = $null' in source
    assert '"NEXUS_SAGE_API_KEY_FILE" = $keyFilePath' in source
    for line in source.splitlines():
        if any(command in line for command in ("Write-Host", "Write-Output", "Write-Error")):
            assert "$sageKey" not in line


def test_launcher_separates_mutable_state_logs_and_credentials() -> None:
    source = _source()

    assert '$stateRoot = Join-Path $runtimeRoot "state"' in source
    assert '$logRoot = Join-Path $runtimeRoot "logs"' in source
    assert "SAGE_RUNTIME_MUST_NOT_SHARE_KEY_DIRECTORY" in source
    assert '"NEXUS_SAGE_RUNTIME_DIR" = $stateRoot' in source
    assert '$stdoutLog = Join-Path $logRoot "brain-$stamp.out.log"' in source
    assert '$stderrLog = Join-Path $logRoot "brain-$stamp.err.log"' in source


def test_sage_runtime_env_writes_job_database_only_to_state_dir(
    monkeypatch,
    tmp_path,
) -> None:
    credential_dir = tmp_path / "credentials"
    state_dir = tmp_path / "mutable-state"
    credential_dir.mkdir()
    key_file = credential_dir / ".sage_api_token"
    key = "launcher-runtime-test-" + ("k" * 40)
    key_file.write_text(key, encoding="utf-8")

    monkeypatch.delenv("NEXUS_SAGE_API_KEY", raising=False)
    monkeypatch.setenv("NEXUS_SAGE_API_KEY_FILE", str(key_file))
    monkeypatch.setenv("NEXUS_SAGE_GATEWAY_MODE", "proposal_write")
    monkeypatch.setenv("NEXUS_SAGE_RUNTIME_DIR", str(state_dir))
    routes.reset_sage_stores_for_tests()
    app = FastAPI()
    app.add_middleware(SageBodyLimitMiddleware)
    app.include_router(routes.router)

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/sage/v1/jobs",
                headers={"Authorization": f"Bearer {key}"},
                json={
                    "workflow_type": "grounding_audit",
                    "parameters": {"files": ["NEXUS_MANIFEST.md"]},
                    "idempotency_key": "launcher-runtime-001",
                },
            )
    finally:
        routes.reset_sage_stores_for_tests()

    assert response.status_code == 202
    assert (state_dir / "sage_jobs.sqlite3").is_file()
    assert not (credential_dir / "sage_jobs.sqlite3").exists()


def test_launcher_defaults_to_observe_only_and_gates_proposal_write() -> None:
    source = _source()

    assert '[string]$Mode = "observe_only"' in source
    assert "[switch]$EnableProposalWrite" in source
    assert 'if ($Mode -eq "proposal_write" -and -not $EnableProposalWrite)' in source
    assert '"NEXUS_SAGE_GATEWAY_MODE" = $Mode' in source


def test_launcher_starts_hidden_venv_brain_module_without_public_transport() -> None:
    source = _source()
    lowered = source.lower()

    assert 'Join-Path $repoRoot ".venv\\Scripts\\python.exe"' in source
    assert '"-m", "nexus_os.api.brain_api"' in source
    assert '"--host", $BindAddress' in source
    assert '"--port", [string]$Port' in source
    assert "-WindowStyle Hidden" in source
    assert "-Environment $childEnvironment" in source
    assert "0.0.0.0" not in source
    assert "--reload" not in source
    assert not any(name in lowered for name in ("ngrok", "cloudflared", "tailscale funnel"))


def test_launcher_has_bounded_brain_and_authenticated_sage_readiness() -> None:
    source = _source()

    assert "[ValidateRange(5, 60)]" in source
    assert '"http://127.0.0.1:$Port/"' in source
    assert '"http://127.0.0.1:$Port/health"' not in source
    assert '$brainIdentity.service -eq "NEXUS Brain API"' in source
    assert '"http://127.0.0.1:$Port/api/sage/v1/health"' in source
    assert 'Authorization = "Bearer $sageKey"' in source
    assert "Invoke-RestMethod" in source
    assert "-TimeoutSec 3" in source
    assert "SAGE_BRAIN_READINESS_FAILED" in source
    assert "SAGE_BRAIN_AMBIGUOUS_LISTENER_DETECTED" in source
    assert 'Where-Object { $_.LocalPort -eq $Port }' in source
    assert "OwningProcess -eq $process.Id" not in source
    assert source.index("if ($listeners.Count -eq 0)") < source.index(
        'Authorization = "Bearer $sageKey"'
    )
    assert "Stop-SageOwnedProcessTree" in source


def test_launcher_reports_verified_child_listener_and_supervisor_pids() -> None:
    source = _source()

    assert "$candidateListenerPid = [int]$listeners[0].OwningProcess" in source
    assert "$verifiedListenerPid = $candidateListenerPid" in source
    assert "$confirmedListenerPid -ne $verifiedListenerPid" in source
    assert "SAGE_BRAIN_UNOWNED_LISTENER_DETECTED" in source
    assert "SAGE_BRAIN_LISTENER_CHANGED_DURING_READINESS" in source
    assert "pid={0} listener_pid={0} supervisor_pid={1}" in source
    assert source.index("$verifiedListenerPid = $candidateListenerPid") < source.index(
        "SAGE_BRAIN_READY pid={0}"
    )


def test_launcher_cleans_only_identity_checked_tree_and_orphan_listener() -> None:
    source = _source()

    assert "$Process.Kill($true)" in source
    assert "$Process.WaitForExit(5000)" in source
    assert "if (-not $byPid.ContainsKey($candidatePid))" in source
    assert "-ge $OwnedProcesses[$parentPid]" in source
    assert "Test-SageOwnedProcessRecord" in source
    assert "Stop-Process -Id $candidatePid" in source
    assert "-VerifiedListenerPid $verifiedListenerPid" in source
    assert source.index("Test-SageOwnedProcessRecord") < source.index(
        "Stop-Process -Id $candidatePid"
    )
    assert "taskkill" not in source.lower()
    assert "Get-Process -Name" not in source



def test_owned_tree_helpers_clean_orphan_and_reject_reused_parent_pid() -> None:
    environment = os.environ.copy()
    environment["NEXUS_TEST_POWERSHELL_FILE"] = str(LAUNCHER)
    command = r"""
$tokens = $null
$errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile(
    $env:NEXUS_TEST_POWERSHELL_FILE,
    [ref]$tokens,
    [ref]$errors
)
if ($errors.Count -gt 0) { throw "launcher parse failed" }
$wanted = @(
    "Get-SageProcessIdentity",
    "Get-SageProcessSnapshot",
    "Test-SageOwnedProcessRecord",
    "Update-SageOwnedProcesses",
    "Stop-SageOwnedProcessTree"
)
$definitions = @(
    $ast.FindAll({
        param($node)
        $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and
            $wanted -contains $node.Name
    }, $true) | Sort-Object { $_.Extent.StartOffset }
)
if ($definitions.Count -ne $wanted.Count) { throw "helper extraction failed" }
Invoke-Expression (($definitions | ForEach-Object { $_.Extent.Text }) -join "`n")

$rootTime = [DateTime]::Parse("2026-07-13T00:00:00Z").ToUniversalTime()
$orphan = [pscustomobject]@{
    ProcessId = 200
    ParentProcessId = 100
    CreationDate = $rootTime.AddSeconds(1)
}
$owned = @{ 100 = $rootTime.Ticks }
$script:active = $true
$script:stopped = @()
function Get-SageProcessSnapshot {
    if ($script:active) { return @($orphan) }
    return @()
}
function Get-CimInstance {
    [CmdletBinding()]
    param([string]$ClassName, [string]$Filter, [string[]]$Property)
    if ($script:active) { return $orphan }
    return @()
}
function Stop-Process {
    [CmdletBinding()]
    param([int]$Id, [switch]$Force)
    $script:stopped += $Id
    $script:active = $false
}
function Start-Sleep { param([int]$Milliseconds) }

Stop-SageOwnedProcessTree `
    -Process $null `
    -OwnedProcesses $owned `
    -VerifiedListenerPid 200
if ($script:stopped.Count -ne 1 -or $script:stopped[0] -ne 200) {
    throw "identity-checked orphan was not cleaned"
}

$reusedRoot = [pscustomobject]@{
    ProcessId = 100
    ParentProcessId = 1
    CreationDate = $rootTime.AddSeconds(2)
}
$unrelatedChild = [pscustomobject]@{
    ProcessId = 201
    ParentProcessId = 100
    CreationDate = $rootTime.AddSeconds(3)
}
$reusedOwned = @{ 100 = $rootTime.Ticks }
Update-SageOwnedProcesses `
    -OwnedProcesses $reusedOwned `
    -Snapshot @($reusedRoot, $unrelatedChild)
if ($reusedOwned.ContainsKey(201)) {
    throw "child of reused parent PID was incorrectly adopted"
}
"OWNERSHIP_HELPERS_OK"
"""
    result = subprocess.run(
        ["pwsh", "-NoProfile", "-NonInteractive", "-Command", command],
        cwd=REPO_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "OWNERSHIP_HELPERS_OK" in result.stdout
