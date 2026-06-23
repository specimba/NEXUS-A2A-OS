"""Tests for archivist.py critical bug fixes.

Covers:
1. file_hash() returns None on exception (not 'error')
2. file_hash_blake3() returns None on exception (not 'error')
3. should_exclude() exact component matching (no false positives)
4. should_exclude() correctly matches __pycache__, .git, node_modules
5. scan_directory() handles unreadable files gracefully
6. categorize_file() returns expected string categories
7. CATEGORIZE_TO_FILETYPE mapping exists and covers all categories
8. logger exists at module level
"""

import logging
from pathlib import Path
from unittest.mock import patch

import pytest

from nexus_os.archivist.archivist import (
    CATEGORIZE_TO_FILETYPE,
    categorize_file,
    file_hash,
    file_hash_blake3,
    logger,
    scan_directory,
    should_exclude,
)


# ── BUG 1: file_hash() returns None on exception ──────────────────

class TestFileHashReturnsNoneOnError:
    def test_nonexistent_file_returns_none(self, tmp_path):
        missing = tmp_path / "does_not_exist.txt"
        result = file_hash(missing)
        assert result is None

    def test_stat_failure_returns_none(self, tmp_path):
        f = tmp_path / "real.txt"
        f.write_text("content")
        with patch.object(Path, "stat", side_effect=OSError("permission denied")):
            result = file_hash(f)
        assert result is None

    def test_valid_file_returns_string(self, tmp_path):
        f = tmp_path / "exists.txt"
        f.write_text("hello")
        result = file_hash(f)
        assert result is not None
        assert isinstance(result, str)
        assert "-" in result

    def test_not_error_string(self, tmp_path):
        missing = tmp_path / "nope.txt"
        result = file_hash(missing)
        assert result != "error"


# ── BUG 2: file_hash_blake3() returns None on exception ──────────

class TestFileHashBlake3ReturnsNoneOnError:
    def test_nonexistent_file_returns_none(self, tmp_path):
        missing = tmp_path / "does_not_exist.bin"
        result = file_hash_blake3(missing)
        assert result is None

    def test_stat_failure_returns_none(self, tmp_path):
        f = tmp_path / "real.bin"
        f.write_bytes(b"\x00\x01\x02")
        with patch.object(Path, "stat", side_effect=OSError("no access")):
            result = file_hash_blake3(f)
        assert result is None

    def test_valid_file_returns_hex_string(self, tmp_path):
        f = tmp_path / "real.bin"
        f.write_bytes(b"hello world")
        result = file_hash_blake3(f)
        assert result is not None
        assert isinstance(result, str)
        assert len(result) >= 32

    def test_not_error_string(self, tmp_path):
        missing = tmp_path / "nope.bin"
        result = file_hash_blake3(missing)
        assert result != "error"


# ── BUG 4: should_exclude() exact component matching ─────────────

class TestShouldExcludeExactComponentMatch:
    def test_architecture_not_matching_archive(self):
        assert not should_exclude(Path("/some/project/architecture.md"))

    def test_git_dir_excluded(self):
        assert should_exclude(Path("/project/.git/config"))

    def test_pycache_excluded(self):
        assert should_exclude(Path("/project/__pycache__/mod.pyc"))

    def test_node_modules_excluded(self):
        assert should_exclude(Path("/project/node_modules/react/index.js"))

    def test_nexus_pi_excluded(self):
        assert should_exclude(Path("/project/.nexus_pi/state.json"))

    def test_regular_file_not_excluded(self):
        assert not should_exclude(Path("/project/src/main.py"))

    def test_archive_dir_excluded(self):
        assert should_exclude(Path("/project/archive/old_file.txt"))

    def test_archived_in_filename_not_excluded(self):
        assert not should_exclude(Path("/project/archived_report.txt"))

    def test_node_modules_backup_not_excluded(self):
        assert not should_exclude(Path("/project/node_modules_backup/thing.js"))


