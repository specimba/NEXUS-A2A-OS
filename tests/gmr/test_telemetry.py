"""tests/gmr/test_telemetry.py — ModelTelemetry and TelemetryIngest tests"""
import pytest
from unittest.mock import patch, MagicMock

from nexus_os.gmr.telemetry import ModelTelemetry, TelemetryIngest, default_catalogue_urls, parse_models_payload


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
    def test_default_urls_prefer_health_aware_model_arena_manifest(self):
        urls = default_catalogue_urls()
        assert urls[0] == "http://127.0.0.1:7356/api/client-manifest"
        assert "http://127.0.0.1:7350/v1/models" in urls

    def test_initial_cache_empty(self):
        ingest = TelemetryIngest(url="http://fake:9999")
        assert ingest.cache == {}
        assert ingest.last_fetch is None

    @patch("nexus_os.gmr.telemetry._http_json")
    def test_fetch_populates_cache(self, mock_get):
        mock_get.return_value = {
            "models": [
                {"name": "m1", "provider": "ollama", "tier": 40,
                 "latency_ms": 50, "uptime": 1.0, "status": "up"},
            ]
        }
        ingest = TelemetryIngest(url="http://fake:9999")
        result = ingest.fetch()
        assert "m1" in result
        assert result["m1"].provider == "ollama"
        assert ingest.last_fetch is not None

    @patch("nexus_os.gmr.telemetry._http_json")
    def test_fetch_updates_existing_entries(self, mock_get):
        mock_get.return_value = {
            "models": [
                {"name": "m1", "provider": "ollama", "tier": 80,
                 "latency_ms": 200, "uptime": 0.5, "status": "up"},
            ]
        }
        ingest = TelemetryIngest(url="http://fake:9999")
        ingest.fetch()
        assert ingest.cache["m1"].tier == 80
        assert ingest.cache["m1"].latency_ms == 200

    @patch("nexus_os.gmr.telemetry._http_json", side_effect=Exception("net err"))
    def test_fetch_handles_network_error(self, mock_get):
        ingest = TelemetryIngest(url="http://fake:9999")
        result = ingest.fetch()
        assert result == {}


def test_parse_model_arena_manifest_requires_fresh_observed_health_for_availability():
    payload = {
        "contract": {"source": "nexus-model-arena-live-projection"},
        "models": [
            {
                "id": "fresh-code",
                "provider": "opencode",
                "health": {"state": "healthy", "observed": True, "fresh": True, "latency_ms": 123},
                "benchmarks": {"dimensions": {"quality": 0.81}},
            },
            {
                "id": "stale-model",
                "provider": "nvidia",
                "health": {"state": "stale", "observed": True, "fresh": False, "latency_ms": 456},
                "benchmarks": {"dimensions": {"quality": 0.9}},
            },
            {
                "id": "unverified-model",
                "provider": "nvidia",
                "health": {"state": "unverified", "observed": False, "fresh": False},
                "benchmarks": {"dimensions": {}},
            },
        ],
    }

    models = parse_models_payload(payload, timestamp="now")
    assert models["fresh-code"].is_available is True
    assert models["fresh-code"].tier == 81
    assert models["stale-model"].status == "stale"
    assert models["stale-model"].is_available is False
    assert models["unverified-model"].status == "unverified"
    assert models["unverified-model"].is_available is False


# ─────────────────────────────────────────────────────────────────────────
# Seam 2: routing-decision telemetry sink (record_routing_decision)
# ─────────────────────────────────────────────────────────────────────────

import asyncio
import json
import logging

from nexus_os.gmr import telemetry as gmr_telemetry
from nexus_os.gmr.telemetry import (
    ROUTING_SCHEMA_FIELDS,
    ROUTING_SCHEMA_VERSION,
    record_routing_decision,
)


