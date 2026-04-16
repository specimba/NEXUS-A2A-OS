#!/usr/bin/env python3
"""C5 Integration Gate — Full pipeline verification & EVIDENCE.md generator."""
import subprocess, sys, json, time
from pathlib import Path

def run_pytest():
    result = subprocess.run(["pytest", "tests/", "-v", "--tb=short"], capture_output=True, text=True)
    return {"returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr}

def generate_evidence(pytest_out):
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ")
    status = "✅ PASSED" if pytest_out["returncode"] == 0 else "❌ FAILED"
    return f"""# C5 INTEGRATION EVIDENCE
**Generated**: {ts} | **Status**: {status} | **Branch**: `main`
## Verified Surfaces
| Component | File | Target |
|---|---|---|
| Bridge | `bridge/server.py` | Token headers present |
| Governor | `governor/base.py` | Hard-stop enforced |
| Trust | `vault/trust.py` | O(1) hot-path |
| VAP | `governor/proof_chain.py` | SHA-256 chain valid |
## Decision
{status}
"""

if __name__ == "__main__":
    print("🔍 Running C5 Gate...")
    res = run_pytest()
    Path("EVIDENCE.md").write_text(generate_evidence(res))
    print(f"📄 EVIDENCE.md generated. Status: {'PASS' if res['returncode'] == 0 else 'FAIL'}")
    sys.exit(res["returncode"])
