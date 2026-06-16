import json
import subprocess
import sys


def run_nexusctl(*args):
    return subprocess.run(
        [sys.executable, "-m", "nexusctl", *args],
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )


def test_nexusclaw_status_cli_reports_port_policy():
    proc = run_nexusctl("nexusclaw", "status")

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["command"] == "nexusclaw.status"
    assert payload["port_ownership"]["7352"] == "nexus_governance"
    assert payload["port_ownership"]["7355"] == "modelrelay_internal"
    assert payload["config"]["cloud_fallback_enabled"] is False


def test_nexusclaw_dispatch_dry_run_cli_returns_result_envelope():
    proc = run_nexusctl(
        "nexusclaw",
        "dispatch-dry-run",
        "--task-id",
        "CLI-001",
        "--source",
        "pytest",
        "--intent",
        "cli dry run",
        "--risk-level",
        "low",
        "--capability",
        "dry_run",
        "--evidence-ref",
        "docs/handoff/nexusclaw/NEXUSCLAW_CORE_V0_EVIDENCE_MATRIX_2026-06-03.md",
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["command"] == "nexusclaw.dispatch_dry_run"
    assert payload["result"]["status"] == "dry_run"
    assert payload["result"]["vap_record_id"] == "vap-dryrun-CLI-001"
