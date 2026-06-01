"""tests/gmr/test_context_packet.py — ContextPacket tests"""
import pytest

from nexus_os.gmr.context_packet import ContextPacket


class TestContextPacket:
    def _make(self, **overrides):
        defaults = dict(
            task_id="t1", original_prompt="hello", intent="code",
            budget_remaining=100000,
        )
        defaults.update(overrides)
        return ContextPacket(**defaults)

    def test_default_fields(self):
        pkt = self._make()
        assert pkt.core_facts == []
        assert pkt.decisions_made == []
        assert pkt.pending_actions == []
        assert pkt.tool_state == {}
        assert pkt.handoff_count == 0
        assert pkt.previous_models == []
        assert pkt.trace_id is None

    def test_to_prompt_prefix_header(self):
        pkt = self._make(handoff_count=2)
        prefix = pkt.to_prompt_prefix()
        assert "## Context Handoff (v2)" in prefix

    def test_to_prompt_prefix_includes_facts(self):
        pkt = self._make(core_facts=["fact1", "fact2"])
        prefix = pkt.to_prompt_prefix()
        assert "### Facts" in prefix
        assert "- fact1" in prefix
        assert "- fact2" in prefix

    def test_to_prompt_prefix_limits_facts_to_5(self):
        facts = [f"fact{i}" for i in range(10)]
        pkt = self._make(core_facts=facts)
        prefix = pkt.to_prompt_prefix()
        assert "- fact5" in prefix
        assert "- fact9" in prefix
        assert "- fact0" not in prefix

    def test_to_prompt_prefix_includes_decisions(self):
        pkt = self._make(decisions_made=[{"choice": "A"}])
        prefix = pkt.to_prompt_prefix()
        assert "### Decisions" in prefix

    def test_to_prompt_prefix_limits_decisions_to_3(self):
        decisions = [{"choice": f"d{i}"} for i in range(5)]
        pkt = self._make(decisions_made=decisions)
        prefix = pkt.to_prompt_prefix()
        assert "d2" in prefix
        assert "d4" in prefix

    def test_to_prompt_prefix_includes_pending(self):
        pkt = self._make(pending_actions=["action1", "action2"])
        prefix = pkt.to_prompt_prefix()
        assert "### Pending" in prefix
        assert "- action1" in prefix

    def test_to_prompt_prefix_empty_packet(self):
        pkt = self._make()
        prefix = pkt.to_prompt_prefix()
        assert "## Context Handoff (v0)" in prefix
        assert "### Facts" not in prefix