# ── BUG 3: scan_directory() handles unreadable files ──────────────

class TestScanDirectoryGracefulErrors:
    def test_unreadable_file_skipped(self, tmp_path):
        good = tmp_path / "good.txt"
        good.write_text("readable")
        bad = tmp_path / "bad.txt"
        bad.write_text("unreadable")

        original_stat = Path.stat

        def patched_stat(self):
            if "bad" in str(self):
                raise PermissionError("no access")
            return original_stat(self)

        with patch.object(Path, "stat", patched_stat):
            result = scan_directory(tmp_path, max_depth=1)
        assert len(result) == 1
        assert result[0]["path"].endswith("good.txt")

    def test_nonexistent_dir_returns_empty(self, tmp_path):
        missing = tmp_path / "nonexistent"
        result = scan_directory(missing)
        assert result == []

    def test_scan_logs_debug_on_stat_failure(self, tmp_path, caplog):
        good = tmp_path / "good.txt"
        good.write_text("ok")
        bad = tmp_path / "bad.txt"
        bad.write_text("fail")

        original_stat = Path.stat

        def patched_stat(self):
            if "bad" in str(self):
                raise PermissionError("denied")
            return original_stat(self)

        with caplog.at_level(logging.DEBUG, logger="nexus_os.archivist"):
            with patch.object(Path, "stat", patched_stat):
                scan_directory(tmp_path, max_depth=1)

        assert any("Failed to stat" in r.message for r in caplog.records)


# ── BUG 5: categorize_file() categories and CATEGORIZE_TO_FILETYPE ─

class TestCategorizeFile:
    @pytest.mark.parametrize("filename,expected", [
        ("paper.pdf", "paper"),
        ("script.py", "code"),
        ("app.js", "code"),
        ("module.ts", "code"),
        ("config.yaml", "config"),
        ("settings.json", "config"),
        ("readme.md", "documentation"),
        ("plan.md", "plan"),
        ("implementation_guide.md", "plan"),
        ("report.md", "report"),
        ("log.md", "report"),
        ("output.log", "log"),
        ("notes.txt", "text"),
        ("backup.zip", "archive"),
        ("data.tar.gz", "archive"),
        ("unknown.xyz", "other"),
    ])
    def test_categorize_mapping(self, filename, expected):
        assert categorize_file(filename) == expected


class TestCategorizeToFiletypeMapping:
    def test_mapping_exists(self):
        assert isinstance(CATEGORIZE_TO_FILETYPE, dict)
        assert len(CATEGORIZE_TO_FILETYPE) > 0

    def test_all_categories_mapped(self):
        possible_categories = {"paper", "log", "code", "config", "documentation",
                               "plan", "report", "text", "archive", "other"}
        for cat in possible_categories:
            assert cat in CATEGORIZE_TO_FILETYPE, f"Missing mapping for category: {cat}"

    def test_values_are_filetype_strings(self):
        valid_types = {"PAPER", "LOG", "CODE", "CONFIG", "MARKDOWN", "UNKNOWN"}
        for cat, ft in CATEGORIZE_TO_FILETYPE.items():
            assert ft in valid_types, f"Category {cat!r} maps to invalid FileType {ft!r}"

    def test_paper_maps_to_paper(self):
        assert CATEGORIZE_TO_FILETYPE["paper"] == "PAPER"

    def test_documentation_maps_to_markdown(self):
        assert CATEGORIZE_TO_FILETYPE["documentation"] == "MARKDOWN"


# ── BUG 6: logger exists at module level ──────────────────────────

class TestLoggerExists:
    def test_logger_is_logging_logger(self):
        assert isinstance(logger, logging.Logger)

    def test_logger_name(self):
        assert logger.name == "nexus_os.archivist"

    def test_module_has_logger_attribute(self):
        import nexus_os.archivist.archivist as mod
        assert hasattr(mod, "logger")
        assert isinstance(mod.logger, logging.Logger)
