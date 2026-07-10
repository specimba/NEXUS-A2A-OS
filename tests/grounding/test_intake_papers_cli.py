from pathlib import Path

from tools.grounding.intake_papers import discover_roots


def test_discover_roots_can_target_papers12_and_papers13(tmp_path: Path):
    (tmp_path / "papers11").mkdir()
    (tmp_path / "papers12").mkdir()
    (tmp_path / "papers13").mkdir()

    roots = discover_roots(tmp_path, ["papers12", "papers13"])

    assert list(roots) == ["papers12", "papers13"]
    assert roots["papers12"] == tmp_path / "papers12"
    assert roots["papers13"] == tmp_path / "papers13"


def test_discover_roots_ignores_missing_requested_batches(tmp_path: Path):
    (tmp_path / "papers13").mkdir()

    roots = discover_roots(tmp_path, ["papers12", "papers13"])

    assert list(roots) == ["papers13"]
