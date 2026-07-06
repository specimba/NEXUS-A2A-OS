"""
nexusctl - NEXUS OS Command-Line Interface
Canonical CLI for system operations, health checks, and integrations.
"""
import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))


def cmd_status(args):
    from nexus_os.monitoring.provider_health import get_health_monitor
    health = get_health_monitor()
    status = health.get_status()
    summary = status.get("summary", {})
    print(f"Providers tracked: {summary.get('total_tracked', 0)}")
    print(f"  Healthy:   {summary.get('healthy', 0)}")
    print(f"  Degraded:  {summary.get('degraded', 0)}")
    print(f"  Failing:   {summary.get('failing', 0)}")
    print(f"  Offline:   {summary.get('offline', 0)}")
    # FI-D4: discovery candidates are never a silent log entry
    candidates = _load_model_candidates()
    if candidates:
        high = sum(1 for c in candidates if c["priority"] == "high")
        oldest = max((c["age_days"] or 0) for c in candidates)
        print(f"Model candidates: {len(candidates)} awaiting review "
              f"({high} high-priority, oldest {oldest}d) — `nexusctl models candidates`")


def cmd_doctor(args):
    print("NEXUS Doctor Check")
    print("=" * 40)
    checks = {
        "Python": sys.version.split()[0],
        "Project Root": str(ROOT),
    }
    try:
        from nexus_os.monitoring.provider_health import get_health_monitor
        health = get_health_monitor()
        summary = health.get_status().get("summary", {})
        checks["Provider Health"] = f"{summary.get('healthy', 0)} healthy / {summary.get('total_tracked', 0)} total"
    except Exception as e:
        checks["Provider Health"] = f"ERROR: {e}"

    try:
        from nexus_os.bridge.port_registry import PortRegistry
        pr = PortRegistry()
        pr.register(7352, "brain_api", force=True)
        pr.register(7353, "twave", force=True)
        pr.register(7350, "modelrelay_npm", force=True)
        pr.register(7355, "modelrelay_python", force=True)
        health_check = pr.health_check()
        checks["Port Registry"] = health_check.get("status", "unknown")
    except Exception as e:
        checks["Port Registry"] = f"ERROR: {e}"

    try:
        from nexus_cli_ctl.integrations.wiki_pipeline import get_wiki_pipeline
        wiki = get_wiki_pipeline()
        wiki._build_index()
        checks["Wiki Pipeline"] = f"{wiki._page_count} pages indexed"
    except Exception as e:
        checks["Wiki Pipeline"] = f"ERROR: {e}"

    if getattr(args, "mcp_gateway", False):
        try:
            from nexus_os.security.mcp_gateway import MCPGateway
            gw = MCPGateway()
            stats = gw.get_stats()
            cb = gw.get_circuit_breaker_status()
            dead = cb.get("dead_providers", {})
            checks["MCP Gateway"] = (
                f"{stats['total_requests']} reqs, "
                f"{stats['allowed']} allowed, "
                f"{stats['blocked']} blocked"
            )
            if dead:
                checks["MCP Gateway Circuit Breaker"] = (
                    f"{len(dead)} providers in cooldown"
                )
        except Exception as e:
            checks["MCP Gateway"] = f"ERROR: {e}"

    try:
        from nexus_cli_ctl.integrations.messaging.messaging_integration import get_messaging_integration
        msg = get_messaging_integration()
        status = msg.get_status()
        enabled = status.get("enabled_platforms", [])
        checks["Messaging"] = f"Platforms: {', '.join(enabled) or 'none configured'}"
    except Exception as e:
        checks["Messaging"] = f"ERROR: {e}"

    all_ok = True
    for name, result in checks.items():
        status_icon = "OK" if "ERROR" not in str(result) and result != "unknown" else "FAIL"
        if status_icon == "FAIL":
            all_ok = False
        print(f"  [{status_icon}] {name}: {result}")

    print("=" * 40)
    print(f"Overall: {'ALL CHECKS PASSED' if all_ok else 'SOME CHECKS FAILED'}")
    return 0 if all_ok else 1


