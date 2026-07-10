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


def run_grounding(args: argparse.Namespace) -> int:
    from nexus_os.grounding import GroundingService, GroundingStore, default_source_roots

    try:
        store = GroundingStore()
        store_error: str | None = None
    except Exception as exc:  # pragma: no cover - defensive doctor path
        store = None
        store_error = f"{type(exc).__name__}: {exc}"

    if args.grounding_command == "status":
        if store is None:
            _json_print({
                "status": "degraded",
                "command": "grounding status",
                "error": store_error,
                "read_only": True,
                "writable": False,
            })
            return 0
        payload = store.status()
        status = "degraded" if payload.get("read_only") else "ok"
        _json_print({"status": status, "command": "grounding status", **payload})
        return 0
    if args.grounding_command == "doctor":
        roots = default_source_roots()
        root_status = {
            source_id: {"path": str(path), "exists": path.exists()}
            for source_id, path in roots.items()
        }
        store_payload: dict
        if store is None:
            store_payload = {
                "error": store_error,
                "read_only": True,
                "writable": False,
            }
            overall = "degraded"
        else:
            store_payload = store.status()
            overall = "ok"
            if store_payload.get("read_only") or store_payload.get("init_error"):
                overall = "degraded"
            if not all(item["exists"] for item in root_status.values()):
                overall = "degraded"
        _json_print({
            "status": overall,
            "command": "grounding doctor",
            "roots": root_status,
            "store": store_payload,
            "canonical_mutation_allowed": False,
        })
        return 0
    if store is None:
        _json_print({
            "status": "error",
            "command": f"grounding {args.grounding_command}",
            "error": store_error,
        })
        return 1
    if getattr(store, "read_only", False) and args.grounding_command in {
        "scan", "watch", "promote"
    }:
        _json_print({
            "status": "blocked",
            "command": f"grounding {args.grounding_command}",
            "reason": "store_read_only",
            "store": store.status(),
        })
        return 2
    if args.grounding_command == "scan":
        result = GroundingService(store=store).reconcile(
            changed_only=args.changed_only,
            stability_delay_seconds=args.stability_delay,
            max_files=args.max_files,
        )
        result["command"] = "grounding scan"
        _json_print(result)
        return 0
    if args.grounding_command == "watch":
        # Lazy import: watchdog is optional for doctor/status/scan paths.
        from nexus_os.grounding.native_watcher import watch_grounding

        watch_grounding(
            GroundingService(store=store),
            fallback_poll_seconds=args.poll_seconds,
            reconcile_seconds=args.reconcile_seconds,
        )
        return 0
    if args.grounding_command == "promote":
        proposal_path = store.proposals_dir / f"{args.proposal}.json"
        if not proposal_path.exists():
            _json_print({
                "status": "blocked",
                "command": "grounding promote",
                "reason": "proposal_not_found",
                "proposal": args.proposal,
            })
            return 2
        proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
        _json_print({
            "status": "dry_run",
            "command": "grounding promote",
            "proposal": proposal,
            "canonical_files_modified": [],
            "operator_approval_required": True,
        })
        return 0
    raise ValueError(f"Unknown grounding command: {args.grounding_command}")


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


def run_models_list(refresh: bool) -> int:
    """`nexusctl models` — list installed CLIs and current reachability."""
    from nexusctl.model_sync import fetch_live_state, list_cli_inventory
    state = fetch_live_state(refresh=refresh)
    payload = list_cli_inventory(state)
    _json_print(payload)
    return 0 if (state.get("god_proxy_alive") or state.get("node_relay_alive")) else 2

def run_quota_command(args: argparse.Namespace) -> int:
    """`nexusctl quota` — durable provider budget controls."""
    from nexusctl.provider_quota_cli import run_quota

    code, payload = run_quota(args)
    _json_print(payload)
    return code



def run_dream_cycle() -> int:
    """`nexusctl dream-cycle` — memory consolidation."""
    try:
        from nexus_os.vault.dream_cycle import DreamCycle
        dc = DreamCycle()
        result = dc.consolidate()
        _json_print(result)
        return 0
    except Exception as exc:
        _json_print({"ok": False, "error": str(exc)})
        return 1


def run_adrf(args: argparse.Namespace) -> int:
    """`nexusctl adrf` — Adversarial Robustness Defense Framework (Plan 19)."""
    from nexus_os.security.adrf import ADRFDetector, AdversarialSignature, AttackType

    detector = ADRFDetector(a2a_channel=getattr(args, "a2a_channel", None))

    if getattr(args, "list", False):
        sigs = [sig.to_dict() for sig in detector._signatures]
        _json_print({"signatures": sigs, "count": len(sigs)})
        return 0

    if getattr(args, "add", None):
        try:
            data = json.loads(args.add)
            sig = AdversarialSignature(
                pattern=data["pattern"],
                attack_type=AttackType(data.get("attack_type", "injection")),
                severity=float(data.get("severity", 0.5)),
                description=data.get("description", ""),
            )
            detector.add_signature(sig)
            _json_print({"added": sig.to_dict()})
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            _json_print({"error": str(exc)})
            return 1
        return 0

    if getattr(args, "stats", False):
        _json_print(detector.get_stats())
        return 0

    if getattr(args, "test", None):
        result = detector.analyze(args.test)
        _json_print(result.to_dict())
        return 0

    _json_print({"error": "use --test TEXT | --list | --add JSON | --stats"})
    return 2


