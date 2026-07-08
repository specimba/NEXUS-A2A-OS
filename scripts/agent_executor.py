#!/usr/bin/env python3
"""
CANARY_TOKEN: fc2dbcf8ba5f13b2b02f6bba3b7beed8
"""
"""agent_executor.py — Remote command executor for agent verification.

Since the agent sandbox cannot run shell commands directly, this script
acts as the agent's "hands" in the user's environment. The agent edits
this script with the commands it needs run, and the user executes it.

Usage:
    python scripts/agent_executor.py

The agent will populate COMMANDS and VERIFICATION below.
"""
import subprocess
import sys
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# ═══════════════════════════════════════════════════════════════════════
# AGENT-POPULATED SECTION — Edit these variables via file tools
# ═══════════════════════════════════════════════════════════════════════

COMMANDS = [
    # Example: ['python', '-m', 'pytest', 'tests/governor/test_trust_scoring.py', '-v']
]

VERIFICATION = {
    # 'expected_outputs': [...],
    # 'expected_returncodes': [...],
}

# ═══════════════════════════════════════════════════════════════════════
# EXECUTION ENGINE — Do not modify below this line
# ═══════════════════════════════════════════════════════════════════════

def run_command(cmd: list[str], cwd: Path = REPO_ROOT) -> dict:
    """Run a command and return structured output."""
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return {
        "command": " ".join(cmd),
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def main() -> int:
    if not COMMANDS:
        print("No commands configured. Agent should populate COMMANDS list.")
        return 0

    results = []
    for cmd in COMMANDS:
        print(f"Running: {' '.join(cmd)}")
        result = run_command(cmd)
        results.append(result)
        status = "OK" if result["returncode"] == 0 else "FAIL"
        print(f"  Status: {status} (returncode={result['returncode']})")
        if result["stdout"]:
            print(f"  stdout:\n{result['stdout'][:2000]}")
        if result["stderr"]:
            print(f"  stderr:\n{result['stderr'][:2000]}")
        print()

    # Write results for agent consumption
    results_path = REPO_ROOT / ".nexus_pi" / "state" / "agent_executor_results.json"
    results_path.parent.mkdir(parents=True, exist_ok=True)
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Results written to: {results_path}")

    # Overall status
    all_ok = all(r["returncode"] == 0 for r in results)
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
