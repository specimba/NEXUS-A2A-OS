"""tests/vault/test_memory_channels.py — 8-Channel Memory Architecture Tests

Validates:
- Channel enum (8 values)
- Trust-gated write access (min thresholds)
- Execution path mapping (HOT/WARM/COLD)
- Backward compatibility: EPISODIC merges EVENT+FAILURE_PATTERN, TRUST merges TRUST+GOVERNANCE, PROCEDURAL merges CAPABILITY
- Buffer management and queries
- Singleton behavior
"""

import pytest
from nexus_os.vault.memory_channels import (
    MemoryChannel,
    ChannelRecord,
    MemoryChannelManager,
    get_manager,
    CHANNEL_WRITE_TRUST,
    CapabilityProfile,
    FailurePattern,
)
from nexus_os.execution_paths import ExecutionPath


# ── Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def manager():
    return MemoryChannelManager()


@pytest.fixture
def agent_id():
    return "test_agent"


# ── MemoryChannel Enum ─────────────────────────────────────────────────

class TestMemoryChannel:
    def test_eight_channels(self):
        assert len(MemoryChannel) == 8

    def test_channel_values(self):
        assert MemoryChannel.SENSORY.value == "sensory"
        assert MemoryChannel.WORKING.value == "working"
        assert MemoryChannel.EPISODIC.value == "episodic"
        assert MemoryChannel.SEMANTIC.value == "semantic"
        assert MemoryChannel.PROCEDURAL.value == "procedural"
        assert MemoryChannel.TRUST.value == "trust"
        assert MemoryChannel.TASK.value == "task"
        assert MemoryChannel.META.value == "meta"

    def test_channel_order(self):
        """Channels 0-7 as specified in architecture."""
        channels = list(MemoryChannel)
        assert channels[0] == MemoryChannel.SENSORY
        assert channels[1] == MemoryChannel.WORKING
        assert channels[2] == MemoryChannel.EPISODIC
        assert channels[3] == MemoryChannel.SEMANTIC
        assert channels[4] == MemoryChannel.PROCEDURAL
        assert channels[5] == MemoryChannel.TRUST
        assert channels[6] == MemoryChannel.TASK
        assert channels[7] == MemoryChannel.META


# ── Trust-Gated Write Access ─────────────────────────────────────────

class TestTrustGatedWrite:
    def test_sensory_open(self, manager, agent_id):
        """SENSORY: trust gate = 0 (open to all)."""
        result = manager.append_sensory(agent_id, "raw input")
        assert result is not None

    def test_working_open(self, manager, agent_id):
        """WORKING: trust gate = 0 (open to all)."""
        result = manager.append_working(agent_id, "context data")
        assert result is not None

    def test_semantic_denied_low_trust(self, manager, agent_id):
        """SEMANTIC: trust gate = 65, denied at 50."""
        result = manager.append_semantic(agent_id, "knowledge", trust_score=50.0)
        assert result is None

    def test_semantic_allowed_high_trust(self, manager, agent_id):
        """SEMANTIC: trust gate = 65, allowed at 70."""
        result = manager.append_semantic(agent_id, "knowledge", trust_score=70.0)
        assert result is not None

    def test_procedural_denied_at_75(self, manager, agent_id):
        """PROCEDURAL: trust gate = 80, denied at 75."""
        result = manager.append_procedural(agent_id, "skill", ["python"], 0.9, trust_score=75.0)
        assert result is None

    def test_procedural_allowed_at_85(self, manager, agent_id):
        """PROCEDURAL: trust gate = 80, allowed at 85."""
        result = manager.append_procedural(agent_id, "skill", ["python"], 0.9, trust_score=85.0)
        assert result is not None

    def test_trust_open(self, manager, agent_id):
        """TRUST: trust gate = 90 but append_trust does not check gate (governance)."""
        result = manager.append_trust(agent_id, "general", 0.5, 10)
        assert result is not None

    def test_task_denied_at_30(self, manager, agent_id):
        """TASK: trust gate = 40, denied at 30."""
        result = manager.append_task(agent_id, "task context", "task-1", trust_score=30.0)
        assert result is None

    def test_task_allowed_at_50(self, manager, agent_id):
        """TASK: trust gate = 40, allowed at 50."""
        result = manager.append_task(agent_id, "task context", "task-1", trust_score=50.0)
        assert result is not None

    def test_meta_denied_at_60(self, manager, agent_id):
        """META: trust gate = 70, denied at 60."""
        result = manager.append_meta(agent_id, "health", 0.5, trust_score=60.0)
        assert result is None

    def test_meta_allowed_at_75(self, manager, agent_id):
        """META: trust gate = 70, allowed at 75."""
        result = manager.append_meta(agent_id, "health", 0.5, trust_score=75.0)
        assert result is not None

    def test_threshold_values_match_spec(self):
        """Verify thresholds match NEXUS Trust Framework §4.2."""
        assert CHANNEL_WRITE_TRUST[MemoryChannel.SENSORY] == 0.0
        assert CHANNEL_WRITE_TRUST[MemoryChannel.WORKING] == 0.0
        assert CHANNEL_WRITE_TRUST[MemoryChannel.EPISODIC] == 30.0
        assert CHANNEL_WRITE_TRUST[MemoryChannel.SEMANTIC] == 65.0
        assert CHANNEL_WRITE_TRUST[MemoryChannel.PROCEDURAL] == 80.0
        assert CHANNEL_WRITE_TRUST[MemoryChannel.TRUST] == 90.0
        assert CHANNEL_WRITE_TRUST[MemoryChannel.TASK] == 40.0
        assert CHANNEL_WRITE_TRUST[MemoryChannel.META] == 70.0


