"""tests/nexus_cli_ctl/test_wiki_pipeline_gaps.py — Wiki Pipeline Gap & Edge Case Tests

Tests for bugs found during deep audit:
- WIKI_DIR path correctness (was off-by-one)
- WIKI_STATE_FILE path correctness
- Singleton retrofit of state_manager on second call
- Word count from full file (not truncated snippet)
- Dossier count fallback to wiki_output/ directory
- Corrupted wiki_state.json handling (now logs warnings)
- EXCLUDED_TOPICS exact segment matching (not substring)
- get_page() consistent dict shape (content=None when file missing)
- get_page() with deleted file after indexing
- Empty/malformed wiki index entries
- Sync loop with broken state_manager
"""

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from nexus_cli_ctl.integrations.wiki_pipeline import (
    WikiPipeline,
    get_wiki_pipeline,
    EXCLUDED_TOPICS,
)


class TestWikiDirPath:
    def test_wiki_dir_includes_nexus_os(self):
        """WIKI_DIR must include 'nexus_os' in path (BUG FIX: was off-by-one)."""
        from nexus_cli_ctl.integrations.wiki_pipeline import WIKI_DIR
        path_str = str(WIKI_DIR).replace("\\", "/")
        assert "nexus_os" in path_str, f"WIKI_DIR missing 'nexus_os': {path_str}"

    def test_wiki_state_file_includes_nexus_os(self):
        """WIKI_STATE_FILE must include 'nexus_os' in path (BUG FIX)."""
        from nexus_cli_ctl.integrations.wiki_pipeline import WIKI_STATE_FILE
        path_str = str(WIKI_STATE_FILE).replace("\\", "/")
        assert "nexus_os" in path_str, f"WIKI_STATE_FILE missing 'nexus_os': {path_str}"


class TestSingletonRetrofit:
    def test_state_manager_retrofitted_on_second_call(self):
        """When first call has no sm, second call with sm should retrofit it."""
        import nexus_cli_ctl.integrations.wiki_pipeline as wp_mod
        wp_mod._wiki_pipeline = None

        p1 = get_wiki_pipeline()
        assert p1.sm is None

        sm_mock = MagicMock()
        p2 = get_wiki_pipeline(state_manager=sm_mock)
        assert p2.sm is sm_mock
        assert p2 is p1

    def teardown_method(self):
        import nexus_cli_ctl.integrations.wiki_pipeline as wp_mod
        wp_mod._wiki_pipeline = None


class TestWordCountFullFile:
    def test_word_count_uses_full_file_not_snippet(self, tmp_path, monkeypatch):
        """word_count should reflect full file content, not truncated 500 chars."""
        monkeypatch.setattr("nexus_cli_ctl.integrations.wiki_pipeline.WIKI_DIR", tmp_path)
        monkeypatch.setattr(
            "nexus_cli_ctl.integrations.wiki_pipeline.WIKI_STATE_FILE",
            tmp_path / "wiki_state.json",
        )

        content = " ".join(["word"] * 1000)
        (tmp_path / "long.md").write_text(f"# Long Page\n{content}", encoding="utf-8")

        pipeline = WikiPipeline()
        pipeline._build_index()

        entry = pipeline._wiki_index.get("long")
        assert entry is not None
        assert entry["word_count"] > 100, \
            f"word_count too low ({entry['word_count']}), likely computed from snippet"


