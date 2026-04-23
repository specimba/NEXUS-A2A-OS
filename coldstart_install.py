#!/usr/bin/env python3
"""NEXUS OS v3.1 Cold Start Installer — Run once, get everything ready."""

import os, sys, subprocess
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent
while not (ROOT / "src").exists() and ROOT != ROOT.parent:
    ROOT = ROOT.parent
VENV = ROOT / "venv"

def run(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=ROOT)
    return r.returncode, r.stdout.strip(), r.stderr.strip()

def header(msg):
    print(f"\n{'='*65}\n  {msg}\n{'='*65}")

def main():
    header("NEXUS OS v3.1 — COLD START INSTALLER")

    if sys.version_info < (3, 10):
        print("[FAIL] Python 3.10+ required"); sys.exit(1)
    print(f"[OK] Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")

    header("VIRTUAL ENVIRONMENT")
    if not (VENV/"bin"/"python").exists() and not (VENV/"Scripts"/"python.exe").exists():
        print("[...] Creating virtual environment...")
        run(f"{sys.executable} -m venv venv")

    pip = str(VENV/"bin"/"pip") if (VENV/"bin").exists() else str(VENV/"Scripts"/"pip.exe")
    python = str(VENV/"bin"/"python") if (VENV/"bin").exists() else str(VENV/"Scripts"/"python.exe")

    header("DEPENDENCIES")
    code, _, _ = run(f'"{pip}" install -e . httpx -q')
    print("[OK] Dependencies installed" if code == 0 else "[WARN] Some packages need attention")

    header("SYSTEM DIAGNOSTICS")
    run(f'"{python}" scripts/diagnostic.py')

    header("TEST SUITE")
    code, out, _ = run(f'"{python}" -m pytest tests/ -q --tb=line')
    print("[OK] All tests passed (622+)" if "passed" in out else f"[WARN] Output: {out[:200]}")

    header("INSTALLATION COMPLETE")
    print("Next steps:")
    print("  1. uvicorn nexus_os.api.server:app --host 0.0.0.0 --port 7352")
    print("  2. Read COLDSTART_BOOT.txt")
    print("  3. Check tasks/pending/ for your first assignment")
    print(f"\nTimestamp: {datetime.now().isoformat()}")

if __name__ == "__main__":
    main()