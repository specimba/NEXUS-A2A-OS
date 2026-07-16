"""Regression coverage for Windows legacy-console help rendering."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def test_gmr_help_survives_cp1252_stdout() -> None:
    """Help must not crash when a Windows console cannot encode a Unicode arrow."""
    root = Path(__file__).resolve().parents[2]
    script = (
        "import sys; "
        "sys.stdout.reconfigure(encoding='cp1252'); "
        "sys.argv=['nexusctl','gmr','--help']; "
        "from nexusctl.cli import main; main()"
    )
    env = {**os.environ, "PYTHONUTF8": "0"}
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=root,
        env=env,
        capture_output=True,
        text=False,
        check=False,
    )

    assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
    assert b"Chimera route -> optional ModelRelay" in result.stdout
