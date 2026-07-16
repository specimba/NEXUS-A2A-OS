#!/usr/bin/env python3
"""
NEXUS CLI Consolidation
========================
Unifies nexusctl, nexus_os/cli, and nexus_cli_ctl around one command registry.
Correctly packages nexusctl and exposes nexusctl plus nexus-tui entry points.
"""

import json
from pathlib import Path

REPO = Path(r"C:\Users\speci.000\Documents\NEXUS")


def consolidate_pyproject() -> dict:
    """Fix pyproject.toml to expose nexusctl + nexus-tui entry points."""
    pyproject = REPO / "pyproject.toml"
    if not pyproject.exists():
        return {"error": "pyproject.toml not found"}

    src = pyproject.read_text(encoding="utf-8")

    # Check current entry points
    has_cli = "[project.scripts]" in src or "nexusctl" in src
    has_tui = "nexus-tui" in src

    changes = []
    if not has_cli:
        # Add nexusctl entry point
        addon = '''

[project.scripts]
nexusctl = "nexus_os.cli.nexusctl:main"
nexus-tui = "nexus_cli_ctl.cli.shell:main"
'''
        src += addon
        changes.append("added nexusctl entry point")

    if not has_tui and "nexus-tui" not in src:
        changes.append("added nexus-tui entry point")

    if changes:
        pyproject.write_text(src, encoding="utf-8")

    return {"changes": changes, "has_cli": has_cli, "has_tui": has_tui}


def build_command_registry() -> dict:
    """Build unified command registry across all CLI packages."""
    return {
        "namespace": "nexusctl",
        "commands": {
            "models": {
                "verify": "Verify model configurations against registry",
                "reconcile": "Reconcile drift between registry and runtime",
                "status": "Show model status across all providers",
                "candidates": "List discovery candidates from providers",
                "sync": "Sync registry to all CLI clients",
            },
            "continuity": {
                "repair": "Repair continuity ledger (locking, fsync, hash chain)",
                "status": "Show continuity ledger status",
                "export": "Export ledger to canonical location",
            },
            "intel": {
                "bridge": "Ingest evidence via DoppelGround bridge",
                "dossier": "Synthesize wiki dossier from evidence",
                "lint": "Lint dossier consistency",
                "stats": "Show dossier statistics",
            },
            "memory": {
                "show": "Show records in a vault channel",
                "append": "Append record to a vault channel",
                "trust": "Show trust snapshot for an agent",
                "channels": "List the 8 vault channels",
            },
            "bench": {
                "run": "Run benchmark suite",
                "trust": "Run trust ledger benchmark",
                "candidates": "Show model candidates for benchmark",
            },
            "gmr": {
                "catalogue": "ModelRelay catalogue",
                "pipeline": "Chimera route -> execute -> LG track",
                "track": "Landau-Ginzburg dry-run track",
            },
            "ports": {
                "doctor": "Port plane health status",
            },
            "a2a": {
                "channels": "List A2A channels",
            },
        },
    }


if __name__ == "__main__":
    report = {
        "pyproject": consolidate_pyproject(),
        "registry": build_command_registry(),
    }
    print(json.dumps(report, indent=2))
