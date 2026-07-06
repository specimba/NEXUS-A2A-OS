"""Tests for the fable_engine module."""

import tempfile
import json
import pytest

pytest.importorskip("nexus_os.reasoning.fable_engine")

from nexus_os.reasoning.fable_engine import FableReasoningEngine, create_default_engine
from nexus_os.reasoning.pattern_extractor import ReasoningPattern


@pytest.fixture
def sample_patterns():
    """A curated set of ReasoningPattern instances across categories."""
    return [
        ReasoningPattern(
            pattern_id="test-1",
            category="DIAGNOSIS",
            subcategory="context_check",
            text="Let me check the current environment state by reading the config file.",
            context="[U] What is the current state?",
            tool_sequence=["Read"],
            confidence=0.85,
            source_uid="test",
        ),
        ReasoningPattern(
            pattern_id="test-2",
            category="HYPOTHESIS",
            subcategory="solution_generation",
            text="Maybe the issue is a missing dependency. We could install the package or use a fallback.",
            context="[U] Why is it failing?",
            tool_sequence=["Bash"],
            confidence=0.72,
            source_uid="test",
        ),
        ReasoningPattern(
            pattern_id="test-3",
            category="BOUNDARY",
            subcategory="safety_analysis",
            text="We must not modify the production config file as it would cause a service outage.",
            context="[U] Update the config",
            tool_sequence=[],
            confidence=0.91,
            source_uid="test",
        ),
        ReasoningPattern(
            pattern_id="test-4",
            category="TOOL_SELECTION",
            subcategory="precise_choice",
            text="I'll use the Grep tool to find the exact line instead of reading the whole file.",
            context="[U] Find the bug location",
            tool_sequence=["Grep"],
            confidence=0.78,
            source_uid="test",
        ),
        ReasoningPattern(
            pattern_id="test-5",
            category="VERIFICATION",
            subcategory="post_check",
            text="Let me verify the fix by running the test suite and checking the output.",
            context="[U] Confirm the fix works",
            tool_sequence=["Bash", "Read"],
            confidence=0.65,
            source_uid="test",
        ),
    ]


class TestFableReasoningEngine:
    """Tests for the FableReasoningEngine class."""

    def test_create_default_engine(self):
        """create_default_engine() returns FableReasoningEngine instance."""
        engine = create_default_engine()
        assert isinstance(engine, FableReasoningEngine)

    def test_generate_prompt(self, sample_patterns):
        """Returns non-empty string containing reasoning keywords."""
        engine = FableReasoningEngine(patterns=sample_patterns)
        prompt = engine.generate_prompt("debug the config file")
        assert isinstance(prompt, str)
        assert len(prompt) > 50
        assert any(kw in prompt.lower() for kw in ("diagnos", "check", "verify", "reason"))

    def test_inject_reasoning(self, sample_patterns):
        """Injects into base prompt, result contains both base and query."""
        engine = FableReasoningEngine(patterns=sample_patterns)
        base = "You are a NEXUS agent."
        query = "Find the root cause."
        result = engine.inject_reasoning(base, query)
        assert base in result
        assert query in result

    def test_status_empty(self):
        """Engine without data returns sensible status dict."""
        engine = FableReasoningEngine(patterns=[])
        status = engine.get_status()
        assert isinstance(status, dict)
        assert "pattern_count" in status

    def test_status_with_patterns(self, sample_patterns):
        """Engine with patterns returns nonzero counts."""
        engine = FableReasoningEngine(patterns=sample_patterns)
        status = engine.get_status()
        total = 0
        for v in status.values():
            if isinstance(v, int):
                total += v
        assert total > 0

    def test_extract_patterns_from_file(self, sample_patterns):
        """Create temp jsonl with 1 entry, extract, verify 1+ patterns."""
        engine = FableReasoningEngine(patterns=[])
        entry = {
            "uid": "extract-test-001",
            "source_file": "test.jsonl",
            "session": "test-session",
            "model": "claude-fable-5",
            "context": (
                "USER: Check the server\n"
                "ASSISTANT: Let me diagnose the server state by inspecting the logs.\n"
                "TOOL RESULT: Server log shows no errors\n"
                "ASSISTANT: The server is healthy.\n"
            ),
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
            temp_path = f.name

        try:
            result = engine.extract_patterns_from_file(temp_path, limit=1)
            assert len(result) >= 1
        finally:
            import os
            os.unlink(temp_path)