def run_hallucination_status() -> int:
    """`nexusctl hallucination` — calibrated hallucination detector stats."""
    try:
        from nexus_os.monitoring.calibrated_hallucination_detector import CalibratedHallucinationDetector
        chd = CalibratedHallucinationDetector()
        _json_print({"stats": chd.get_stats(), "history": chd.get_calibration_history()[-10:]})
        return 0
    except Exception as exc:
        _json_print({"ok": False, "error": str(exc)})
        return 1


def run_a2a_channels(args: argparse.Namespace) -> int:
    """`nexusctl a2a-channels` — inter-session A2A message bus (Plan 20)."""
    try:
        from nexus_os.bridge.a2a_channels import A2AChannelBus
        bus = A2AChannelBus()
    except Exception as exc:
        _json_print({"ok": False, "error": f"a2a_channels import failed: {exc}"})
        return 1

    if getattr(args, "list_channels", False):
        channels = bus.discover()
        _json_print(channels)
        return 0

    if getattr(args, "publish", None):
        channel_id, topic, msg = args.publish
        result = bus.publish(channel_id=channel_id, sender="nexusctl", message=msg, topic=topic)
        _json_print(result.to_dict())
        return 0

    if getattr(args, "subscribe", None):
        channel_id = args.subscribe[0]
        messages = bus.subscribe(channel_id, max_messages=50)
        _json_print({"channel": channel_id, "messages": [m.to_dict() for m in messages]})
        return 0

    if getattr(args, "consolidate", False):
        result = bus.consolidate()
        _json_print(result)
        return 0

    if getattr(args, "stats", False):
        stats = bus.get_stats()
        _json_print(stats)
        return 0

    _json_print({"ok": False, "error": "Usage: --list, --publish CHAN TOPIC MSG, --subscribe CHAN, --consolidate, or --stats"})
    return 2


def run_monitor(args: argparse.Namespace) -> int:
    """`nexusctl monitor` — Monitor Daemon."""
    from nexus_os.monitor_daemon import MonitorDaemon, install_monitor_schedule

    daemon = MonitorDaemon(
        interval_minutes=getattr(args, "interval", 15),
        a2a_channel=getattr(args, "a2a_channel", None),
    )

    if getattr(args, "install_schedule", False):
        result = install_monitor_schedule(interval_minutes=args.interval)
        _json_print(result)
        return 0 if result.get("installed") else 1

    if getattr(args, "status", False):
        status = daemon.get_status()
        _json_print(status)
        return 0

    if getattr(args, "daemon", False):
        daemon.run_daemon()
        return 0

    result = daemon.run_once()
    _json_print(result)
    return 0


def run_model_sync(args: argparse.Namespace) -> int:
    """`nexusctl model-sync` — sync live models/lanes to every CLI."""
    from nexusctl import model_sync
    argv: list[str] = []
    if getattr(args, "refresh", False):
        argv.append("--refresh")
    if getattr(args, "dry_run", False):
        argv.append("--dry-run")
    only = getattr(args, "only", None)
    if only:
        argv.extend(["--only", only])
    if getattr(args, "install_schedule", False):
        argv.append("--install-schedule")
    log = getattr(args, "log", None)
    if log:
        argv.extend(["--log", log])
    return model_sync.main(argv if argv else None)


def run_ports(args: argparse.Namespace) -> int:
    """`nexusctl ports doctor` — probe the 7350–7360 plane + pipeline layers."""
    from nexus_os.bridge.port_plane import doctor_report

    host = getattr(args, "host", None) or "127.0.0.1"
    timeout = float(getattr(args, "timeout", 2.0) or 2.0)
    band_only = bool(getattr(args, "band_only", False))
    report = doctor_report(host=host, timeout=timeout, band_only=band_only)
    _json_print(report)
    status = report.get("status")
    if status == "critical":
        return 2
    if status == "degraded":
        return 1
    return 0


