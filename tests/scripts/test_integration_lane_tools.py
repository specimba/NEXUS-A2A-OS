from __future__ import annotations

import importlib.util
import json
from pathlib import Path


# CANARY: b88f7b5fdb6798d7980609f75d6cce86
ROOT = Path(__file__).resolve().parents[2]


def load_script(name: str):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_doppelground_ledger_redacts_run_tokens(tmp_path: Path) -> None:
    mod = load_script("doppelground_false_positive_ledger")
    report = tmp_path / "gitleaks-report.json"
    report.write_text(
        json.dumps(
            [
                {
                    "RuleID": "generic-api-key",
                    "File": "demo/contradiction_workspace/drill_runs/DR-01_20260321_181852_983021_4ac7ea02.json",
                    "StartLine": 3,
                    "Commit": "abc123",
                    "Secret": "DR-01_20260321_181852_983021_4ac7ea02",
                    "Match": 'run_token": "DR-01_20260321_181852_983021_4ac7ea02"',
                }
            ]
        ),
        encoding="utf-8",
    )

    ledger = mod.build_ledger(report, "sample")

    assert ledger["classification_counts"] == {"likely_false_positive": 1}
    entry = ledger["entries"][0]
    assert entry["secret_sha256"]
    assert entry["file_sha256"]
    assert "DR-01_20260321" not in entry["redacted_match"]
    assert "DR-01_20260321" not in entry["file_redacted"]
    assert "[REDACTED]" in entry["redacted_match"]
    assert "[RUN_TOKEN_REDACTED]" in entry["file_redacted"]


def test_qwave_artifact_ledger_summarizes_json(tmp_path: Path) -> None:
    mod = load_script("qwave_artifact_ledger")
    artifact_dir = tmp_path / "results" / "benchmark_quant"
    artifact_dir.mkdir(parents=True)
    artifact = artifact_dir / "truth_lab_qwen25_05b_chi64_m8.json"
    artifact.write_text(
        json.dumps({"status": "PASS", "model": "Qwen/Qwen2.5-0.5B", "chi": 64}),
        encoding="utf-8",
    )

    ledger = mod.build_ledger(tmp_path)

    assert ledger["artifact_count"] == 1
    item = ledger["artifacts"][0]
    assert item["path"] == "results/benchmark_quant/truth_lab_qwen25_05b_chi64_m8.json"
    assert item["json_summary"]["json_ok"] is True
    assert item["json_summary"]["chi"] == 64


def test_reviewground_wiki_check_requires_published_frontmatter(tmp_path: Path) -> None:
    mod = load_script("reviewground_wiki_check")
    for name in ["raw", "briefs", "drafts", "published", "graph", "obsidian"]:
        (tmp_path / name).mkdir()
    (tmp_path / "published" / "good.md").write_text(
        """---
id: TEST-1
title: Good
truth_layer: EVIDENCE
source_sha256: abc
evidence_quality: partial
review_status: draft
---
# Good
""",
        encoding="utf-8",
    )
    (tmp_path / "published" / "bad.md").write_text("# Bad\n", encoding="utf-8")

    report = mod.check_wiki(tmp_path)

    assert report["passed"] is False
    assert any(issue["file"] == "published/bad.md" for issue in report["issues"])
