#!/usr/bin/env python3
"""Zo NEXUS State Bridge — read-only snapshot of workspace health.

Used by Zo automations (Nightly Audit, Morning Brief) to produce
a durable state snapshot without modifying any files.

Usage:
    python3 scripts/zo_nexus_state_bridge.py snapshot --check-only
    python3 scripts/zo_nexus_state_bridge.py snapshot --full
"""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path("/home/workspace")

def git(*args):
    try:
        r = subprocess.run(["git"] + list(args), capture_output=True,
                           text=True, cwd=WORKSPACE, timeout=30)
        return r.stdout.strip(), r.returncode
    except Exception as e:
        return str(e), -1

def snapshot(check_only=False):
    head, _ = git("rev-parse", "--short", "HEAD")
    branch, _ = git("rev-parse", "--abbrev-ref", "HEAD")
    status_out, _ = git("status", "--short")
    log_out, _ = git("log", "--oneline", "-5")
    dirty_count = len([l for l in status_out.split("\n") if l.strip()])

    # Check AGENTS.md exists
    agents_present = (WORKSPACE / "AGENTS.md").exists()

    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "head": head or "unknown",
        "branch": branch or "unknown",
        "dirty_count": dirty_count,
        "agents_present": agents_present,
        "recent_commits": log_out,
        "status": "degraded" if dirty_count > 20 else "clean",
    }

    if check_only:
        print(json.dumps({"status": result["status"],
                          "checks": {"git_available": head != "unknown",
                                     "branch": branch}}))
    else:
        print(json.dumps(result, indent=2))

    return result

def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "snapshot"
    if cmd == "snapshot":
        check_only = "--check-only" in sys.argv
        snapshot(check_only=check_only)
    elif cmd == "help":
        print(__doc__)
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)

if __name__ == "__main__":
    main()