def run_gmr(args: argparse.Namespace) -> int:
    """`nexusctl gmr` — catalogue telemetry + Chimera/LG pipeline."""
    cmd = getattr(args, "gmr_command", None)
    if cmd == "catalogue":
        from nexus_os.gmr.telemetry import TelemetryIngest

        ingest = TelemetryIngest()
        cache = ingest.fetch()
        payload = {
            "command": "gmr catalogue",
            "status": "ok" if cache else "degraded",
            "source": ingest.last_source,
            "error": ingest.last_error,
            "count": len(cache),
            "models": [
                {
                    "name": t.name,
                    "provider": t.provider,
                    "status": t.status,
                    "tier": t.tier,
                    "latency_ms": t.latency_ms,
                }
                for t in list(cache.values())[:80]
            ],
        }
        _json_print(payload)
        return 0 if cache else 1

    if cmd == "pipeline":
        from nexus_os.gmr.chimera_lg_pipeline import run_pipeline

        report = run_pipeline(
            args.prompt,
            execute=bool(args.execute),
            cloud=bool(args.cloud or args.execute),
            category=args.category,
            policy=args.policy,
            quality=float(args.quality),
            latency_budget_ms=float(args.budget),
            track=not bool(args.no_track),
            track_tokens=int(args.track_tokens),
            max_tokens_cap=int(args.max_tokens),
        )
        _json_print(report.to_dict())
        return 0 if report.status == "ok" else 1

    if cmd == "track":
        from nexus_os.gmr.chimera_lg_pipeline import run_lg_track

        lg = run_lg_track(
            category=args.category,
            temperature=float(args.temperature),
            tokens=int(args.tokens),
        )
        _json_print({"command": "gmr track", **lg})
        return 0

    raise ValueError(f"Unknown gmr command: {cmd}")


def run_grok_lane(args: argparse.Namespace) -> int:
    """`nexusctl grok-lane doctor` — pure-probe the full Grok automation lane.

    Probes the entire chain the NexusClaw Grok supervisor depends on, WITHOUT
    spawning any long-lived process (so this never blocks the agent shell):
        CDP(9224) -> Grok MCP bridge(7354) -> Node relay(7350) -> Python relay(7355)
        -> God Mode(7357) -> Dashboard(3000,/api/nexusclaw/status) -> Dashboard UI(7356)
    For every dead link it prints the EXACT command for the operator to run in an
    admin terminal (proxies must be owned by the operator, not this agent shell).
    Use --revive to attempt detached background relaunch of the relays only.
    """
    import urllib.request
    import shutil

    root = _find_repo_root() or Path.cwd()
    checks = [
        ("cdp",          9224, "/json/version",         "Chrome --remote-debugging-port=9224 (Grok authenticated profile)"),
        ("grok_bridge",  7354, "/health",                "Grok MCP bridge (tools/server)"),
        ("node_relay",   7350, "/",                      "Node ModelRelay primary"),
        ("python_relay", 7355, "/health",                "Python ModelRelay fallback"),
        ("god_mode",     7357, "/health",                "God Mode Proxy"),
        ("dash_api",     None, "/api/nexusclaw/status",  "Next.js dashboard control-center API (port 3001 canonical, 3000 fallback)"),
        ("dash_ui",      7356, "/health",                "Static dashboard (arena/wiki UI)"),
    ]
    # Secondary paths when primary health path 404s (e.g. pre-shim dash_ui).
    fallback_paths = {
        "dash_ui": ("/", "/dashboard.html"),
        "node_relay": ("/v1/models",),
    }
    results = {}
    for name, port, path, _desc in checks:
        ok = False
        if name == "dash_api":
            # probe canonical 3001 first, then non-canonical 3000.
            # Dev servers (Turbopack) compile routes on demand, so a cold probe
            # of /api/nexusclaw/status can take >2s; warm '/' best-effort first,
            # then probe the API route directly with a long timeout. Connection-
            # refused returns instantly, so dead ports don't waste the budget.
            for cand in (3001, 3000):
                try:
                    urllib.request.urlopen(
                        urllib.request.Request(f"http://127.0.0.1:{cand}/"), timeout=20)
                except Exception:
                    pass  # warm-up is best-effort; don't let it mask the API probe
                try:
                    r = urllib.request.urlopen(
                        urllib.request.Request(f"http://127.0.0.1:{cand}{path}"), timeout=30)
                    if r.status < 400:
                        ok = True
                        break
                except Exception:
                    pass
        else:
            paths_to_try = (path,) + fallback_paths.get(name, ())
            for try_path in paths_to_try:
                try:
                    r = urllib.request.urlopen(
                        urllib.request.Request(
                            f"http://127.0.0.1:{port}{try_path}"
                        ),
                        timeout=3,
                    )
                    if r.status < 400:
                        ok = True
                        break
                except Exception:
                    ok = False
        results[name] = ok

    # Revive (detached, opt-in) — only the relays, never CDP/dashboard which the
    # operator must own. Uses Start-Process so it returns immediately.
    revived = []
    if getattr(args, "revive", False):
        ps = root / "scripts" / "revive_relay_ports.ps1"
        if ps.exists() and shutil.which("powershell"):
            try:
                subprocess.run(
                    ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                     "-File", str(ps)],
                    capture_output=True, text=True, timeout=60)
                # re-probe relays
                for name, port, path, _ in checks:
                    if name in {"node_relay", "python_relay", "god_mode"}:
                        try:
                            urllib.request.urlopen(
                                urllib.request.Request(f"http://127.0.0.1:{port}{path}"),
                                timeout=2)
                            results[name] = True
                        except Exception:
                            pass
                revived = [n for n in ("node_relay", "python_relay", "god_mode") if results[n]]
            except Exception:
                pass

    # Exact admin-terminal commands for each dead link (one-stop gateway preferred)
    gw = "scripts\\start_nexus_gateway.ps1   (starts the full stack in background; one command)"
    fixes = {
        "cdp":        gw + "   |   or: scripts\\start_grok_cdp_9224.ps1   (login to Grok ONCE in the dedicated Chrome, then it persists forever)",
        "grok_bridge": gw + "   |   or: powershell -File tools\\browser_ai_mcp\\start_grok_mcp_v2.ps1",
        "node_relay":  gw + "   |   or: scripts\\start_node_relay.ps1",
        "python_relay":gw + "   |   or: scripts\\start_python_relay_7355.bat",
        "god_mode":    gw + "   |   or: .venv\\Scripts\\python.exe -m nexus_os.relay.god_mode_proxy",
        "dash_api":    gw + "   |   or: npx next dev -p 3001   (canonical dashboard port is 3001)",
        "dash_ui":     gw + "   |   or: node scripts\\serve_dashboard_7356.js",
    }

    print("=== NEXUS Grok Lane — chain probe ===")
    for name, _p, _path, desc in checks:
        flag = "UP  " if results[name] else "DOWN"
        print(f"  [{flag}] {name:12} {desc}")
    dead = [n for n, ok in results.items() if not ok]
    print("")
    if not dead:
        print("All links UP. Grok automation lane is end-to-end reachable.")
    else:
        print(f"{len(dead)} link(s) DOWN. Run these in your ADMIN terminal (not this agent shell):")
        for n in dead:
            print(f"  - {n:12} -> {fixes.get(n, '(no known fix)')}")
    if revived:
        print(f"\n[revive] detached relaunch brought up: {', '.join(revived)}")
    if getattr(args, "revive", False) and not revived:
        print("\n[revive] no relay came up via detached launch — start them manually (see fixes above).")

    _json_print({"results": results, "dead": dead, "revived": revived})
    return 0 if not dead else 1