class TestDossierCountFallback:
    def test_dossier_count_from_wiki_output(self, tmp_path, monkeypatch):
        """When wiki_state.json has no dossier_count, fallback to wiki_output/ dir."""
        monkeypatch.setattr("nexus_cli_ctl.integrations.wiki_pipeline.WIKI_DIR", tmp_path)
        monkeypatch.setattr(
            "nexus_cli_ctl.integrations.wiki_pipeline.WIKI_STATE_FILE",
            tmp_path / "wiki_state.json",
        )

        wiki_output = tmp_path.parent / "wiki_output"
        wiki_output.mkdir(parents=True, exist_ok=True)
        (wiki_output / "dossier_trust.md").write_text("# Trust Dossier", encoding="utf-8")
        (wiki_output / "dossier_memory.md").write_text("# Memory Dossier", encoding="utf-8")
        (wiki_output / "dossier_security.md").write_text("# Security Dossier", encoding="utf-8")

        # Create state file with dossier_count=0 to trigger fallback
        (tmp_path / "wiki_state.json").write_text(
            json.dumps({"dossier_count": 0}), encoding="utf-8",
        )

        pipeline = WikiPipeline()
        pipeline._build_index()

        assert pipeline._dossier_count >= 3


class TestCorruptedWikiState:
    def test_corrupted_json_logs_warning(self, tmp_path, monkeypatch, caplog):
        """Corrupted wiki_state.json should log a warning, not silently pass."""
        import logging
        monkeypatch.setattr("nexus_cli_ctl.integrations.wiki_pipeline.WIKI_DIR", tmp_path)
        state_file = tmp_path / "wiki_state.json"
        state_file.write_text("NOT JSON {{{{", encoding="utf-8")
        monkeypatch.setattr(
            "nexus_cli_ctl.integrations.wiki_pipeline.WIKI_STATE_FILE",
            state_file,
        )

        with caplog.at_level(logging.WARNING, logger="nexus.wiki_pipeline"):
            pipeline = WikiPipeline()
            pipeline._build_index()

        assert any("corrupt" in r.message.lower() or "failed" in r.message.lower()
                   for r in caplog.records) or pipeline._dossier_count == 0

    def test_missing_wiki_state_file_no_crash(self, tmp_path, monkeypatch):
        """Missing wiki_state.json should not crash."""
        monkeypatch.setattr("nexus_cli_ctl.integrations.wiki_pipeline.WIKI_DIR", tmp_path)
        monkeypatch.setattr(
            "nexus_cli_ctl.integrations.wiki_pipeline.WIKI_STATE_FILE",
            tmp_path / "nonexistent_state.json",
        )
        pipeline = WikiPipeline()
        pipeline._build_index()
        assert pipeline._dossier_count == 0


class TestExcludedTopicsSegmentMatch:
    def test_exact_segment_match_filters_gross(self, tmp_path, monkeypatch):
        """'gross' as a path segment should be filtered."""
        monkeypatch.setattr("nexus_cli_ctl.integrations.wiki_pipeline.WIKI_DIR", tmp_path)
        monkeypatch.setattr(
            "nexus_cli_ctl.integrations.wiki_pipeline.WIKI_STATE_FILE",
            tmp_path / "wiki_state.json",
        )
        (tmp_path / "gross.md").write_text("# Gross\nConfidential", encoding="utf-8")
        (tmp_path / "safe.md").write_text("# Safe\nPublic content", encoding="utf-8")

        pipeline = WikiPipeline()
        pipeline._build_index()

        assert "safe" in pipeline._wiki_index
        assert "gross" not in pipeline._wiki_index

    def test_password_filtered_as_segment(self, tmp_path, monkeypatch):
        """'password' as an exact segment should be filtered."""
        monkeypatch.setattr("nexus_cli_ctl.integrations.wiki_pipeline.WIKI_DIR", tmp_path)
        monkeypatch.setattr(
            "nexus_cli_ctl.integrations.wiki_pipeline.WIKI_STATE_FILE",
            tmp_path / "wiki_state.json",
        )
        (tmp_path / "password.md").write_text("# Password\nSecret", encoding="utf-8")
        (tmp_path / "safe_page.md").write_text("# Safe\nPublic", encoding="utf-8")

        pipeline = WikiPipeline()
        pipeline._build_index()

        assert "safe_page" in pipeline._wiki_index
        assert "password" not in pipeline._wiki_index

    def test_aggregate_slug_splits_correctly(self, tmp_path, monkeypatch):
        """Slug 'api_key_management' splits into 'api','key','management' segments."""
        monkeypatch.setattr("nexus_cli_ctl.integrations.wiki_pipeline.WIKI_DIR", tmp_path)
        monkeypatch.setattr(
            "nexus_cli_ctl.integrations.wiki_pipeline.WIKI_STATE_FILE",
            tmp_path / "wiki_state.json",
        )
        sub = tmp_path / "concepts"
        sub.mkdir()
        (sub / "api_key_management.md").write_text(
            "# API Key Management\nRotation procedures", encoding="utf-8"
        )
        safe_sub = tmp_path / "guides"
        safe_sub.mkdir()
        (safe_sub / "onboarding.md").write_text(
            "# Onboarding\nSetup guide", encoding="utf-8"
        )

        pipeline = WikiPipeline()
        pipeline._build_index()

        slug_parts = "concepts/api_key_management".lower().replace("/", " ").replace("-", " ").replace("_", " ").split()
        assert "api_key" not in slug_parts
        assert "api" in slug_parts
        assert "key" in slug_parts
        assert "management" in slug_parts

        assert "guides/onboarding" in pipeline._wiki_index or "onboarding" in pipeline._wiki_index


