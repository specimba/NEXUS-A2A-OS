from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "tools" / "browser_ai_supervisor" / "grok_cdp_uipath_feedback.mjs"
EXAMPLE = ROOT / "tools" / "browser_ai_supervisor" / "uipath_feedback_answers.example.json"


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["node", str(SCRIPT), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=15,
    )


def test_help_is_read_only_and_documents_explicit_gates() -> None:
    result = run_script("--help")
    assert result.returncode == 0
    assert "read-only probe" in result.stdout
    assert "FILL_REVIEW_DRAFT" in result.stdout
    assert "SUBMIT_UIPATH_FEEDBACK" in result.stdout


def test_fill_requires_explicit_confirmation_before_cdp_access() -> None:
    result = run_script("--fill", "--answers", str(EXAMPLE))
    assert result.returncode == 1
    assert "--confirm-fill FILL_REVIEW_DRAFT" in result.stdout


def test_submit_requires_separate_confirmation_before_cdp_access() -> None:
    result = run_script(
        "--fill", "--confirm-fill", "FILL_REVIEW_DRAFT", "--submit",
        "--answers", str(EXAMPLE),
    )
    assert result.returncode == 1
    assert "--confirm-submit SUBMIT_UIPATH_FEEDBACK" in result.stdout


def test_example_placeholders_cannot_be_filled() -> None:
    result = run_script(
        "--fill", "--confirm-fill", "FILL_REVIEW_DRAFT",
        "--answers", str(EXAMPLE),
    )
    assert result.returncode == 1
    assert "answer file contains placeholders" in result.stdout


def test_script_contains_no_embedded_identity() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "specimba@gmail.com" not in source
    assert '"Canberk"' not in source
