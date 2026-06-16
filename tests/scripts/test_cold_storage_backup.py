from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def load_backup_tool():
    path = ROOT / "scripts" / "cold_storage_backup.py"
    spec = importlib.util.spec_from_file_location("cold_storage_backup", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def configure_tmp_backup(tool, tmp_path: Path) -> tuple[Path, Path]:
    source = tmp_path / "source"
    cold = tmp_path / "cold"
    (source / "datasets").mkdir(parents=True)
    (source / "datasets" / "sample.txt").write_text("sample\n", encoding="utf-8")

    tool.SOURCE_ROOT = source
    tool.COLD_ROOT = cold
    tool.BACKUP_DIRS = ["datasets"]
    return source, cold


def test_default_mode_is_manifest_first_dry_run(tmp_path: Path) -> None:
    tool = load_backup_tool()
    _, cold = configure_tmp_backup(tool, tmp_path)

    assert tool.main([]) == 0

    assert not cold.exists()


def test_full_backup_refuses_low_cold_storage_free_space(tmp_path: Path, monkeypatch) -> None:
    tool = load_backup_tool()
    _, cold = configure_tmp_backup(tool, tmp_path)
    cold.mkdir()
    monkeypatch.setattr(tool, "get_free_bytes", lambda _path: 1)

    assert tool.main(["--full"]) == 2

    assert list(cold.iterdir()) == []


def test_full_backup_prunes_automatically(tmp_path: Path, monkeypatch) -> None:
    tool = load_backup_tool()
    source, cold = configure_tmp_backup(tool, tmp_path)
    cold.mkdir()
    (cold / "level1_backup_20260601" / "NEXUS").mkdir(parents=True)
    (cold / "level2_backup_20260602" / "NEXUS").mkdir(parents=True)
    monkeypatch.setattr(tool, "KEEP_BACKUPS", 2)
    monkeypatch.setattr(tool, "get_free_bytes", lambda _path: 200 * 1024**3)

    assert tool.main(["--full"]) == 0

    assert not (cold / "level1_backup_20260601").exists()
    assert (cold / "level2_backup_20260602").exists()
    created = sorted(cold.glob("level3_backup_*"))
    assert len(created) == 1
    assert (created[0] / "NEXUS" / "datasets" / "sample.txt").read_text(encoding="utf-8") == "sample\n"
    assert (created[0] / "NEXUS" / "_manifest.json").exists()
