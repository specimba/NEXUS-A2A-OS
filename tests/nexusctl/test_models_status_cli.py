from __future__ import annotations

import json
import sys

from nexusctl.cli import main


def test_models_status_committed_suspended_overrides_stale_runtime(capsys, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["nexusctl", "models", "status", "--provider", "nvidia", "--json"])

    assert main() == 0
    payload = json.loads(capsys.readouterr().out)
    by_id = {model["id"]: model for model in payload["models"]}

    assert by_id["z-ai/glm-5.1"]["status"] == "suspended"
    assert by_id["z-ai/glm-5.1"]["runtime_status"] == "suspended"


def test_status_checks_canonical_engine_router_export(capsys):
    from nexusctl import cli

    assert cli.run_status() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    assert payload["health"]["engine.router"] == "ok"


def test_legacy_health_checks_canonical_engine_router_export(capsys):
    import importlib.util
    from pathlib import Path

    cli_path = Path(__file__).parents[2] / "nexus_os" / "cli.py"
    spec = importlib.util.spec_from_file_location("nexus_os_legacy_cli", cli_path)
    assert spec is not None and spec.loader is not None
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)

    assert cli._cmd_health(None) == 0
    output = capsys.readouterr().out
    assert "[PASS] engine.router: ok" in output
    assert "Overall: ALL OK" in output

