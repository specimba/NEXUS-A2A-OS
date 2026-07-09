from types import SimpleNamespace

from nexus_os.continuity.records import ProgressClass, read_records
from nexusctl.continuity_cli import run_continuity


def _args(command, **kwargs):
    base = {
        "continuity_command": command,
        "hours": 24.0,
        "run_id": "run-1",
        "agent_id": "codex-test",
        "source_lane": "grok-project-nexus",
        "input_fingerprint": None,
        "output_fingerprint": None,
        "artifact": [],
        "test": [],
        "provider_calls": 0,
        "quota_reserved": 0,
        "blocker": None,
        "next_action": None,
        "started_at": None,
        "implemented": False,
        "advisory_only": False,
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_continuity_open_close_resume_and_coverage(monkeypatch, tmp_path):
    ledger = tmp_path / "runs.jsonl"
    monkeypatch.setenv("NEXUS_CONTINUITY_LEDGER", str(ledger))

    open_code, open_payload = run_continuity(_args("open", input_fingerprint="in-1"))
    assert open_code == 0
    assert open_payload["record"]["progress_class"] == ProgressClass.NOOP_RECAP.value

    close_code, close_payload = run_continuity(
        _args(
            "close",
            input_fingerprint="in-1",
            output_fingerprint="out-1",
            artifact=["docs/verified.md"],
            test=["python -m pytest tests/nexusctl/test_continuity_cli.py -q"],
            provider_calls=1,
            next_action="promote proposal",
        )
    )
    assert close_code == 0
    assert close_payload["record"]["progress_class"] == ProgressClass.VERIFIED_DELTA.value

    records, meta = read_records(ledger)
    assert meta["exists"] is True
    assert len(records) == 2

    coverage_code, coverage_payload = run_continuity(_args("coverage", hours=1.0))
    assert coverage_code == 0
    assert coverage_payload["summary"]["progress_counts"][ProgressClass.VERIFIED_DELTA.value] == 1

    resume_code, resume_payload = run_continuity(_args("resume-plan"))
    assert resume_code == 0
    assert resume_payload["resume_plan"]["next_action"] == "promote proposal"


def test_continuity_corrupt_tail_degrades_without_rewrite(monkeypatch, tmp_path):
    ledger = tmp_path / "runs.jsonl"
    ledger.write_text('{"schema":"nexus.continuity.run.v1","run_id":"ok","agent_id":"a","source_lane":"s"}\n{bad-tail', encoding="utf-8")
    monkeypatch.setenv("NEXUS_CONTINUITY_LEDGER", str(ledger))

    code, payload = run_continuity(_args("status"))

    assert code == 2
    assert payload["status"] == "degraded"
    assert payload["ledger"]["corrupt_tail"] is True
    assert ledger.read_text(encoding="utf-8").endswith("{bad-tail")