# ── Execution Path Mapping ────────────────────────────────────────────

class TestExecutionPathMapping:
    def test_hot_channels(self, manager):
        assert manager.get_execution_path(MemoryChannel.SENSORY) == ExecutionPath.HOT
        assert manager.get_execution_path(MemoryChannel.WORKING) == ExecutionPath.HOT
        assert manager.get_execution_path(MemoryChannel.TRUST) == ExecutionPath.HOT

    def test_warm_channels(self, manager):
        assert manager.get_execution_path(MemoryChannel.EPISODIC) == ExecutionPath.WARM
        assert manager.get_execution_path(MemoryChannel.TASK) == ExecutionPath.WARM

    def test_cold_channels(self, manager):
        assert manager.get_execution_path(MemoryChannel.SEMANTIC) == ExecutionPath.COLD
        assert manager.get_execution_path(MemoryChannel.PROCEDURAL) == ExecutionPath.COLD
        assert manager.get_execution_path(MemoryChannel.META) == ExecutionPath.COLD


# ── Backward Compatibility: Merged Tracks ────────────────────────────

class TestMergedTracks:
    def test_episodic_includes_event_and_failure(self, manager, agent_id):
        """EPISODIC merges original EVENT + FAILURE_PATTERN tracks."""
        record = manager.append_episodic(
            agent_id, "task failed", "failure", 1000.0, 500,
            failure_type="timeout",
        )
        assert record is not None
        assert record.channel == MemoryChannel.EPISODIC
        assert record.outcome == "failure"
        assert record.failure_type == "timeout"

        # Failure pattern should be tracked
        failures = manager.get_failures(agent_id)
        assert "timeout" in failures
        assert failures["timeout"].frequency >= 1

    def test_trust_includes_governance(self, manager, agent_id):
        """TRUST merges original TRUST + GOVERNANCE tracks."""
        trust_record = manager.append_trust(agent_id, "general", 0.8, 5)
        gov_record = manager.append_governance(agent_id, "rule-1", "high")

        assert trust_record is not None
        assert gov_record is not None
        assert trust_record.channel == MemoryChannel.TRUST
        assert gov_record.channel == MemoryChannel.TRUST

        # Both in same buffer
        history = manager.get_trust_history(agent_id)
        assert len(history) >= 2

    def test_procedural_includes_capability(self, manager, agent_id):
        """PROCEDURAL merges original CAPABILITY track."""
        record = manager.append_procedural(
            agent_id, "python skill", ["python"], 0.95,
            trust_score=85.0,
        )
        assert record is not None
        assert record.channel == MemoryChannel.PROCEDURAL
        assert "python" in record.skill_tags

        # Capability profile updated
        profile = manager.get_capability(agent_id)
        assert profile is not None
        assert "python" in profile.languages


# ── Buffer Management ─────────────────────────────────────────────────

class TestBufferManagement:
    def test_working_auto_prune(self, manager, agent_id):
        """WORKING auto-prunes to 50 entries."""
        for i in range(60):
            manager.append_working(agent_id, f"data-{i}")
        
        records = manager.get_records(agent_id, MemoryChannel.WORKING)
        assert len(records) == 50
        assert records[0].content == "data-10"  # oldest kept

    def test_buffer_summary(self, manager, agent_id):
        manager.append_sensory(agent_id, "s1")
        manager.append_sensory(agent_id, "s2")
        manager.append_working(agent_id, "w1")
        
        summary = manager.get_buffer_summary(agent_id)
        assert summary["sensory"] == 2
        assert summary["working"] == 1
        assert summary["episodic"] == 0

    def test_clear_buffer(self, manager, agent_id):
        manager.append_sensory(agent_id, "s1")
        manager.clear_buffer(agent_id)
        
        summary = manager.get_buffer_summary(agent_id)
        assert all(v == 0 for v in summary.values())

    def test_episodic_success_updates_capability(self, manager, agent_id):
        manager.append_episodic(agent_id, "task", "success", 100.0, 50)
        profile = manager.get_capability(agent_id)
        assert profile.total_tasks == 1
        assert profile.successful_tasks == 1
        assert profile.success_rate == 1.0

    def test_failure_pattern_severity(self, manager, agent_id):
        for _ in range(5):
            manager.append_episodic(agent_id, "task", "failure", 100.0, 50, failure_type="timeout")
        
        failures = manager.get_failures(agent_id)
        assert failures["timeout"].severity == "high"
        
        critical = manager.get_critical_failures(agent_id)
        assert len(critical) == 1


