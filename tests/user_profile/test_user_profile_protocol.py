"""tests/user_profile/test_user_profile_protocol.py — Tests for FileOrganizationProtocol.

Covers:
  - AutoCloneRule execution (find files, copy, preserve structure, manifest)
  - File matching with patterns and exclusions
  - Time window filtering
  - CleanupRule dry-run (safety)
  - IndexRule advisory
  - Error handling (nonexistent paths, disabled rules)
"""

from __future__ import annotations

import os
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from nexus_os.user_profile.preferences import (
    AutoCloneRule,
    CleanupRule,
    IndexRule,
    RuleStatus,
    FileScope,
)
from nexus_os.user_profile.protocol import (
    FileOrganizationProtocol,
    RuleExecutionResult,
    CloneOperation,
)


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

@pytest.fixture
def temp_protocol():
    """Create a protocol with a temporary worklog."""
    return FileOrganizationProtocol()


@pytest.fixture
def sample_source_dir():
    """Create a temporary source directory with sample files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        src = Path(tmpdir) / "source"
        src.mkdir()

        # Create test files
        (src / "file1.md").write_text("# File 1", encoding="utf-8")
        (src / "file2.py").write_text("print('hello')", encoding="utf-8")
        (src / "file3.tmp").write_text("temp", encoding="utf-8")
        (src / "sub1").mkdir(parents=True, exist_ok=True)
        (src / "sub1" / "file4.md").write_text("# Sub file", encoding="utf-8")
        (src / ".git").mkdir(parents=True, exist_ok=True)
        (src / ".git" / "config").write_text("git config", encoding="utf-8")

        yield src


@pytest.fixture
def old_file_source_dir():
    """Create a source directory with old and new files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        src = Path(tmpdir) / "source"
        src.mkdir()

        # New file (just created)
        new_file = src / "new_file.md"
        new_file.write_text("new", encoding="utf-8")

        # Old file (10 days ago)
        old_file = src / "old_file.md"
        old_file.write_text("old", encoding="utf-8")
        old_time = (datetime.now(timezone.utc) - timedelta(days=10)).timestamp()
        os.utime(str(old_file), (old_time, old_time))

        yield src


# ------------------------------------------------------------------
# AutoCloneRule Execution Tests
# ------------------------------------------------------------------

