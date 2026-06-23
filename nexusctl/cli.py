import argparse
import importlib.util
import json
import subprocess
from datetime import date, datetime, timezone
from pathlib import Path


def _state_dir() -> Path:
    repo_root = _find_repo_root()
    return (repo_root or Path.cwd()) / ".nexus_pi" / "state"


def _protected_workloads() -> list[str]:
    return ["browser_tabs", "OBS/Streamlabs", "devin", "Docker", "active_agent_shells"]


def _json_print(payload: dict) -> None:
    print(json.dumps(payload, indent=2))


def _as_dict(payload: object) -> dict:
    return payload if isinstance(payload, dict) else {}


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
    paths = {*task_dir.glob("*.task.md"), *task_dir.glob("TASK-*.json")}
    return len(paths)


def _module_presence(module_names: list[str]) -> dict:
    presence = {}
    for name in module_names:
        presence[name] = importlib.util.find_spec(name) is not None
    return presence


def run_cycle_check() -> int:
    state_dir = _state_dir()
    compact_path = state_dir / "session_compact.json"
    halt_path = state_dir / "halt_report.json"

    if halt_path.exists():
        try:
            halt = _as_dict(json.loads(halt_path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            halt = {}
        _json_print({
            "status": "halted",
            "reason": halt.get("failed_check", "unknown"),
            "recovery_hint": halt.get("recovery_hint"),
            "source": str(halt_path),
        })
        return 1

    if compact_path.exists():
        try:
            compact = _as_dict(json.loads(compact_path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError) as exc:
            _json_print({
                "status": "unavailable",
                "reason": "Invalid cycle state file",
                "error": str(exc),
                "source": str(compact_path),
            })
            return 2
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
        "nexus_os/bridge/cloudflare_bypass.py",
        "nexus_os/governor/trust_kernel.py",
        "nexus_os/twave/chimera_router_v2.py",
        "src/nexus_os/governor/trust_kernel.py",
        "src/nexus_os/governor/trust_scoring.py",
        "src/nexus_os/monitoring/token_guard.py",
        "src/nexus_os/monitoring/token_policy.py",
    ]
    missing = [p for p in required_files if not (repo_root / p).exists()]

    head = _git_json(repo_root, ["rev-parse", "--short", "HEAD"])
    branch = _git_json(repo_root, ["rev-parse", "--abbrev-ref", "HEAD"])
    status = _git_json(repo_root, ["status", "--porcelain=v1"])
    github_main = _git_json(repo_root, ["rev-parse", "--verify", "--short", "github/main"])
    origin_main = _git_json(repo_root, ["rev-parse", "--verify", "--short", "origin/main"])

    porcelain_lines = [line for line in status.get("stdout", "").splitlines() if line]
    project_state = repo_root / "01_PROJECT_STATE.md"
    try:
        project_state_text = project_state.read_text(encoding="utf-8") if project_state.exists() else ""
    except OSError:
        project_state_text = ""
    head_short = head.get("stdout", "")
    project_state_current_date = f"Date: {date.today().isoformat()}" in project_state_text
    obsolete_project_state_claim = "617 passed" in project_state_text or "636 passed" in project_state_text
    git_ok = all(probe.get("ok") for probe in (head, branch, status))

    payload = {
        "status": "ok" if git_ok and not missing and project_state_current_date and not obsolete_project_state_claim else "degraded",
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


def run_doctor_hygiene(report_only: bool) -> int:
    from nexus_os.monitoring.disk_hygiene import build_hygiene_report

    payload = build_hygiene_report(paths=[], top_file_limit=0, include_system_files=True)
    payload["command"] = "doctor hygiene"
    payload["report_only"] = report_only
    payload["scope"] = "drive_accounting_plus_root_system_files"
    _json_print(payload)
    return 0


def run_doctor(report_only: bool, topic: str | None, refresh: bool) -> int:
    if topic == "memory":
        return run_doctor_memory(report_only)
    if topic == "version":
        return run_doctor_version(report_only, refresh)
    if topic == "hygiene":
        return run_doctor_hygiene(report_only)

    # No topic specified — run comprehensive diagnostic
    memory_result = run_doctor_memory(report_only=True)
    version_result = run_doctor_version(report_only=True, refresh=refresh)

    # Build comprehensive diagnostic payload
    repo_root = _find_repo_root()
    payload = {
        "status": "ok",
        "command": "doctor",
        "report_only": report_only,
        "message": "NEXUS OS comprehensive diagnostic complete.",
        "protected_workloads": _protected_workloads(),
        "no_fake_counts": True,
        "subsystems": {
            "memory": "checked",
            "version": "checked",
        },
        "repo_root": str(repo_root) if repo_root else None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    _json_print(payload)
    return 0


def run_status() -> int:
    repo_root = _find_repo_root()

    # Module health checks (same set as nexus_os.cli _cmd_health)
    modules = [
        ("engine.router", "nexus_os.engine.router", "TaskRouter"),
        ("governor.base", "nexus_os.governor.base", "NexusGovernor"),
        ("vault.manager", "nexus_os.vault.manager", "VaultManager"),
        ("bridge.server", "nexus_os.bridge.server", "BridgeServer"),
        ("monitoring.token_guard", "nexus_os.monitoring.token_guard", "TokenGuard"),
        ("mcp.server", "nexus_os.mcp.server", "GovernedMCPServer"),
        ("team.coordinator", "nexus_os.team.coordinator", "TeamCoordinator"),
        ("nexusclaw.orchestrator", "nexus_os.nexusclaw.orchestrator", "NexusClawOrchestrator"),
        ("nexusclaw.agent_pool", "nexus_os.nexusclaw.agent_pool", "AgentPool"),
        ("nexusclaw.task_router", "nexus_os.nexusclaw.task_router", "TaskRouter"),
        ("nexusclaw.message_bus", "nexus_os.nexusclaw.message_bus", "MessageBus"),
        ("nexusclaw.brainstorm", "nexus_os.nexusclaw.brainstorm", "BrainstormEngine"),
    ]
    health = {}
    all_ok = True
    for name, import_path, import_name in modules:
        try:
            mod = __import__(import_path, fromlist=[import_name])
            getattr(mod, import_name)
            health[name] = "ok"
        except Exception as e:
            health[name] = f"FAIL: {e}"
            all_ok = False

    payload = {
        "status": "ok" if all_ok else "degraded",
        "command": "status",
        "message": "NEXUS OS status report.",
        "protected_workloads": _protected_workloads(),
        "repo_root": str(repo_root) if repo_root else None,
        "health": health,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    _json_print(payload)
    return 0 if all_ok else 1


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


def run_disk_rescue_level6(args: argparse.Namespace) -> int:
    repo_root = _find_repo_root()
    if repo_root is None:
        _json_print({
            "status": "degraded",
            "command": "disk-rescue level6",
            "error": "git_repo_not_found",
        })
        return 2

    script_path = repo_root / "scripts" / "nexus_level6_controlled_cleanup.ps1"
    if not script_path.exists():
        _json_print({
            "status": "degraded",
            "command": "disk-rescue level6",
            "error": "level6_script_missing",
            "expected_path": str(script_path),
        })
        return 2

    selected_actions = [
        args.approved_stale_apps,
        args.approved_caches,
        args.notion_caches,
        args.streamlabs_caches,
        args.kilo_snapshot,
        args.kilo_git_garbage,
        args.legacy_project_candidates,
    ]
    if args.execute and not any(selected_actions):
        _json_print({
            "status": "blocked",
            "command": "disk-rescue level6",
            "reason": "execute_requested_without_action_flags",
            "hint": "Select at least one approved action group.",
        })
        return 2

    command = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script_path),
    ]
    if args.execute:
        command.append("-Execute")
    if args.stop_approved_processes:
        command.append("-StopApprovedProcesses")
    if args.approved_stale_apps:
        command.append("-MoveApprovedStaleApps")
    if args.approved_caches:
        command.append("-CleanApprovedCaches")
    if args.notion_caches:
        command.append("-CleanNotionCaches")
    if args.streamlabs_caches:
        command.append("-CleanStreamlabsCaches")
    if args.kilo_snapshot:
        command.append("-QuarantineKiloSnapshot")
    if args.kilo_git_garbage:
        command.append("-QuarantineKiloGitGarbage")
    if args.legacy_project_candidates:
        command.append("-MoveLegacyProjectCandidates")
    if args.quarantine_root:
        command.extend(["-QuarantineRoot", args.quarantine_root])

    try:
        proc = subprocess.run(command, cwd=repo_root, check=False)
    except FileNotFoundError:
        _json_print({
            "status": "degraded",
            "command": "disk-rescue level6",
            "error": "powershell_not_found",
            "argv": command,
        })
        return 2

    return proc.returncode


def run_disk_rescue_kilo_forensics(args: argparse.Namespace) -> int:
    try:
        from scripts.kilo_snapshot_forensics import analyze
    except ImportError:
        import sys
        repo_root = _find_repo_root()
        if repo_root and str(repo_root) not in sys.path:
            sys.path.insert(0, str(repo_root))
        from scripts.kilo_snapshot_forensics import analyze

    report = analyze(
        snapshot_root=args.snapshot_root,
        repo_root=args.repo_root,
        max_compare_bytes=args.max_compare_mib * 1024 * 1024,
        redact_sensitive=not args.include_sensitive_paths,
        hash_working_tree=args.include_working_tree_hash,
        candidate_limit=args.candidate_limit,
        byte_compare_prefixes=(
            args.byte_compare_prefix
            or (
                (
                    "benchmarks",
                    "datasets",
                    "models",
                    "src",
                    "nexus_os",
                    "research",
                    "docs",
                    ".agents",
                    "tests",
                    "tasks",
                    "evidence",
                    "logs",
                    "upload",
                )
                if args.byte_compare_high_value
                else None
            )
        ),
        extract_missing_review_dir=args.extract_missing_review_dir,
    )
    report["command"] = "disk-rescue kilo-forensics"
    payload = json.dumps(report, indent=2, sort_keys=True)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload, encoding="utf-8")
    print(payload)
    return 0


def run_wiki_check(wiki_dir: Path, out_path: Path | None) -> int:
    try:
        from scripts.reviewground_wiki_check import check_wiki
    except ImportError:
        import sys
        repo_root = _find_repo_root()
        if repo_root and str(repo_root) not in sys.path:
            sys.path.insert(0, str(repo_root))
        from scripts.reviewground_wiki_check import check_wiki

    report = check_wiki(wiki_dir)
    report["command"] = "wiki check"
    report["status"] = "ok" if report["passed"] else "degraded"

    payload = json.dumps(report, indent=2, sort_keys=True)
    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(payload, encoding="utf-8")

    print(payload)
    return 0 if report["passed"] else 1


def run_nexusclaw_status() -> int:
    from nexus_os.nexusclaw.coordinator import NexusClawCoordinator
    import sys
    repo_root = _find_repo_root()
    if repo_root and str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    coordinator = NexusClawCoordinator()
    res = coordinator.status()
    res["command"] = "nexusclaw.status"
    print(json.dumps(res, indent=2))
    return 0


def run_nexusclaw_dispatch_dry_run(args: argparse.Namespace) -> int:
    from nexus_os.nexusclaw.coordinator import NexusClawCoordinator
    from nexus_os.nexusclaw.envelope import NexusClawTaskEnvelope
    import sys
    repo_root = _find_repo_root()
    if repo_root and str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    task_payload = {
        "task_id": args.task_id,
        "source": args.source,
        "lane": "orchestrator",
        "intent": args.intent,
        "risk_level": args.risk_level,
        "required_capabilities": args.capability,
        "evidence_refs": args.evidence_ref,
        "resource_budget": {"max_tokens": 4000},
    }

    coordinator = NexusClawCoordinator()
    envelope = NexusClawTaskEnvelope.from_dict(task_payload)
    result = coordinator.dispatch_dry_run(envelope)

    res = {
        "command": "nexusclaw.dispatch_dry_run",
        "result": result.to_dict(),
    }
    print(json.dumps(res, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="nexusctl")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.required = True
    subparsers.required = True
    subparsers.add_parser("cycle-check", help="Validate the latest recorded agent cycle")
    doctor = subparsers.add_parser("doctor", help="Report-only system diagnostics")
    doctor.add_argument("topic", nargs="?", choices=["memory", "version", "hygiene"])
    doctor.add_argument("--report-only", action="store_true")
    doctor.add_argument("--refresh", action="store_true", help="Reserved for future explicit ref refresh")
    subparsers.add_parser("status", help="Report current Nexus status")
    handoff = subparsers.add_parser("handoff", help="Generate a cold-handoff package")
    handoff.add_argument("--output", default=None)

    wiki = subparsers.add_parser("wiki", help="Manage and validate docs/wiki workspace")
    wiki_sub = wiki.add_subparsers(dest="subcommand")
    wiki_sub.required = True
    wiki_check = wiki_sub.add_parser("check", help="Check wiki frontmatter and links")
    wiki_check.add_argument("--dir", required=True, type=Path, help="docs/wiki workspace path")
    wiki_check.add_argument("--out", type=Path, help="Optional JSON report path")

    disk_rescue = subparsers.add_parser("disk-rescue", help="Run controlled disk rescue protocols")
    disk_rescue_subparsers = disk_rescue.add_subparsers(dest="disk_rescue_command")
    disk_rescue_subparsers.required = True
    level6 = disk_rescue_subparsers.add_parser("level6", help="Dry-run or execute Level 6 cleanup quarantine")
    level6.add_argument("--execute", action="store_true", help="Perform selected moves/stops instead of dry-run")
    level6.add_argument("--stop-approved-processes", action="store_true", help="Stop only processes matched by the approved Level 6 allowlist")
    level6.add_argument("--approved-stale-apps", action="store_true", help="Move approved Windsurf/Cursor/Jan/DJ targets to D quarantine")
    level6.add_argument("--approved-caches", action="store_true", help="Move approved Notion and Streamlabs cache folders to D quarantine")
    level6.add_argument("--notion-caches", action="store_true", help="Move approved Notion cache folders to D quarantine")
    level6.add_argument("--streamlabs-caches", action="store_true", help="Move approved Streamlabs cache folders to D quarantine; Media is not touched")
    level6.add_argument("--kilo-snapshot", action="store_true", help="Move the full Kilo snapshot store to D quarantine")
    level6.add_argument("--kilo-git-garbage", action="store_true", help="Move only Kilo tmp_pack Git garbage to D quarantine")
    level6.add_argument("--legacy-project-candidates", action="store_true", help="Move C-root legacy candidates only after explicit approval")
    level6.add_argument("--quarantine-root", default=None, help="Override the D quarantine root")
    kilo_forensics = disk_rescue_subparsers.add_parser("kilo-forensics", help="Read-only Kilo snapshot inventory and live repo comparison")
    kilo_forensics.add_argument("--snapshot-root", type=Path, default=Path(r"D:\NEXUS_COLD\level6_quarantine_20260608\Users_speci.000_.local_share_kilo_snapshot"))
    kilo_forensics.add_argument("--repo-root", type=Path, default=Path(r"C:\Users\speci.000\Documents\NEXUS"))
    kilo_forensics.add_argument("--out", type=Path, help="Optional JSON report output path")
    kilo_forensics.add_argument("--max-compare-mib", type=int, default=50)
    kilo_forensics.add_argument("--include-sensitive-paths", action="store_true", help="Do not redact sensitive-looking path names in output")
    kilo_forensics.add_argument("--include-working-tree-hash", action="store_true", help="Hash live working-tree files; slower and opt-in")
    kilo_forensics.add_argument("--candidate-limit", type=int, default=200, help="Maximum candidate rows per list")
    kilo_forensics.add_argument("--byte-compare-high-value", action="store_true", help="Git blob-byte compare high-value prefixes")
    kilo_forensics.add_argument("--byte-compare-prefix", action="append", default=[], help="Git blob-byte compare one prefix; repeatable")
    kilo_forensics.add_argument("--extract-missing-review-dir", type=Path, help="Extract missing-live blobs into a review-only folder inside the repo")

    nexusclaw = subparsers.add_parser("nexusclaw", help="NexusClaw subsystem commands")
    nexusclaw_sub = nexusclaw.add_subparsers(dest="nexusclaw_command")
    nexusclaw_sub.required = True
    nexusclaw_sub.add_parser("status", help="Get NexusClaw status")

    dispatch = nexusclaw_sub.add_parser("dispatch-dry-run", help="Dispatch dry-run task")
    dispatch.add_argument("--task-id", required=True)
    dispatch.add_argument("--source", required=True)
    dispatch.add_argument("--intent", required=True)
    dispatch.add_argument("--risk-level", required=True)
    dispatch.add_argument("--capability", action="append", default=[])
    dispatch.add_argument("--evidence-ref", action="append", default=[])
    args = parser.parse_args()

    if args.command == "cycle-check":
        return run_cycle_check()
    if args.command == "doctor":
        return run_doctor(args.report_only, args.topic, args.refresh)
    if args.command == "status":
        return run_status()
    if args.command == "handoff":
        return run_handoff(args.output)
    if args.command == "wiki":
        if args.subcommand == "check":
            return run_wiki_check(args.dir, args.out)
    if args.command == "disk-rescue":
        if args.disk_rescue_command == "level6":
            return run_disk_rescue_level6(args)
        if args.disk_rescue_command == "kilo-forensics":
            return run_disk_rescue_kilo_forensics(args)
        parser.error(f"Unknown disk-rescue command: {args.disk_rescue_command}")
        return 2
    if args.command == "nexusclaw":
        if args.nexusclaw_command == "status":
            return run_nexusclaw_status()
        if args.nexusclaw_command == "dispatch-dry-run":
            return run_nexusclaw_dispatch_dry_run(args)
    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
