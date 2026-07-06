"""`nexusctl models candidates` + status surface (FI-D4: never a silent log)."""
from __future__ import annotations

import json
import time

import pytest

from nexus_os.cli import nexusctl


@pytest.fixture()
def sidecar(tmp_path, monkeypatch):
    home = tmp_path
    (home / ".nexus").mkdir()
    monkeypatch.setattr(
        "pathlib.Path.home", classmethod(lambda cls: home)
    )
    path = home / ".nexus" / "registry_health.json"

    def write(payload):
        path.write_text(json.dumps(payload), encoding="utf-8")

    return write


def test_candidates_listing_sorted_high_first(sidecar, capsys):
    now = time.time()
    sidecar({
        "providers": {
            "nvidia": {"candidates": {
                "acme/normal-model": {"first_seen": now - 86400, "last_seen": now,
                                      "priority": "normal", "reason": "new-model",
                                      "emitted": True, "baseline": False},
            }},
            "openrouter": {"candidates": {
                "meituan/owl-alpha": {"first_seen": now - 3 * 86400, "last_seen": now,
                                      "priority": "high",
                                      "reason": "unknown-vendor-prefix",
                                      "emitted": True, "baseline": False},
            }},
        },
        "models": {},
    })
    rows = nexusctl._load_model_candidates()
    assert [r["model_id"] for r in rows] == ["meituan/owl-alpha", "acme/normal-model"]

    class Args:
        json = False
        action = "candidates"

    assert nexusctl.cmd_models_candidates(Args()) == 0
    out = capsys.readouterr().out
    assert "meituan/owl-alpha" in out and "1 high-priority" in out


def test_candidates_json_output(sidecar, capsys):
    now = time.time()
    sidecar({"providers": {"groq": {"candidates": {
        "x/y": {"first_seen": now, "last_seen": now, "priority": "normal",
                "reason": "new-model", "emitted": True, "baseline": True}}}},
        "models": {}})

    class Args:
        json = True

    nexusctl.cmd_models_candidates(Args())
    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["model_id"] == "x/y" and payload[0]["baseline"] is True


def test_no_sidecar_is_clean(sidecar, capsys, tmp_path):
    # fixture patched home but wrote nothing — missing file must not raise
    assert nexusctl._load_model_candidates() == []

    class Args:
        json = False

    assert nexusctl.cmd_models_candidates(Args()) == 0
    assert "No discovery candidates" in capsys.readouterr().out
