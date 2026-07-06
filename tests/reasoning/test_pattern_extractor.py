"""Tests for the pattern_extractor module."""

import json
import tempfile
import pytest

from nexus_os.reasoning.pattern_extractor import (
    PATTERN_CATEGORIES,
    ReasoningPattern,
    PatternExtractor,
)


class TestReasoningPattern:
    """Tests for the ReasoningPattern dataclass."""

    def test_pattern_creation(self):
        """Create a ReasoningPattern with all fields, verify all attributes."""
        p = ReasoningPattern(
            pattern_id="test-123",
            category="DIAGNOSIS",
            subcategory="context_check",
            text="Let me check the environment state.",
            context="[U] What is the state?",
            tool_sequence=["Read", "Grep"],
            confidence=0.85,
            source_uid="session-001",
            metadata={"turn_index": 2, "trajectory_length": 5},
        )
        assert p.pattern_id == "test-123"
        assert p.category == "DIAGNOSIS"
        assert p.subcategory == "context_check"
        assert p.text == "Let me check the environment state."
        assert p.context == "[U] What is the state?"
        assert p.tool_sequence == ["Read", "Grep"]
        assert p.confidence == 0.85
        assert p.source_uid == "session-001"
        assert p.metadata["turn_index"] == 2

    def test_pattern_default_fields(self):
        """Create with minimal fields, verify defaults."""
        p = ReasoningPattern(
            pattern_id="minimal-1",
            category="HYPOTHESIS",
            subcategory="general",
            text="Maybe we should try option A.",
            context="USER: What to do?",
            tool_sequence=[],
            confidence=0.5,
            source_uid="test",
        )
        assert p.metadata == {}
        assert p.tool_sequence == []
        assert p.confidence == 0.5


class TestPatternExtractor:
    """Tests for the PatternExtractor class."""

    @pytest.fixture
    def extractor(self, temp_cot_file):
        """Create a PatternExtractor pointing at a temp CoT file."""
        return PatternExtractor(temp_cot_file)

    def test_parse_empty_trajectory(self, extractor):
        """Empty string returns []."""
        assert extractor.parse_trajectory("") == []
        assert extractor.parse_trajectory("   ") == []
        assert extractor.parse_trajectory("\n\n") == []

    def test_parse_single_turn(self, extractor):
        """Single USER turn."""
        turns = extractor.parse_trajectory("USER: Hello world")
        assert len(turns) == 1
        assert turns[0].role == "USER"
        assert turns[0].content == "Hello world"
        assert turns[0].index == 0

    def test_parse_multi_turn(self, extractor):
        """Multiple USER/ASSISTANT/TOOL RESULT turns."""
        text = (
            "USER: What is the state?\n"
            "ASSISTANT: Let me check the config.\n"
            "TOOL RESULT: Config file found.\n"
            "ASSISTANT: Config is valid.\n"
        )
        turns = extractor.parse_trajectory(text)
        assert len(turns) == 4
        assert turns[0].role == "USER"
        assert turns[1].role == "ASSISTANT"
        assert turns[2].role == "TOOL RESULT"
        assert turns[3].role == "ASSISTANT"
        assert turns[2].content == "Config file found."
        assert turns[3].index == 3

    def test_extract_patterns_empty(self, extractor):
        """Empty trajectory returns []."""
        assert extractor.extract_patterns([]) == []

    def test_extract_patterns_diagnosis(self, extractor):
        """Text with diagnosis keywords returns DIAGNOSIS category."""
        from nexus_os.reasoning.pattern_extractor import Turn
        turns = [
            Turn(role="USER", content="What is the state?", index=0),
            Turn(role="ASSISTANT", content="Let me check the environment and inspect the current config.", index=1),
        ]
        patterns = extractor.extract_patterns(turns)
        assert len(patterns) == 1
        assert patterns[0].category == "DIAGNOSIS"

    def test_extract_patterns_hypothesis(self, extractor):
        """Text with hypothesis keywords returns HYPOTHESIS category."""
        from nexus_os.reasoning.pattern_extractor import Turn
        turns = [
            Turn(role="USER", content="How should we fix this?", index=0),
            Turn(role="ASSISTANT", content="Maybe we could try approach A or consider another option.", index=1),
        ]
        patterns = extractor.extract_patterns(turns)
        assert len(patterns) == 1
        assert patterns[0].category == "HYPOTHESIS"

    def test_extract_tool_sequences(self, extractor):
        """Verify tool extraction from text."""
        from nexus_os.reasoning.pattern_extractor import Turn
        turns = [
            Turn(role="USER", content="Check the file", index=0),
            Turn(role="ASSISTANT", content="I will use the Read tool to inspect the file.", index=1),
            Turn(role="TOOL RESULT", content="file content: DEBUG=true", index=2),
            Turn(role="USER", content="What next?", index=3),
        ]
        sequences = extractor.extract_tool_sequences(turns)
        assert len(sequences) >= 1
        assert "Read" in sequences[0]


class TestPatternCategories:
    """Tests for PATTERN_CATEGORIES."""

    def test_all_categories_defined(self):
        """PATTERN_CATEGORIES has all 7 expected strings."""
        expected = {
            "DIAGNOSIS",
            "HYPOTHESIS",
            "BOUNDARY",
            "TOOL_SELECTION",
            "VERIFICATION",
            "SELF_CORRECTION",
            "DELEGATION",
        }
        assert set(PATTERN_CATEGORIES) == expected
        assert len(PATTERN_CATEGORIES) == 7
