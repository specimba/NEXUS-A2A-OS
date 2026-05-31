"""tests/monitoring/test_counters.py — Token counter tests

Covers:
- BaseCounter ABC interface
- LocalCounter (tiktoken fallback)
- NativeCounter (tiktoken + fallback)
- TokscaleCounter (subprocess + fallback)
"""

import pytest
from unittest.mock import patch, MagicMock

from nexus_os.monitoring.counters import (
    BaseCounter,
    LocalCounter,
    NativeCounter,
    TokscaleCounter,
)


# ── BaseCounter ──────────────────────────────────────────────────────

class TestBaseCounter:
    def test_cannot_instantiate(self):
        with pytest.raises(TypeError):
            BaseCounter()


# ── LocalCounter ─────────────────────────────────────────────────────

class TestLocalCounter:
    def test_init(self):
        counter = LocalCounter()

    def test_fallback_estimate(self):
        counter = LocalCounter()
        counter.encoder = None
        result = counter.count("a" * 100)
        assert result == 25  # 100 / 4

    def test_empty_string(self):
        counter = LocalCounter()
        counter.encoder = None
        result = counter.count("")
        assert result == 0

    def test_count_returns_positive(self):
        counter = LocalCounter()
        # If tiktoken not available, falls back to len//4
        result = counter.count("Hello world, this is a test string.")
        assert result > 0


# ── NativeCounter ────────────────────────────────────────────────────

class TestNativeCounter:
    def test_init(self):
        counter = NativeCounter("gpt-4")
        assert counter.model_name == "gpt-4"

    def test_count_returns_positive(self):
        counter = NativeCounter("gpt-4")
        result = counter.count("Hello world")
        assert result > 0

    def test_fallback_estimate(self):
        counter = NativeCounter("gpt-4")
        with patch.dict("sys.modules", {"tiktoken": None}):
            text = "x" * 80
            # Will use fallback: len(text) // 4
            result = counter.count(text)
            assert result > 0


# ── TokscaleCounter ─────────────────────────────────────────────────

class TestTokscaleCounter:
    def test_init_with_key(self):
        counter = TokscaleCounter(api_key="test-key")
        assert counter.api_key == "test-key"

    def test_init_without_key(self):
        counter = TokscaleCounter()
        assert counter.api_key is None

    def test_fallback_when_binary_missing(self):
        counter = TokscaleCounter()
        result = counter.count("Hello world, testing token counting")
        assert result > 0

    def test_dashboard_url(self):
        counter = TokscaleCounter()
        url = counter.get_dashboard_url()
        assert "tokscale" in url

    def test_count_with_mock_subprocess(self):
        counter = TokscaleCounter()
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Token count: 42"
        with patch("subprocess.run", return_value=mock_result):
            result = counter.count("some text")
            assert result == 42

    def test_count_subprocess_timeout(self):
        counter = TokscaleCounter()
        import subprocess
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("tokscale", 5)):
            result = counter.count("hello")
            assert result == len("hello") // 4
