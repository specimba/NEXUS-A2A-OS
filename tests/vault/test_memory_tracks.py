"""tests/vault/test_memory_tracks.py — 5-Track Memory Tests"""

import pytest
from nexus_os.vault.memory_tracks import (
    MemoryTrack, MemoryTracker, TrackRecord,
    CapabilityProfile, FailurePattern, get_tracker, VALID_LANES
)


class TestMemoryTrack:
    """Test MemoryTrack enum."""
    
    def test_track_values(self):
        """Test track enum values."""
        assert MemoryTrack.EVENT.value == "event"
        assert MemoryTrack.TRUST.value == "trust"
        assert MemoryTrack.CAPABILITY.value == "capability"
        assert MemoryTrack.FAILURE_PATTERN.value == "failure_pattern"
        assert MemoryTrack.GOVERNANCE.value == "governance"
    
    def test_all_tracks_defined(self):
        """Test all 5 tracks are defined."""
        tracks = list(MemoryTrack)
        assert len(tracks) == 5


class TestTrackRecord:
    """Test TrackRecord dataclass."""
    
    def test_event_record(self):
        """Test EVENT track record creation."""
        record = TrackRecord(
            track=MemoryTrack.EVENT,
            agent_id="agent-1",
            content="Task completed",
            outcome="success",
            duration_ms=150.5,
            token_count=500,
        )
        
        assert record.track == MemoryTrack.EVENT
        assert record.agent_id == "agent-1"
        assert record.outcome == "success"
        assert record.duration_ms == 150.5
    
    def test_trust_record(self):
        """Test TRUST track record creation."""
        record = TrackRecord(
            track=MemoryTrack.TRUST,
            agent_id="agent-1",
            content="High trust",
            lane="implementation",
            trust_score=0.85,
            evidence_count=10,
        )
        
        assert record.track == MemoryTrack.TRUST
        assert record.lane == "implementation"
        assert record.trust_score == 0.85
    
    def test_capability_record(self):
        """Test CAPABILITY track record creation."""
        record = TrackRecord(
            track=MemoryTrack.CAPABILITY,
            agent_id="agent-1",
            content="Python expert",
            skill_tags=["python", "javascript"],
            confidence=0.9,
        )
        
        assert record.skill_tags == ["python", "javascript"]
        assert record.confidence == 0.9
    
    def test_failure_record(self):
        """Test FAILURE_PATTERN record creation."""
        record = TrackRecord(
            track=MemoryTrack.FAILURE_PATTERN,
            agent_id="agent-1",
            content="Timeout repeated",
            failure_type="timeout",
            error_count=3,
        )
        
        assert record.failure_type == "timeout"
        assert record.error_count == 3
    
    def test_governance_record(self):
        """Test GOVERNANCE record creation."""
        record = TrackRecord(
            track=MemoryTrack.GOVERNANCE,
            agent_id="agent-1",
            content="TOKEN-BUDGET-001 violated",
            rule_violated="TOKEN-BUDGET-001",
            severity="high",
        )
        
        assert record.rule_violated == "TOKEN-BUDGET-001"
        assert record.severity == "high"


class TestCapabilityProfile:
    """Test CapabilityProfile dataclass."""
    
    @pytest.fixture
    def profile(self):
        return CapabilityProfile(
            agent_id="test-agent",
            languages={"python": 0.9, "javascript": 0.7},
            domains={"code": 0.85},
            tools={"bash": 0.8},
            total_tasks=10,
            successful_tasks=8,
        )
    
    def test_creation(self, profile):
        """Test profile creation."""
        assert profile.agent_id == "test-agent"
        assert profile.languages["python"] == 0.9
    
    def test_success_rate(self, profile):
        """Test success rate calculation."""
        assert profile.success_rate == 0.8
    
    def test_success_rate_zero_tasks(self):
        """Test success rate with zero tasks."""
        profile = CapabilityProfile(agent_id="test")
        assert profile.success_rate == 0.0
    
    def test_best_skill(self, profile):
        """Test best skill selection."""
        # python has highest at 0.9
        assert profile.best_skill() == "python"
    
    def test_best_skill_empty(self):
        """Test best skill with empty profile."""
        profile = CapabilityProfile(agent_id="test")
        assert profile.best_skill() is None


class TestFailurePattern:
    """Test FailurePattern dataclass."""
    
    def test_creation(self):
        """Test pattern creation."""
        pattern = FailurePattern(
            agent_id="test-agent",
            failure_type="timeout",
            frequency=3,
            lanes_affected=["implementation", "research"],
        )
        
        assert pattern.frequency == 3
        assert pattern.severity == "medium"  # 2 <= 3 < 5
    
    def test_severity_high(self):
        """Test high severity."""
        pattern = FailurePattern(
            agent_id="test",
            failure_type="security",
            frequency=6,
        )
        assert pattern.severity == "high"
    
    def test_severity_low(self):
        """Test low severity."""
        pattern = FailurePattern(
            agent_id="test",
            failure_type="minor",
            frequency=1,
        )
        assert pattern.severity == "low"


