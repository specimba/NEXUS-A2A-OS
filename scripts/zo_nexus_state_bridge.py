"""Read-only Zo/NEXUS state digest and narrow endpoint helpers."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
ALLOWED_ENDPOINTS = {"/state", "/git", "/queue", "/nexusctl", "/ports", "/docker", "/handoff"}


def _run(cmd: list[str], timeout: int = 10) -> dict[str, Any]:
    try:
        result = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, timeout=timeout)
        return {"ok": result.returncode == 0, "code": result.returncode, "stdout": result.stdout.strip(), "stderr": result.stderr.strip()}
    except Exception as exc:
        return {"ok": False, "code": -1, "stdout": "", "stderr": str(exc)}


def _git_digest(run_probes: bool) -> dict[str, Any]:
    if not run_probes:
        return {"probes_ran": False}
    branch = _run(["git", "branch", "--show-current"])
    head = _run(["git", "rev-parse", "--short=12", "HEAD"])
    status = _run(["git", "status", "--porcelain=v1"])
    return {
        "probes_ran": True,
        "branch": branch["stdout"] if branch["ok"] else "unknown",
        "head": head["stdout"] if head["ok"] else "unknown",
        "dirty_count": len(status["stdout"].splitlines()) if status["ok"] and status["stdout"] else 0,
    }


def _queue_digest() -> dict[str, int]:
    root = REPO_ROOT / "tasks"
    return {
        "pending": len(list((root / "pending").glob("*.task.md"))) if (root / "pending").exists() else 0,
        "done": len(list((root / "done").glob("*.task.md"))) if (root / "done").exists() else 0,
        "failed": len(list((root / "failed").glob("*.task.md"))) if (root / "failed").exists() else 0,
    }


def build_digest(run_probes: bool = False) -> dict[str, Any]:
    """Build a sanitized state digest without reading env/secrets."""
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "scripts/zo_nexus_state_bridge.py",
        "role": "Zo cloud watchtower; local NEXUS remains execution authority",
        "git": _git_digest(run_probes),
        "queue": _queue_digest(),
        "nexusctl": {"probes_ran": False} if not run_probes else _run(["python", "-m", "nexusctl", "doctor", "version", "--report-only"]),
        "ports": {"live_scan": False},
        "docker": {"live_scan": False},
        "handoff": {"recommended": "docs/handoff"},
        "security": {
            "no_env": True,
            "no_arbitrary_file_read": True,
            "no_command_execution_in_server_mode": True,
            "side_effects": "blocked",
        },
        "allowed_endpoints": sorted(ALLOWED_ENDPOINTS),
    }


def endpoint_payload(snapshot: dict[str, Any], path: str) -> tuple[int, dict[str, Any]]:
    route = "/" + path.split("?", 1)[0].strip("/").split("/", 1)[0]
    if route == "/state":
        return 200, snapshot
    if route in ALLOWED_ENDPOINTS:
        return 200, snapshot.get(route.strip("/"), {})
    return 404, {"error": "not_found", "allowed_endpoints": sorted(ALLOWED_ENDPOINTS)}


def is_authorized(header: str | None, token: str | None) -> bool:
    if not header or not token:
        return False
    return header == f"Bearer {token}"


def write_snapshot(output: str | Path, run_probes: bool = False) -> dict[str, Any]:
    digest = build_digest(run_probes=run_probes)
    out_path = Path(output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(digest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return digest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command")
    snap = sub.add_parser("snapshot")
    snap.add_argument("--output", default="docs/handoff/zo-coordination/NEXUS_STATE_DIGEST.json")
    snap.add_argument("--run-probes", action="store_true")
    args = parser.parse_args()
    if args.command == "snapshot":
        write_snapshot(args.output, run_probes=args.run_probes)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
