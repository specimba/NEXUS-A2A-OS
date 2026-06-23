"""tests/archivist/test_import_stage_gaps.py — Tests for import_stage bug fixes.

Covers:
1. discover_files() excludes __pycache__, node_modules, .git directories
2. discover_files() includes normal files
3. compute_hash() returns valid hash for real file, empty string for unreadable
4. process_file() returns None for empty hash (dedup/failed)
5. import_batch() duplicate count tracking is correct
6. EXCLUDE_PATTERNS class constant exists on ArchivistImporter
7. classify_file() handles all extensions correctly
8. score_priority() clamps to 0-120 range
9. determine_admission() correct for various file types
10. extract_arxiv_id() extracts IDs correctly
"""

import hashlib
import stat
from pathlib import Path
from unittest.mock import patch

import pytest

from nexus_os.archivist.import_stage import (
    ArchivistImporter,
    FileType,
    AdmissionClass,
    ImportRecord,
)


@pytest.fixture
def importer():
    return ArchivistImporter()


@pytest.fixture
def temp_dir(tmp_path):
    return tmp_path


class TestDiscoverFilesExclusion:
    def test_excludes_pycache(self, importer, temp_dir):
        cache_dir = temp_dir / "__pycache__"
        cache_dir.mkdir()
        (cache_dir / "module.pyc").write_text("bytecode")
        (temp_dir / "real.py").write_text("code")
        importer.watched_dirs = [str(temp_dir)]
        files = importer.discover_files()
        names = [f.name for f in files]
        assert "real.py" in names
        assert "module.pyc" not in names

    def test_excludes_node_modules(self, importer, temp_dir):
        nm = temp_dir / "node_modules"
        nm.mkdir()
        (nm / "package" / "index.js").parent.mkdir(parents=True)
        (nm / "package" / "index.js").write_text("js")
        (temp_dir / "app.py").write_text("code")
        importer.watched_dirs = [str(temp_dir)]
        files = importer.discover_files()
        names = [f.name for f in files]
        assert "app.py" in names
        assert "index.js" not in names

    def test_excludes_git(self, importer, temp_dir):
        git_dir = temp_dir / ".git"
        git_dir.mkdir()
        (git_dir / "HEAD").write_text("ref: refs/heads/main")
        (temp_dir / "README.md").write_text("readme")
        importer.watched_dirs = [str(temp_dir)]
        files = importer.discover_files()
        names = [f.name for f in files]
        assert "README.md" in names
        assert "HEAD" not in names

    def test_excludes_archive(self, importer, temp_dir):
        archive_dir = temp_dir / "archive"
        archive_dir.mkdir()
        (archive_dir / "old.txt").write_text("old")
        (temp_dir / "current.txt").write_text("current")
        importer.watched_dirs = [str(temp_dir)]
        files = importer.discover_files()
        names = [f.name for f in files]
        assert "current.txt" in names
        assert "old.txt" not in names

    def test_excludes_nexus_pi(self, importer, temp_dir):
        pi_dir = temp_dir / ".nexus_pi"
        pi_dir.mkdir()
        (pi_dir / "state.json").write_text("{}")
        (temp_dir / "config.yaml").write_text("key: val")
        importer.watched_dirs = [str(temp_dir)]
        files = importer.discover_files()
        names = [f.name for f in files]
        assert "config.yaml" in names
        assert "state.json" not in names

    def test_includes_normal_files(self, importer, temp_dir):
        (temp_dir / "paper.pdf").write_bytes(b"%PDF")
        (temp_dir / "notes.md").write_text("# Notes")
        (temp_dir / "script.py").write_text("print(1)")
        importer.watched_dirs = [str(temp_dir)]
        files = importer.discover_files()
        names = [f.name for f in files]
        assert "paper.pdf" in names
        assert "notes.md" in names
        assert "script.py" in names

    def test_nested_exclusion(self, importer, temp_dir):
        src = temp_dir / "src"
        src.mkdir()
        cache = src / "__pycache__"
        cache.mkdir()
        (cache / "mod.pyc").write_text("bytecode")
        (src / "main.py").write_text("main")
        importer.watched_dirs = [str(temp_dir)]
        files = importer.discover_files()
        names = [f.name for f in files]
        assert "main.py" in names
        assert "mod.pyc" not in names