# ── Query Methods ─────────────────────────────────────────────────────

class TestQueryMethods:
    def test_get_records_by_channel(self, manager, agent_id):
        for i in range(3):
            manager.append_sensory(agent_id, f"s{i}")
        
        records = manager.get_records(agent_id, MemoryChannel.SENSORY, limit=2)
        assert len(records) == 2
        assert records[0].content == "s1"

    def test_trust_history_lane_filter(self, manager, agent_id):
        manager.append_trust(agent_id, "general", 0.5, 1)
        manager.append_trust(agent_id, "audit", 0.8, 2)
        manager.append_trust(agent_id, "general", 0.6, 3)
        
        general = manager.get_trust_history(agent_id, "general")
        assert len(general) == 2
        
        audit = manager.get_trust_history(agent_id, "audit")
        assert len(audit) == 1

    def test_latest_trust(self, manager, agent_id):
        manager.append_trust(agent_id, "general", 0.5, 1)
        manager.append_trust(agent_id, "general", 0.7, 2)
        
        latest = manager.get_latest_trust(agent_id, "general")
        assert latest == 0.7

    def test_latest_trust_none(self, manager, agent_id):
        latest = manager.get_latest_trust(agent_id, "general")
        assert latest is None


# ── Consolidation Stats ──────────────────────────────────────────────

class TestConsolidationStats:
    def test_update_stats(self, manager):
        manager.update_consolidation_stats(
            MemoryChannel.EPISODIC,
            total=100,
            consolidated=80,
            deduplicated=10,
            avg_retrieval_ms=5.0,
            hit_rate=0.85,
        )
        
        stats = manager.get_consolidation_stats(MemoryChannel.EPISODIC)
        assert stats.total_records == 100
        assert stats.consolidated_records == 80
        assert stats.deduplicated_records == 10
        assert stats.retrieval_hit_rate == 0.85


# ── Singleton ────────────────────────────────────────────────────────

class TestSingleton:
    def test_same_instance(self):
        m1 = get_manager()
        m2 = get_manager()
        assert m1 is m2

    def test_manager_is_singleton(self):
        manager = get_manager()
        assert isinstance(manager, MemoryChannelManager)


# ── Record Fields ────────────────────────────────────────────────────

class TestChannelRecord:
    def test_all_fields(self):
        record = ChannelRecord(
            channel=MemoryChannel.EPISODIC,
            agent_id="agent-1",
            content="test",
            outcome="success",
            failure_type="timeout",
            trust_score=0.8,
            skill_tags=["python"],
            compression_ratio=0.5,
            task_id="task-1",
            meta_type="health",
        )
        assert record.channel == MemoryChannel.EPISODIC
        assert record.outcome == "success"
        assert record.failure_type == "timeout"
        assert record.compression_ratio == 0.5
        assert record.task_id == "task-1"
        assert record.meta_type == "health"

    def test_defaults(self):
        record = ChannelRecord(
            channel=MemoryChannel.SENSORY,
            agent_id="agent-1",
            content="test",
        )
        assert record.lane == "general"
        assert record.severity == "low"
        assert record.confidence == 0.0
        assert record.compression_ratio == 1.0


# ── CapabilityProfile ────────────────────────────────────────────────

class TestCapabilityProfile:
    def test_success_rate(self):
        profile = CapabilityProfile(agent_id="a1", total_tasks=10, successful_tasks=7)
        assert profile.success_rate == 0.7

    def test_success_rate_zero(self):
        profile = CapabilityProfile(agent_id="a1")
        assert profile.success_rate == 0.0

    def test_best_skill(self):
        profile = CapabilityProfile(
            agent_id="a1",
            languages={"python": 0.9, "rust": 0.7},
        )
        assert profile.best_skill() == "python"

    def test_best_skill_none(self):
        profile = CapabilityProfile(agent_id="a1")
        assert profile.best_skill() is None


# ── FailurePattern ────────────────────────────────────────────────────

class TestFailurePattern:
    def test_severity_low(self):
        f = FailurePattern(agent_id="a1", failure_type="timeout", frequency=1)
        assert f.severity == "low"

    def test_severity_medium(self):
        f = FailurePattern(agent_id="a1", failure_type="timeout", frequency=2)
        assert f.severity == "medium"

    def test_severity_high(self):
        f = FailurePattern(agent_id="a1", failure_type="timeout", frequency=5)
        assert f.severity == "high"