class TestAutoCloneExecution:
    def test_clone_disabled_rule(self, temp_protocol):
        rule = AutoCloneRule(
            rule_id="disabled",
            name="Disabled",
            description="",
            source_path="/tmp",
            destination_path="/tmp",
            status=RuleStatus.DRAFT,
        )
        result = temp_protocol.execute_clone_rule(rule)
        assert result.success is False
        assert "not enabled" in result.errors[0]

    def test_clone_nonexistent_source(self, temp_protocol):
        rule = AutoCloneRule(
            rule_id="bad-src",
            name="Bad Source",
            description="",
            source_path="/nonexistent/path/12345",
            destination_path="/tmp",
            status=RuleStatus.ENABLED,
        )
        result = temp_protocol.execute_clone_rule(rule)
        assert result.success is False
        assert "Source path does not exist" in result.errors[0]

    def test_clone_simple_files(self, temp_protocol, sample_source_dir):
        with tempfile.TemporaryDirectory() as tmpdir:
            dest = Path(tmpdir) / "dest"
            rule = AutoCloneRule(
                rule_id="simple",
                name="Simple Clone",
                description="",
                source_path=str(sample_source_dir),
                destination_path=str(dest),
                file_patterns=["*.md"],
                status=RuleStatus.ENABLED,
                time_window_hours=9999.0,  # Large window to catch all
            )
            result = temp_protocol.execute_clone_rule(rule)
            assert result.success is True
            assert result.files_processed >= 2  # file1.md + sub1/file4.md
            assert dest.exists()
            assert (dest / "file1.md").exists()
            assert (dest / "sub1" / "file4.md").exists()

    def test_clone_preserves_structure(self, temp_protocol, sample_source_dir):
        with tempfile.TemporaryDirectory() as tmpdir:
            dest = Path(tmpdir) / "dest"
            rule = AutoCloneRule(
                rule_id="structured",
                name="Structured Clone",
                description="",
                source_path=str(sample_source_dir),
                destination_path=str(dest),
                file_patterns=["*.md"],
                status=RuleStatus.ENABLED,
                preserve_structure=True,
                time_window_hours=9999.0,
            )
            result = temp_protocol.execute_clone_rule(rule)
            assert (dest / "sub1" / "file4.md").exists()
            assert result.files_processed >= 2

    def test_clone_flat_structure(self, temp_protocol, sample_source_dir):
        with tempfile.TemporaryDirectory() as tmpdir:
            dest = Path(tmpdir) / "dest"
            rule = AutoCloneRule(
                rule_id="flat",
                name="Flat Clone",
                description="",
                source_path=str(sample_source_dir),
                destination_path=str(dest),
                file_patterns=["*.md"],
                status=RuleStatus.ENABLED,
                preserve_structure=False,
                time_window_hours=9999.0,
            )
            result = temp_protocol.execute_clone_rule(rule)
            # In flat mode, all files go to root of dest, but name collisions may occur
            assert dest.exists()
            assert result.files_processed >= 1

    def test_clone_excludes_patterns(self, temp_protocol, sample_source_dir):
        with tempfile.TemporaryDirectory() as tmpdir:
            dest = Path(tmpdir) / "dest"
            rule = AutoCloneRule(
                rule_id="exclude",
                name="Exclude Clone",
                description="",
                source_path=str(sample_source_dir),
                destination_path=str(dest),
                file_patterns=["*"],
                exclude_patterns=["*.tmp", "*.git*"],
                status=RuleStatus.ENABLED,
                time_window_hours=9999.0,
            )
            result = temp_protocol.execute_clone_rule(rule)
            assert result.success is True
            assert (dest / "file1.md").exists()
            assert (dest / "file2.py").exists()
            assert not (dest / "file3.tmp").exists()
            assert not (dest / ".git").exists()

    def test_clone_time_window_filter(self, temp_protocol, old_file_source_dir):
        with tempfile.TemporaryDirectory() as tmpdir:
            dest = Path(tmpdir) / "dest"
            rule = AutoCloneRule(
                rule_id="time-filter",
                name="Time Filter",
                description="",
                source_path=str(old_file_source_dir),
                destination_path=str(dest),
                file_patterns=["*.md"],
                status=RuleStatus.ENABLED,
                time_window_hours=24.0,  # Only last 24 hours
            )
            result = temp_protocol.execute_clone_rule(rule)
            # Only new_file.md should be copied (old_file.md is 10 days old)
            assert (dest / "new_file.md").exists()
            assert not (dest / "old_file.md").exists()
            assert result.files_processed == 1

    def test_clone_generates_manifest(self, temp_protocol, sample_source_dir):
        with tempfile.TemporaryDirectory() as tmpdir:
            dest = Path(tmpdir) / "dest"
            rule = AutoCloneRule(
                rule_id="manifest",
                name="Manifest Clone",
                description="",
                source_path=str(sample_source_dir),
                destination_path=str(dest),
                file_patterns=["*.md"],
                status=RuleStatus.ENABLED,
                create_manifest=True,
                time_window_hours=9999.0,
            )
            result = temp_protocol.execute_clone_rule(rule)
            assert result.manifest_path is not None
            manifest = Path(result.manifest_path)
            assert manifest.exists()
            assert manifest.name == "MANIFEST.md"
            content = manifest.read_text(encoding="utf-8")
            assert "Auto-Clone Manifest" in content

    def test_clone_skips_existing_newer(self, temp_protocol, sample_source_dir):
        with tempfile.TemporaryDirectory() as tmpdir:
            dest = Path(tmpdir) / "dest"
            # Pre-create a newer file in dest
            dest.mkdir()
            (dest / "file1.md").write_text("newer content", encoding="utf-8")

            rule = AutoCloneRule(
                rule_id="skip-newer",
                name="Skip Newer",
                description="",
                source_path=str(sample_source_dir),
                destination_path=str(dest),
                file_patterns=["*.md"],
                status=RuleStatus.ENABLED,
                time_window_hours=9999.0,
            )
            result = temp_protocol.execute_clone_rule(rule)
            # file1.md should be skipped because dest version is newer or equal
            assert result.files_skipped >= 1
            # Content should still be the newer pre-created version
            assert "newer content" in (dest / "file1.md").read_text(encoding="utf-8")

    def test_clone_operation_result(self, temp_protocol, sample_source_dir):
        with tempfile.TemporaryDirectory() as tmpdir:
            dest = Path(tmpdir) / "dest"
            rule = AutoCloneRule(
                rule_id="ops",
                name="Ops Clone",
                description="",
                source_path=str(sample_source_dir),
                destination_path=str(dest),
                file_patterns=["*.md"],
                status=RuleStatus.ENABLED,
                time_window_hours=9999.0,
            )
            result = temp_protocol.execute_clone_rule(rule)
            assert len(result.operations) > 0
            for op in result.operations:
                assert op.success is True
                assert op.bytes_copied > 0
                assert op.source is not None
                assert op.destination is not None

    def test_clone_result_to_dict(self, temp_protocol, sample_source_dir):
        with tempfile.TemporaryDirectory() as tmpdir:
            dest = Path(tmpdir) / "dest"
            rule = AutoCloneRule(
                rule_id="dict",
                name="Dict Clone",
                description="",
                source_path=str(sample_source_dir),
                destination_path=str(dest),
                file_patterns=["*.md"],
                status=RuleStatus.ENABLED,
                time_window_hours=9999.0,
            )
            result = temp_protocol.execute_clone_rule(rule)
            d = result.to_dict()
            assert d["rule_id"] == "dict"
            assert d["rule_type"] == "auto_clone"
            assert d["files_processed"] > 0
            assert "operations" in d
            assert "duration_ms" in d

    def test_clone_no_files_match(self, temp_protocol, sample_source_dir):
        with tempfile.TemporaryDirectory() as tmpdir:
            dest = Path(tmpdir) / "dest"
            rule = AutoCloneRule(
                rule_id="no-match",
                name="No Match",
                description="",
                source_path=str(sample_source_dir),
                destination_path=str(dest),
                file_patterns=["*.nonexistent"],
                status=RuleStatus.ENABLED,
                time_window_hours=9999.0,
            )
            result = temp_protocol.execute_clone_rule(rule)
            assert result.files_processed == 0

    def test_clone_no_patterns_matches_all(self, temp_protocol, sample_source_dir):
        with tempfile.TemporaryDirectory() as tmpdir:
            dest = Path(tmpdir) / "dest"
            rule = AutoCloneRule(
                rule_id="all",
                name="All Files",
                description="",
                source_path=str(sample_source_dir),
                destination_path=str(dest),
                file_patterns=[],  # No patterns = match all
                status=RuleStatus.ENABLED,
                time_window_hours=9999.0,
            )
            result = temp_protocol.execute_clone_rule(rule)
            assert result.files_processed >= 4  # file1, file2, file3, file4, git config