class TestExcludePatternsConstant:
    def test_constant_exists(self):
        assert hasattr(ArchivistImporter, "EXCLUDE_PATTERNS")

    def test_constant_is_set(self):
        assert isinstance(ArchivistImporter.EXCLUDE_PATTERNS, set)

    def test_required_patterns_present(self):
        patterns = ArchivistImporter.EXCLUDE_PATTERNS
        assert "__pycache__" in patterns
        assert ".git" in patterns
        assert "node_modules" in patterns
        assert "archive" in patterns
        assert ".nexus_pi" in patterns

    def test_case_insensitive_matching(self, importer, temp_dir):
        upper = temp_dir / "NODE_MODULES"
        upper.mkdir()
        (upper / "pkg.js").write_text("js")
        (temp_dir / "real.py").write_text("code")
        importer.watched_dirs = [str(temp_dir)]
        files = importer.discover_files()
        names = [f.name for f in files]
        assert "pkg.js" not in names
        assert "real.py" in names


class TestComputeHash:
    def test_returns_valid_hash_for_real_file(self, importer, temp_dir):
        f = temp_dir / "test.txt"
        f.write_text("hello world")
        h = importer.compute_hash(f)
        assert h != ""
        assert len(h) >= 32

    def test_returns_empty_string_for_unreadable(self, importer, temp_dir):
        f = temp_dir / "missing.txt"
        h = importer.compute_hash(f)
        assert h == ""

    def test_hash_is_deterministic(self, importer, temp_dir):
        f = temp_dir / "data.bin"
        f.write_bytes(b"\x00\x01\x02\x03")
        h1 = importer.compute_hash(f)
        h2 = importer.compute_hash(f)
        assert h1 == h2


class TestProcessFileEmptyHash:
    def test_returns_none_on_empty_hash(self, importer, temp_dir):
        f = temp_dir / "test.txt"
        f.write_text("content")
        with patch.object(importer, "compute_hash", return_value=""):
            result = importer.process_file(f)
            assert result is None

    def test_returns_record_on_valid_hash(self, importer, temp_dir):
        f = temp_dir / "test.txt"
        f.write_text("content")
        result = importer.process_file(f)
        assert result is not None
        assert isinstance(result, ImportRecord)


class TestImportBatchDuplicateCount:
    def test_duplicate_count_tracked(self, importer, temp_dir):
        for i, content in enumerate(["A", "B", "A"]):
            (temp_dir / f"file_{i}.txt").write_text(content)
        importer.watched_dirs = [str(temp_dir)]
        records = importer.import_batch()
        assert importer._duplicate_count == 1
        assert len(records) == 2

    def test_duplicate_count_multiple(self, importer, temp_dir):
        contents = ["X", "X", "X", "Y"]
        for i, c in enumerate(contents):
            (temp_dir / f"f{i}.txt").write_text(c)
        importer.watched_dirs = [str(temp_dir)]
        records = importer.import_batch()
        assert importer._duplicate_count == 2
        assert len(records) == 2

    def test_duplicate_count_in_stats(self, importer, temp_dir):
        for i, c in enumerate(["A", "B", "A"]):
            (temp_dir / f"file_{i}.txt").write_text(c)
        importer.watched_dirs = [str(temp_dir)]
        importer.import_batch()
        stats = importer.get_stats()
        assert stats["duplicates"] == 1

    def test_no_duplicates_count_is_zero(self, importer, temp_dir):
        for i in range(3):
            (temp_dir / f"unique_{i}.txt").write_text(f"content_{i}")
        importer.watched_dirs = [str(temp_dir)]
        importer.import_batch()
        assert importer._duplicate_count == 0


