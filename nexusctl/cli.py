import argparse
import importlib.util
import json
import subprocess
import sys
from datetime import date
from pathlib import Path


def _state_dir() -> Path:
    return Path(".nexus_pi") / "state"


def _protected_workloads() -> list[str]:
    return ["browser_tabs", "OBS/Streamlabs", "devin", "Docker", "active_agent_shells"]


def _json_print(payload: dict) -> None:
    print(json.dumps(payload, indent=2))


def _find_repo_root(start: Path | None = None) -> Path | None:
    current = (start or Path.cwd()).resolve()
    for path in [current, *current.parents]:
        if (path / ".git").exists():
            return path
    return None


def _git_json(repo_root: Path, args: list[str]) -> dict:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
    except Exception as exc:  # pragma: no cover - defensive host diagnostic
        return {"ok": False, "error": str(exc), "args": args}

    return {
        "ok": proc.returncode == 0,
        "code": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
        "args": args,
    }


def _count_task_files(repo_root: Path, queue: str) -> int:
    task_dir = repo_root / "tasks" / queue
    if not task_dir.exists():
        return 0
    return len(list(task_dir.glob("*.task.md")))


def _module_presence(module_names: list[str]) -> dict:
    repo_root = _find_repo_root()
    if repo_root is not None:
        for path in [repo_root, repo_root / "src"]:
            path_text = str(path)
            if path_text not in sys.path:
                sys.path.insert(0, path_text)

    presence = {}
    for name in module_names:
        try:
            presence[name] = importlib.util.find_spec(name) is not None
        except (ImportError, AttributeError, ValueError):
            presence[name] = False
    return presence


def run_cycle_check() -> int:
    state_dir = _state_dir()
    compact_path = state_dir / "session_compact.json"
    halt_path = state_dir / "halt_report.json"

    if halt_path.exists():
        try:
            halt = json.loads(halt_path.read_text(encoding="utf-8"))
            _json_print({
                "status": "halted",
                "reason": halt.get("failed_check", "unknown"),
                "recovery_hint": halt.get("recovery_hint"),
                "source": str(halt_path),
            })
            return 1
        except (json.JSONDecodeError, OSError) as exc:
            _json_print({
                "status": "unavailable",
                "reason": "malformed_state",
                "source": str(halt_path),
                "error": str(exc),
            })
            return 2

    if compact_path.exists():
        try:
            compact = json.loads(compact_path.read_text(encoding="utf-8"))
            _json_print({
                "status": "ok",
                "source": str(compact_path),
                "last_cycle": compact.get("last_cycle"),
                "updated_at": compact.get("updated_at"),
            })
            return 0
        except (json.JSONDecodeError, OSError) as exc:
            _json_print({
                "status": "unavailable",
                "reason": "malformed_state",
                "source": str(compact_path),
                "error": str(exc),
            })
            return 2

    _json_print({
        "status": "unavailable",
        "reason": "No cycle state file found",
        "expected_paths": [str(compact_path), str(halt_path)],
    })
    return 2


def run_doctor_memory(report_only: bool) -> int:
    modules = [
        "nexus_os.vault.memory_adapter",
        "nexus_os.governor.trust_kernel",
        "src.nexus_os.governor.trust_kernel",
        "src.nexus_os.governor.trust_scoring",
        "src.nexus_os.monitoring.token_guard",
        "src.nexus_os.monitoring.token_policy",
    ]
    checks = _module_presence(modules)
    payload = {
        "status": "ok" if all(checks.values()) else "degraded",
        "command": "doctor memory",
        "report_only": report_only,
        "checks": checks,
        "trust_kernel": {
            "root_compat": checks["nexus_os.governor.trust_kernel"],
            "src_public": checks["src.nexus_os.governor.trust_kernel"],
        },
        "token_policy_plane": {
            "token_guard": checks["src.nexus_os.monitoring.token_guard"],
            "token_policy": checks["src.nexus_os.monitoring.token_policy"],
        },
        "memory_backend": {
            "adapter_present": checks["nexus_os.vault.memory_adapter"],
            "spew_status": "module_presence_only",
        },
        "protected_workloads": _protected_workloads(),
    }
    _json_print(payload)
    return 0