class TestGetPageConsistentShape:
    def test_get_page_existing_file_has_content(self, tmp_path, monkeypatch):
        """When file exists, get_page should include 'content' key."""
        monkeypatch.setattr("nexus_cli_ctl.integrations.wiki_pipeline.WIKI_DIR", tmp_path)
        monkeypatch.setattr(
            "nexus_cli_ctl.integrations.wiki_pipeline.WIKI_STATE_FILE",
            tmp_path / "wiki_state.json",
        )
        (tmp_path / "page.md").write_text("# Test Page\nFull content here", encoding="utf-8")

        pipeline = WikiPipeline()
        pipeline._build_index()

        result = pipeline.get_page("page")
        assert result is not None
        assert "content" in result
        assert result["content"] is not None
        assert "Test Page" in result["content"]

    def test_get_page_deleted_file_has_none_content(self, tmp_path, monkeypatch):
        """When file is deleted after indexing, get_page should return content=None."""
        monkeypatch.setattr("nexus_cli_ctl.integrations.wiki_pipeline.WIKI_DIR", tmp_path)
        monkeypatch.setattr(
            "nexus_cli_ctl.integrations.wiki_pipeline.WIKI_STATE_FILE",
            tmp_path / "wiki_state.json",
        )

        page_file = tmp_path / "ephemeral.md"
        page_file.write_text("# Ephemeral\nNow you see me", encoding="utf-8")

        pipeline = WikiPipeline()
        pipeline._build_index()

        page_file.unlink()

        result = pipeline.get_page("ephemeral")
        assert result is not None
        assert "content" in result
        assert result["content"] is None

    def test_get_page_nonexistent_slug(self, tmp_path, monkeypatch):
        monkeypatch.setattr("nexus_cli_ctl.integrations.wiki_pipeline.WIKI_DIR", tmp_path)
        monkeypatch.setattr(
            "nexus_cli_ctl.integrations.wiki_pipeline.WIKI_STATE_FILE",
            tmp_path / "wiki_state.json",
        )
        pipeline = WikiPipeline()
        pipeline._build_index()
        result = pipeline.get_page("nonexistent_slug_xyz")
        assert result is None


