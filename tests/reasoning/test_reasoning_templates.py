"""Tests for the reasoning_templates module."""

import pytest

from nexus_os.reasoning.reasoning_templates import (
    ReasoningStyle,
    ReasoningTemplateEngine,
)


@pytest.fixture
def fable_engine():
    return ReasoningTemplateEngine(ReasoningStyle.FABLE)


@pytest.fixture
def nexus_engine():
    return ReasoningTemplateEngine(ReasoningStyle.NEXUS)


@pytest.fixture
def hybrid_engine():
    return ReasoningTemplateEngine(ReasoningStyle.HYBRID)


class TestReasoningStyle:
    """Tests for the ReasoningStyle enum."""

    def test_enum_values(self):
        """Verify FABLE, NEXUS, HYBRID have correct values."""
        assert ReasoningStyle.FABLE.value == "fable"
        assert ReasoningStyle.NEXUS.value == "nexus"
        assert ReasoningStyle.HYBRID.value == "hybrid"


class TestReasoningTemplateEngine:
    """Tests for the ReasoningTemplateEngine class."""

    def test_fable_5_step_contains_diagnose(self, fable_engine):
        """get_fable_5_step() contains "DIAGNOSE"."""
        result = fable_engine.get_fable_5_step()
        assert "DIAGNOSE" in result

    def test_fable_5_step_contains_options(self, fable_engine):
        """get_fable_5_step() contains "OPTIONS"."""
        result = fable_engine.get_fable_5_step()
        assert "OPTIONS" in result

    def test_coger_routing_l1(self, nexus_engine):
        """get_coger_routing("L1") contains "Direct"."""
        result = nexus_engine.get_coger_routing("L1")
        assert "Direct" in result

    def test_coger_routing_l4(self, nexus_engine):
        """get_coger_routing("L4") contains "Systematic" or "Critical"."""
        result = nexus_engine.get_coger_routing("L4")
        assert "Systematic" in result or "Critical" in result

    def test_coger_routing_invalid(self, nexus_engine):
        """get_coger_routing("invalid") falls back to L2."""
        result = nexus_engine.get_coger_routing("invalid")
        assert "Guided Analysis" in result

    def test_generate_system_prompt(self, fable_engine):
        """Returns non-empty string with correct sections."""
        result = fable_engine.generate_system_prompt("debug", "L2")
        assert isinstance(result, str)
        assert len(result) > 100
        assert "NEXUS agent" in result
        assert "Debugging Guidance" in result

    def test_generate_thinking_block(self, fable_engine):
        """Contains <thinking_process> tags."""
        result = fable_engine.generate_thinking_block("Fix the bug in config.py")
        assert "<thinking_process>" in result
        assert "</thinking_process>" in result
        assert "Fix the bug in config.py" in result

    def test_generate_verification_checklist(self, fable_engine):
        """Contains checklist items."""
        result = fable_engine.generate_verification_checklist("Update config")
        assert "Verification Checklist for: Update config" in result
        assert "[ ]" in result
        assert "Rollback path" in result

    def test_inject_into_prompt(self, fable_engine):
        """Inject into base prompt, verify query appended."""
        base = "You are a helpful assistant."
        query = "Read the config file."
        result = fable_engine.inject_into_prompt(base, query)
        assert base in result
        assert query in result
        assert "## User Query" in result

    def test_hybrid_style(self, hybrid_engine):
        """HYBRID style includes CogER + Fable content."""
        prompt = hybrid_engine.generate_system_prompt("analysis", "L3")
        assert "Hybrid Reasoning" in prompt or "CogER" in prompt
        assert "DIAGNOSE" in prompt
        assert "Delegation Protocol" in prompt