def run_doctor_version(report_only: bool, refresh: bool) -> int:
    repo_root = _find_repo_root()
    if repo_root is None:
        _json_print({
            "status": "degraded",
            "command": "doctor version",
            "report_only": report_only,
            "error": "git_repo_not_found",
        })
        return 0

    required_files = [
        "README.md",
        "AGENTS.md",
        "pyproject.toml",
        "nexusctl/__main__.py",
        "nexusctl/cli.py",
        "src/nexus_os/governor/trust_kernel.py",
        "src/nexus_os/governor/trust_scoring.py",
        "src/nexus_os/monitoring/token_guard.py",
        "src/nexus_os/monitoring/token_policy.py",
        "src/nexus_os/security/sanitizer.py",
        "src/nexus_os/mcp/server.py",
    ]
    missing = [p for p in required_files if not (repo_root / p).exists()]

    head = _git_json(repo_root, ["rev-parse", "--short", "HEAD"])
    branch = _git_json(repo_root, ["rev-parse", "--abbrev-ref", "HEAD"])
    status = _git_json(repo_root, ["status", "--porcelain=v1"])
    github_main = _git_json(repo_root, ["rev-parse", "--verify", "--short", "github/main"])
    origin_main = _git_json(repo_root, ["rev-parse", "--verify", "--short", "origin/main"])

    porcelain_lines = [line for line in status.get("stdout", "").splitlines() if line]
    project_state = repo_root / "01_PROJECT_STATE.md"
    project_state_text = project_state.read_text(encoding="utf-8") if project_state.exists() else ""
    head_short = head.get("stdout", "")
    project_state_current_date = f"Date: {date.today().isoformat()}" in project_state_text
    obsolete_project_state_claim = "617 passed" in project_state_text or "636 passed" in project_state_text

    payload = {
        "status": "ok" if not missing and project_state_current_date and not obsolete_project_state_claim else "degraded",
        "command": "doctor version",
        "report_only": report_only,
        "refresh_requested": refresh,
        "refresh_performed": False,
        "repo_root": str(repo_root),
        "branch": branch.get("stdout"),
        "head": head_short,
        "cached_refs": {
            "github/main": github_main.get("stdout") if github_main.get("ok") else None,
            "origin/main": origin_main.get("stdout") if origin_main.get("ok") else None,
        },
        "dirty": {
            "count": len(porcelain_lines),
            "entries": porcelain_lines[:50],
            "truncated": len(porcelain_lines) > 50,
        },
        "queue": {
            "pending": _count_task_files(repo_root, "pending"),
            "done": _count_task_files(repo_root, "done"),
            "failed": _count_task_files(repo_root, "failed"),
        },
        "required_files": {
            "missing": missing,
            "present_count": len(required_files) - len(missing),
            "total": len(required_files),
        },
        "docs_drift": {
            "project_state_exists": project_state.exists(),
            "project_state_current_date": project_state_current_date,
            "project_state_mentions_head": bool(head_short and head_short in project_state_text),
            "obsolete_test_count_claim": obsolete_project_state_claim,
        },
        "protected_workloads": _protected_workloads(),
    }
    _json_print(payload)
    return 0


def run_doctor(report_only: bool, topic: str | None, refresh: bool) -> int:
    if topic == "memory":
        return run_doctor_memory(report_only)
    if topic == "version":
        return run_doctor_version(report_only, refresh)

    payload = {
        "status": "unavailable",
        "command": "doctor",
        "report_only": report_only,
        "error": "legacy_doctor_entrypoint_not_restored",
        "message": "Use direct evidence checks until the full doctor workflow is restored.",
        "protected_workloads": _protected_workloads(),
        "no_fake_counts": True,
    }
    _json_print(payload)
    return 2


def run_status() -> int:
    payload = {
        "status": "unavailable",
        "command": "status",
        "error": "legacy_status_entrypoint_not_restored",
        "message": "Use direct evidence checks until the full status workflow is restored.",
        "protected_workloads": _protected_workloads(),
    }
    _json_print(payload)
    return 2


def run_handoff(output: str | None) -> int:
    payload = {
        "status": "unavailable",
        "command": "handoff",
        "error": "legacy_handoff_entrypoint_not_restored",
        "message": "Cold handoff packaging is not yet restored in the tracked CLI.",
        "suggested_output": output,
    }
    _json_print(payload)
    return 2


def main() -> int:
    parser = argparse.ArgumentParser(prog="nexusctl")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.required = True
    subparsers.add_parser("cycle-check", help="Validate the latest recorded agent cycle")
    doctor = subparsers.add_parser("doctor", help="Report-only system diagnostics")
    doctor.add_argument("topic", nargs="?", choices=["memory", "version"])
    doctor.add_argument("--report-only", action="store_true")
    doctor.add_argument("--refresh", action="store_true", help="Reserved for future explicit ref refresh")
    subparsers.add_parser("status", help="Report current Nexus status")
    handoff = subparsers.add_parser("handoff", help="Generate a cold-handoff package")
    handoff.add_argument("--output", default=None)
    args = parser.parse_args()

    if args.command == "cycle-check":
        return run_cycle_check()
    if args.command == "doctor":
        return run_doctor(args.report_only, args.topic, args.refresh)
    if args.command == "status":
        return run_status()
    if args.command == "handoff":
        return run_handoff(args.output)
    parser.error(f"Unknown command: {args.command}")
    return 2
