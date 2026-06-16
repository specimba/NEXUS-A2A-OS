"""tests/vault/test_consolidation_daemon.py — LightMem 3-Stage Consolidation Tests"""

import pytest
from unittest.mock import MagicMock, patch

from nexus_os.vault.consolidation_daemon import (
    ConsolidationConfig,
    ConsolidationStats,
    LightMemConsolidationDaemon,
    get_daemon,
)
from nexus_os.vault.memory_channels import MemoryChannelManager, MemoryChannel


class TestConsolidationConfig:
    def test_default_config_values(self):
        config = ConsolidationConfig()
        assert config.cpu_threshold_pct == 15.0
        assert config.idle_duration_seconds == 300
        assert config.sensory_queue_threshold == 100
        assert config.working_queue_threshold == 50
        assert config.sensory_batch_size == 20

    def test_custom_config(self):
        config = ConsolidationConfig(
            cpu_threshold_pct=10.0,
            idle_duration_seconds=60,
            sensory_queue_threshold=50,
        )
        assert config.cpu_threshold_pct == 10.0
        assert config.idle_duration_seconds == 60
        assert config.sensory_queue_threshold == 50


class TestConsolidationStats:
    def test_to_dict(self):
        stats = ConsolidationStats(
            run_id="test-1",
            timestamp="2026-06-11T12:00:00Z",
            stage="sensory_to_working",
            agent_id="agent_1",
            records_read=10,
            records_written=8,
            records_dropped=2,
            duration_ms=50.0,
        )
        d = stats.to_dict()
        assert d["run_id"] == "test-1"
        assert d["stage"] == "sensory_to_working"
        assert d["records_read"] == 10
        assert d["records_written"] == 8
        assert d["records_dropped"] == 2


class TestLightMemConsolidationDaemon:
    def test_daemon_initializes_with_defaults(self):
        daemon = LightMemConsolidationDaemon()
        assert daemon.config is not None
        assert daemon.manager is not None
        assert daemon._running is False

    def test_daemon_start_stop(self):
        daemon = LightMemConsolidationDaemon()
        daemon.start()
        assert daemon._running is True
        assert daemon._thread is not None
        daemon.stop()
        assert daemon._running is False

    def test_trigger_explicit_empty_buffers(self):
        manager = MemoryChannelManager()
        daemon = LightMemConsolidationDaemon(manager=manager)
        stats = daemon.trigger_explicit()
        assert stats == []  # No records to consolidate

    def test_stage_sensory_to_working(self):
        manager = MemoryChannelManager()
        aid = "test_agent"
        manager.append_sensory(aid, content="raw input 1", topic_tags=["sensor_1"])
        manager.append_sensory(aid, content="raw input 2", topic_tags=["sensor_2"])

        daemon = LightMemConsolidationDaemon(manager=manager)
        stats = daemon._stage_sensory_to_working(aid)

        assert len(stats) == 1
        assert stats[0].stage == "sensory_to_working"
        assert stats[0].records_read == 2
        assert stats[0].records_written == 2
        # SENSORY should be cleared
        assert len(manager.get_records(aid, MemoryChannel.SENSORY)) == 0

    def test_stage_working_to_episodic(self):
        manager = MemoryChannelManager()
        aid = "test_agent"
        manager.append_working(aid, content="working memory 1")
        manager.append_working(aid, content="working memory 2")

        daemon = LightMemConsolidationDaemon(manager=manager)
        stats = daemon._stage_working_to_episodic(aid)

        assert len(stats) == 1
        assert stats[0].stage == "working_to_episodic"
        assert stats[0].records_read == 2
        assert stats[0].records_written == 2

    def test_stage_episodic_to_semantic(self):
        manager = MemoryChannelManager()
        aid = "test_agent"
        manager.append_episodic(
            aid, content="this is a test event about benchmarking", outcome="success", duration_ms=1.0, token_count=1
        )
        manager.append_episodic(
            aid, content="another test about memory consolidation", outcome="success", duration_ms=1.0, token_count=1
        )

        daemon = LightMemConsolidationDaemon(manager=manager)
        stats = daemon._stage_episodic_to_semantic(aid)

        assert len(stats) == 1
        assert stats[0].stage == "episodic_to_semantic"
        assert stats[0].records_read == 2
        assert stats[0].records_written > 0  # Should extract some concepts

    def test_full_pipeline_single_agent(self):
        manager = MemoryChannelManager()
        aid = "test_agent"
        manager.append_sensory(aid, content="sensory input", topic_tags=["sensor"])
        manager.append_working(aid, content="working memory")
        manager.append_episodic(
            aid, content="episodic event about testing", outcome="success", duration_ms=1.0, token_count=1
        )

        daemon = LightMemConsolidationDaemon(manager=manager)
        stats = daemon._run_consolidation(agent_id=aid, reason="test")

        assert len(stats) == 3  # 3 stages
        stages = [s.stage for s in stats]
        assert "sensory_to_working" in stages
        assert "working_to_episodic" in stages
        assert "episodic_to_semantic" in stages

    def test_should_trigger_explicit(self):
        manager = MemoryChannelManager()
        daemon = LightMemConsolidationDaemon(manager=manager)
        # Empty queue should not trigger
        assert daemon._should_trigger_explicit() is False

        # Fill SENSORY above threshold
        for i in range(105):
            manager.append_sensory("agent_1", content=f"input {i}", topic_tags=["test"])
        assert daemon._should_trigger_explicit() is True

    def test_singleton(self):
        d1 = get_daemon()
        d2 = get_daemon()
        assert d1 is d2

    def test_stats_accumulation(self):
        daemon = LightMemConsolidationDaemon()
        stats = ConsolidationStats(
            run_id="s1",
            timestamp="2026-06-11T12:00:00Z",
            stage="sensory_to_working",
            agent_id="a1",
            records_read=5,
            records_written=4,
            records_dropped=1,
            duration_ms=10.0,
        )
        daemon._stats.append(stats)
        assert len(daemon.get_stats()) == 1
        assert daemon.get_stats()[0].records_read == 5
