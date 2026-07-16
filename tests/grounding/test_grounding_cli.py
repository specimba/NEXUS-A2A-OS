import hashlib
import json
from pathlib import Path

from nexusctl.cli import main


def test_grounding_doctor_uses_configured_runtime_root(
    tmp_path: Path, monkeypatch, capsys
):
    monkeypatch.setenv("NEXUS_GROUNDING_ROOT", str(tmp_path))
    monkeypatch.setattr("sys.argv", ["nexusctl", "grounding", "doctor", "--json"])

    result = main()
    payload = json.loads(capsys.readouterr().out)

    assert result == 0
    assert payload["store"]["root"] == str(tmp_path)
    assert payload["canonical_mutation_allowed"] is False
    assert payload["store"].get("writable") is True
    assert payload["status"] in {"ok", "degraded"}  # roots may be missing on CI


def test_grounding_doctor_survives_unwritable_root(
    tmp_path: Path, monkeypatch, capsys
):
    """A1: doctor must exit 0 with degraded JSON when store is RO."""
    ro = tmp_path / "ro_grounding"
    ro.mkdir()
    monkeypatch.setenv("NEXUS_GROUNDING_ROOT", str(ro))
    monkeypatch.setattr(
        "nexus_os.grounding.reliable_store._path_is_writable",
        lambda path: False,
    )
    monkeypatch.setattr("sys.argv", ["nexusctl", "grounding", "doctor", "--json"])

    result = main()
    payload = json.loads(capsys.readouterr().out)

    assert result == 0
    assert payload["command"] == "grounding doctor"
    assert payload["status"] == "degraded"
    assert payload["store"].get("read_only") is True or payload["store"].get("error")


def test_grounding_status_and_doctor_degrade_on_corrupt_ledger(
    tmp_path: Path, monkeypatch, capsys
):
    ledger = tmp_path / "events.jsonl"
    ledger.write_text('{"event_id":"truncated"\n', encoding="utf-8")

    monkeypatch.setenv("NEXUS_GROUNDING_ROOT", str(tmp_path))
    monkeypatch.setattr("sys.argv", ["nexusctl", "grounding", "status"])
    assert main() == 0
    status_payload = json.loads(capsys.readouterr().out)

    monkeypatch.setattr("sys.argv", ["nexusctl", "grounding", "doctor", "--json"])
    assert main() == 0
    doctor_payload = json.loads(capsys.readouterr().out)

    assert status_payload["status"] == "degraded"
    assert status_payload["corrupt_lines"] == 1
    assert doctor_payload["status"] == "degraded"
    assert doctor_payload["store"]["corrupt_lines"] == 1


def test_grounding_repair_ledger_is_dry_run_and_non_mutating(
    tmp_path: Path, monkeypatch, capsys
):
    ledger = tmp_path / "events.jsonl"
    corrupt = b'{"broken":\n'
    ledger.write_bytes(corrupt)
    before = ledger.read_bytes()

    monkeypatch.setenv("NEXUS_GROUNDING_ROOT", str(tmp_path))
    monkeypatch.setattr("sys.argv", ["nexusctl", "grounding", "repair-ledger"])

    result = main()
    payload = json.loads(capsys.readouterr().out)

    assert result == 0
    assert ledger.read_bytes() == before
    assert payload["status"] == "degraded"
    assert payload["command"] == "grounding repair-ledger"
    assert payload["mode"] == "dry_run"
    assert payload["ledger_mutation_performed"] is False
    assert payload["canonical_mutation_allowed"] is False
    assert payload["operator_approval_required"] is True
    assert payload["next_action"] == "quarantine_exact_hashed_rows_after_review"
    assert payload["report"]["invalid_count"] == 1
    assert "raw" not in json.dumps(payload["report"])


def test_grounding_repair_ledger_apply_preserves_backup_and_clears_corruption(
    tmp_path: Path, monkeypatch, capsys
):
    ledger = tmp_path / "events.jsonl"
    corrupt = b'{"broken":\n'
    ledger.write_bytes(corrupt)
    expected_sha256 = "sha256:" + hashlib.sha256(corrupt.rstrip()).hexdigest()

    monkeypatch.setenv("NEXUS_GROUNDING_ROOT", str(tmp_path))
    monkeypatch.setattr(
        "sys.argv",
        [
            "nexusctl",
            "grounding",
            "repair-ledger",
            "--apply",
            "--expected-line",
            "1",
            "--expected-sha256",
            expected_sha256,
        ],
    )

    result = main()
    payload = json.loads(capsys.readouterr().out)

    assert result == 0
    assert payload["status"] == "ok"
    assert payload["mode"] == "apply"
    assert payload["ledger_mutation_performed"] is True
    assert payload["operator_approval_required"] is False
    assert payload["result"]["remaining_invalid_count"] == 0
    assert Path(payload["result"]["backup"]).read_bytes() == corrupt
    assert ledger.read_bytes() == b""
    assert Path(payload["result"]["manifest"]).exists()


def test_grounding_promote_missing_proposal_is_blocked(
    tmp_path: Path, monkeypatch, capsys
):
    monkeypatch.setenv("NEXUS_GROUNDING_ROOT", str(tmp_path))
    monkeypatch.setattr(
        "sys.argv",
        ["nexusctl", "grounding", "promote", "--proposal", "missing", "--dry-run"],
    )

    result = main()
    payload = json.loads(capsys.readouterr().out)

    assert result == 2
    assert payload["status"] == "blocked"
    assert payload["reason"] == "proposal_not_found"
