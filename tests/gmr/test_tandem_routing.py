"""tests/gmr/test_tandem_routing.py — TandemRouter tests"""

import json
import io
import pytest
from unittest.mock import patch, MagicMock
from urllib.error import URLError

from nexus_os.gmr.tandem_routing import TandemRouter


class TestTandemRouter:

    def test_initialization(self):
        router = TandemRouter(relay_url="http://mock-relay:1234", timeout=15.0)
        assert router._relay_url == "http://mock-relay:1234"
        assert router._timeout == 15.0

    @patch("urllib.request.urlopen")
    def test_call_model_success(self, mock_urlopen):
        # Mock successful JSON response from ModelRelay
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": "Test response content"
                }
            }]
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        router = TandemRouter(relay_url="http://mock-relay", timeout=10.0)
        result = router._call_model("fugu", "sys prompt", "user prompt")
        assert result == "Test response content"

    @patch("urllib.request.urlopen")
    def test_call_model_failure_fallback(self, mock_urlopen):
        # Mock HTTP error
        mock_urlopen.side_effect = URLError("Connection refused")

        router = TandemRouter(relay_url="http://mock-relay", timeout=10.0)
        result = router._call_model("fugu", "sys prompt", "user prompt")
        assert result == ""

    @patch("urllib.request.urlopen")
    def test_generate_blueprint(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": "1. Key point A\n2. Key point B"
                }
            }]
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        router = TandemRouter(relay_url="http://mock-relay")
        blueprint = router.generate_blueprint("solve x+y", "fugu-ultra")
        assert "Key point A" in blueprint
        assert "Key point B" in blueprint

    @patch("urllib.request.urlopen")
    def test_route_full_success(self, mock_urlopen):
        # Mock two consecutive successful calls: one for blueprint, one for execution
        mock_response_blueprint = MagicMock()
        mock_response_blueprint.read.return_value = json.dumps({
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": "Use mathematical formula"
                }
            }]
        }).encode("utf-8")

        mock_response_exec = MagicMock()
        mock_response_exec.read.return_value = json.dumps({
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": "The answer is 42."
                }
            }]
        }).encode("utf-8")

        # Side effect to return blueprint first, then execution result
        mock_urlopen.side_effect = [
            MagicMock(__enter__=MagicMock(return_value=mock_response_blueprint)),
            MagicMock(__enter__=MagicMock(return_value=mock_response_exec))
        ]

        router = TandemRouter(relay_url="http://mock-relay")
        result = router.route("solve universe life and everything", "fugu-ultra", "VibeThinker-3B")
        assert result == "The answer is 42."

    @patch("urllib.request.urlopen")
    def test_route_blueprint_fail_fallback_to_direct(self, mock_urlopen):
        # First call (blueprint) fails/returns empty, second (direct fallback) succeeds
        mock_response_direct = MagicMock()
        mock_response_direct.read.return_value = json.dumps({
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": "Direct fallback answer"
                }
            }]
        }).encode("utf-8")

        mock_urlopen.side_effect = [
            Exception("Blueprint failed"),  # First call fails
            MagicMock(__enter__=MagicMock(return_value=mock_response_direct))  # Second call succeeds
        ]

        router = TandemRouter(relay_url="http://mock-relay")
        result = router.route("solve universe life and everything", "fugu-ultra", "VibeThinker-3B")
        assert result == "Direct fallback answer"