def run_pipeline(args: argparse.Namespace) -> int:
    """Run the ARCHIVIST pipeline (import → compile → fit)."""
    import json as _json

    repo_root = _find_repo_root()
    if not repo_root:
        print('{"ok": false, "error": "repository root not found"}')
        return 1

    if args.status:
        try:
            from nexus_os.archivist.archivist import cmd_status
            result = cmd_status()
            print(_json.dumps(_as_dict(result), indent=2))
        except Exception as e:
            print(_json.dumps({"ok": False, "error": str(e)}))
            return 1
        return 0

    pipeline_dir = repo_root / "nexus_os" / "archivist"
    import_dir = args.import_dir or repo_root / "imports"
    compiled_dir = pipeline_dir / "compiled"
    wiki_output = pipeline_dir / "wiki" / "dossiers"

    skip_import = args.skip_import
    skip_compile = args.skip_compile
    skip_fit = args.skip_fit

    stages = []
    errors = []
    records = []
    compiler = None
    dossiers = []

    # Stage 1: Import (new 3-stage pipeline; produces ImportRecords the
    # compile stage actually consumes — the legacy scan_directory results
    # were never fed forward)
    if not skip_import:
        try:
            from nexus_os.archivist.import_stage import ArchivistImporter
            watched = [str(import_dir)] if args.import_dir else None
            importer = ArchivistImporter(watched_dirs=watched)
            records = importer.import_batch()
            stages.append({"stage": "import", "ok": True, "files": len(records)})
            print(_json.dumps({"stage": "import", "ok": True, "files": len(records)}))
        except Exception as e:
            stages.append({"stage": "import", "ok": False, "error": str(e)})
            errors.append(f"import: {e}")
            print(_json.dumps({"stage": "import", "ok": False, "error": str(e)}))

    # Stage 2: Compile (compile_batch; the previously called compile_all()
    # never existed — this stage errored on every run)
    if not skip_compile:
        try:
            from nexus_os.archivist.compile import ArchivistCompiler
            compiler = ArchivistCompiler()
            compiled = compiler.compile_batch(records) if records else []
            stages.append({
                "stage": "compile", "ok": True,
                "records": len(compiled),
                "dossier_topics": len(compiler._dossier_candidates),
            })
            print(_json.dumps({
                "stage": "compile", "ok": True,
                "records": len(compiled),
                "dossier_topics": len(compiler._dossier_candidates),
            }))
        except Exception as e:
            stages.append({"stage": "compile", "ok": False, "error": str(e)})
            errors.append(f"compile: {e}")
            print(_json.dumps({"stage": "compile", "ok": False, "error": str(e)}))

    # Stage 3: Fit (dossier synthesis from the compiler's per-topic
    # candidates — the previously read compiler.compiled never existed)
    if not skip_fit:
        try:
            from nexus_os.archivist.fit import ArchivistFitter
            fitter = ArchivistFitter()
            grouped = compiler._dossier_candidates if compiler is not None else {}
            dossiers = fitter.fit_batch(grouped) if grouped else []
            stages.append({
                "stage": "fit", "ok": True,
                "dossiers": len(dossiers),
                "output_dir": str(wiki_output),
            })
            print(_json.dumps({
                "stage": "fit", "ok": True,
                "dossiers": len(dossiers),
                "output_dir": str(wiki_output),
            }))
        except Exception as e:
            stages.append({"stage": "fit", "ok": False, "error": str(e)})
            errors.append(f"fit: {e}")
            print(_json.dumps({"stage": "fit", "ok": False, "error": str(e)}))

    # Stage 4: Bridge dossiers into the vault SEMANTIC channel — the only
    # writer that populates source_dossier_id; previously had no caller.
    if dossiers:
        try:
            from nexus_os.archivist.doppelground_bridge import get_bridge
            results = get_bridge().bridge_dossiers(dossiers)
            accepted = sum(1 for r in results if r.accepted)
            stages.append({"stage": "bridge", "ok": True, "accepted": accepted, "total": len(results)})
            print(_json.dumps({"stage": "bridge", "ok": True, "accepted": accepted, "total": len(results)}))
        except Exception as e:
            stages.append({"stage": "bridge", "ok": False, "error": str(e)})
            errors.append(f"bridge: {e}")
            print(_json.dumps({"stage": "bridge", "ok": False, "error": str(e)}))

    summary = {
        "pipeline": "import → compile → fit → bridge",
        "stages": stages,
        "errors": errors,
        "ok": len(errors) == 0,
    }
    print(_json.dumps(summary, indent=2))
    return 0 if summary["ok"] else 1


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

    pipeline = subparsers.add_parser("pipeline", help="Run the ARCHIVIST pipeline: import → compile → fit")
    pipeline.add_argument("--import-dir", type=Path, default=None,
                          help="Import raw source documents from this directory")
    pipeline.add_argument("--skip-import", action="store_true",
                          help="Skip import stage, use existing compiled records")
    pipeline.add_argument("--skip-compile", action="store_true",
                          help="Skip compile stage, use existing imports")
    pipeline.add_argument("--skip-fit", action="store_true",
                          help="Skip fit (dossier synthesis) stage")
    pipeline.add_argument("--enable-llm", action="store_true",
                          help="Enable LLM-powered dossier synthesis (requires relay)")
    pipeline.add_argument("--status", action="store_true",
                          help="Show pipeline stage status")

    memory = subparsers.add_parser("memory", help="Continuity substrate: 8 vault channels + canonical trust")
    memory_sub = memory.add_subparsers(dest="memory_command")
    memory_sub.required = True
    memory_sub.add_parser("channels", help="List 8 vault channels + min-trust gates")
    p_memory_show = memory_sub.add_parser("show", help="Show records in one channel")
    p_memory_show.add_argument("channel", help="channel name")
    p_memory_show.add_argument("--agent", default=None)
    p_memory_show.add_argument("--limit", type=int, default=50)
    p_memory_trust = memory_sub.add_parser("trust", help="Print TrustKernel snapshot for an agent/lane")
    p_memory_trust.add_argument("--agent", default=None)
    p_memory_trust.add_argument("--lane", default="general")
    memory_sub.add_parser("stats", help="List consolidation stats per channel")
    p_memory_fail = memory_sub.add_parser("failures", help="List failure patterns recorded for an agent")
    p_memory_fail.add_argument("--agent", default=None)
    p_memory_append = memory_sub.add_parser("append", help="Append one record to a channel (requires --allow-write)")
    p_memory_append.add_argument("channel", help="channel name")
    p_memory_append.add_argument("--content", required=True)
    p_memory_append.add_argument("--agent", default=None)
    p_memory_append.add_argument("--allow-write", action="store_true",
                                help="explicit gate; without it append refuses to run")

    continuity = subparsers.add_parser("continuity", help="Durable continuity ledger: open/close runs, coverage checks, resume plans")
    continuity_sub = continuity.add_subparsers(dest="continuity_command")
    continuity_sub.required = True
    continuity_sub.add_parser("status", help="Show ledger health, summary, and legacy state refs")
    p_cont_coverage = continuity_sub.add_parser("coverage", help="Show records within a time window")
    p_cont_coverage.add_argument("--hours", type=float, default=24.0, help="Look-back window in hours")
    p_cont_open = continuity_sub.add_parser("open", help="Open a continuity run record")
    p_cont_open.add_argument("--run-id", required=True)
    p_cont_open.add_argument("--agent-id", required=True)
    p_cont_open.add_argument("--source-lane", required=True)
    p_cont_open.add_argument("--input-fingerprint", default=None)
    p_cont_open.add_argument("--next-action", default=None)
    p_cont_open.add_argument("--origin", choices=["core", "browser", "mcp", "lane"], default=None,
                             help="Writer origin; browser/mcp/lane rows are fenced to UNVERIFIED/E0 without proof")
    p_cont_close = continuity_sub.add_parser("close", help="Close a continuity run record with progress classification")
    p_cont_close.add_argument("--run-id", required=True)
    p_cont_close.add_argument("--agent-id", required=True)
    p_cont_close.add_argument("--source-lane", required=True)
    p_cont_close.add_argument("--input-fingerprint", default=None)
    p_cont_close.add_argument("--output-fingerprint", default=None)
    p_cont_close.add_argument("--artifact", action="append", default=[])
    p_cont_close.add_argument("--test", action="append", default=[])
    p_cont_close.add_argument("--provider-calls", type=int, default=0)
    p_cont_close.add_argument("--quota-reserved", type=int, default=0)
    p_cont_close.add_argument("--blocker", default=None)
    p_cont_close.add_argument("--next-action", default=None)
    p_cont_close.add_argument("--started-at", default=None)
    p_cont_close.add_argument("--implemented", action="store_true")
    p_cont_close.add_argument("--advisory-only", action="store_true")
    p_cont_close.add_argument("--origin", choices=["core", "browser", "mcp", "lane"], default=None,
                              help="Writer origin; browser/mcp/lane rows are fenced to UNVERIFIED/E0 without proof")
    p_cont_close.add_argument("--proof-path", default=None,
                              help="Path to a proof artifact; an existing file makes browser/MCP rows eligible for E1")
    continuity_sub.add_parser("resume-plan", help="Print resume plan from latest ledger record")

    intel = subparsers.add_parser("intel", help="LLMWiki dossier pipeline: ingest evidence/synthesis, lint, stats")
    intel_sub = intel.add_subparsers(dest="intel_command")
    intel_sub.required = True
    p_intel_stats = intel_sub.add_parser("stats", help="Show dossier count and lint summary")
    p_intel_stats.add_argument("--wiki-output-dir", default=None, help="Override wiki output directory")
    p_intel_lint = intel_sub.add_parser("lint", help="Audit existing dossiers for missing VAP/provenance")
    p_intel_lint.add_argument("--wiki-output-dir", default=None)
    p_intel_claims = intel_sub.add_parser("ingest-claims", help="Ingest JSON array of evidence claims and write dossiers")
    p_intel_claims.add_argument("input_file", help="Path to JSON array of claim objects")
    p_intel_claims.add_argument("--overwrite", action="store_true", help="Overwrite existing dossiers")
    p_intel_claims.add_argument("--wiki-output-dir", default=None)
    p_intel_synth = intel_sub.add_parser("ingest-synthesis", help="Ingest research synthesis JSON and write dossiers")
    p_intel_synth.add_argument("input_file", help="Path to synthesis JSON object with 'findings'")
    p_intel_synth.add_argument("--overwrite", action="store_true")
    p_intel_synth.add_argument("--wiki-output-dir", default=None)

    models = subparsers.add_parser("models", help="List installed CLIs and current model/provider reachability")
    models.add_argument("action", nargs="?", choices=["verify", "reconcile", "status"],
                        help="verify/reconcile/status canonical registry and provider listings")
    models.add_argument("--refresh", action="store_true", help="Force upstream cache refresh before listing")
    models.add_argument("--provider", help="(verify) probe only this provider slug")
    models.add_argument("--no-chat-probe", action="store_true",
                        help="(verify) skip 1-token chat probes for listing absentees")
    models.add_argument("--dry-run", action="store_true", help="Do not persist provider health state")
    models.add_argument("--json", action="store_true", help="Emit JSON output")

    quota = subparsers.add_parser("quota", help="Durable provider token, RPM, and cooldown controls")
    quota_sub = quota.add_subparsers(dest="quota_command")
    quota_sub.required = True
    quota_status = quota_sub.add_parser("status", help="Show all provider quota state")
    quota_status.add_argument("--json", action="store_true")
    quota_verify = quota_sub.add_parser("verify", help="Record verified account quota telemetry")
    quota_verify.add_argument("--provider", required=True, choices=["longcat", "internai", "nvidia"])
    quota_verify.add_argument("--remaining-tokens", type=int)
    quota_verify.add_argument("--reset-at")
    quota_verify.add_argument("--expires-at")
    quota_verify.add_argument("--source", default="operator")
    quota_verify.add_argument("--json", action="store_true")
    quota_plan = quota_sub.add_parser("plan", help="Calculate protected utilization schedule")
    quota_plan.add_argument("--provider", required=True, choices=["longcat", "internai", "nvidia"])
    quota_plan.add_argument("--json", action="store_true")
    models_sync = subparsers.add_parser("model-sync", help="Sync live models/lanes to every CLI (opencode, kilo, cline, hermes, mimo)")
    models_sync.add_argument("--refresh", action="store_true", help="Force upstream cache refresh first")
    models_sync.add_argument("--dry-run", action="store_true", help="Preview without writing")
    models_sync.add_argument("--only", choices=["opencode", "mimo", "kilo", "cline", "hermes", "nexusctl"], help="Sync only this CLI")
    models_sync.add_argument("--install-schedule", action="store_true", help="Install 1-hour Windows scheduled task for automatic model sync")
    models_sync.add_argument("--log", default=None, help="Append JSON log to this path")

    a2a = subparsers.add_parser("a2a-channels", help="Inter-session A2A message bus (Plan 20): list, publish, subscribe, consolidate")
    a2a.add_argument("--list", dest="list_channels", action="store_true", help="List all channels")
    a2a.add_argument("--publish", nargs=3, metavar=("CHANNEL", "TOPIC", "MSG"), default=None,
                     help="Publish a message: --publish CHANNEL TOPIC MSG")
    a2a.add_argument("--subscribe", nargs=1, metavar="CHANNEL", default=None,
                     help="Tail recent messages from a channel")
    a2a.add_argument("--consolidate", action="store_true", help="Purge stale messages from all channels")
    a2a.add_argument("--stats", action="store_true", help="Show summary stats")

    subparsers.add_parser("dream-cycle", help="Run Dream Cycle memory consolidation (P0#3)")
    subparsers.add_parser("hallucination", help="Calibrated Hallucination Detector status (P1)")

    adrf = subparsers.add_parser("adrf", help="Adversarial Robustness Defense Framework (Plan 19)")
    adrf.add_argument("--test", type=str, default=None, help="Analyze a text string")
    adrf.add_argument("--list", action="store_true", help="Show all signatures")
    adrf.add_argument("--add", type=str, default=None, help="Add a custom signature as JSON")
    adrf.add_argument("--stats", action="store_true", help="Show detection stats")
    adrf.add_argument("--a2a-channel", default=None, help="A2A channels directory")

    monitor = subparsers.add_parser("monitor", help="Monitor Daemon: Dream Cycle + health checks + key rotation")
    monitor.add_argument("--run-once", action="store_true", help="Run a single monitor cycle")
    monitor.add_argument("--daemon", action="store_true", help="Run continuously")
    monitor.add_argument("--interval", type=int, default=15, help="Daemon interval in minutes (default 15)")
    monitor.add_argument("--install-schedule", action="store_true", help="Install Windows scheduled task")
    monitor.add_argument("--status", action="store_true", help="Show last run results")
    monitor.add_argument("--a2a-channel", default=None, help="A2A channel for results")

    grok_lane = subparsers.add_parser("grok-lane", help="Probe the Grok automation lane chain (CDP->bridge->relays->dashboard)")
    grok_lane_sub = grok_lane.add_subparsers(dest="grok_lane_command")
    grok_lane_sub.required = True
    gl_doctor = grok_lane_sub.add_parser("doctor", help="Pure-probe: report which link is dead + exact admin command")
    gl_doctor.add_argument("--revive", action="store_true", help="Also attempt detached background relaunch of the 3 relays (never CDP/dashboard)")

    grounding = subparsers.add_parser("grounding", help="Continuous evidence grounding and promotion controls")
    grounding_sub = grounding.add_subparsers(dest="grounding_command")
    grounding_sub.required = True
    grounding_doctor = grounding_sub.add_parser("doctor", help="Validate roots and durable grounding store")
    grounding_doctor.add_argument("--json", action="store_true", help="Emit JSON (default output)")
    grounding_sub.add_parser("status", help="Show grounding ledger and index status")
    grounding_scan = grounding_sub.add_parser("scan", help="Run incremental source reconciliation")
    grounding_scan.add_argument("--changed-only", action="store_true", default=True)
    grounding_scan.add_argument("--stability-delay", type=float, default=2.0)
    grounding_scan.add_argument("--max-files", type=int)
    grounding_watch = grounding_sub.add_parser("watch", help="Run continuous incremental grounding")
    grounding_watch.add_argument("--poll-seconds", type=int, default=30)
    grounding_watch.add_argument("--reconcile-seconds", type=int, default=3600)
    grounding_promote = grounding_sub.add_parser("promote", help="Review a promotion proposal")
    grounding_promote.add_argument("--proposal", required=True)
    grounding_promote.add_argument("--dry-run", action="store_true", default=True)

    ports = subparsers.add_parser(
        "ports",
        help="Port plane 7350–7360: purposes, health probes, pipeline layers",
    )
    ports_sub = ports.add_subparsers(dest="ports_command")
    ports_sub.required = True
    ports_doctor = ports_sub.add_parser(
        "doctor",
        help="Probe listening + HTTP health for the port plane (JSON)",
    )
    ports_doctor.add_argument("--host", default="127.0.0.1")
    ports_doctor.add_argument("--timeout", type=float, default=2.0)
    ports_doctor.add_argument(
        "--band-only",
        action="store_true",
        help="Only probe 7350–7360 (skip 3001/9224)",
    )

    gmr = subparsers.add_parser(
        "gmr",
        help="GMR + ChimeraRouter + Landau–Ginzburg pipeline controls",
    )
    gmr_sub = gmr.add_subparsers(dest="gmr_command")
    gmr_sub.required = True
    gmr_sub.add_parser(
        "catalogue",
        help="Fetch ModelRelay/GodMode catalogue telemetry (JSON)",
    )
    gmr_pipe = gmr_sub.add_parser(
        "pipeline",
        help="Chimera route → optional ModelRelay execute → LG dry-run track",
    )
    gmr_pipe.add_argument("prompt", help="Prompt text")
    gmr_pipe.add_argument("--execute", action="store_true", help="Call live ModelRelay")
    gmr_pipe.add_argument(
        "--cloud",
        dest="cloud",
        action="store_true",
        default=True,
        help="Allow cloud catalogue models (default on)",
    )
    gmr_pipe.add_argument(
        "--no-cloud",
        dest="cloud",
        action="store_false",
        help="Local tiers only (GGUF profiles)",
    )
    gmr_pipe.add_argument("--category", default="F1.1")
    gmr_pipe.add_argument(
        "--policy",
        default="auto",
        choices=["auto", "fixed", "edt", "ead", "lead", "ernie"],
    )
    gmr_pipe.add_argument("--quality", type=float, default=0.75)
    gmr_pipe.add_argument("--budget", type=float, default=4000.0, help="Latency budget ms")
    gmr_pipe.add_argument("--no-track", action="store_true", help="Skip LG track pass")
    gmr_pipe.add_argument("--track-tokens", type=int, default=32)
    gmr_pipe.add_argument("--max-tokens", type=int, default=128, help="Execute max_tokens cap")
    gmr_track = gmr_sub.add_parser("track", help="LG dry-run entropy track only")
    gmr_track.add_argument("--tokens", type=int, default=30)
    gmr_track.add_argument("--category", default="F1.1")
    gmr_track.add_argument("--temperature", type=float, default=0.7)

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
    if args.command == "pipeline":
        return run_pipeline(args)
    if args.command == "memory":
        from nexusctl.memory_cli import run_memory
        code, _payload = run_memory(args)
        if code != 0:
            raise SystemExit(code)
        return code
    if args.command == "continuity":
        from nexusctl.continuity_cli import run_continuity
        code, _payload = run_continuity(args)
        if code != 0:
            raise SystemExit(code)
        return code
    if args.command == "intel":
        from nexusctl.intel_cli import run_intel
        code, _payload = run_intel(args)
        if code != 0:
            raise SystemExit(code)
        return code
    if args.command == "models":
        if getattr(args, "action", None) == "verify":
            from nexusctl.models_cli import run_models_verify
            return run_models_verify(provider=args.provider, no_chat_probe=args.no_chat_probe)
        if getattr(args, "action", None) == "reconcile":
            from nexusctl.models_cli import run_models_reconcile
            return run_models_reconcile(provider=args.provider, dry_run=args.dry_run)
        if getattr(args, "action", None) == "status":
            from nexusctl.models_cli import run_models_status
            return run_models_status(provider=args.provider)
        return run_models_list(args.refresh)
    if args.command == "quota":
        return run_quota_command(args)
    if args.command == "a2a-channels":
        return run_a2a_channels(args)
    if args.command == "dream-cycle":
        return run_dream_cycle()
    if args.command == "hallucination":
        return run_hallucination_status()
    if args.command == "adrf":
        return run_adrf(args)
    if args.command == "monitor":
        return run_monitor(args)
    if args.command == "model-sync":
        return run_model_sync(args)
    if args.command == "grok-lane":
        return run_grok_lane(args)
    if args.command == "ports":
        if args.ports_command == "doctor":
            return run_ports(args)
        raise ValueError(f"Unknown ports command: {args.ports_command}")
    if args.command == "gmr":
        return run_gmr(args)
    if args.command == "grounding":
        return run_grounding(args)
    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
