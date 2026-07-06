"""Shared test fixtures for reasoning tests."""

import tempfile
import json
import pytest

from nexus_os.reasoning.pattern_extractor import ReasoningPattern


@pytest.fixture
def sample_trajectory():
    """A minimal USER/ASSISTANT/TOOL RESULT trajectory."""
    return (
        "USER: What is the current state of the config file?\n"
        "ASSISTANT: Let me check the config file to verify our assumptions.\n"
        "TOOL RESULT: The config file shows DEBUG mode is enabled.\n"
        "ASSISTANT: I see DEBUG mode is on. I need to disable it for production.\n"
    )


@pytest.fixture
def temp_cot_file():
    """Create a temporary JSONL file with sample CoT entries."""
    entries = [
        {
            "uid": "test-001",
            "source_file": "test.jsonl",
            "session": "test-session",
            "model": "claude-fable-5",
            "context": (
                "USER: Check if the server is running\n"
                "ASSISTANT: Let me run a diagnostic check on the server status.\n"
                "TOOL RESULT: Server is running on port 8080\n"
                "ASSISTANT: The server is active. I'll proceed with the update.\n"
            ),
        },
    ]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")
        temp_path = f.name
    yield temp_path
    import os
    os.unlink(temp_path)


@pytest.fixture
def sample_pattern_list():
    """A list of 5 ReasoningPattern fixtures for vectorizer tests."""
    patterns = []
    for i, (cat, text) in enumerate([
        ("DIAGNOSIS", "Let me check the environment and verify the current state."),
        ("HYPOTHESIS", "Maybe the issue is related to the configuration. We could try approach A or B."),
        ("BOUNDARY", "We must not change the config file as it would break other services."),
        ("TOOL_SELECTION", "I'll use the grep tool to find the exact location of the bug."),
        ("VERIFICATION", "Let me verify the change was applied correctly by running the tests."),
    ]):
        patterns.append(ReasoningPattern(
            pattern_id=f"test-{i}",
            category=cat,
            subcategory="general",
            text=text,
            context="USER: Test query",
            tool_sequence=[],
            confidence=0.7 + i * 0.05,
            source_uid="test",
        ))
    return patterns
