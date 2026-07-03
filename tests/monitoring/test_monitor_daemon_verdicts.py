"""tests/monitoring/test_monitor_daemon_verdicts.py — P2-7: monitor daemon
consumes real relay hallucination verdicts and emits A2A alerts."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from nexus_os.monitor_daemon import MonitorDaemon


@pytest.fixture
def fake_home(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".nexus").mkdir()
    return tmp_path


def _write_verdicts(home: Path, verdicts: list[dict], mode: str = "w"):
    path = home / ".nexus" / "hallucination_verdicts.jsonl"
    with open(path, mode, encoding="utf-8") as f:
        for v in verdicts:
            f.write(json.dumps(v) + "\n")
    return path


HIGH = {"risk_level": "high", "risk_score": 0.91, "reasons": ["epr_critical"],
        "ts": "2026-07-03T10:00:00+00:00", "model": "qwen3:8b"}
MEDIUM = {"risk_level": "medium", "risk_score": 0.55, "reasons": ["epr_high"],
          "ts": "2026-07-03T10:01:00+00:00", "model": "qwen3:8b"}


class _StubBus:
    published: list[dict] = []

    def publish(self, channel_id, sender, message, topic, **kw):
        _StubBus.published.append({
            "channel_id": channel_id, "sender": sender,
            "message": json.loads(message), "topic": topic,
        })


@pytest.fixture
def stub_bus(monkeypatch):
    _StubBus.published = []
    import nexus_os.bridge.a2a_channels as a2a
    monkeypatch.setattr(a2a, "A2AChannelBus", _StubBus)
    return _StubBus


class TestConsumeRelayVerdicts:
    def test_tail_reads_only_new_entries(self, fake_home):
        daemon = MonitorDaemon()
        path = _write_verdicts(fake_home, [HIGH, MEDIUM])
        first = daemon._consume_relay_verdicts()
        assert len(first) == 2
        # File is NOT truncated — the relay owns it
        assert path.stat().st_size > 0
        # Nothing new → nothing returned
        assert daemon._consume_relay_verdicts() == []
        # Append one more; only the new entry comes back
        _write_verdicts(fake_home, [HIGH], mode="a")
        second = daemon._consume_relay_verdicts()
        assert len(second) == 1

    def test_rotation_resets_offset(self, fake_home):
        daemon = MonitorDaemon()
        _write_verdicts(fake_home, [HIGH, MEDIUM, HIGH])
        assert len(daemon._consume_relay_verdicts()) == 3
        # Relay rotation rewrites the file smaller
        _write_verdicts(fake_home, [MEDIUM])
        assert len(daemon._consume_relay_verdicts()) == 1

    def test_missing_file(self, fake_home):
        assert MonitorDaemon()._consume_relay_verdicts() == []

    def test_malformed_lines_skipped(self, fake_home):
        path = fake_home / ".nexus" / "hallucination_verdicts.jsonl"
        path.write_text(json.dumps(HIGH) + "\nnot-json\n", encoding="utf-8")
        verdicts = MonitorDaemon()._consume_relay_verdicts()
        assert len(verdicts) == 1


class TestHallucinationAlerts:
    def test_injected_high_risk_verdict_emits_a2a_alert(self, fake_home, stub_bus):
        """P2-7 gate: injected high-entropy verdict → alert emitted."""
        daemon = MonitorDaemon(a2a_channel="monitor-alerts")
        _write_verdicts(fake_home, [HIGH])
        result = daemon._run_hallucination_check()
        assert result["ok"] is True
        assert result["result"]["alert_count"] == 1
        assert len(stub_bus.published) == 1
        alert = stub_bus.published[0]
        assert alert["channel_id"] == "monitor-alerts"
        assert alert["topic"] == "hallucination"
        assert alert["message"]["type"] == "hallucination-alert"
        assert alert["message"]["risk_level"] == "high"
        assert alert["message"]["model"] == "qwen3:8b"

    def test_low_risk_only_no_alert(self, fake_home, stub_bus):
        daemon = MonitorDaemon(a2a_channel="monitor-alerts")
        _write_verdicts(fake_home, [{"risk_level": "low", "risk_score": 0.02,
                                     "reasons": [], "ts": "t", "model": "m"}])
        result = daemon._run_hallucination_check()
        assert result["ok"] is True
        assert result["result"]["alert_count"] == 0
        assert stub_bus.published == []

    def test_no_channel_no_emit(self, fake_home, stub_bus):
        daemon = MonitorDaemon(a2a_channel=None)
        _write_verdicts(fake_home, [HIGH])
        result = daemon._run_hallucination_check()
        assert result["ok"] is True
        assert stub_bus.published == []


class TestBreakerSync:
    """P2-4 seam: relay breaker state file → GMR breaker via the daemon."""

    def test_relay_open_providers_open_gmr_breaker(self, fake_home, tmp_path, monkeypatch):
        # sync_from_relay resolves ~ via expanduser, not Path.home()
        monkeypatch.setenv("USERPROFILE", str(fake_home))
        monkeypatch.setenv("HOME", str(fake_home))
        # Relay server persisted an OPEN provider
        relay_state = fake_home / ".modelrelay.circuit.json"
        relay_state.write_text(json.dumps({
            "nvidia": {"state": "open", "failure_count": 3},
        }), encoding="utf-8")
        # Keep the GMR breaker's own persistence in the fake home too
        import nexus_os.gmr.circuit_breaker as gcb
        monkeypatch.setattr(gcb, "CIRCUIT_STATE_FILE", fake_home / ".gmr_circuit.json")
        daemon = MonitorDaemon()
        result = daemon._run_breaker_sync()
        assert result["ok"] is True
        assert result["result"]["synced"] is True
        assert "nvidia" in result["result"]["dead_providers"]
        assert result["result"]["gmr_state"] == "open"

    def test_no_relay_state_is_clean_noop(self, fake_home, monkeypatch):
        import nexus_os.gmr.circuit_breaker as gcb
        monkeypatch.setattr(gcb, "CIRCUIT_STATE_FILE", fake_home / ".gmr_circuit.json")
        daemon = MonitorDaemon()
        result = daemon._run_breaker_sync()
        assert result["ok"] is True
        assert result["result"]["synced"] is False
        assert result["result"]["reason"] == "relay_state_not_found"


class TestRelayBreakerPersistDefault:
    def test_persist_resolves_from_env(self, monkeypatch, fake_home):
        from nexus_os.relay.circuit_breaker import ProviderCircuitBreaker
        monkeypatch.delenv("RELAY_BREAKER_PERSIST", raising=False)
        assert ProviderCircuitBreaker().persist is False  # library default
        monkeypatch.setenv("RELAY_BREAKER_PERSIST", "1")
        assert ProviderCircuitBreaker().persist is True   # server default
        assert ProviderCircuitBreaker(persist=False).persist is False  # explicit wins