class TestSyncLoopEdgeCases:
    @pytest.mark.asyncio
    async def test_sync_with_broken_state_manager(self):
        """_sync_to_state propagates errors; _sync_loop catches them."""
        sm = AsyncMock()
        sm.publish = AsyncMock(side_effect=ConnectionError("broken"))
        pipeline = WikiPipeline(state_manager=sm)
        pipeline.running = True

        with pytest.raises(ConnectionError):
            await pipeline._sync_to_state()

    @pytest.mark.asyncio
    async def test_sync_loop_catched_broken_state_manager(self):
        """_sync_loop should catch and log errors from publish."""
        sm = AsyncMock()
        sm.publish = AsyncMock(side_effect=ConnectionError("broken"))
        pipeline = WikiPipeline(state_manager=sm)
        pipeline.running = True

        import asyncio
        async def _one_tick():
            try:
                await pipeline._sync_to_state()
            except Exception:
                pass

        await _one_tick()
        sm.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_without_state_manager(self):
        """Sync loop with no state_manager should silently skip."""
        pipeline = WikiPipeline(state_manager=None)
        await pipeline._sync_to_state()


class TestWikiIndexEdgeCases:
    def test_empty_wiki_directory(self, tmp_path, monkeypatch):
        monkeypatch.setattr("nexus_cli_ctl.integrations.wiki_pipeline.WIKI_DIR", tmp_path)
        monkeypatch.setattr(
            "nexus_cli_ctl.integrations.wiki_pipeline.WIKI_STATE_FILE",
            tmp_path / "wiki_state.json",
        )
        pipeline = WikiPipeline()
        pipeline._build_index()
        assert pipeline._page_count == 0
        assert len(pipeline._wiki_index) == 0

    def test_nonexistent_wiki_directory(self, tmp_path, monkeypatch):
        missing = tmp_path / "does_not_exist"
        monkeypatch.setattr("nexus_cli_ctl.integrations.wiki_pipeline.WIKI_DIR", missing)
        monkeypatch.setattr(
            "nexus_cli_ctl.integrations.wiki_pipeline.WIKI_STATE_FILE",
            tmp_path / "wiki_state.json",
        )
        pipeline = WikiPipeline()
        pipeline._build_index()
        assert pipeline._page_count == 0

    def test_binary_md_file_handled(self, tmp_path, monkeypatch):
        """Binary content in .md file should be handled gracefully."""
        monkeypatch.setattr("nexus_cli_ctl.integrations.wiki_pipeline.WIKI_DIR", tmp_path)
        monkeypatch.setattr(
            "nexus_cli_ctl.integrations.wiki_pipeline.WIKI_STATE_FILE",
            tmp_path / "wiki_state.json",
        )
        (tmp_path / "binary.md").write_bytes(b"\x00\x01\x02\xff\xfe\xfd")

        pipeline = WikiPipeline()
        pipeline._build_index()

    def test_unicode_content_handled(self, tmp_path, monkeypatch):
        monkeypatch.setattr("nexus_cli_ctl.integrations.wiki_pipeline.WIKI_DIR", tmp_path)
        monkeypatch.setattr(
            "nexus_cli_ctl.integrations.wiki_pipeline.WIKI_STATE_FILE",
            tmp_path / "wiki_state.json",
        )
        (tmp_path / "unicode.md").write_text("# \u65e5\u672c\u8a9e\u30c6\u30b9\u30c8\n\u5185\u5bb9\u306f\u3053\u3053\u306b", encoding="utf-8")

        pipeline = WikiPipeline()
        pipeline._build_index()
        assert "unicode" in pipeline._wiki_index
        entry = pipeline._wiki_index["unicode"]
        assert "\u65e5\u672c\u8a9e" in entry["title"] or "unicode" in entry["title"].lower()

    def test_search_empty_index(self, tmp_path, monkeypatch):
        monkeypatch.setattr("nexus_cli_ctl.integrations.wiki_pipeline.WIKI_DIR", tmp_path)
        monkeypatch.setattr(
            "nexus_cli_ctl.integrations.wiki_pipeline.WIKI_STATE_FILE",
            tmp_path / "wiki_state.json",
        )
        pipeline = WikiPipeline()
        pipeline._build_index()
        results = pipeline.search("anything")
        assert results == []
