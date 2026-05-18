import argparse
import json
from pathlib import Path


def _state_dir() -> Path:
    return Path(".nexus_pi") / "state"


def _protected_workloads() -> list[str]:
    return ["browser_tabs", "OBS/Streamlabs", "devin", "Docker", "active_agent_shells"]


def _json_print(payload: dict) -> None:
    print(json.dumps(payload, indent=2))


def run_cycle_check() -> int:
    state_dir = _state_dir()
    compact_path = state_dir / "session_compact.json"
    halt_path = state_dir / "halt_report.json"

    if halt_path.exists():
        halt = json.loads(halt_path.read_text(encoding="utf-8"))
        _json_print({
            "status": "halted",
            "reason": halt.get("failed_check", "unknown"),
            "recovery_hint": halt.get("recovery_hint"),
            "source": str(halt_path),
        })
        return 1

    if compact_path.exists():
        compact = json.loads(compact_path.read_text(encoding="utf-8"))
        _json_print({
            "status": "ok",
            "source": str(compact_path),
            "last_cycle": compact.get("last_cycle"),
            "updated_at": compact.get("updated_at"),
        })
        return 0

    _json_print({
        "status": "unavailable",
        "reason": "No cycle state file found",
        "expected_paths": [str(compact_path), str(halt_path)],
    })
    return 2


def run_doctor(report_only: bool) -> int:
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
    doctor.add_argument("--report-only", action="store_true")
    subparsers.add_parser("status", help="Report current Nexus status")
    handoff = subparsers.add_parser("handoff", help="Generate a cold-handoff package")
    handoff.add_argument("--output", default=None)
    args = parser.parse_args()

    if args.command == "cycle-check":
        return run_cycle_check()
    if args.command == "doctor":
        return run_doctor(args.report_only)
    if args.command == "status":
        return run_status()
    if args.command == "handoff":
        return run_handoff(args.output)
    parser.error(f"Unknown command: {args.command}")
    return 2