def _read_records(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


class TestRecordRoutingDecision:
    def test_schema_v1_fields_always_present(self, tmp_path, monkeypatch):
        sink = tmp_path / "gmr_telemetry.jsonl"
        monkeypatch.setenv("NEXUS_GMR_TELEMETRY", str(sink))
        record_routing_decision({
            "source": "relay-auto-gmr",
            "task_id": "task-1",
            "coger_level": "L2",
            "quality_target": 0.82,
            "latency_budget_ms": 8000,
            "chosen_model": "qwen2.5-3b-instruct-q4_k_m",
            "candidate_count": 3,
            "chimera_quality_score": 0.62,
            "lg_verdict": {"risk_level": "low"},
            "outcome": "success",
        })
        records = _read_records(sink)
        assert len(records) == 1
        rec = records[0]
        assert rec["schema_version"] == ROUTING_SCHEMA_VERSION == 1
        for field in ROUTING_SCHEMA_FIELDS:
            assert field in rec, field
        assert rec["ts"]
        assert rec["source"] == "relay-auto-gmr"
        assert rec["coger_level"] == "L2"
        assert rec["lg_verdict"] == {"risk_level": "low"}
        assert rec["outcome"] == "success"

    def test_missing_fields_recorded_as_null(self, tmp_path, monkeypatch):
        sink = tmp_path / "t.jsonl"
        monkeypatch.setenv("NEXUS_GMR_TELEMETRY", str(sink))
        record_routing_decision({"source": "coger"})
        rec = _read_records(sink)[0]
        for field in ROUTING_SCHEMA_FIELDS:
            assert field in rec, field
        assert rec["chosen_model"] is None
        assert rec["lg_verdict"] is None
        assert rec["outcome"] is None

    def test_extra_fields_pass_through(self, tmp_path, monkeypatch):
        sink = tmp_path / "t.jsonl"
        monkeypatch.setenv("NEXUS_GMR_TELEMETRY", str(sink))
        record_routing_decision({"source": "chimera", "phase": "decision", "strategy": "Tandem Routing"})
        rec = _read_records(sink)[0]
        assert rec["phase"] == "decision"
        assert rec["strategy"] == "Tandem Routing"

    def test_append_only(self, tmp_path, monkeypatch):
        sink = tmp_path / "t.jsonl"
        monkeypatch.setenv("NEXUS_GMR_TELEMETRY", str(sink))
        record_routing_decision({"source": "coger", "outcome": "success"})
        record_routing_decision({"source": "chimera", "outcome": "error"})
        records = _read_records(sink)
        assert [r["source"] for r in records] == ["coger", "chimera"]

    def test_failsafe_swallows_sink_errors(self, tmp_path, monkeypatch):
        # A directory at the sink path makes the append-open fail.
        sink = tmp_path / "sink_is_a_dir"
        sink.mkdir()
        monkeypatch.setenv("NEXUS_GMR_TELEMETRY", str(sink))
        record_routing_decision({"source": "coger"})  # must not raise

    def test_failsafe_swallows_non_dict_event(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NEXUS_GMR_TELEMETRY", str(tmp_path / "t.jsonl"))
        record_routing_decision(None)  # must not raise
        record_routing_decision("not-a-dict")  # must not raise

    def test_failsafe_warns_once(self, tmp_path, monkeypatch, caplog):
        monkeypatch.setattr(gmr_telemetry, "_routing_warned", False)
        sink = tmp_path / "sink_is_a_dir"
        sink.mkdir()
        monkeypatch.setenv("NEXUS_GMR_TELEMETRY", str(sink))
        with caplog.at_level(logging.WARNING, logger="nexus.gmr.telemetry"):
            record_routing_decision({"source": "coger"})
            record_routing_decision({"source": "coger"})
        warnings = [r for r in caplog.records if "telemetry sink failed" in r.getMessage()]
        assert len(warnings) == 1

    def test_disabled_via_env(self, monkeypatch):
        for value in ("off", "0", "none", "disabled", "false"):
            monkeypatch.setenv("NEXUS_GMR_TELEMETRY", value)
            assert gmr_telemetry._routing_telemetry_path() is None
            record_routing_decision({"source": "coger"})  # silent no-op

    def test_default_path_honors_nexus_home(self, tmp_path, monkeypatch):
        monkeypatch.delenv("NEXUS_GMR_TELEMETRY", raising=False)
        monkeypatch.setenv("NEXUS_HOME", str(tmp_path))
        path = gmr_telemetry._routing_telemetry_path()
        assert path == tmp_path / "gmr_telemetry.jsonl"

    def test_default_path_under_home(self, monkeypatch):
        monkeypatch.delenv("NEXUS_GMR_TELEMETRY", raising=False)
        monkeypatch.delenv("NEXUS_HOME", raising=False)
        path = gmr_telemetry._routing_telemetry_path()
        assert path is not None
        assert path.name == "gmr_telemetry.jsonl"
        assert path.parent.name == ".nexus"

    def test_rotation_triggers_at_size_guard(self, tmp_path, monkeypatch):
        sink = tmp_path / "t.jsonl"
        monkeypatch.setenv("NEXUS_GMR_TELEMETRY", str(sink))
        monkeypatch.setattr(gmr_telemetry, "ROTATE_MAX_BYTES", 128)
        sink.write_text("x" * 200, encoding="utf-8")
        record_routing_decision({"source": "chimera", "outcome": "success"})
        rotated = tmp_path / "t.jsonl.1"
        assert rotated.exists()
        assert rotated.stat().st_size == 200
        records = _read_records(sink)  # fresh file holds only the new record
        assert len(records) == 1

    def test_rotation_replaces_previous_dot1(self, tmp_path, monkeypatch):
        sink = tmp_path / "t.jsonl"
        rotated = tmp_path / "t.jsonl.1"
        monkeypatch.setenv("NEXUS_GMR_TELEMETRY", str(sink))
        monkeypatch.setattr(gmr_telemetry, "ROTATE_MAX_BYTES", 128)
        rotated.write_text("old rotation", encoding="utf-8")
        sink.write_text("y" * 200, encoding="utf-8")
        record_routing_decision({"source": "chimera"})
        assert rotated.read_text(encoding="utf-8") == "y" * 200

    def test_no_rotation_below_size_guard(self, tmp_path, monkeypatch):
        sink = tmp_path / "t.jsonl"
        monkeypatch.setenv("NEXUS_GMR_TELEMETRY", str(sink))
        record_routing_decision({"source": "coger"})
        record_routing_decision({"source": "coger"})
        assert not (tmp_path / "t.jsonl.1").exists()
        assert len(_read_records(sink)) == 2


class TestCallSiteSmoke:
    """Call-site smoke: exercise the routed functions and assert a record is
    emitted on a routed decision, with the actual model calls mocked out."""

    @pytest.fixture
    def captured(self, monkeypatch, tmp_path):
        events = []
        monkeypatch.setattr(gmr_telemetry, "record_routing_decision",
                            lambda event: events.append(event))
        # Belt-and-braces: if any code path bypasses the monkeypatch, keep
        # writes away from the real home sink.
        monkeypatch.setenv("NEXUS_GMR_TELEMETRY", str(tmp_path / "sink.jsonl"))
        return events

    def test_coger_route_emits_outcome_record(self, captured, monkeypatch):
        from nexus_os.gmr.coger import CogER
        monkeypatch.setattr(CogER, "_call_direct_slm", lambda self, q: "4")
        result = CogER().route("2+2?", level="L1")
        assert result["level"] == "L1"
        events = [e for e in captured if e.get("source") == "coger"]
        assert len(events) == 1
        assert events[0]["coger_level"] == "L1"
        assert events[0]["strategy"] == "Direct SLM"
        assert events[0]["outcome"] == "success"

    def test_coger_route_records_error_outcome(self, captured, monkeypatch):
        from nexus_os.gmr.coger import CogER
        monkeypatch.setattr(CogER, "_call_direct_slm", lambda self, q: "")
        CogER().route("2+2?", level="L1")
        events = [e for e in captured if e.get("source") == "coger"]
        assert events[0]["outcome"] == "error"

    def test_chimera_route_emits_selection_record(self, captured):
        from nexus_os.twave.chimera_router_v2 import ChimeraRouterV2
        router = ChimeraRouterV2()
        decision = router.route("hello world", latency_budget_ms=2000.0, quality_target=0.6)
        events = [e for e in captured if e.get("source") == "chimera"]
        assert len(events) == 1
        ev = events[0]
        assert ev["chosen_model"] == decision.model
        assert ev["candidate_count"] >= 1
        assert ev["chimera_quality_score"] == decision.expected_quality
        assert ev["quality_target"] == 0.6
        assert ev["outcome"] == "success"

    @staticmethod
    def _mock_ollama(monkeypatch, model_relay):
        class _Resp:
            ok = True

            def raise_for_status(self):
                pass

            def json(self):
                return {
                    "choices": [{"message": {"content": "ok"}}],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                }

        monkeypatch.setattr(model_relay.requests, "post",
                            lambda url, json=None, timeout=None: _Resp())

    def test_relay_auto_gmr_emits_decision_and_response_records(self, captured, monkeypatch):
        from nexus_os.relay import model_relay
        self._mock_ollama(monkeypatch, model_relay)
        relay = model_relay.ModelRelay()
        result = asyncio.run(relay.proxy_completion({
            "model": "auto-gmr",
            "messages": [{"role": "user", "content": "2+2?"}],  # CogER L1 -> Chimera path
            "task_id": "task-telemetry-smoke",
        }))
        assert result["relay_info"]["gmr_level"] == "L1"
        relay_events = [e for e in captured if e.get("source") == "relay-auto-gmr"]
        phases = [e.get("phase") for e in relay_events]
        assert "decision" in phases
        assert "response" in phases
        decision_ev = next(e for e in relay_events if e["phase"] == "decision")
        assert decision_ev["coger_level"] == "L1"
        assert decision_ev["task_id"] == "task-telemetry-smoke"
        assert decision_ev["chosen_model"]
        q, lat = model_relay.ModelRelay.GMR_LEVEL_TARGETS["L1"]
        assert decision_ev["quality_target"] == q
        assert decision_ev["latency_budget_ms"] == lat
        response_ev = next(e for e in relay_events if e["phase"] == "response")
        assert response_ev["outcome"] in ("success", "fallback")
        assert response_ev["chosen_model"]

    def test_plain_auto_emits_no_relay_gmr_records(self, captured, monkeypatch):
        from nexus_os.relay import model_relay
        self._mock_ollama(monkeypatch, model_relay)
        relay = model_relay.ModelRelay()
        asyncio.run(relay.proxy_completion({
            "model": "auto",
            "messages": [{"role": "user", "content": "2+2?"}],
        }))
        assert [e for e in captured if e.get("source") == "relay-auto-gmr"] == []
        # The Chimera choke point still records for plain auto.
        assert [e for e in captured if e.get("source") == "chimera"]

    def test_relay_survives_raising_telemetry_writer(self, captured, monkeypatch):
        from nexus_os.relay import model_relay

        def boom(event):
            raise RuntimeError("sink exploded")

        monkeypatch.setattr(gmr_telemetry, "record_routing_decision", boom)
        self._mock_ollama(monkeypatch, model_relay)
        relay = model_relay.ModelRelay()
        result = asyncio.run(relay.proxy_completion({
            "model": "auto-gmr",
            "messages": [{"role": "user", "content": "2+2?"}],
        }))
        assert result["choices"][0]["message"]["content"] == "ok"
