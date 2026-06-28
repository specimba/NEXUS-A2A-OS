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
