import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "dashboard_reconciliation_audit.py"


def test_dashboard_reconciliation_audit_runs_and_reports_expected_contract():
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode in (0, 1)
    assert '"expected_files"' in result.stdout
    assert '"missing_expected_files"' in result.stdout
    assert '"stale_hits"' in result.stdout
    assert "7352_modelrelay" in result.stdout
