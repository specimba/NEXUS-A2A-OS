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