class TestMemoryTracker:
    """Test MemoryTracker class."""
    
    @pytest.fixture
    def tracker(self):
        return MemoryTracker()
    
    def test_append_event(self, tracker):
        """Test appending EVENT record."""
        record = tracker.append_event(
            agent_id="agent-1",
            content="Task completed",
            outcome="success",
            duration_ms=100.0,
            token_count=200,
        )
        
        assert record.track == MemoryTrack.EVENT
        assert record.outcome == "success"
    
    def test_append_event_failure(self, tracker):
        """Test appending failed EVENT."""
        record = tracker.append_event(
            agent_id="agent-1",
            content="Task failed",
            outcome="failure",
            duration_ms=50.0,
            token_count=100,
        )
        
        assert record.outcome == "failure"
    
    def test_append_trust(self, tracker):
        """Test appending TRUST record."""
        record = tracker.append_trust(
            agent_id="agent-1",
            lane="implementation",
            trust_score=0.85,
            evidence_count=5,
        )
        
        assert record.track == MemoryTrack.TRUST
        assert record.lane == "implementation"
        assert record.trust_score == 0.85
    
    def test_append_trust_unknown_lane(self, tracker):
        """Test trust with unknown lane defaults to general."""
        record = tracker.append_trust(
            agent_id="agent-1",
            lane="unknown_lane",
            trust_score=0.5,
            evidence_count=1,
        )
        
        assert record.lane == "general"  # default
    
    def test_append_capability(self, tracker):
        """Test appending CAPABILITY record."""
        record = tracker.append_capability(
            agent_id="agent-1",
            skill_tags=["python", "security"],
            confidence=0.9,
        )
        
        assert record.track == MemoryTrack.CAPABILITY
        assert "python" in record.skill_tags
    
    def test_capability_profile_updated(self, tracker):
        """Test capability profile is updated."""
        tracker.append_capability(
            agent_id="agent-1",
            skill_tags=["python"],
            confidence=0.8,
        )
        
        profile = tracker.get_capability("agent-1")
        assert profile is not None
        assert profile.languages["python"] == 0.8
    
    def test_append_failure(self, tracker):
        """Test appending FAILURE_PATTERN record."""
        record = tracker.append_failure(
            agent_id="agent-1",
            failure_type="timeout",
            lane="implementation",
        )
        
        assert record.track == MemoryTrack.FAILURE_PATTERN
        assert record.failure_type == "timeout"
    
    def test_critical_failure_detection(self, tracker):
        """Test high-frequency failures detected."""
        # Add 5 failures
        for _ in range(5):
            tracker.append_failure(
                agent_id="agent-1",
                failure_type="timeout",
            )
        
        critical = tracker.get_critical_failures("agent-1")
        assert len(critical) == 1
        assert critical[0].failure_type == "timeout"
    
    def test_append_governance(self, tracker):
        """Test appending GOVERNANCE record."""
        record = tracker.append_governance(
            agent_id="agent-1",
            rule_violated="TOKEN-BUDGET-001",
            severity="high",
        )
        
        assert record.track == MemoryTrack.GOVERNANCE
        assert record.rule_violated == "TOKEN-BUDGET-001"
    
    def test_get_events(self, tracker):
        """Test getting events."""
        tracker.append_event("a1", "t1", "success", 100, 100)
        tracker.append_event("a1", "t2", "failure", 50, 50)
        
        events = tracker.get_events("a1")
        assert len(events) == 2
    
    def test_get_trust_history(self, tracker):
        """Test getting trust history."""
        tracker.append_trust("a1", "implementation", 0.8, 3)
        tracker.append_trust("a1", "general", 0.7, 2)
        tracker.append_trust("a1", "implementation", 0.85, 4)
        
        impl_trust = tracker.get_trust_history("a1", "implementation")
        assert len(impl_trust) == 2
    
    def test_get_latest_trust(self, tracker):
        """Test getting latest trust score."""
        tracker.append_trust("a1", "implementation", 0.7, 2)
        tracker.append_trust("a1", "implementation", 0.8, 3)
        
        latest = tracker.get_latest_trust("a1", "implementation")
        assert latest == 0.8
    
    def test_buffer_summary(self, tracker):
        """Test buffer summary."""
        tracker.append_event("a1", "e1", "success", 100, 100)
        tracker.append_trust("a1", "general", 0.8, 5)
        
        summary = tracker.get_buffer_summary("a1")
        assert summary["event"] == 1
        assert summary["trust"] == 1
    
    def test_clear_buffer(self, tracker):
        """Test clearing buffer."""
        tracker.append_event("a1", "e1", "success", 100, 100)
        tracker.clear_buffer("a1")
        
        events = tracker.get_events("a1")
        assert len(events) == 0


class TestValidLanes:
    """Test valid lane definitions."""
    
    def test_all_lanes_defined(self):
        """Test all required lanes exist."""
        expected = {"research", "audit", "compliance", "implementation", "orchestration", "general"}
        assert VALID_LANES == expected


class TestGetTracker:
    """Test singleton getter."""
    
    def test_singleton(self):
        """Test get_tracker returns same instance."""
        t1 = get_tracker()
        t2 = get_tracker()
        assert t1 is t2