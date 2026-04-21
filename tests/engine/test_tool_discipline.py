"""tests/engine/test_tool_discipline.py — Tool Discipline Tests"""

import pytest

from nexus_os.engine.tool_discipline import (
    ToolDiscipline,
    ToolStatus,
    record_tool_call,
    get_tool_discipline,
)


class TestToolDisciplineBasics:
    """Test basic tool discipline."""

    def test_record_call(self):
        disc = ToolDiscipline()
        disc.record_call("tool1", ToolStatus.SUCCESS, 100)
        
        stats = disc.get_stats("tool1")
        assert stats["total_calls"] == 1
        assert stats["success_rate"] == 1.0

    def test_can_execute(self):
        disc = ToolDiscipline(max_calls_per_minute=5)
        disc.set_limits("tool1", max_per_minute=2)
        
        assert disc.can_execute("tool1") is True
        # Record 2 calls
        disc.record_call("tool1", ToolStatus.SUCCESS, 100)
        disc.record_call("tool1", ToolStatus.SUCCESS, 100)
        # Now rate limited
        assert disc.can_execute("tool1") is False

    def test_rate_limited_status(self):
        disc = ToolDiscipline()
        disc.record_call("tool1", ToolStatus.RATE_LIMITED, 0)
        
        stats = disc.get_stats("tool1")
        assert stats["rate_limited_count"] == 1


class TestRecommendations:
    """Test recommendations."""

    def test_low_success_rate(self):
        disc = ToolDiscipline()
        disc.record_call("bad_tool", ToolStatus.SUCCESS, 100)
        disc.record_call("bad_tool", ToolStatus.FAILURE, 100)
        disc.record_call("bad_tool", ToolStatus.FAILURE, 100)
        
        recs = disc.get_recommendations()
        assert any(r["tool"] == "bad_tool" for r in recs)


class TestConvenienceFunctions:
    """Test module-level functions."""

    def test_record_tool_call(self):
        disc = get_tool_discipline()
        disc.clear_for_testing = lambda: None
        
        record_tool_call("test_tool", ToolStatus.SUCCESS, 50)
        
        stats = disc.get_stats("test_tool")
        assert stats["total_calls"] == 1