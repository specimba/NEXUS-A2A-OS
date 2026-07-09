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
