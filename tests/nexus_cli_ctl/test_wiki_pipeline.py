"""Tests for NEXUS CLI-CTL wiki pipeline integration."""
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from nexus_cli_ctl.integrations.wiki_pipeline import (
    WikiPipeline,
    get_wiki_pipeline,
    WIKI_DIR,
    EXCLUDED_TOPICS,
)


class TestWikiPipelineIndexing:
    def test_init_default(self):
        pipeline = WikiPipeline()
        assert pipeline.running is False
        assert pipeline._page_count == 0

    def test_build_index_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr("nexus_cli_ctl.integrations.wiki_pipeline.WIKI_DIR", tmp_path)
        pipeline = WikiPipeline()
        pipeline._build_index()
        assert pipeline._page_count == 0
        assert len(pipeline._wiki_index) == 0

    def test_build_index_with_pages(self, tmp_path, monkeypatch):
        monkeypatch.setattr("nexus_cli_ctl.integrations.wiki_pipeline.WIKI_DIR", tmp_path)
        (tmp_path / "topic1.md").write_text("# Topic 1\nThis is content", encoding="utf-8")
        (tmp_path / "sub" / "topic2.md").parent.mkdir(parents=True)
        (tmp_path / "sub" / "topic2.md").write_text("## Topic 2\nMore content", encoding="utf-8")

        pipeline = WikiPipeline()
        pipeline._build_index()
        assert pipeline._page_count == 2
        assert "topic1" in pipeline._wiki_index
        assert "sub/topic2" in pipeline._wiki_index

    def test_excluded_topics_filtered(self, tmp_path, monkeypatch):
        monkeypatch.setattr("nexus_cli_ctl.integrations.wiki_pipeline.WIKI_DIR", tmp_path)
        (tmp_path / "safe.md").write_text("# Safe\nContent", encoding="utf-8")
        (tmp_path / "gross_secret.md").write_text("# Gross\nConfidential", encoding="utf-8")

        pipeline = WikiPipeline()
        pipeline._build_index()
        assert "safe" in pipeline._wiki_index
        assert not any("gross" in k for k in pipeline._wiki_index.keys())

    def test_extract_title_from_h1(self):
        pipeline = WikiPipeline()
        assert pipeline._extract_title("# My Title\nBody") == "My Title"

    def test_extract_title_from_h2(self):
        pipeline = WikiPipeline()
        assert pipeline._extract_title("## Subtitle\nBody") == "Subtitle"

    def test_extract_title_no_heading(self):
        pipeline = WikiPipeline()
        assert pipeline._extract_title("No heading here\nJust text") is None

    def test_extract_title_h1_preferred(self):
        pipeline = WikiPipeline()
        assert pipeline._extract_title("# Main\n## Sub") == "Main"


class TestWikiPipelineSearch:
    def _populate(self, pipeline, tmp_path):
        pipeline._wiki_index = {
            "agents": {
                "slug": "agents",
                "title": "NEXUSCLAW Agents",
                "path": str(tmp_path / "agents.md"),
                "word_count": 100,
                "snippet": "Agents are components that perform tasks autonomously",
                "last_modified": "2026-01-01T00:00:00",
            },
            "trust": {
                "slug": "trust",
                "title": "Trust Engine",
                "path": str(tmp_path / "trust.md"),
                "word_count": 200,
                "snippet": "Mathematical trust system with HARDWALL defenses",
                "last_modified": "2026-01-01T00:00:00",
            },
        }
        pipeline._page_count = 2

    def test_search_by_title(self, tmp_path):
        pipeline = WikiPipeline()
        self._populate(pipeline, tmp_path)
        results = pipeline.search("trust")
        assert len(results) >= 1
        assert any("Trust" in r["title"] for r in results)

    def test_search_by_snippet(self, tmp_path):
        pipeline = WikiPipeline()
        self._populate(pipeline, tmp_path)
        results = pipeline.search("HARDWALL")
        assert len(results) >= 1

    def test_search_no_results(self, tmp_path):
        pipeline = WikiPipeline()
        self._populate(pipeline, tmp_path)
        results = pipeline.search("nonexistent_keyword_xyz")
        assert results == []

    def test_search_limit(self, tmp_path):
        pipeline = WikiPipeline()
        self._populate(pipeline, tmp_path)
        results = pipeline.search("a", limit=1)
        assert len(results) <= 1


class TestWikiPipelineStatus:
    def test_get_status(self):
        pipeline = WikiPipeline()
        status = pipeline.get_status()
        assert "running" in status
        assert "pages" in status
        assert "dossiers" in status
        assert "wiki_dir" in status
        assert status["running"] is False

    def test_list_pages(self, tmp_path):
        pipeline = WikiPipeline()
        pipeline._wiki_index = {
            "a": {"slug": "a", "title": "A", "path": "a.md", "word_count": 1, "snippet": "x", "last_modified": "2026-01-01"},
        }
        pages = pipeline.list_pages()
        assert len(pages) == 1
        assert pages[0]["slug"] == "a"

    def test_list_sources(self):
        pipeline = WikiPipeline()
        sources = pipeline.list_sources()
        assert "archivist" in sources
        assert "papers" in sources
        assert "nexuslogs" in sources
        for name, info in sources.items():
            assert "path" in info
            assert "exists" in info

    def test_refresh_rebuilds(self, tmp_path, monkeypatch):
        monkeypatch.setattr("nexus_cli_ctl.integrations.wiki_pipeline.WIKI_DIR", tmp_path)
        (tmp_path / "x.md").write_text("# X\ncontent", encoding="utf-8")
        pipeline = WikiPipeline()
        result = pipeline.refresh()
        assert result["pages"] >= 1
        assert "timestamp" in result


class TestWikiPipelineSingleton:
    def test_singleton_returns_same_instance(self):
        a = get_wiki_pipeline()
        b = get_wiki_pipeline()
        assert a is b

    def test_singleton_initialized(self):
        pipeline = get_wiki_pipeline()
        assert isinstance(pipeline, WikiPipeline)


class TestWikiPipelineAsync:
    @pytest.mark.asyncio
    async def test_start_stop(self):
        pipeline = WikiPipeline()
        await pipeline.start()
        assert pipeline.running is True
        await pipeline.stop()
        assert pipeline.running is False

    @pytest.mark.asyncio
    async def test_double_start_no_op(self):
        pipeline = WikiPipeline()
        await pipeline.start()
        await pipeline.start()  # Should not error
        await pipeline.stop()

    @pytest.mark.asyncio
    async def test_publishes_to_state(self):
        sm = AsyncMock()
        sm.publish = AsyncMock()
        pipeline = WikiPipeline(state_manager=sm)
        await pipeline._sync_to_state()
        sm.publish.assert_called_once()
        call_args = sm.publish.call_args
        assert call_args[0][0] == "wiki"
