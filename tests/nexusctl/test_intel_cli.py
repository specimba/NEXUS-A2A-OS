"""Tests for nexusctl intel subcommand."""

import json
from types import SimpleNamespace

from nexusctl.intel_cli import run_intel


def _args(command, **kwargs):
    base = {
        "intel_command": command,
        "input_file": None,
        "overwrite": False,
        "wiki_output_dir": None,
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_intel_stats_empty(tmp_path):
    code, payload = run_intel(_args("stats", wiki_output_dir=str(tmp_path)))
    assert code == 0
    assert payload["known_dossiers"] == 0
    assert payload["lint"]["dossiers"] == 0
    assert payload["lint"]["missing_vap"] == 0
    assert payload["lint"]["missing_provenance"] == 0


def test_intel_ingest_claims_and_lint(tmp_path):
    wiki_dir = tmp_path / "dossiers"
    claims = [
        {"artifact": "model-foo", "claim": "Model foo achieves 90% recall", "disposition": "verified"},
        {"artifact": "model-foo", "claim": "Model foo has low VRAM", "disposition": "verified"},
        {"artifact": "paper-bar", "claim": "Paper bar introduces FTPO", "disposition": "rejected"},
    ]

    claims_file = tmp_path / "claims.json"
    claims_file.write_text(json.dumps(claims), encoding="utf-8")

    code, payload = run_intel(
        _args("ingest-claims", input_file=str(claims_file), wiki_output_dir=str(wiki_dir))
    )
    assert code == 0
    assert payload["claims_ingested"] == 3
    assert payload["dossiers_generated"] == 2
    assert payload["dossiers_written"] == 2
    assert len(payload["written_paths"]) == 2

    # Lint should find dossiers with full provenance
    lint_code, lint_payload = run_intel(_args("lint", wiki_output_dir=str(wiki_dir)))
    assert lint_payload["dossiers"] == 2
    assert lint_payload["missing_provenance"] == 0
    assert lint_payload["missing_vap"] == 0

    # Stats should show 2 known dossiers
    stats_code, stats_payload = run_intel(_args("stats", wiki_output_dir=str(wiki_dir)))
    assert stats_payload["known_dossiers"] == 2


def test_intel_ingest_synthesis(tmp_path):
    wiki_dir = tmp_path / "dossiers"
    synthesis = {
        "findings": [
            {"domain": "Safety", "source": "arxiv-2406.11717", "content": "Refusal direction identified"},
            {"domain": "Safety", "source": "arxiv-2601.05693", "content": "DPO alignment via preference data"},
            {"domain": "Efficiency", "source": "lfm-paper", "content": "Liquid AI FTPO reduces doom loops"},
        ]
    }

    synth_file = tmp_path / "synthesis.json"
    synth_file.write_text(json.dumps(synthesis), encoding="utf-8")

    code, payload = run_intel(
        _args("ingest-synthesis", input_file=str(synth_file), wiki_output_dir=str(wiki_dir))
    )
    assert code == 0
    assert payload["findings_count"] == 3
    assert payload["dossiers_generated"] == 2  # "Safety" and "Efficiency"
    assert payload["dossiers_written"] == 2


def test_intel_ingest_synthesis_empty_findings(tmp_path):
    wiki_dir = tmp_path / "dossiers"
    synth_file = tmp_path / "empty.json"
    synth_file.write_text(json.dumps({"findings": []}), encoding="utf-8")

    code, payload = run_intel(
        _args("ingest-synthesis", input_file=str(synth_file), wiki_output_dir=str(wiki_dir))
    )
    assert code == 2
    assert "no findings" in payload["error"]


def test_intel_missing_file(tmp_path):
    code, payload = run_intel(
        _args("ingest-claims", input_file=str(tmp_path / "nonexistent.json"))
    )
    assert code == 2
    assert "not found" in payload["error"].lower() or "parse" in payload["error"].lower()


def test_intel_ingest_claims_dedup(tmp_path):
    """Second ingest without --overwrite should skip existing dossiers."""
    wiki_dir = tmp_path / "dossiers"
    claims = [
        {"artifact": "model-x", "claim": "X is fast", "disposition": "verified"},
    ]
    claims_file = tmp_path / "claims.json"
    claims_file.write_text(json.dumps(claims), encoding="utf-8")

    code1, p1 = run_intel(
        _args("ingest-claims", input_file=str(claims_file), wiki_output_dir=str(wiki_dir))
    )
    assert p1["dossiers_written"] == 1

    code2, p2 = run_intel(
        _args("ingest-claims", input_file=str(claims_file), wiki_output_dir=str(wiki_dir))
    )
    assert p2["dossiers_written"] == 0