class TestClassifyFileAllExtensions:
    def test_pdf_paper(self, importer, temp_dir):
        assert importer.classify_file(temp_dir / "x.pdf") == FileType.PAPER

    def test_py_code(self, importer, temp_dir):
        f = temp_dir / "x.py"
        f.write_text("pass")
        assert importer.classify_file(f) == FileType.CODE

    def test_ts_code(self, importer, temp_dir):
        f = temp_dir / "x.ts"
        f.write_text("const a = 1")
        assert importer.classify_file(f) == FileType.CODE

    def test_png_image(self, importer, temp_dir):
        f = temp_dir / "x.png"
        f.write_bytes(b"\x89PNG")
        assert importer.classify_file(f) == FileType.IMAGE

    def test_ipynb_notebook(self, importer, temp_dir):
        f = temp_dir / "x.ipynb"
        f.write_text("{}")
        assert importer.classify_file(f) == FileType.NOTEBOOK

    def test_parquet_data(self, importer, temp_dir):
        f = temp_dir / "x.parquet"
        f.write_bytes(b"PAR1")
        assert importer.classify_file(f) == FileType.DATA

    def test_csv_data(self, importer, temp_dir):
        f = temp_dir / "x.csv"
        f.write_text("a,b\n1,2")
        assert importer.classify_file(f) == FileType.DATA

    def test_yaml_config(self, importer, temp_dir):
        f = temp_dir / "x.yaml"
        f.write_text("k: v")
        assert importer.classify_file(f) == FileType.CONFIG

    def test_toml_config(self, importer, temp_dir):
        f = temp_dir / "x.toml"
        f.write_text("[section]")
        assert importer.classify_file(f) == FileType.CONFIG

    def test_prompt_txt(self, importer, temp_dir):
        f = temp_dir / "system_prompt.txt"
        f.write_text("prompt")
        assert importer.classify_file(f) == FileType.PROMPT

    def test_markdown(self, importer, temp_dir):
        f = temp_dir / "doc.md"
        f.write_text("# Hello")
        assert importer.classify_file(f) == FileType.MARKDOWN

    def test_log(self, importer, temp_dir):
        f = temp_dir / "output.log"
        f.write_text("INFO: start")
        assert importer.classify_file(f) == FileType.LOG

    def test_unknown_ext(self, importer, temp_dir):
        f = temp_dir / "data.xyz"
        f.write_text("xyz")
        assert importer.classify_file(f) == FileType.UNKNOWN


class TestScorePriorityClamp:
    def test_clamps_to_max_120(self, importer, temp_dir):
        f = temp_dir / "test.txt"
        f.write_text("x")
        with patch.object(importer, "score_priority", return_value=150):
            score = importer.score_priority(f, FileType.PAPER, f.stat().st_mtime, str(temp_dir / "ARCHIVIST"))
            assert score <= 120

    def test_clamps_to_min_0(self, importer, temp_dir):
        f = temp_dir / "test.txt"
        f.write_text("x")
        score = importer.score_priority(f, FileType.LOG, 0, "/tmp/unknown")
        assert score >= 0

    def test_score_within_range(self, importer, temp_dir):
        f = temp_dir / "test.txt"
        f.write_text("x")
        score = importer.score_priority(f, FileType.PAPER, f.stat().st_mtime, str(temp_dir))
        assert 0 <= score <= 120

    def test_negative_sum_clamps_to_zero(self, importer, temp_dir):
        f = temp_dir / "small.txt"
        f.write_text("x")
        mtime_old = 0
        score = importer.score_priority(f, FileType.LOG, mtime_old, "/tmp/NoMatchDir")
        assert score >= 0


