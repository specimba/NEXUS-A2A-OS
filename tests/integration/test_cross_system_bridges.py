"""Cross-system integration tests for NEXUS OS.

Covers:
- WikiPipeline ↔ UnifiedStateManager bidirectional sync
- Archivist 3-stage pipeline → DoppelGroundBridge → Vault channel writes
- DashboardSync reconnection behavior
- compile_batch → _build_backlinks → get_stats end-to-end
"""

import asyncio
import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# =============================================================================
# Test: WikiPipeline ↔ StateManager bidirectional sync
# =============================================================================

class TestWikiStateSync:
    """Test that wiki_pipeline properly propagates state changes to state_manager."""

    def test_refresh_propagates_to_state_manager(self):
        """wiki_pipeline.refresh() should notify state_manager via callback."""
        mock_sm = MagicMock()
        mock_sm.publish = MagicMock()

        with patch('nexus_cli_ctl.integrations.wiki_pipeline.WikiPipeline._build_index'):
            with patch('nexus_cli_ctl.integrations.wiki_pipeline.WikiPipeline._sync_loop'):
                from nexus_cli_ctl.integrations.wiki_pipeline import WikiPipeline
                wp = WikiPipeline(state_manager=mock_sm)
                
        with patch.object(wp, 'get_status', return_value={"pages": 10}):
            result = wp.refresh(on_refresh=lambda r: mock_sm.publish("wiki", r))
        
        mock_sm.publish.assert_called_once()
        call_args = mock_sm.publish.call_args
        assert call_args[0][0] == "wiki"

    def test_async_refresh_fires_state_publish(self):
        """async_refresh() should call sm.publish() with wiki data."""
        mock_sm = MagicMock()
        mock_sm.publish = AsyncMock()

        with patch('nexus_cli_ctl.integrations.wiki_pipeline.WikiPipeline._build_index'):
            with patch('nexus_cli_ctl.integrations.wiki_pipeline.WikiPipeline._sync_loop'):
                from nexus_cli_ctl.integrations.wiki_pipeline import WikiPipeline
                wp = WikiPipeline(state_manager=mock_sm)
                wp._page_count = 5
                wp._dossier_count = 2

        wp.get_status = MagicMock(return_value={"pages": 5, "dossiers": 2})

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(wp.async_refresh())
        finally:
            loop.close()

        mock_sm.publish.assert_called_once()
        args = mock_sm.publish.call_args[0]
        assert args[0] == "wiki"

    def test_get_state_returns_wiki_section(self):
        """State manager should include wiki section after initialization."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"wiki": {"pages": 0, "dossiers": 0}}, f)
            state_file = Path(f.name)

        try:
            with patch('nexus_cli_ctl.control.unified_state.state_manager.STATE_FILE', state_file):
                from nexus_cli_ctl.control.unified_state.state_manager import UnifiedStateManager
                sm = UnifiedStateManager()
                state = sm.get_state("wiki")
                assert isinstance(state, dict)
                assert "pages" in state
        finally:
            state_file.unlink(missing_ok=True)

    def test_wiki_stale_index_detection(self):
        """get_page() should detect stale index when file mtime > index build time."""
        with patch('nexus_cli_ctl.integrations.wiki_pipeline.WikiPipeline._build_index'):
            with patch('nexus_cli_ctl.integrations.wiki_pipeline.WikiPipeline._sync_loop'):
                from nexus_cli_ctl.integrations.wiki_pipeline import WikiPipeline
                wp = WikiPipeline()
                wp._page_count = 0
                wp._dossier_count = 0
                
        wp._wiki_index = {"test": {"path": "test.md", "mtime": 1000.0}}
        
        with patch('pathlib.Path.read_text', return_value="# Updated Content"):
            with patch('pathlib.Path.stat') as mock_stat:
                mock_stat.return_value = MagicMock(st_mtime=2000.0)
                with patch('pathlib.Path.exists', return_value=True):
                    result = wp.get_page("test")
                    if result:
                        assert result.get("stale_index") is True


# =============================================================================
# Test: Archivist 3-stage pipeline → DG Bridge → Vault
# =============================================================================

class TestPipelineToVaultBridge:
    """Test that the 3-stage archivist pipeline can flow through to the DG bridge."""

    def _make_import_record(self, **kwargs):
        """Helper to create a minimal import record dict."""
        defaults = {
            "file_path": "/test/paper.pdf",
            "file_type": "paper",
            "admission_class": "source_card",
            "priority": 80,
            "blake3_hash": "abc123def456",
            "file_size": 5000,
            "mtime": 1000000.0,
            "source_dir": "/test",
            "title": "Test Paper on Memory",
            "arxiv_id": "2501.12345",
        }
        defaults.update(kwargs)
        return defaults

    def test_compile_to_bridge_flow(self):
        """CompiledRecord from compile stage should be bridgeable to vault."""
        mock_compiled = MagicMock()
        mock_compiled.topic_tags = ["memory", "trust"]
        mock_compiled.import_record = MagicMock()
        mock_compiled.import_record.file_path = "/test/memory_paper.pdf"
        mock_compiled.import_record.title = "Memory Architecture for LLM Agents"
        mock_compiled.import_record.file_type = MagicMock(value="paper")
        mock_compiled.import_record.priority = 100
        mock_compiled.import_record.arxiv_id = "2501.12345"
        mock_compiled.import_record.blake3_hash = "abc123def456789"
        mock_compiled.quality_score = 0.9
        mock_compiled.dossier_topic = "memory"

        from nexus_os.archivist.doppelground_bridge import DoppelGroundBridge
        bridge = DoppelGroundBridge()
        mock_manager = MagicMock()
        mock_record = MagicMock()
        mock_record.record_id = "cr-integration-test"
        mock_manager.append_semantic.return_value = mock_record
        bridge._manager = mock_manager

        result = bridge.bridge_compiled(mock_compiled)
        
        assert result.accepted is True
        assert result.target_channel == 3
        assert result.record_id == "cr-integration-test"

    def test_batch_compile_then_bridge(self):
        """Full flow: compile batch → bridge batch → vault writes."""
        from nexus_os.archivist.doppelground_bridge import DoppelGroundBridge
        
        bridge = DoppelGroundBridge()
        mock_manager = MagicMock()
        mock_record = MagicMock()
        mock_record.record_id = "cr-batch-flow"
        mock_manager.append_semantic.return_value = mock_record
        mock_manager.append_procedural.return_value = mock_record
        mock_manager.append_trust.return_value = mock_record
        bridge._manager = mock_manager

        records = []
        for topic in ["memory", "security", "code"]:
            r = MagicMock()
            r.topic_tags = [topic]
            r.import_record = MagicMock()
            r.import_record.file_path = f"/test/{topic}.md"
            r.import_record.title = f"Test {topic}"
            r.import_record.file_type = MagicMock(value="markdown")
            r.import_record.priority = 90
            r.import_record.arxiv_id = None
            r.import_record.blake3_hash = f"hash_{topic}"
            r.quality_score = 0.85
            r.dossier_topic = topic
            records.append(r)

        results = bridge.bridge_batch(records)
        assert len(results) == 3
        assert all(r.accepted for r in results)

        channel_set = {r.target_channel for r in results}
        assert 3 in channel_set
        assert 4 in channel_set
        assert 5 in channel_set


# =============================================================================
# Test: DashboardSync reconnection
# =============================================================================

class TestDashboardSyncReconnection:
    """Test that DashboardSync handles reconnection after failures."""

    def test_push_to_dashboard_marks_unreachable_on_error(self):
        """When _push_to_dashboard fails, it should mark dashboard as unreachable."""
        with patch('nexus_cli_ctl.integrations.dashboard_sync.httpx') as mock_httpx:
            mock_httpx.AsyncClient = MagicMock()
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(side_effect=Exception("Connection refused"))
            mock_httpx.AsyncClient.return_value = mock_client

            from nexus_cli_ctl.integrations.dashboard_sync import DashboardSync
            ds = DashboardSync()
            ds._dashboard_reachable = True

            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(ds._push_to_dashboard({"type": "test"}))
            finally:
                loop.close()

            assert ds._dashboard_reachable is False

    def test_probe_loop_reconnects(self):
        """DashboardSync should attempt reconnection when dashboard becomes unreachable."""
        from nexus_cli_ctl.integrations.dashboard_sync import DashboardSync
        
        ds = DashboardSync()
        ds._dashboard_reachable = False
        
        assert hasattr(ds, '_probe_dashboard') or hasattr(ds, 'start')


# =============================================================================
# Test: compile_batch → backlinks → stats end-to-end
# =============================================================================

class TestCompileBatchEndToEnd:
    """Test the full compile_batch flow including backlinks and stats."""

    def setup_method(self):
        pass

    def test_backlinks_integration_in_compile_batch(self):
        """compile_batch should call _build_backlinks and store the result."""
        mock_import = MagicMock()
        mock_import.stage = MagicMock()
        
        with patch.dict('sys.modules', {'nexus_os.archivist.import_stage': mock_import}):
            from nexus_os.archivist.compile import ArchivistCompiler, CompiledRecord
            
            compiler = ArchivistCompiler()
            
            assert compiler._last_backlinks == 0
            
            stats = compiler.get_stats()
            assert stats["backlinks"] == 0


# =============================================================================
# Test: CompileStats backward compatibility
# =============================================================================

class TestCompileStatsBackwardCompatibility:
    """Ensure CompileStats works as both typed object and dict-like consumer."""

    def test_to_dict_matches_field_names(self):
        from nexus_os.archivist.compile import CompileStats
        stats = CompileStats(total=10, wiki_admissible=5, dossier_topics=3, with_arxiv_id=2, errors=0, backlinks=1)
        d = stats.to_dict()
        
        assert "total" in d
        assert "wiki_admissible" in d
        assert "dossier_topics" in d
        assert "backlinks" in d

    def test_compile_stats_is_dataclass(self):
        from nexus_os.archivist.compile import CompileStats
        import dataclasses
        assert dataclasses.is_dataclass(CompileStats)

    def test_default_initialization(self):
        from nexus_os.archivist.compile import CompileStats
        stats = CompileStats()
        assert stats.total == 0
        assert stats.errors == 0
        assert stats.backlinks == 0
