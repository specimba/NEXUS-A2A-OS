import json
from pathlib import Path

from tools.browser_ai_supervisor.external_browser_ai_director import main, stable_fingerprint
import tools.browser_ai_supervisor.external_browser_ai_director as director


def write_probe(path: Path, *, tail: str = "stable", title: str = "NEXUS OS (clone) - Grok") -> None:
    path.write_text(
        json.dumps(
            {
                "status": "READY",
                "target": {"title": title, "url": "https://grok.com/project/x?REDACTED"},
                "state": {
                    "title": title,
                    "inputs": [{"aria": "Ask Grok anything"}],
                    "buttons": [{"label": "Submit"}],
                    "tailText": tail,
                },
            }
        ),
        encoding="utf-8",
    )


def test_cli_probe_run_writes_noop_when_fingerprint_unchanged(tmp_path: Path, capsys):
    probe = tmp_path / "probe.json"
    memory = tmp_path / "memory.jsonl"
    write_probe(probe, tail="stable")
    previous = stable_fingerprint("NEXUS OS (clone) - Grok|Submit", "stable", "")
    memory.write_text(
        json.dumps(
            {
                "run_id": "previous",
                "source_id": "grok-project-nexus",
                "started_at": "2026-06-21T18:00:00Z",
                "visible_fingerprint": previous,
                "action": "CONTINUE_SENT",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    rc = main(
        [
            "--probe-json",
            str(probe),
            "--memory",
            str(memory),
            "--run-id",
            "cli-noop",
            "--now",
            "2026-06-21T18:10:00Z",
        ]
    )

    assert rc == 0
    output = json.loads(capsys.readouterr().out)
    assert output["action"] == "NOOP_UNCHANGED"
    assert output["provider_calls"] == 0


def test_cli_probe_run_records_artifact_and_bridge_tool_map(tmp_path: Path, capsys):
    probe = tmp_path / "probe.json"
    memory = tmp_path / "memory.jsonl"
    write_probe(probe, tail="new artifact GrokDirectorCycleContract_v1 arrived")

    rc = main(
        [
            "--probe-json",
            str(probe),
            "--memory",
            str(memory),
            "--run-id",
            "cli-artifact",
            "--bridge-status",
            "ok",
            "--requires-bridge",
            "--now",
            "2026-06-21T18:30:00Z",
        ]
    )

    assert rc == 0
    output = json.loads(capsys.readouterr().out)
    assert output["action"] == "ARTIFACT_CAPTURED"
    assert output["provider"] == "internai"
    assert output["provider_calls"] == 1
    assert output["bridge_tool_map"]["task_add"] == "single_bounded_task_proposal"

def test_cli_egress_probe_records_non_provider_memory_entry(tmp_path: Path, capsys, monkeypatch):
    probe = tmp_path / "probe.json"
    memory = tmp_path / "memory.jsonl"
    write_probe(probe, tail="new artifact GrokDirectorCycleContract_v1 arrived")

    def fake_egress_probe(url: str, *, method: str = "HEAD", audit_id: str = "director-egress", operator: str = "director"):
        return {
            "status_code": 200,
            "access_result": "allowed",
            "blocked": False,
            "reason": None,
        }

    monkeypatch.setattr(director, "run_egress_probe", fake_egress_probe)

    rc = main(
        [
            "--probe-json",
            str(probe),
            "--memory",
            str(memory),
            "--run-id",
            "cli-egress",
            "--bridge-status",
            "ok",
            "--requires-bridge",
            "--egress-url",
            "https://huggingface.co",
            "--now",
            "2026-06-21T19:00:00Z",
        ]
    )

    assert rc == 0
    output = json.loads(capsys.readouterr().out)
    assert output["egress_probe"]["status_code"] == 200
    assert output["egress_probe"]["access_result"] == "allowed"

    lines = [json.loads(line) for line in memory.read_text(encoding="utf-8").splitlines()]
    assert lines[-1]["run_id"] == "cli-egress-egress"
    assert lines[-1]["action"] == "EGRESS_PROBE_RECORDED"
    assert lines[-1]["provider"] == "none"
    assert lines[-1]["provider_calls"] == 0