class TestDetermineAdmission:
    def test_paper_with_arxiv_is_source_card(self, importer):
        rec = ImportRecord(
            file_path="/tmp/paper_2403.13031.pdf",
            file_type=FileType.PAPER,
            admission_class=AdmissionClass.QUARANTINE,
            priority=80,
            blake3_hash="abc",
            file_size=1000,
            mtime=0,
            source_dir="/Downloads",
            arxiv_id="2403.13031",
        )
        assert importer.determine_admission(rec) == AdmissionClass.SOURCE_CARD

    def test_prompt_is_template_fragment(self, importer):
        rec = ImportRecord(
            file_path="/tmp/prompt.txt",
            file_type=FileType.PROMPT,
            admission_class=AdmissionClass.QUARANTINE,
            priority=80,
            blake3_hash="abc",
            file_size=100,
            mtime=0,
            source_dir="/tmp",
        )
        assert importer.determine_admission(rec) == AdmissionClass.TEMPLATE_FRAGMENT

    def test_low_priority_quarantined(self, importer):
        rec = ImportRecord(
            file_path="/tmp/file.txt",
            file_type=FileType.LOG,
            admission_class=AdmissionClass.QUARANTINE,
            priority=5,
            blake3_hash="abc",
            file_size=100,
            mtime=0,
            source_dir="/tmp",
        )
        assert importer.determine_admission(rec) == AdmissionClass.QUARANTINE

    def test_temp_file_quarantined(self, importer):
        rec = ImportRecord(
            file_path="/tmp/temp_data.txt",
            file_type=FileType.LOG,
            admission_class=AdmissionClass.QUARANTINE,
            priority=80,
            blake3_hash="abc",
            file_size=100,
            mtime=0,
            source_dir="/tmp",
        )
        assert importer.determine_admission(rec) == AdmissionClass.QUARANTINE

    def test_downloads_web_reference(self, importer):
        rec = ImportRecord(
            file_path="/Users/x/Downloads/blog.txt",
            file_type=FileType.LOG,
            admission_class=AdmissionClass.QUARANTINE,
            priority=80,
            blake3_hash="abc",
            file_size=100,
            mtime=0,
            source_dir="/Users/x/Downloads",
        )
        assert importer.determine_admission(rec) == AdmissionClass.WEB_REFERENCE

    def test_nexus_log_is_operator_fragment(self, importer):
        rec = ImportRecord(
            file_path="/tmp/NEXUS/run.log",
            file_type=FileType.LOG,
            admission_class=AdmissionClass.QUARANTINE,
            priority=80,
            blake3_hash="abc",
            file_size=100,
            mtime=0,
            source_dir="/tmp/NEXUS",
        )
        assert importer.determine_admission(rec) == AdmissionClass.OPERATOR_FRAGMENT


class TestExtractArxivId:
    def test_standard_pattern(self, importer, temp_dir):
        f = temp_dir / "paper_2403.13031.pdf"
        assert importer.extract_arxiv_id(f) == "2403.13031"

    def test_arxiv_prefix_underscore(self, importer, temp_dir):
        f = temp_dir / "arxiv_2511_20857.pdf"
        assert importer.extract_arxiv_id(f) == "2511.20857"

    def test_arxiv_prefix_hyphen(self, importer, temp_dir):
        f = temp_dir / "arxiv-2511-20857.pdf"
        assert importer.extract_arxiv_id(f) == "2511.20857"

    def test_no_arxiv_id(self, importer, temp_dir):
        f = temp_dir / "random_paper.pdf"
        assert importer.extract_arxiv_id(f) is None

    def test_five_digit_id(self, importer, temp_dir):
        f = temp_dir / "2603.07670.pdf"
        assert importer.extract_arxiv_id(f) == "2603.07670"

    def test_case_insensitive_prefix(self, importer, temp_dir):
        f = temp_dir / "ARXIV_2501_12345.pdf"
        assert importer.extract_arxiv_id(f) == "2501.12345"
