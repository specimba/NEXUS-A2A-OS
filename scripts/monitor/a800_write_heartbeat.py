#!/usr/bin/env python3
"""
A800 Heartbeat Writer
======================
Call this from your calm loop on the A800 machine to write HEARTBEAT.json to GitHub.
The monitor downloads this file to check training progress.

Usage (add to your calm loop, call every N ticks):
    python scripts/monitor/a800_write_heartbeat.py --tick 323 --mode sft --project-pct 72.5
    
Or import and call from your training script:
    from scripts.monitor.a800_write_heartbeat import write_heartbeat
    write_heartbeat(tick=323, mode="sft", project_pct=72.5)
"""

import argparse
import base64
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

GH_REPO = "specimba/NEXUS_discovery_GPU"
HEARTBEAT_PATH = "reports/session4/a800/HEARTBEAT.json"
BRANCH = "main"


def get_token():
    """Get GitHub token from environment or gh CLI."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return token
    # Try gh CLI
    import subprocess
    try:
        result = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def write_heartbeat(tick: int, mode: str = "sft", project_pct: float = 0.0,
                    extra: dict | None = None) -> dict:
    """Write heartbeat JSON to GitHub."""
    token = get_token()
    if not token:
        return {"error": "no_github_token"}

    body = {
        "tick": tick,
        "mode": mode,
        "project_pct": project_pct,
        "stamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "calm_pid": os.getpid(),
        "extra": extra or {},
    }

    # Get current file SHA (for update)
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "a800-heartbeat",
    }

    sha = None
    try:
        req = urllib.request.Request(
            f"https://api.github.com/repos/{GH_REPO}/contents/{HEARTBEAT_PATH}",
            headers=headers,
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            info = json.loads(resp.read().decode())
            sha = info.get("sha")
    except Exception:
        pass  # File may not exist yet

    # Write file
    content = base64.b64encode(json.dumps(body, indent=2).encode()).decode()
    payload = {
        "message": f"heartbeat tick={tick} mode={mode}",
        "content": content,
        "branch": BRANCH,
    }
    if sha:
        payload["sha"] = sha

    try:
        req = urllib.request.Request(
            f"https://api.github.com/repos/{GH_REPO}/contents/{HEARTBEAT_PATH}",
            data=json.dumps(payload).encode(),
            headers=headers,
            method="PUT",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode())
            return {"status": "ok", "tick": tick, "sha": result.get("content", {}).get("sha", "")}
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Write A800 heartbeat to GitHub")
    parser.add_argument("--tick", type=int, required=True)
    parser.add_argument("--mode", default="sft")
    parser.add_argument("--project-pct", type=float, default=0.0)
    args = parser.parse_args()

    result = write_heartbeat(args.tick, args.mode, args.project_pct)
    print(json.dumps(result, indent=2))
