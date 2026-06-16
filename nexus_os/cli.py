"""NEXUS OS — Command-line interface.

Usage:
    python -m nexus_os.cli [command]

Commands:
    bridge          Start the A2A Bridge server (default)
    mcp             Start the MCP stdio server
    cron            Run one agent cycle (test, backup, rotate)
    patrol          Run foreman patrol check
    health          Quick system health check
    version         Print version info
"""

import sys
import argparse
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("nexus_os.cli")


def main():
    # Initialize all system components at startup
    from nexus_os.boot import initialize_system
    initialize_system()

    parser = argparse.ArgumentParser(
        description="NEXUS OS — Sovereign Agent Operating System",
    )
    parser.add_argument(
        "command",
        nargs="?" if True else None,
        default="bridge",
        choices=["bridge", "mcp", "cron", "patrol", "health", "version"],
        help="Command to execute (default: bridge)",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Bridge server host (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Bridge server port (default: 8000)",
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Project root directory (default: current dir)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger("nexus_os").setLevel(logging.DEBUG)

    commands = {
        "bridge": _cmd_bridge,
        "mcp": _cmd_mcp,
        "cron": _cmd_cron,
        "patrol": _cmd_patrol,
        "health": _cmd_health,
        "version": _cmd_version,
    }

    commands[args.command](args)


def _cmd_bridge(args):
    from nexus_os.bridge.server import create_app
    import uvicorn

    app = create_app()
    logger.info(
        "Starting Nexus OS Bridge server on http://%s:%d",
        args.host, args.port,
    )
    uvicorn.run(app, host=args.host, port=args.port)


def _cmd_mcp(args):
    from nexus_os.mcp.server import serve_stdio

    logger.info("Starting Nexus OS MCP stdio server")
    serve_stdio()


def _cmd_cron(args):
    from nexus_os.cron.agent_cycle import AgentCycleRunner
    from pathlib import Path

    runner = AgentCycleRunner(project_root=Path(args.root).resolve())
    result = runner.run_cycle()
    if result.tests_passed:
        logger.info(
            "Cycle %d: PASSED (%d tests, %.1fs)",
            result.cycle_number, result.test_count, result.test_duration_s,
        )
    else:
        logger.error(
            "Cycle %d: FAILED (%s)",
            result.cycle_number, result.error,
        )
        sys.exit(1)


def _cmd_patrol(args):
    from nexus_os.team.coordinator import TeamCoordinator

    coordinator = TeamCoordinator(project_root=args.root)
    report = coordinator.run_foreman_patrol()
    stalled = len(report["stalled_tasks"])
    balanced = report["load_balanced"]
    logger.info("Patrol complete: stalled=%d balanced=%s", stalled, balanced)
    print(f"Stalled tasks: {stalled}")
    print(f"Load balanced: {balanced}")
    print(f"Pending counts: {report['pending_counts']}")
    if report["recommendations"]:
        print("Recommendations:")
        for rec in report["recommendations"]:
            print(f"  - {rec}")


def _cmd_health(args):
    """Quick health check of core modules."""
    results = {}
    for module_name, import_path, import_name in [
        ("engine.router", "nexus_os.engine.router", "TaskRouter"),
        ("governor.base", "nexus_os.governor.base", "NexusGovernor"),
        ("vault.manager", "nexus_os.vault.manager", "VaultManager"),
        ("bridge.server", "nexus_os.bridge.server", "BridgeServer"),
        ("monitoring.token_guard", "nexus_os.monitoring.token_guard", "TokenGuard"),
        ("mcp.server", "nexus_os.mcp.server", "GovernedMCPServer"),
        ("team.coordinator", "nexus_os.team.coordinator", "TeamCoordinator"),
    ]:
        try:
            mod = __import__(import_path, fromlist=[import_name])
            getattr(mod, import_name)
            results[module_name] = "ok"
        except Exception as e:
            results[module_name] = f"FAIL: {e}"

    print("NEXUS OS Health Check")
    print("=" * 50)
    all_ok = True
    for module, status in results.items():
        flag = "PASS" if status == "ok" else "FAIL"
        print(f"  [{flag}] {module}: {status}")
        if status != "ok":
            all_ok = False
    print("=" * 50)
    print(f"Overall: {'ALL OK' if all_ok else 'SOME FAILURES'}")
    return 0 if all_ok else 1


def _cmd_version(args):
    from nexus_os import __version__
    print(f"NEXUS OS version {__version__}")


if __name__ == "__main__":
    sys.exit(main())
