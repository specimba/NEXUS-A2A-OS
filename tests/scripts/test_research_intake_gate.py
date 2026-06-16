from __future__ import annotations

import importlib.util
from pathlib import Path


# CANARY: 209d17e3690eff54e14c538ed31cfe5f
ROOT = Path(__file__).resolve().parents[2]


def load_gate():
    path = ROOT / "scripts" / "research_intake_gate.py"
    spec = importlib.util.spec_from_file_location("research_intake_gate", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_research_intake_manifest_hashes_and_maps_components(tmp_path: Path) -> None:
    gate = load_gate()
    artifact = tmp_path / "artifact.md"
    artifact.write_text("Guard Plane adversarial evidence with trust governance notes.\n", encoding="utf-8")

    manifest = gate.build_manifest(tmp_path, ["artifact.md"])
    report = gate.validate_manifest(manifest, tmp_path)

    assert report["passed"] is True
    assert manifest["artifact_count"] == 1
    item = manifest["artifacts"][0]
    assert len(item["sha256"]) == 64
    assert "guard_plane" in item["components"]
    assert "trust_kernel" in item["components"]
    assert item["proposal"]["type"] == "guard_plane_candidate"


def test_research_intake_reports_missing_artifacts(tmp_path: Path) -> None:
    gate = load_gate()

    manifest = gate.build_manifest(tmp_path, ["missing.md"])

    assert manifest["artifact_count"] == 0
    assert manifest["missing_artifacts"] == ["missing.md"]


def test_research_intake_writes_vap_records_and_lane_b_summary(tmp_path: Path) -> None:
    gate = load_gate()
    artifact = tmp_path / "artifact.md"
    artifact.write_text("Guard Plane evidence for VAP provenance.\n", encoding="utf-8")
    manifest = gate.build_manifest(tmp_path, ["artifact.md"])

    vap_report = gate.write_vap_records(manifest, tmp_path / "vap.jsonl")
    summary_report = gate.write_lane_b_summary(manifest, vap_report, tmp_path / "lane-b.md")

    assert vap_report["record_count"] == 1
    assert vap_report["chain_integrity"] is True
    assert (tmp_path / "vap.jsonl").read_text(encoding="utf-8").count("\n") == 1
    assert summary_report["artifact_count"] == 1
    assert "Lane B - Active Diagnosis" in (tmp_path / "lane-b.md").read_text(encoding="utf-8")