# ------------------------------------------------------------------
# CleanupRule Execution Tests (Safety-First)
# ------------------------------------------------------------------

class TestCleanupExecution:
    def test_cleanup_disabled_rule(self, temp_protocol):
        rule = CleanupRule(
            rule_id="disabled",
            name="Disabled",
            description="",
            target_path="/tmp",
            status=RuleStatus.DRAFT,
        )
        result = temp_protocol.execute_cleanup_rule(rule)
        assert result.success is False
        assert "not enabled" in result.errors[0]

    def test_cleanup_enabled_dry_run(self, temp_protocol):
        rule = CleanupRule(
            rule_id="dry-run",
            name="Dry Run",
            description="",
            target_path="/tmp",
            status=RuleStatus.ENABLED,
        )
        result = temp_protocol.execute_cleanup_rule(rule)
        assert result.success is True  # Dry-run succeeds
        assert "dry-run only" in result.errors[0]
        assert result.files_processed == 0


# ------------------------------------------------------------------
# IndexRule Execution Tests
# ------------------------------------------------------------------

class TestIndexExecution:
    def test_index_disabled_rule(self, temp_protocol):
        rule = IndexRule(
            rule_id="disabled",
            name="Disabled",
            description="",
            source_path="/tmp",
            status=RuleStatus.DRAFT,
        )
        result = temp_protocol.execute_index_rule(rule)
        assert result.success is False
        assert "not enabled" in result.errors[0]

    def test_index_nonexistent_source(self, temp_protocol):
        rule = IndexRule(
            rule_id="bad-src",
            name="Bad Source",
            description="",
            source_path="/nonexistent",
            status=RuleStatus.ENABLED,
        )
        result = temp_protocol.execute_index_rule(rule)
        assert result.success is False
        assert "Source path does not exist" in result.errors[0]

    def test_index_advisory(self, temp_protocol, sample_source_dir):
        rule = IndexRule(
            rule_id="advisory",
            name="Advisory",
            description="",
            source_path=str(sample_source_dir),
            file_patterns=["*.md"],
            status=RuleStatus.ENABLED,
            time_window_hours=9999.0,
        )
        result = temp_protocol.execute_index_rule(rule)
        assert result.success is True  # Advisory succeeds
        assert "advisory" in result.errors[0].lower()
        assert result.files_processed == 0  # No actual processing yet

    def test_index_counts_matching_files(self, temp_protocol, sample_source_dir):
        rule = IndexRule(
            rule_id="count",
            name="Count",
            description="",
            source_path=str(sample_source_dir),
            file_patterns=["*.md"],
            status=RuleStatus.ENABLED,
            time_window_hours=9999.0,
        )
        result = temp_protocol.execute_index_rule(rule)
        # Should mention 2 matching .md files (file1.md and sub1/file4.md)
        assert "2 files" in result.errors[0] or "files match" in result.errors[0]


