"""tests/gmr/test_telemetry.py — ModelTelemetry and TelemetryIngest tests"""
import pytest
from unittest.mock import patch, MagicMock

from nexus_os.gmr.telemetry import ModelTelemetry, TelemetryIngest


class TestModelTelemetry:
    def _make(self, **overrides):
        defaults = dict(
            name="test-model", provider="ollama", tier=40,
            latency_ms=100, uptime_pct=1.0, status="up", timestamp="now",
        )
        defaults.update(overrides)
        return ModelTelemetry(**defaults)

    def test_quality_score_formula(self):
        tel = self._make(tier=80, uptime_pct=0.9)
        expected = 80 * 0.7 + (0.9 * 100) * 0.3
        assert tel.quality_score == expected

    def test_quality_score_tier_capped_at_100(self):
        tel = self._make(tier=150, uptime_pct=1.0)
        expected = 100 * 0.7 + 100 * 0.3
        assert tel.quality_score == expected

    def test_is_available_true(self):
        tel = self._make(status="up", uptime_pct=0.8)
        assert tel.is_available is True

    def test_is_available_false_when_down(self):
        tel = self._make(status="down", uptime_pct=0.9)
        assert tel.is_available is False

    def test_is_available_false_when_low_uptime(self):
        tel = self._make(status="up", uptime_pct=0.3)
        assert tel.is_available is False

    def test_is_local_ollama(self):
        tel = self._make(provider="ollama")
        assert tel.is_local is True

    def test_is_local_nvidia(self):
        tel = self._make(provider="nvidia")
        assert tel.is_local is False


class TestTelemetryIngest:
    def test_initial_cache_empty(self):
        ingest = TelemetryIngest(url="http://fake:9999")
        assert ingest.cache == {}
        assert ingest.last_fetch is None

    @patch("nexus_os.gmr.telemetry.requests.get")
    def test_fetch_populates_cache(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "models": [
                {"name": "m1", "provider": "ollama", "tier": 40,
                 "latency_ms": 50, "uptime": 1.0, "status": "up"},
            ]
        }
        mock_get.return_value = mock_resp
        ingest = TelemetryIngest(url="http://fake:9999")
        result = ingest.fetch()
        assert "m1" in result
        assert result["m1"].provider == "ollama"
        assert ingest.last_fetch is not None

    @patch("nexus_os.gmr.telemetry.requests.get")
    def test_fetch_updates_existing_entries(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "models": [
                {"name": "m1", "provider": "ollama", "tier": 80,
                 "latency_ms": 200, "uptime": 0.5, "status": "up"},
            ]
        }
        mock_get.return_value = mock_resp
        ingest = TelemetryIngest(url="http://fake:9999")
        ingest.fetch()
        assert ingest.cache["m1"].tier == 80
        assert ingest.cache["m1"].latency_ms == 200

    @patch("nexus_os.gmr.telemetry.requests.get", side_effect=Exception("net err"))
    def test_fetch_handles_network_error(self, mock_get):
        ingest = TelemetryIngest(url="http://fake:9999")
        result = ingest.fetch()
        assert result == {}