def _probe_http_endpoint(url: str, timeout: float = 2.0):
    """Read-only HTTP probe for local NEXUS service ownership checks."""
    import urllib.error
    import urllib.request

    request = urllib.request.Request(url, headers={"Accept": "application/json,text/html;q=0.8,*/*;q=0.1"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read(512)
            return {
                "url": url,
                "ok": 200 <= response.status < 300,
                "status_code": response.status,
                "content_type": response.headers.get("content-type", ""),
                "preview": body.decode("utf-8", errors="replace")[:160],
                "error": None,
            }
    except urllib.error.HTTPError as exc:
        body = exc.read(512)
        return {
            "url": url,
            "ok": False,
            "status_code": exc.code,
            "content_type": exc.headers.get("content-type", ""),
            "preview": body.decode("utf-8", errors="replace")[:160],
            "error": f"HTTP {exc.code}",
        }
    except Exception as exc:
        return {
            "url": url,
            "ok": False,
            "status_code": None,
            "content_type": "",
            "preview": "",
            "error": str(exc),
        }


def _classify_brain_api_probe(probe):
    preview = str(probe.get("preview") or "").lstrip()
    content_type = str(probe.get("content_type") or "").lower()
    if not probe.get("ok"):
        return "offline_or_wrong_service"
    if "html" in content_type or preview.lower().startswith("<!doctype") or "<html" in preview.lower():
        return "wrong_service_html"
    if "json" in content_type or preview.startswith("{"):
        return "brain_api_candidate"
    return "unknown_non_json"


def cmd_dashboard(args):
    """Read-only dashboard and Brain API runtime ownership checks."""
    if not args.doctor:
        print("Usage: nexusctl dashboard --doctor [--json]")
        return 2

    brain_base = args.brain_api_url.rstrip("/")
    dashboard_url = args.dashboard_url
    brain_probe = _probe_http_endpoint(f"{brain_base}/health", timeout=args.timeout)
    dashboard_probe = _probe_http_endpoint(dashboard_url, timeout=args.timeout)
    brain_class = _classify_brain_api_probe(brain_probe)
    status = "ok" if brain_class == "brain_api_candidate" and dashboard_probe.get("ok") else "degraded"
    result = {
        "status": status,
        "expected_ports": {
            "7350": "modelrelay_npm",
            "7352": "brain_api",
            "7355": "modelrelay_python",
            "7356": "static_dashboard",
            "3001": "next_dashboard",
        },
        "checks": {
            "brain_api": {
                "expected_owner": "brain_api",
                "url": f"{brain_base}/health",
                "classification": brain_class,
                "probe": brain_probe,
            },
            "static_dashboard": {
                "expected_owner": "static_dashboard",
                "url": dashboard_url,
                "classification": "reachable" if dashboard_probe.get("ok") else "unreachable",
                "probe": dashboard_probe,
            },
        },
        "next_action": "relocate_or_stop_wrong_7352_process_then_start_brain_api" if brain_class != "brain_api_candidate" else "verify_dashboard_contracts",
        "read_only": True,
    }

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("NEXUS Dashboard Doctor")
        print("=" * 40)
        print(f"Brain API: {brain_class} ({brain_probe.get('status_code')}) {brain_probe.get('url')}")
        print(f"Static dashboard: {'reachable' if dashboard_probe.get('ok') else 'unreachable'} ({dashboard_probe.get('status_code')}) {dashboard_url}")
        print(f"Overall: {status.upper()}")
        print(f"Next action: {result['next_action']}")
    return 0 if status == "ok" else 1

def cmd_hygiene(args):
    """Run read-only disk hygiene inventory."""
    from nexus_os.monitoring.disk_hygiene import (
        build_hygiene_report,
        default_targets,
        visible_roots_for_drives,
    )

    paths = [Path(path) for path in args.path] if args.path else default_targets()
    previous_report = None
    if args.baseline:
        with Path(args.baseline).open("r", encoding="utf-8") as fh:
            previous_report = json.load(fh)

    visible_roots = visible_roots_for_drives(args.drive) if args.visible_root_scan else None
    report = build_hygiene_report(
        paths=paths,
        min_file_mib=args.min_file_mib,
        top_file_limit=args.top_files,
        include_system_files=not args.no_system_files,
        include_drive_accounting=not args.no_drive_accounting,
        drives=args.drive or None,
        visible_roots=visible_roots,
        previous_report=previous_report,
        hidden_gap_threshold_gib=args.hidden_gap_threshold_gib,
        free_delta_threshold_gib=args.free_delta_threshold_gib,
    )

    if args.json:
        print(json.dumps(report, indent=2))
        return 0

    print("NEXUS Disk Hygiene Check")
    print("=" * 40)
    print("Mode: read-only; no deletes, moves, or process stops")
    print("")
    if report["drive_accounting"]:
        print("Drive accounting:")
        for row in report["drive_accounting"]:
            visible = "n/a" if row["visible_gib"] is None else f"{row['visible_gib']:.3f} GiB visible"
            hidden = "n/a" if row["hidden_gap_gib"] is None else f"{row['hidden_gap_gib']:.3f} GiB hidden-gap"
            print(
                f"  {row['drive']:<4} used={row['used_gib']:.3f} GiB "
                f"free={row['free_gib']:.3f} GiB  {visible}  {hidden}"
            )
        print("")
    if report["drive_findings"]:
        print("Drive findings:")
        for finding in report["drive_findings"]:
            print(
                f"  [{finding['severity']}] {finding['drive']} "
                f"{finding['type']} {finding.get('delta_gib')} GiB - {finding['message']}"
            )
        print("")
    print("Largest scanned paths:")
    for row in report["summaries"][: args.summary_limit]:
        print(
            f"  {row['size_gib']:>8.3f} GiB  {row['category']:<24} "
            f"{row['risk']:<16} {row['path']}"
        )
    print("")
    print("Largest files:")
    for row in report["top_files"][: args.top_files]:
        print(
            f"  {row['size_gib']:>8.3f} GiB  {row['category']:<24} "
            f"{row['risk']:<16} {row['path']}"
        )
    print("")
    print(
        "Reviewable candidates: "
        f"{report['candidate_summary']['reviewable_file_count']} files / "
        f"{report['candidate_summary']['reviewable_file_gib']} GiB"
    )
    readiness = report["cleanup_readiness"]
    print(
        "Cleanup readiness: "
        f"{readiness['estimated_confirmation_reclaim_gib']} GiB needs confirmation; "
        f"{readiness['protected_gib']} GiB protected/tool-managed"
    )
    if report["candidate_summary"]["admin_only_count"]:
        print("Admin-only items detected; use elevated Windows diagnostics before changing them.")
    if report["drive_findings"]:
        print("Protocol: diagnose hidden/system allocation before deleting visible files.")
    return 0


def cmd_cycle_check(args):
    print("NEXUS Cycle Check")
    try:
        from nexus_os.monitoring.provider_health import get_health_monitor
        health = get_health_monitor()
        status = health.get_status()
        total = status["summary"]["total_tracked"]
        failing = status["summary"]["failing"]
        if failing > 0:
            print(f"WARN: {failing}/{total} providers failing")
        else:
            print(f"OK: All {total} providers healthy")
    except Exception as e:
        print(f"Cycle check error: {e}")
        return 1
    return 0


def cmd_wiki(args):
    from nexus_cli_ctl.integrations.wiki_pipeline import WikiPipeline
    pipeline = WikiPipeline()

    if args.wiki_search:
        results = pipeline.search(args.wiki_search)
        if results:
            for r in results:
                print(f"  {r['slug']}: {r['title']} ({r['word_count']} words)")
        else:
            print("No results found")
    elif args.wiki_list:
        pipeline._build_index()
        for page in pipeline.list_pages():
            print(f"  {page['slug']}: {page['title']}")
    elif args.wiki_status:
        pipeline._build_index()
        status = pipeline.get_status()
        print(json.dumps(status, indent=2))
    elif args.wiki_sources:
        sources = pipeline.list_sources()
        print(json.dumps(sources, indent=2))
    elif args.wiki_refresh:
        result = pipeline.refresh()
        print(json.dumps(result, indent=2))
    else:
        print("Usage: nexusctl wiki [--search QUERY | --list | --status | --sources | --refresh]")


def cmd_messaging(args):
    from nexus_cli_ctl.integrations.messaging.messaging_integration import get_messaging_integration
    mi = get_messaging_integration()
    status = mi.get_status()
    print(json.dumps(status, indent=2))


def cmd_state(args):
    try:
        state_file = Path.home() / ".nexus_pi" / "state" / "unified_state.json"
        if state_file.exists():
            data = json.loads(state_file.read_text(encoding="utf-8"))
            if args.section:
                section_data = data.get(args.section)
                if section_data:
                    print(json.dumps(section_data, indent=2, default=str))
                else:
                    print(f"Section '{args.section}' not found")
            else:
                print(json.dumps(data, indent=2, default=str))
        else:
            print("No state file found")
    except Exception as e:
        print(f"State error: {e}")


def cmd_handoff(args):
    """Generate a cold-handoff package for agent transfers."""
    import shutil
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    handoff_dir = Path.home() / ".nexus_pi" / "state" / "handoff"
    handoff_dir.mkdir(parents=True, exist_ok=True)

    pkg_dir = handoff_dir / f"handoff_{timestamp}"
    pkg_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "timestamp": timestamp,
        "generator": "nexusctl handoff",
        "components": [],
    }

    state_file = Path.home() / ".nexus_pi" / "state" / "unified_state.json"
    if state_file.exists():
        shutil.copy2(state_file, pkg_dir / "unified_state.json")
        manifest["components"].append("unified_state")

    wiki_state = Path(ROOT) / "archivist" / "wiki_state.json"
    if wiki_state.exists():
        shutil.copy2(wiki_state, pkg_dir / "wiki_state.json")
        manifest["components"].append("wiki_state")

    pid_file = Path.home() / ".nexus_pi" / "state" / "master_daemon.pid"
    if pid_file.exists():
        manifest["daemon_pid"] = pid_file.read_text().strip()

    try:
        from nexus_os.monitoring.provider_health import get_health_monitor
        health = get_health_monitor()
        manifest["provider_health"] = health.get_status().get("summary", {})
        manifest["components"].append("provider_health")
    except Exception:
        pass

    try:
        from nexus_os.governor.trust_engine_v2 import get_trust_engine
        te = get_trust_engine()
        manifest["trust_engine"] = {"baseline": te.baseline, "max_score": te.max_score}
        manifest["components"].append("trust_engine_config")
    except Exception:
        pass

    project_state = Path(ROOT) / "01_PROJECT_STATE.md"
    if project_state.exists():
        shutil.copy2(project_state, pkg_dir / "01_PROJECT_STATE.md")
        manifest["components"].append("project_state")

    (pkg_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"Handoff package: {pkg_dir}")
    print(f"Components: {', '.join(manifest['components'])}")


def cmd_stress_lab(args):
    """Run safety stress tests (legacy system checks or adversarial StressLab)."""
    if args is None:
        return _run_legacy_stress()
    if args.scenario or args.team or getattr(args, 'red_team', False) or getattr(args, 'blue_team', False):
        return _run_adversarial_stress(args)
    return _run_legacy_stress()


def _run_adversarial_stress(args):
    from nexus_os.stress.stress_lab import (
        RedScenarioBank, BlueScenarioBank, PurpleScenarioBank,
        StressLab, compute_report, print_report, TeamMode,
    )

    class SimpleClient:
        def generate(self, q, **kw):
            from nexus_os.models.registry import ModelRegistry
            try:
                reg = ModelRegistry.load_default()
                model = reg.get_model(args.model) if args.model else None
                if model and hasattr(model, "generate"):
                    return model.generate(q)
            except Exception:
                pass
            return "[No model connected - run with --model to test against a real registry model]"

    if args.team == "purple" or (args.red_team and args.blue_team):
        team = TeamMode.PURPLE
        scenarios = PurpleScenarioBank.build_combined(args.count)
    elif args.team == "blue" or args.blue_team:
        team = TeamMode.BLUE
        if args.scenario == "over-refusal":
            scenarios = BlueScenarioBank.build_over_refusal()
        else:
            scenarios = BlueScenarioBank.build_restore(args.count)
    else:
        team = TeamMode.RED
        if args.scenario == "injection":
            scenarios = RedScenarioBank.build_injection(args.count)
        elif args.scenario == "escalation":
            scenarios = RedScenarioBank.build_escalation()
        else:
            topic = args.topic or "dangerous content"
            scenarios = RedScenarioBank.build(topic, args.count)

    lab = StressLab(SimpleClient())
    results = lab.run(scenarios, quiet=args.quiet)
    report = compute_report(team, results)

    if args.json:
        import json as j
        print(j.dumps({
            "scenario_count": report.scenario_count,
            "guard_rate": report.guard_rate,
            "bypass_rate": report.bypass_rate,
            "over_refusal_rate": report.over_refusal_rate,
            "per_type": report.per_type,
        }, indent=2))
    else:
        print_report(report)

    return 1 if report.bypass_rate > 0.5 else 0


def _run_legacy_stress():
    import logging
    logging.disable(logging.CRITICAL)
    print("NEXUS Safety Stress Tests")
    print("=" * 40)

    results = []
    try:
        from nexus_os.governor.trust_engine_v2 import get_trust_engine, DangerLevel
        te = get_trust_engine()
        result = te.update_trust("stress-test-agent", "governance", success=False, danger=DangerLevel.CRITICAL)
        score = te.get_trust("stress-test-agent")
        results.append(("TrustEngine CRITICAL penalty", "PASS" if result.new_score < te.baseline else "FAIL"))
        te.reset_agent("stress-test-agent")
    except Exception as e:
        results.append(("TrustEngine CRITICAL penalty", f"SKIP: {e}"))

    try:
        from nexus_os.api.brain_api import SimpleRateLimiter
        limiter = SimpleRateLimiter(max_requests=3, window_seconds=10)
        for _ in range(3):
            limiter.is_allowed("stress_test")
        blocked = not limiter.is_allowed("stress_test")
        results.append(("Rate limiter enforcement", "PASS" if blocked else "FAIL"))
    except Exception as e:
        results.append(("Rate limiter enforcement", f"ERROR: {e}"))

    try:
        from nexus_os.governor.misalignment_detector import get_detector, RiskLevel
        md = get_detector()
        events = md.analyze_command("sudo rm -rf / --no-preserve-root", agent_id="stress-test")
        has_high = any(e.risk_level.value >= RiskLevel.HIGH.value for e in events)
        results.append(("Misalignment detection (sudo rm)", "PASS" if has_high else "FAIL"))
        md.reset_profile("stress-test")
    except Exception as e:
        results.append(("Misalignment detection", f"ERROR: {e}"))

    try:
        from nexus_os.governor.intent_classifier import IntentClassifier
        ic = IntentClassifier()
        result = ic.classify("I want to synthesize a dangerous biological weapon agent for mass harm")
        results.append(("Intent classifier (harmful)", "PASS" if result.action.value not in ("ALLOW",) else "FAIL"))
    except Exception as e:
        results.append(("Intent classifier", f"ERROR: {e}"))

    passed = sum(1 for _, s in results if s == "PASS")
    skipped = sum(1 for _, s in results if s.startswith("SKIP"))
    failed = sum(1 for _, s in results if s == "FAIL")
    total = len(results)
    for name, status in results:
        print(f"  [{status}] {name}")

    print("=" * 40)
    print(f"Results: {passed}/{total} passed, {skipped} skipped, {failed} failed")
    return 0 if failed == 0 else 1


def cmd_eval(args):
    """Run evaluations (VibeThinker, NEXUS-Bench, etc)."""
    if args.vibethinker or args.backend:
        return _run_vibethinker_eval(args)
    print("Usage: nexusctl eval --vibethinker [--model NAME] [--backend relay|ollama|hf] [--count N]")
    return 2


def _run_vibethinker_eval(args):
    from nexus_os.eval.vibethinker_eval import (
        build_task_bank, compute_report, EvalReport, verify_answer, print_report as print_eval,
    )

    print(f"VibeThinker Eval — model={args.model}, backend={args.backend}")
    print("=" * 50)

    tasks = build_task_bank(seed=args.seed, include_refusal=args.include_refusal)
    if args.count and args.count < len(tasks):
        tasks = tasks[:args.count]

    results = []
    for task in tasks:
        response = _eval_prompt(task.query, model=args.model, backend=args.backend)
        correct, refused = verify_answer(task, response)
        from nexus_os.eval.vibethinker_eval import TaskResult
        import time
        import time
        results.append(TaskResult(
            task_id=task.id, category=task.category.value, difficulty=task.difficulty,
            query=task.query, expected_answer=task.expected_answer,
            model_answer=response, correct=correct, latency_ms=0.0,
            refused=refused, over_refused=False,
            timestamp=datetime.now().isoformat(),
        ))

    report = compute_report(args.model, args.backend, results)

    if args.json:
        print(json.dumps({
            "total": report.total_tasks,
            "correct": report.correct,
            "accuracy": report.accuracy,
            "refusal_rate": report.refusal_rate,
            "per_category": report.per_category,
        }, indent=2))
    else:
        print_eval(report)

    return 0


def _eval_prompt(query, model="WeiboAI/VibeThinker-3B", backend="relay"):
    if backend == "relay":
        return _eval_via_relay(query, model)
    elif backend == "ollama":
        return _eval_via_ollama(query, model)
    else:
        return _eval_via_hf(query, model)


def _eval_via_relay(query, model):
    try:
        from nexus_os.api.brain_api import _ModelRelayProxy
        import asyncio
        proxy = _ModelRelayProxy()
        payload = {"model": model, "messages": [{"role": "user", "content": query}]}
        result = asyncio.run(proxy.chat_completions(payload))
        if result and "choices" in result:
            return result["choices"][0].get("message", {}).get("content", str(result))
        return str(result)
    except Exception as e:
        return f"[Relay error: {e}]"


def _eval_via_ollama(query, model):
    try:
        import requests
        resp = requests.post("http://127.0.0.1:11434/api/generate",
                            json={"model": model, "prompt": query, "stream": False}, timeout=60)
        data = resp.json()
        return data.get("response", str(data))
    except Exception as e:
        return f"[Ollama error: {e}]"


def _eval_via_hf(query, model):
    return f"[HF eval not available in CLI; use backend=relay or ollama]"


def cmd_gross_http(args):
    """Prepare or run a governed browser HTTP diagnostic through GROSS."""
    from nexus_os.bridge.browser_http_diagnostic import BrowserHTTPDiagnosticRelay

    relay = BrowserHTTPDiagnosticRelay(bridge_url=args.bridge_url)
    if args.live:
        result = relay.invoke(
            args.url,
            method=args.method,
            audit_id=args.audit_id,
            scenario=args.scenario,
            operator=args.operator,
            safe_preview_max=args.safe_preview_max,
        )
    else:
        decision = relay.prepare(
            args.url,
            method=args.method,
            audit_id=args.audit_id,
            scenario=args.scenario,
            operator=args.operator,
            safe_preview_max=args.safe_preview_max,
        )
        result = {
            "allowed": decision.allowed,
            "reason": decision.reason,
            "gross_tool": "http_diagnostic",
            "gross_arguments": decision.gross_arguments,
            "mode": "dry_run",
        }
    print(json.dumps(result, indent=2))
    return 0 if not result.get("blocked") and result.get("allowed", True) else 2


def cmd_model_lab(args):
    """Read-only model lab inventory and behavior-control proposal commands."""
    if args.inventory:
        from nexus_os.models.registry import ModelRegistry

        registry = ModelRegistry.load_default()
        behavior_models = registry.list_behavior_control_models()
        result = {
            "mode": "inventory",
            "behavior_control_count": len(behavior_models),
            "behavior_control_models": [model.to_dict() for model in behavior_models],
            "stats": registry.get_stats(),
            "dry_run": True,
        }
        print(json.dumps(result, indent=2))
        return 0

    if args.verify_manifest:
        manifest_path = Path(args.verify_manifest)
        if not manifest_path.exists():
            print(json.dumps({"valid": False, "reason": "manifest not found"}, indent=2))
            return 2
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        required = {"artifact_hash", "method_class", "model_path", "before_refusal_score", "after_refusal_score", "capability_retention_score", "vap_record_id"}
        missing = sorted(required - set(manifest))
        print(json.dumps({"valid": not missing, "missing": missing, "dry_run": True}, indent=2))
        return 0 if not missing else 2

    if args.propose:
        from nexus_os.security.behaviormancer_nexus import (
            NexusBehaviorMancer,
            NexusBehaviorMancerConfig,
        )

        config = NexusBehaviorMancerConfig(
            model_path=args.propose,
            target_dataset_path=args.target_dataset or "",
            baseline_dataset_path=args.baseline_dataset or "",
            preservation_dataset_path=args.preservation_dataset or "",
            output_path=args.output_path or "",
            n_samples=args.n_samples,
            direction_multiplier=args.direction_multiplier,
            null_space_constraints=args.null_space_constraints,
            start_layer_ratio=args.start_layer_ratio,
            end_layer_ratio=args.end_layer_ratio,
        )
        proposal = NexusBehaviorMancer(config).prepare_proposal(method_class=args.method_class)
        print(json.dumps(proposal.to_dict(), indent=2))
        return 0

    print("Usage: nexusctl model-lab [--inventory | --propose MODEL | --verify-manifest PATH]")
    return 2


def _load_model_candidates():
    """Discovery candidates from ~/.nexus/registry_health.json (FI-D1)."""
    import time as _time
    from pathlib import Path as _Path

    sidecar = _Path.home() / ".nexus" / "registry_health.json"
    try:
        health = json.loads(sidecar.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    rows = []
    now = _time.time()
    for slug, prov in (health.get("providers") or {}).items():
        for mid, cand in (prov.get("candidates") or {}).items():
            rows.append({
                "provider": slug,
                "model_id": mid,
                "priority": cand.get("priority", "normal"),
                "reason": cand.get("reason", ""),
                "first_seen": cand.get("first_seen"),
                "age_days": round((now - cand["first_seen"]) / 86400.0, 1)
                if cand.get("first_seen") else None,
                "baseline": bool(cand.get("baseline")),
            })
    rows.sort(key=lambda r: (r["priority"] != "high", r["first_seen"] or 0))
    return rows


def cmd_models_candidates(args):
    """`nexusctl models candidates` — new models seen live but unregistered."""
    rows = _load_model_candidates()
    if getattr(args, "json", False):
        print(json.dumps(rows, indent=2))
        return 0
    if not rows:
        print("No discovery candidates recorded. Run `nexusctl models verify` "
              "(provider_refresher) to probe providers.")
        return 0
    print(f"{'PROVIDER':<15} {'MODEL':<45} {'PRIORITY':<9} {'AGE':<7} REASON")
    for r in rows:
        age = f"{r['age_days']}d" if r["age_days"] is not None else "?"
        flag = " [baseline]" if r["baseline"] else ""
        print(f"{r['provider']:<15} {r['model_id']:<45} {r['priority']:<9} "
              f"{age:<7} {r['reason']}{flag}")
    high = sum(1 for r in rows if r["priority"] == "high")
    print(f"-- {len(rows)} candidate(s), {high} high-priority "
          "(unknown vendor prefix = possible stealth release)")
    return 0


def cmd_models_list(args):
    """`nexusctl models` — list installed CLIs and current reachability."""
    if getattr(args, "action", None) == "candidates":
        return cmd_models_candidates(args)
    from nexusctl.model_sync import fetch_live_state, list_cli_inventory

    state = fetch_live_state(refresh=getattr(args, "refresh", False))
    if not state["god_proxy_alive"] and not state["node_relay_alive"]:
        print("WARNING: Neither God Mode Proxy (7357) nor Node ModelRelay (7350) is reachable.")
        print("Start them:")
        print("  scripts\\start_node_relay.ps1")
        print("  python -m nexus_os.relay.god_mode_proxy")
    payload = list_cli_inventory(state)
    print(json.dumps(payload, indent=2))
    return 0 if (state.get("god_proxy_alive") or state.get("node_relay_alive")) else 2


def cmd_model_sync(args):
    """`nexusctl model-sync` — sync models + lanes to all CLIs."""
    from nexusctl import model_sync

    argv: list[str] = []
    if getattr(args, "refresh", False):
        argv.append("--refresh")
    if getattr(args, "dry_run", False):
        argv.append("--dry-run")
    if getattr(args, "only", None):
        argv.extend(["--only", args.only])
    if getattr(args, "install_schedule", False):
        argv.append("--install-schedule")
    if getattr(args, "log", None):
        argv.extend(["--log", args.log])
    return model_sync.main(argv if argv else None)


def cmd_a2a_channels(args):
    """`nexusctl a2a-channels` — Inter-session A2A message bus (Plan 20).

    List, publish, subscribe, or consolidate typed channels under
    ~/.nexus/a2a_channels/.
    """
    from nexus_os.bridge.a2a_channels import A2AChannelBus

    bus = A2AChannelBus()

    if getattr(args, "list_channels", False):
        channels = bus.discover()
        print(json.dumps(channels, indent=2))
        return 0

    if getattr(args, "publish", None):
        channel_id, topic, msg = args.publish
        result = bus.publish(channel_id=channel_id, sender="nexusctl", message=msg, topic=topic)
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        return 0

    if getattr(args, "subscribe", None):
        channel_id = args.subscribe[0]
        messages = bus.subscribe(channel_id, max_messages=50)
        print(json.dumps([m.to_dict() for m in messages], indent=2, ensure_ascii=False))
        return 0

    if getattr(args, "consolidate", False):
        result = bus.consolidate()
        print(json.dumps(result, indent=2))
        return 0

    if getattr(args, "stats", False):
        stats = bus.get_stats()
        print(json.dumps(stats, indent=2))
        return 0

    print("Usage: nexusctl a2a-channels [--list | --publish CHAN TOPIC MSG | --subscribe CHAN | --consolidate | --stats]")
    return 2


def cmd_dream_cycle(args):
    """`nexusctl dream-cycle` — run memory consolidation (Dream Cycle, P0#3).

    Consolidates EPISODIC → SEMANTIC memory, deduplicates, prunes stale
    entries, and emits cross-session learning patterns to A2A channels.
    """
    from nexus_os.vault.dream_cycle import DreamCycle

    dc = DreamCycle(a2a_channel=getattr(args, "a2a_channel", None))

    if getattr(args, "daemon", False):
        dc.run_daemon(interval_minutes=getattr(args, "interval", 30))
        return 0

    if getattr(args, "status", False):
        stats = dc.get_stats()
        print(json.dumps(stats, indent=2))
        return 0

    result = dc.consolidate()
    print(json.dumps(result, indent=2))
    return 0


def cmd_adrf(args):
    """`nexusctl adrf` — Adversarial Robustness Defense Framework (Plan 19).

    Detects prompt injection, jailbreaks, prompt leaks, role overrides,
    encoded payloads, MCP exploits, and rate bypass attempts via
    signature-based scanning.
    """
    from nexus_os.security.adrf import ADRFDetector, AdversarialSignature, AttackType

    detector = ADRFDetector(a2a_channel=getattr(args, "a2a_channel", None))

    if getattr(args, "list", False):
        sigs = [sig.to_dict() for sig in detector._signatures]
        print(json.dumps({"signatures": sigs, "count": len(sigs)}, indent=2))
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
            print(json.dumps({"added": sig.to_dict()}, indent=2))
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            print(json.dumps({"error": str(exc)}, indent=2))
            return 1
        return 0

    if getattr(args, "stats", False):
        print(json.dumps(detector.get_stats(), indent=2))
        return 0

    if getattr(args, "test", None):
        result = detector.analyze(args.test)
        print(json.dumps(result.to_dict(), indent=2))
        return 0

    print("Usage: nexusctl adrf [--test TEXT | --list | --add JSON | --stats]")
    return 2


def cmd_hallucination(args):
    """`nexusctl hallucination` — Calibrated Hallucination Detector (P1).

    Wraps LG tracker's EPR detector with adaptive threshold calibration,
    cross-session learning, and self-correction signaling.
    """
    from nexus_os.monitoring.calibrated_hallucination_detector import CalibratedHallucinationDetector

    chd = CalibratedHallucinationDetector(
        a2a_channel=getattr(args, "a2a_channel", None),
        bebop_weight=getattr(args, "bebop_weight", 0.15),
        bebop_tau=getattr(args, "bebop_tau", 0.40),
    )

    if getattr(args, "status", False):
        print(json.dumps({
            "stats": chd.get_stats(),
            "history": chd.get_calibration_history()[-10:],
        }, indent=2))
        return 0

    if getattr(args, "feedback", None) is not None:
        chd.record_feedback(args.feedback)
        threshold = chd._get_effective_threshold()
        print(json.dumps({"feedback_recorded": args.feedback, "calibrated_threshold": threshold}, indent=2))
        return 0

    if getattr(args, "assess", None) is not None:
        probs = [float(x) for x in args.assess.split(",")] if args.assess else None
        result = chd.assess(topk_probs=probs)
        print(json.dumps(result, indent=2))
        return 0

    print("Usage: nexusctl hallucination [--status | --assess PROBS | --feedback BOOL]")
    return 2


def cmd_rotate_keys(args):
    """`nexusctl rotate-keys` — test provider keys, circuit breaker, propagate to all CLIs."""
    from nexusctl import rotate_keys

    if getattr(args, "install_schedule", False):
        result = rotate_keys.install_hourly_schedule()
        print(__import__("json").dumps(result, indent=2, ensure_ascii=False))
        return 0 if result.get("installed") else 1

    if getattr(args, "health_check", False):
        result = rotate_keys.cmd_health_check()
        print(__import__("json").dumps(result, indent=2, ensure_ascii=False))
        return 0

    if getattr(args, "circuit_breaker", False):
        result = rotate_keys.cmd_circuit_breaker()
        print(__import__("json").dumps(result, indent=2, ensure_ascii=False))
        return 0

    if getattr(args, "test_model", None):
        provider_id, model, key = args.test_model
        result = rotate_keys.test_openai_model(provider_id, key, model)
        print(__import__("json").dumps(result, indent=2, ensure_ascii=False))
        return 0

    key_id = None
    key_value = None
    if getattr(args, "key", None):
        key_id = args.key[0]
        key_value = args.key[1]

    result = rotate_keys.cmd_rotate(key_id=key_id, key_value=key_value, dry_run=getattr(args, "dry_run", False))
    print(__import__("json").dumps(result, indent=2, ensure_ascii=False))
    return 0


def cmd_monitor(args):
    """`nexusctl monitor` — run the Monitor Daemon (Dream Cycle + health + key rotation)."""
    from nexus_os.monitor_daemon import MonitorDaemon, install_monitor_schedule

    daemon = MonitorDaemon(
        interval_minutes=getattr(args, "interval", 15),
        a2a_channel=getattr(args, "a2a_channel", None),
    )

    if getattr(args, "install_schedule", False):
        result = install_monitor_schedule(interval_minutes=args.interval)
        print(json.dumps(result, indent=2))
        return 0

    if getattr(args, "status", False):
        status = daemon.get_status()
        print(json.dumps(status, indent=2, default=str))
        return 0

    if getattr(args, "daemon", False):
        daemon.run_daemon()
        return 0

    result = daemon.run_once()
    print(json.dumps(result, indent=2, default=str))
    return 0


def cmd_route(args):
    """`nexusctl route` — route a prompt through ChimeraRouter, optionally execute via ModelRelay.

    Decision-only mode (default):
        nexusctl route "Explain quantum entanglement step by step."

    Execute mode (calls the live relay):
        nexusctl route "Write a haiku about rust" --execute
        nexusctl route "Code a fibonacci function" --execute --relay-url http://127.0.0.1:7350
    """
    from nexus_os.twave.chimera_router_v2 import (
        ChimeraRouterV2,
        TemperaturePolicy,
        Tier,
    )

    policy_map = {
        "auto": TemperaturePolicy.AUTO,
        "fixed": TemperaturePolicy.FIXED,
        "edt": TemperaturePolicy.EDT,
        "ead": TemperaturePolicy.EAD,
        "lead": TemperaturePolicy.LEAD,
        "ernie": TemperaturePolicy.ERNIE,
    }
    policy = policy_map.get(args.policy, TemperaturePolicy.AUTO)

    router = ChimeraRouterV2(
        vram_gb=args.vram,
        has_cloud_access=args.cloud,
        available_tiers=[Tier.CONTROL_PLANE, Tier.LOCAL_STANDARD, Tier.LOCAL_POWER],
    )
    decision = router.route(
        args.prompt,
        latency_budget_ms=args.budget,
        quality_target=args.quality,
        category=args.category,
        temperature_policy=policy,
    )

    route_payload = {
        "tier": decision.tier.value,
        "model": decision.model,
        "temperature": round(decision.temperature, 3),
        "policy": decision.temperature_policy.value,
        "expected_latency_ms": round(decision.expected_latency_ms, 0),
        "expected_quality": round(decision.expected_quality, 2),
        "max_tokens": decision.budget.max_tokens,
        "features": {
            "edt": decision.use_edt,
            "lead": decision.use_lead,
            "epr": decision.use_epr,
            "led": decision.use_led,
            "ckplug": decision.use_ckplug,
            "attn_divergence": decision.use_attention_divergence,
        },
        "confidence": round(decision.confidence, 2),
        "reason": decision.reason,
    }
    print(json.dumps(route_payload, indent=2))

    if getattr(args, "execute", False):
        from nexus_os.relay.model_relay_adapter import ModelRelayAdapter, RelayRequest

        relay_url = args.relay_url or f"http://127.0.0.1:{os.environ.get('NODERELAY_PORT', '7350')}"
        fallback_url = args.fallback_url or f"http://127.0.0.1:{os.environ.get('PYTHONRELAY_PORT', '7355')}"
        godmode_url = args.godmode_url or f"http://127.0.0.1:{os.environ.get('GODMODE_PORT', '7357')}"

        adapter = ModelRelayAdapter(
            primary_url=relay_url,
            fallback_url=fallback_url,
            godmode_url=godmode_url,
        )
        req = RelayRequest(
            model=decision.model,
            prompt=args.prompt,
            temperature=decision.temperature,
            max_tokens=decision.budget.max_tokens,
            relay_url=relay_url,
            metadata={"category": args.category, "policy": decision.temperature_policy.value},
        )
        result = adapter.execute(req)
        exec_payload = {
            "status": result.status,
            "provider": result.provider,
            "used_fallback": result.used_fallback,
            "latency_ms": result.latency_ms,
            "attempts": result.attempts,
        }
        if result.raw:
            exec_payload["response_preview"] = result.raw[:500]
        print(json.dumps(exec_payload, indent=2))


def cmd_track(args):
    """`nexusctl track` — run TWAVE Landau-Ginzburg entropy tracker and report.

    Surfaces the entropy/hallucination/cooling telemetry that the tracker
    already computes internally but was not visible in the operator CLI.

    Dry-run mode (default) simulates entropy without a live model:
        nexusctl track --tokens 50 --category R2.2

    With real logits (requires a running model backend):
        nexusctl track --tokens 50 --no-dry-run
    """
    try:
        from nexus_os.twave.landau_ginzburg_tracker_v2 import LandauGinzburgTrackerV2
    except ImportError as exc:
        print(f"ERROR: LandauGinzburgTrackerV2 not importable: {exc}")
        return 1

    tracker = LandauGinzburgTrackerV2(
        category=args.category,
        enable_edt=args.edt,
        enable_lead=args.lead,
        enable_epr=args.epr,
        enable_led=args.led,
        enable_ckplug=args.ckplug,
    )
    tracker.set_dry_run(not args.no_dry_run)

    for i in range(args.tokens):
        tracker.step(
            position=i,
            current_temperature=args.temperature,
        )

    report = tracker.get_report()
    payload = {
        "category": report.category,
        "tokens_generated": report.tokens_generated,
        "hallucination_detected": report.hallucination_detected,
        "hallucination_positions": report.hallucination_positions,
        "self_correction_positions": report.self_correction_positions,
        "cooling_events": len(report.cooling_events),
        "mean_entropy": round(report.mean_entropy, 4),
        "max_entropy": round(report.max_entropy, 4),
        "entropy_variance": round(report.entropy_variance, 4),
        "final_temperature": round(report.final_temperature, 4),
        "estimated_healing_length": round(report.estimated_healing_length, 2) if report.estimated_healing_length else None,
        "epr_score": round(report.epr_score, 4) if report.epr_score else None,
        "mode_transitions": len(report.mode_transitions) if report.mode_transitions else 0,
        "led_depths": len(report.led_depth_selected) if report.led_depth_selected else 0,
        "edt_schedule_points": len(report.edt_temperature_schedule) if report.edt_temperature_schedule else 0,
    }
    print(json.dumps(payload, indent=2))
    return 0


# ── Reasoning Engine ───────────────────────────────────────────────────────


def cmd_reasoning(args):
    """FableReasoningEngine CLI — extract, analyze, and generate training data."""
    from nexus_os.reasoning.fable_engine import run_cli
    return run_cli(args)


def main():
    parser = argparse.ArgumentParser(
        prog="nexusctl",
        description="NEXUS OS Control CLI"
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # status
    sub = subparsers.add_parser("status", help="Show system status")
    sub.set_defaults(func=cmd_status)

    # doctor
    sub = subparsers.add_parser("doctor", help="Run system health check")
    sub.add_argument("--mcp-gateway", action="store_true", help="Show MCP Gateway pipeline status + circuit breaker state")
    sub.set_defaults(func=cmd_doctor)

    # dashboard
    sub = subparsers.add_parser("dashboard", help="Dashboard and Brain API diagnostics")
    sub.add_argument("--doctor", action="store_true", help="Run read-only dashboard runtime ownership check")
    sub.add_argument("--json", action="store_true", help="Emit JSON report")
    sub.add_argument("--brain-api-url", default="http://127.0.0.1:7352", help="Brain API base URL")
    sub.add_argument("--dashboard-url", default="http://127.0.0.1:7356/dashboard.html", help="Static dashboard URL")
    sub.add_argument("--timeout", type=float, default=2.0, help="Probe timeout seconds")
    sub.set_defaults(func=cmd_dashboard)

    # hygiene
    sub = subparsers.add_parser("hygiene", help="Read-only disk hygiene inventory")
    sub.add_argument("--path", action="append", default=[], help="Path to scan; repeatable")
    sub.add_argument("--json", action="store_true", help="Emit JSON report")
    sub.add_argument("--top-files", type=int, default=40, help="Number of large files to print")
    sub.add_argument("--summary-limit", type=int, default=20, help="Number of path summaries to print")
    sub.add_argument("--min-file-mib", type=int, default=100, help="Minimum file size for top-file list")
    sub.add_argument("--no-system-files", action="store_true", help="Skip pagefile/swapfile root file checks")
    sub.add_argument("--baseline", help="Previous hygiene JSON report for free-space delta detection")
    sub.add_argument("--drive", action="append", default=[], help="Drive label for accounting; repeatable, e.g. C: or D:")
    sub.add_argument("--no-drive-accounting", action="store_true", help="Skip drive free/used accounting")
    sub.add_argument(
        "--visible-root-scan",
        action="store_true",
        help="Slowly scan first-level drive roots to estimate visible-vs-hidden allocation gaps",
    )
    sub.add_argument(
        "--hidden-gap-threshold-gib",
        type=float,
        default=25.0,
        help="Hidden allocation gap threshold that triggers diagnose-first findings",
    )
    sub.add_argument(
        "--free-delta-threshold-gib",
        type=float,
        default=50.0,
        help="Free-space baseline delta threshold that triggers diagnose-first findings",
    )
    sub.set_defaults(func=cmd_hygiene)

    # cycle-check
    sub = subparsers.add_parser("cycle-check", help="Validate last work cycle")
    sub.set_defaults(func=cmd_cycle_check)

    # wiki
    sub = subparsers.add_parser("wiki", help="Wiki/DoppelGround operations")
    sub.add_argument("--search", dest="wiki_search", help="Search wiki")
    sub.add_argument("--list", dest="wiki_list", action="store_true", help="List pages")
    sub.add_argument("--status", dest="wiki_status", action="store_true", help="Wiki status")
    sub.add_argument("--sources", dest="wiki_sources", action="store_true", help="List sources")
    sub.add_argument("--refresh", dest="wiki_refresh", action="store_true", help="Refresh index")
    sub.set_defaults(func=cmd_wiki)

    # messaging
    sub = subparsers.add_parser("messaging", help="Messaging status")
    sub.set_defaults(func=cmd_messaging)

    # state
    sub = subparsers.add_parser("state", help="View unified state")
    sub.add_argument("--section", help="State section to view")
    sub.set_defaults(func=cmd_state)

    # handoff
    sub = subparsers.add_parser("handoff", help="Generate cold-handoff package for agent transfers")
    sub.set_defaults(func=cmd_handoff)

    # stress-lab
    sub = subparsers.add_parser("stress-lab", help="Run safety stress tests (legacy or adversarial)")
    sub.add_argument("--scenario", default="", choices=["jailbreak", "injection", "escalation", "over-refusal"],
                     help="Adversarial scenario type (empty = legacy safety checks)")
    sub.add_argument("--team", default="", choices=["red", "blue", "purple"],
                     help="Team mode for adversarial stress")
    sub.add_argument("--red-team", action="store_true", help="Shortcut for --team red")
    sub.add_argument("--blue-team", action="store_true", help="Shortcut for --team blue")
    sub.add_argument("--count", type=int, default=10, help="Number of scenarios")
    sub.add_argument("--topic", default="dangerous content", help="Red team topic query")
    sub.add_argument("--model", default="", help="Model name from registry")
    sub.add_argument("--quiet", action="store_true", help="Suppress per-scenario output")
    sub.add_argument("--json", action="store_true", help="Emit JSON report")
    sub.set_defaults(func=cmd_stress_lab)

    # gross-http
    sub = subparsers.add_parser(
        "gross-http",
        help="Prepare or run a governed GROSS bridge HTTP diagnostic",
    )
    sub.add_argument("url", help="HTTPS URL to diagnose")
    sub.add_argument("--method", default="GET", choices=["GET", "HEAD"], help="Read-only HTTP method")
    sub.add_argument("--bridge-url", default="http://127.0.0.1:7354", help="Local GROSS bridge URL")
    sub.add_argument("--safe-preview-max", type=int, default=500, help="Maximum safe preview bytes")
    sub.add_argument("--audit-id", default="", help="Audit correlation id")
    sub.add_argument("--scenario", default="browser_http_diagnostic", help="Audit scenario label")
    sub.add_argument("--operator", default="nexusctl", help="Operator label for audit")
    sub.add_argument("--live", action="store_true", help="Actually invoke the local bridge; default is dry-run only")
    sub.set_defaults(func=cmd_gross_http)

    # model-lab
    sub = subparsers.add_parser(
        "model-lab",
        help="Read-only model inventory and Behavior-Control Lab dry-run proposals",
    )
    sub.add_argument("--inventory", action="store_true", help="List behavior-control candidates from registry")
    sub.add_argument("--propose", metavar="MODEL", help="Create a dry-run behavior-control proposal for MODEL")
    sub.add_argument("--verify-manifest", metavar="PATH", help="Read and validate an existing behavior-control manifest")
    sub.add_argument("--method-class", default="refusal_vector_abliteration", help="Behavior-control method class")
    sub.add_argument("--target-dataset", default="", help="Target/desired-behavior dataset path")
    sub.add_argument("--baseline-dataset", default="", help="Baseline/refusal-behavior dataset path")
    sub.add_argument("--preservation-dataset", default="", help="Capability-preservation dataset path")
    sub.add_argument("--output-path", default="", help="Proposed output path; proposal only")
    sub.add_argument("--n-samples", type=int, default=30, help="Sample count for proposal metadata")
    sub.add_argument("--direction-multiplier", type=float, default=1.0, help="Proposed control-vector strength")
    sub.add_argument("--start-layer-ratio", type=float, default=0.2, help="Start layer ratio")
    sub.add_argument("--end-layer-ratio", type=float, default=0.9, help="End layer ratio")
    sub.add_argument("--null-space-constraints", action="store_true", help="Propose preservation null-space constraints")
    sub.set_defaults(func=cmd_model_lab)

    # eval
    sub = subparsers.add_parser("eval", help="Run evaluations (VibeThinker, NEXUS-Bench)")
    sub.add_argument("--vibethinker", action="store_true", help="Run VibeThinker eval")
    sub.add_argument("--model", default="WeiboAI/VibeThinker-3B", help="Model name or HuggingFace path")
    sub.add_argument("--backend", default="relay", choices=["relay", "ollama", "hf"], help="Eval backend")
    sub.add_argument("--count", type=int, default=0, help="Number of tasks (0 = all)")
    sub.add_argument("--seed", type=int, default=42, help="Random seed for task selection")
    sub.add_argument("--include-refusal", action="store_true", help="Include refusal probe tasks")
    sub.add_argument("--json", action="store_true", help="Emit JSON report")
    sub.set_defaults(func=cmd_eval)

    # monitor — Monitor Daemon
    sub = subparsers.add_parser(
        "monitor",
        help="Monitor Daemon: Dream Cycle consolidation, health checks, key rotation",
    )
    sub.add_argument("--run-once", action="store_true", help="Run a single monitor cycle")
    sub.add_argument("--daemon", action="store_true", help="Run continuously every --interval minutes")
    sub.add_argument("--interval", type=int, default=15, help="Daemon interval in minutes (default 15)")
    sub.add_argument("--install-schedule", action="store_true", help="Install Windows scheduled task")
    sub.add_argument("--status", action="store_true", help="Show last run results")
    sub.add_argument("--a2a-channel", default=None, help="A2A channel for emitting results")
    sub.set_defaults(func=cmd_monitor)

    # route — ChimeraRouter prompt routing + optional execution
    sub = subparsers.add_parser(
        "route",
        help="Route a prompt through ChimeraRouter (decision-only by default, --execute to call relay)",
    )
    sub.add_argument("prompt", help="Prompt text to route")
    sub.add_argument("--vram", type=float, default=8.0, help="Available VRAM in GB")
    sub.add_argument("--budget", type=float, default=2000.0, help="Latency budget in ms")
    sub.add_argument("--quality", type=float, default=0.75, help="Quality target (0-1)")
    sub.add_argument("--category", default="default", help="Prompt category for t_c config")
    sub.add_argument("--policy", default="auto", choices=["auto", "fixed", "edt", "ead", "lead", "ernie"])
    sub.add_argument("--cloud", action="store_true", default=False, help="Allow cloud-tier models")
    sub.add_argument("--execute", action="store_true", default=False, help="Execute the routing decision through ModelRelay")
    sub.add_argument("--relay-url", default=None, help="Primary relay URL (default: http://127.0.0.1:7350)")
    sub.add_argument("--fallback-url", default=None, help="Fallback relay URL (default: http://127.0.0.1:7355)")
    sub.add_argument("--godmode-url", default=None, help="God Mode Proxy URL (default: http://127.0.0.1:7357)")
    sub.set_defaults(func=cmd_route)

    # track — TWAVE Landau-Ginzburg entropy tracker
    sub = subparsers.add_parser(
        "track",
        help="Run TWAVE Landau-Ginzburg entropy tracker and report (dry-run by default)",
    )
    sub.add_argument("--tokens", type=int, default=30, help="Number of tokens to simulate")
    sub.add_argument("--category", default="F1.1", help="Tracker category (affects t_c and weights)")
    sub.add_argument("--temperature", type=float, default=0.7, help="Initial temperature")
    sub.add_argument("--no-dry-run", action="store_true", default=False, help="Disable dry-run (requires real logits)")
    sub.add_argument("--edt", action="store_true", default=True, help="Enable EDT (entropy-based dynamic temperature)")
    sub.add_argument("--lead", action="store_true", default=True, help="Enable LEAD (latent/discrete mode switching)")
    sub.add_argument("--epr", action="store_true", default=True, help="Enable EPR (entropy production rate)")
    sub.add_argument("--led", action="store_true", default=False, help="Enable LED (layer entropy exploration)")
    sub.add_argument("--ckplug", action="store_true", default=False, help="Enable CK-PLUG (retrieval chemical potential)")
    sub.set_defaults(func=cmd_track)

    # models — list installed CLIs and current reachability
    sub = subparsers.add_parser(
        "models",
        help="List installed CLIs (opencode, kilo, cline, hermes, mimo) and current model/provider reachability",
    )
    sub.add_argument("action", nargs="?", choices=["candidates"], default=None,
                     help="'candidates': show live-listed models missing from the registry (FI-D1 discovery)")
    sub.add_argument("--refresh", action="store_true", help="Force upstream God Mode Proxy + Node Relay cache refresh before reporting")
    sub.add_argument("--json", action="store_true", help="JSON output (candidates view)")
    sub.set_defaults(func=cmd_models_list)

    # rotate-keys — test + propagate provider keys to all CLIs
    sub = subparsers.add_parser(
        "rotate-keys",
        help="Test provider API keys, update circuit breaker, propagate to all CLIs",
    )
    sub.add_argument("--key", nargs=2, metavar=("PROVIDER", "VALUE"), default=None,
                     help="Set/update a specific provider key (e.g. --key baseten DDLL...)")
    sub.add_argument("--health-check", action="store_true", help="Ping all providers and show status (read-only)")
    sub.add_argument("--circuit-breaker", action="store_true", help="Show circuit breaker state")
    sub.add_argument("--install-schedule", action="store_true",
                     help="Install 1-hour Windows scheduled task for automatic key rotation")
    sub.add_argument("--dry-run", action="store_true", help="Preview without writing any file")
    sub.add_argument("--test-model", nargs=3, metavar=("PROVIDER", "MODEL", "KEY"),
                     help="Test a specific model: --test-model baseten zai-org/GLM-5.2 <KEY>")
    sub.set_defaults(func=cmd_rotate_keys)

    # model-sync — push live lanes/providers/models to every CLI
    sub = subparsers.add_parser(
        "model-sync",
        help="Sync NEXUS relay providers + auto-routing lanes to all supported CLIs (opencode, kilo, cline, hermes, mimo)",
    )
    sub.add_argument("--refresh", action="store_true", help="Force upstream cache refresh first")
    sub.add_argument("--dry-run", action="store_true", help="Preview without writing any file")
    sub.add_argument("--only", choices=["opencode", "mimo", "kilo", "cline", "hermes", "nexusctl"], default=None, help="Sync only this CLI")
    sub.add_argument("--install-schedule", action="store_true", help="Install/update the 1-hour Windows scheduled task for automatic model sync")
    sub.add_argument("--log", default=None, help="Append JSON log to this path")
    sub.set_defaults(func=cmd_model_sync)

    # a2a-channels — Plan 20 inter-session message bus
    sub = subparsers.add_parser(
        "a2a-channels",
        help="Inter-session A2A message bus (Plan 20): list, publish, subscribe, consolidate",
    )
    sub.add_argument("--list", dest="list_channels", action="store_true", help="List all channels")
    sub.add_argument("--publish", nargs=3, metavar=("CHANNEL", "TOPIC", "MSG"), default=None,
                     help="Publish a message: --publish CHANNEL TOPIC MSG")
    sub.add_argument("--subscribe", nargs=1, metavar="CHANNEL", default=None,
                     help="Tail recent messages from a channel")
    sub.add_argument("--consolidate", action="store_true", help="Purge stale messages from all channels")
    sub.add_argument("--stats", action="store_true", help="Show summary stats")
    sub.set_defaults(func=cmd_a2a_channels)

    # dream-cycle — P0 memory consolidation
    sub = subparsers.add_parser(
        "dream-cycle",
        help="Run Dream Cycle memory consolidation (EPISODIC->SEMANTIC, dedup, prune, A2A emit)",
    )
    sub.add_argument("--daemon", action="store_true", help="Run every N minutes")
    sub.add_argument("--interval", type=int, default=30, help="Daemon interval (minutes)")
    sub.add_argument("--status", action="store_true", help="Show Dream Cycle stats")
    sub.add_argument("--a2a-channel", default=None, help="A2A channels directory (Plan 20)")
    sub.set_defaults(func=cmd_dream_cycle)

    # adrf — Adversarial Robustness Defense Framework
    sub = subparsers.add_parser(
        "adrf",
        help="Adversarial Robustness Defense Framework (Plan 19): detect and defend against adversarial attacks",
    )
    sub.add_argument("--test", type=str, default=None, help="Analyze a text string for adversarial content")
    sub.add_argument("--list", action="store_true", help="Show all registered signatures")
    sub.add_argument("--add", type=str, default=None, help="Add a custom signature as JSON")
    sub.add_argument("--stats", action="store_true", help="Show detection stats")
    sub.add_argument("--a2a-channel", default=None, help="A2A channels directory (Plan 20)")
    sub.set_defaults(func=cmd_adrf)

    # hallucination — Calibrated Hallucination Detector
    sub = subparsers.add_parser(
        "hallucination",
        help="Calibrated Hallucination Detector with adaptive threshold + A2A learning",
    )
    sub.add_argument("--status", action="store_true", help="Show stats + calibration history")
    sub.add_argument("--assess", default=None, help="Comma-separated top-k probs to assess")
    sub.add_argument("--feedback", type=bool, default=None, help="Calibration feedback (True/False)")
    sub.add_argument("--a2a-channel", default=None, help="A2A channels directory (Plan 20)")
    sub.add_argument("--bebop-weight", type=float, default=0.15,
                     help="Weight for Bebop TV-distribution signal (0.0 disables; default 0.15)")
    sub.add_argument("--bebop-tau", type=float, default=0.40,
                     help="TV-distance threshold for Bebop (default 0.40)")
    sub.set_defaults(func=cmd_hallucination)

    # reasoning — FableReasoningEngine
    sub = subparsers.add_parser(
        "reasoning",
        help="FableReasoningEngine: extract CoT patterns, analyze trajectories, "
             "generate prompts, find similar patterns, produce training data",
    )
    sub.add_argument("action", choices=[
        "extract", "analyze", "prompt", "inject", "similar",
        "clusters", "train", "status",
    ], help="Reasoning action to perform")
    sub.add_argument("--limit", type=int, default=100, help="Pattern extraction limit")
    sub.add_argument("--task-type", default="debug", choices=[
        "debug", "feature", "refactor", "security", "analysis",
    ], help="Task type for prompt generation")
    sub.add_argument("--complexity", default="L2", choices=["L1", "L2", "L3", "L4"],
                     help="CogER complexity level")
    sub.add_argument("--query", default="", help="Query text for prompt injection or similarity search")
    sub.add_argument("--style", default="fable", choices=["fable", "nexus", "hybrid"],
                     help="Reasoning style for prompt generation")
    sub.add_argument("--base-prompt", default="", help="Base prompt text for injection")
    sub.add_argument("--k", type=int, default=5, help="Number of similar patterns to return")
    sub.add_argument("--n-clusters", type=int, default=10, help="Number of clusters")
    sub.add_argument("--output", default="", help="Output path for training data")
    sub.add_argument("--format", default="dpo", choices=["dpo", "cot", "openai"],
                     help="Training data format")
    sub.add_argument("--context", default="", help="Trajectory context for analyze action")
    sub.set_defaults(func=cmd_reasoning)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    if hasattr(args, "func"):
        result = args.func(args)
        sys.exit(result if isinstance(result, int) else 0)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