# ------------------------------------------------------------------
# CloneOperation Tests
# ------------------------------------------------------------------

class TestCloneOperation:
    def test_successful_operation(self):
        op = CloneOperation(
            source="/src/file.txt",
            destination="/dst/file.txt",
            success=True,
            bytes_copied=1234,
        )
        assert op.success is True
        assert op.bytes_copied == 1234
        assert op.error is None

    def test_failed_operation(self):
        op = CloneOperation(
            source="/src/file.txt",
            destination="/dst/file.txt",
            success=False,
            error="Permission denied",
        )
        assert op.success is False
        assert op.error == "Permission denied"
        assert op.bytes_copied == 0

    def test_to_dict(self):
        op = CloneOperation(
            source="/src/file.txt",
            destination="/dst/file.txt",
            success=True,
            bytes_copied=1234,
        )
        d = op.to_dict()
        assert d["source"] == "/src/file.txt"
        assert d["destination"] == "/dst/file.txt"
        assert d["success"] is True
        assert d["bytes_copied"] == 1234
        assert d["error"] is None


# ------------------------------------------------------------------
# File Matching Tests
# ------------------------------------------------------------------

class TestFileMatching:
    def test_find_matching_all_patterns(self, temp_protocol):
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir)
            (src / "a.md").write_text("a")
            (src / "b.py").write_text("b")
            (src / "c.tmp").write_text("c")

            files = temp_protocol._find_matching_files(src, ["*.md", "*.py"], [], None)
            names = [f.name for f in files]
            assert "a.md" in names
            assert "b.py" in names
            assert "c.tmp" not in names

    def test_find_matching_excludes(self, temp_protocol):
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir)
            (src / "a.md").write_text("a")
            (src / "b.git").write_text("b")
            (src / "c.md").write_text("c")

            files = temp_protocol._find_matching_files(src, ["*"], ["*.git"], None)
            names = [f.name for f in files]
            assert "a.md" in names
            assert "b.git" not in names
            assert "c.md" in names

    def test_find_matching_with_cutoff(self, temp_protocol):
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir)
            new_file = src / "new.md"
            new_file.write_text("new")

            old_file = src / "old.md"
            old_file.write_text("old")
            old_time = (datetime.now(timezone.utc) - timedelta(days=10)).timestamp()
            os.utime(str(old_file), (old_time, old_time))

            cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
            files = temp_protocol._find_matching_files(src, ["*.md"], [], cutoff)
            names = [f.name for f in files]
            assert "new.md" in names
            assert "old.md" not in names

    def test_find_matching_no_cutoff(self, temp_protocol):
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir)
            old_file = src / "old.md"
            old_file.write_text("old")
            old_time = (datetime.now(timezone.utc) - timedelta(days=10)).timestamp()
            os.utime(str(old_file), (old_time, old_time))

            files = temp_protocol._find_matching_files(src, ["*.md"], [], None)
            names = [f.name for f in files]
            assert "old.md" in names

    def test_find_matching_duplicate_patterns(self, temp_protocol):
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir)
            (src / "a.md").write_text("a")

            # Same file matched by both patterns
            files = temp_protocol._find_matching_files(src, ["*.md", "a.*"], [], None)
            assert len(files) == 1  # Should deduplicate

    def test_find_matching_nested_directories(self, temp_protocol):
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir)
            (src / "sub" / "nested").mkdir(parents=True, exist_ok=True)
            (src / "sub" / "nested" / "deep.md").write_text("deep")

            files = temp_protocol._find_matching_files(src, ["*.md"], [], None)
            names = [f.name for f in files]
            assert "deep.md" in names
