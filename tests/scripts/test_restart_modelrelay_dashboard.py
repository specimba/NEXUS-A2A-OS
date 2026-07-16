"""Static safety contracts for the controlled ModelRelay and Arena reloads.

These checks intentionally parse source only.  They do not query, stop, or
start any local listener.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
MODELRELAY_HELPER = REPO_ROOT / "scripts" / "restart_modelrelay_7350.ps1"
DASHBOARD_HELPER = REPO_ROOT / "scripts" / "restart_dashboard_7356.ps1"


@pytest.mark.parametrize("helper", [MODELRELAY_HELPER, DASHBOARD_HELPER])
def test_reload_helpers_parse_without_execution(helper: Path) -> None:
    environment = os.environ.copy()
    environment["NEXUS_TEST_POWERSHELL_FILE"] = str(helper)
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


def test_modelrelay_reload_requires_owned_7350_and_proves_terminal_410_guard() -> None:
    source = MODELRELAY_HELPER.read_text(encoding="utf-8")

    assert "SupportsShouldProcess = $true" in source
    assert "$port = 7350" in source
    assert "modelrelay_runtime.ps1" in source
    assert "Test-GovernedRelayContract" in source
    assert "Get-RelayEstablishedConnections" in source
    assert "would_block_active_connections" in source
    assert "wait_for_requests_to_drain" in source
    assert "activePersistedAccessBlocks" in source
    assert "terminalCanaryExclusions" in source
    assert "terminal_canary_exclusions" in source
    assert "globalLimitPerWindow" in source
    assert "minimumSpacingSeconds" in source
    assert "canary_hourly_budget" in source
    assert "canary_minimum_spacing_seconds" in source
    assert "/v1/models" in source
    assert "nexus-resilient" in source
    assert "resilient_alias" in source
    assert "provider_config" in source
    assert "provider_credentials" in source
    assert "bearer_token_path" in source
    assert "health_sampler_state" in source
    assert "/chat/completions" not in source
    assert source.index("if (-not (Test-GovernedRelayContract))") < source.index(
        "Stop-Process -Id $currentPid"
    )
    assert source.index("$activeConnections = @(Get-RelayEstablishedConnections") < source.index(
        "Stop-Process -Id $currentPid"
    )


def test_dashboard_reload_requires_owned_7356_and_live_client_contracts() -> None:
    source = DASHBOARD_HELPER.read_text(encoding="utf-8")

    assert "SupportsShouldProcess = $true" in source
    assert "$port = 7356" in source
    assert "serve_dashboard_7356.js" in source
    assert "Test-DashboardContract" in source
    assert "/api/client-manifest" in source
    assert "/api/frontier-intelligence" in source
    assert "nexus-model-arena-live-projection" in source
    assert "automatic_registration" in source
    assert "automatic_routing" in source
    assert "/chat/completions" not in source
    assert source.index("if (-not (Test-DashboardContract))") < source.index(
        "Stop-Process -Id $currentPid"
    )
