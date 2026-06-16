from __future__ import annotations

import json
import subprocess
from pathlib import Path

from scripts.kilo_snapshot_forensics import analyze, safe_rel_path


def _run_git(cwd: Path, *args: str) -> None:
    proc = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr


def test_kilo_snapshot_forensics_compares_without_content_restore(tmp_path: Path) -> None:
    snapshot_root = tmp_path / "snapshot"
    snapshot_git = snapshot_root / "snapshot-id" / "gitdir"
    snapshot_worktree = tmp_path / "snapshot-worktree"
    live_repo = tmp_path / "live"
    snapshot_git.parent.mkdir(parents=True)
    snapshot_worktree.mkdir(parents=True)
    live_repo.mkdir()

    _run_git(snapshot_worktree, "init", "--separate-git-dir", str(snapshot_git.resolve()))
    _run_git(live_repo, "init")

    (snapshot_worktree / "same.txt").write_text("same\n", encoding="utf-8")
    (snapshot_worktree / "changed.txt").write_text("snapshot\n", encoding="utf-8")
    (snapshot_worktree / "missing.py").write_text("print('missing')\n", encoding="utf-8")
    (snapshot_worktree / ".grok").mkdir()
    (snapshot_worktree / ".grok" / "settings.json").write_text("secret-ish path only\n", encoding="utf-8")
    _run_git(snapshot_worktree, "add", ".")

    (live_repo / "same.txt").write_text("same\n", encoding="utf-8")
    (live_repo / "changed.txt").write_text("live\n", encoding="utf-8")
    (live_repo / "missing.py").write_text("print('missing')\n", encoding="utf-8")
    _run_git(live_repo, "add", ".")
    (live_repo / "missing.py").unlink()

    report = analyze(
        snapshot_root=snapshot_root,
        repo_root=live_repo,
        hash_working_tree=True,
        byte_compare_prefixes=["same.txt", "changed.txt", "missing.py", ".grok"],
    )

    assert report["mode"] == "read_only_metadata_no_content_restore"
    assert report["index_summary"]["tracked_file_count"] == 4
    compare = report["repo_compare"]["summary"]
    assert compare["same_blob"] == 1
    assert compare["different_blob"] == 1
    assert compare["missing_in_live_repo"] == 2
    assert report["index_summary"]["sensitive_path_count"] == 1
    assert any(row["sensitive_path_redacted"] for row in report["repo_compare"]["missing_candidates"])
    classification = report["recovery_classification"]
    assert classification["summary"]["missing_live"] == 2
    assert classification["summary"]["different_index"] == 1
    assert classification["summary"]["same_index"] == 1
    assert classification["by_priority"]["P0_sensitive_hold"] == 1
    assert classification["by_priority"]["P0_missing_code_review"] == 1
    byte_summary = report["byte_comparison"]["summary"]
    assert byte_summary["byte_identical_to_snapshot"] == 1
    assert byte_summary["live_matches_current_index_not_snapshot"] == 1
    assert byte_summary["missing_live"] == 2

    review_dir = live_repo / "review"
    extract_report = analyze(
        snapshot_root=snapshot_root,
        repo_root=live_repo,
        byte_compare_prefixes=["same.txt", "changed.txt", "missing.py", ".grok"],
        extract_missing_review_dir=review_dir,
    )
    extract = extract_report["missing_review_extract"]
    assert extract["files_extracted"] == 2
    assert (review_dir / "files" / "missing.py").read_text(encoding="utf-8") == "print('missing')\n"
    assert (review_dir / "files" / ".grok" / "settings.json").exists()
    assert not (live_repo / "missing.py").exists()
    manifest = json.loads((review_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["safety"]["live_paths_modified"] is False


def test_sensitive_paths_redact_by_default() -> None:
    assert safe_rel_path(".grok/settings.json") == "<redacted-sensitive-path:.json>"
    assert safe_rel_path("docs/handoff/report.md") == "docs/handoff/report.md"
