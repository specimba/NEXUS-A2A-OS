"""NEXUS OS — Main entry point.

Usage:
    python -m nexus_os                     Start Bridge server (default)
    python -m nexus_os bridge              Start Bridge server
    python -m nexus_os mcp                 Start MCP stdio server
    python -m nexus_os cron                Run one agent cycle
    python -m nexus_os patrol              Run foreman patrol
"""

import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("nexus_os")


def main():
    # Initialize all system components at startup
    from nexus_os.boot import initialize_system
    initialize_system()

    args = sys.argv[1:] if len(sys.argv) > 1 else []

    mode = "bridge"
    if args:
        mode = args[0].lower()

    if mode == "bridge":
        _start_bridge()
    elif mode == "mcp":
        _start_mcp()
    elif mode == "cron":
        _run_cron()
    elif mode == "patrol":
        _run_patrol()
    else:
        print(f"Unknown mode: {mode}")
        print("Usage: python -m nexus_os [bridge|mcp|cron|patrol]")
        sys.exit(1)


def _start_bridge():
    from nexus_os.bridge.server import create_app
    import uvicorn

    app = create_app()
    logger.info("Starting Nexus OS Bridge server on http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)


def _start_mcp():
    from nexus_os.mcp.server import serve_stdio

    logger.info("Starting Nexus OS MCP stdio server")
    serve_stdio()


def _run_cron():
    from nexus_os.cron.agent_cycle import AgentCycleRunner
    from pathlib import Path

    runner = AgentCycleRunner(project_root=Path.cwd())
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


def _run_patrol():
    from nexus_os.team.coordinator import TeamCoordinator

    coordinator = TeamCoordinator(project_root=".")
    report = coordinator.run_foreman_patrol()
    stalled = len(report["stalled_tasks"])
    balanced = report["load_balanced"]
    logger.info("Patrol complete: stalled=%d balanced=%s", stalled, balanced)


if __name__ == "__main__":
    main()
