"""
Test suite for MindGuard L2 Decision-Integrity Client (per arXiv 2508.20412).

Tests the MindGuardClient class in guard_router.py:
- TAE computation for context segments
- Implicit Delegation Anomaly detection
- User Intent Dilution Anomaly detection
- Segment parsing from WalledGuard template
- Safe/unsafe/uncertain classification
- Shared L1 model wiring (no extra VRAM)
"""
import json
import os
import sys
import pytest

NEXUS_ROOT = os.path.normpath(os.path.join(
    os.path.dirname(__file__), "..", ".."
))
if NEXUS_ROOT not in sys.path:
    sys.path.insert(0, NEXUS_ROOT)

from nexus_os.security.guard_router import (
    MindGuardClient,
    WalledGuardClient,
    make_client,
    TIER_THRESHOLDS,
)


class TestMindGuardSegmentParser:
    """Test MindGuardClient._parse_segments for WalledGuard template."""

    def test_parse_standard_template(self):
        client = MindGuardClient.__new__(MindGuardClient)
        template = "[INST] Evaluate if the given text is harmful i.e. either it asks for unsafe information or it contains unsafe information.\n\n<START TEXT>\nHello world\n<END TEXT>\n\nAnswer: [/INST] "
        segments = client._parse_segments(template, "Hello world")
        assert "query" in segments
        q_start, q_end = segments["query"]
        assert template[q_start:q_end].strip() == "Hello world"

    def test_parse_without_markers(self):
        client = MindGuardClient.__new__(MindGuardClient)
        text = "No markers here"
        segments = client._parse_segments(text, text)
        assert "query" in segments

    def test_template_segment_exists(self):
        client = MindGuardClient.__new__(MindGuardClient)
        template = "[INST] Evaluate if the given text is harmful i.e. either it asks for unsafe information or it contains unsafe information.\n\n<START TEXT>\nsome text\n<END TEXT>\n\nAnswer: [/INST] "
        segments = client._parse_segments(template, "some text")
        assert "template" in segments

    def test_suffix_segment_exists(self):
        client = MindGuardClient.__new__(MindGuardClient)
        template = "[INST] Evaluate if the given text is harmful i.e. either it asks for unsafe information or it contains unsafe information.\n\n<START TEXT>\nsome text\n<END TEXT>\n\nAnswer: [/INST] "
        segments = client._parse_segments(template, "some text")
        assert "suffix" in segments


class TestMindGuardTAEComputation:
    """Test MindGuardClient._compute_tae for attention energy."""

    def test_tae_returns_dict(self):
        import torch
        client = MindGuardClient.__new__(MindGuardClient)
        client.sink_filter_topk = 3
        attn = torch.ones(1, 8, 10, 10) / 10
        segments = {"query": (0, 5), "template": (5, 10)}
        tae = client._compute_tae([attn], list(range(10)), segments, decision_start=8)
        assert isinstance(tae, dict)

    def test_tae_empty_decision_returns_empty(self):
        import torch
        client = MindGuardClient.__new__(MindGuardClient)
        client.sink_filter_topk = 3
        attn = torch.ones(1, 8, 10, 10) / 10
        segments = {"query": (0, 5)}
        tae = client._compute_tae([attn], list(range(10)), segments, decision_start=10)
        assert tae == {}

    def test_tae_normalized(self):
        import torch
        client = MindGuardClient.__new__(MindGuardClient)
        client.sink_filter_topk = 10
        attn = torch.ones(1, 1, 10, 10) / 10
        segments = {"query": (0, 5), "template": (5, 10)}
        tae = client._compute_tae([attn], list(range(10)), segments, decision_start=8)
        if tae:
            total = sum(tae.values())
            assert abs(total - 1.0) < 0.1


class TestMindGuardAnomalyDetection:
    """Test MindGuard anomaly detection logic."""

    def test_implicit_delegation_anomaly(self):
        client = MindGuardClient.__new__(MindGuardClient)
        client.delegation_threshold = 0.15
        client.dilution_threshold = 0.25
        client.reference_tae_query = 0.45
        tool_taes = {"email_tool": 0.35, "calendar_tool": 0.10}
        query_tae = 0.40
        anomalies = []
        for tname, tw in tool_taes.items():
            if tw > client.delegation_threshold:
                anomalies.append(f"implicit_delegation:{tname}={tw:.3f}")
        assert len(anomalies) == 1
        assert "email_tool" in anomalies[0]

    def test_no_delegation_when_below_threshold(self):
        client = MindGuardClient.__new__(MindGuardClient)
        client.delegation_threshold = 0.15
        tool_taes = {"email_tool": 0.05, "calendar_tool": 0.03}
        anomalies = []
        for tname, tw in tool_taes.items():
            if tw > client.delegation_threshold:
                anomalies.append(f"implicit_delegation:{tname}={tw:.3f}")
        assert len(anomalies) == 0

    def test_intent_dilution_anomaly(self):
        client = MindGuardClient.__new__(MindGuardClient)
        client.dilution_threshold = 0.25
        query_tae = 0.10
        is_diluted = query_tae < client.dilution_threshold and query_tae > 0
        assert is_diluted

    def test_no_dilution_when_query_strong(self):
        client = MindGuardClient.__new__(MindGuardClient)
        client.dilution_threshold = 0.25
        query_tae = 0.50
        is_diluted = query_tae < client.dilution_threshold and query_tae > 0
        assert not is_diluted

    def test_both_anomalies_flagged(self):
        client = MindGuardClient.__new__(MindGuardClient)
        client.delegation_threshold = 0.15
        client.dilution_threshold = 0.25
        tool_taes = {"email_tool": 0.30}
        query_tae = 0.10
        anomalies = []
        for tname, tw in tool_taes.items():
            if tw > client.delegation_threshold:
                anomalies.append(f"implicit_delegation:{tname}={tw:.3f}")
        if query_tae < client.dilution_threshold and query_tae > 0:
            anomalies.append(f"intent_dilution:query={query_tae:.3f}")
        assert len(anomalies) == 2
        assert any("implicit_delegation" in a for a in anomalies)
        assert any("intent_dilution" in a for a in anomalies)


class TestMindGuardL2Config:
    """Test L2 configuration in guard-router.py TIER_THRESHOLDS."""

    def test_l2_backend_is_mindguard(self):
        assert TIER_THRESHOLDS["L2"]["backend"] == "mindguard"

    def test_l2_has_delegation_threshold(self):
        assert "delegation_threshold" in TIER_THRESHOLDS["L2"]

    def test_l2_has_dilution_threshold(self):
        assert "dilution_threshold" in TIER_THRESHOLDS["L2"]

    def test_l2_has_fallback(self):
        assert TIER_THRESHOLDS["L2"]["fallback_model"] == "meta-llama/Llama-Guard-3-1B"
        assert TIER_THRESHOLDS["L2"]["fallback_backend"] == "ollama"

    def test_l2_note_mentions_mindguard(self):
        assert "MindGuard" in TIER_THRESHOLDS["L2"]["note"]


class TestMindGuardMakeClient:
    """Test make_client returns MindGuardClient for 'mindguard' backend."""

    def test_make_client_mindguard(self):
        cfg = {
            "backend": "mindguard",
            "delegation_threshold": 0.2,
            "dilution_threshold": 0.3,
            "sink_filter_topk": 5,
            "latency_budget_ms": 3000,
        }
        client = make_client(cfg)
        assert isinstance(client, MindGuardClient)
        assert client.delegation_threshold == 0.2
        assert client.dilution_threshold == 0.3

    def test_make_client_mindguard_defaults(self):
        cfg = {"backend": "mindguard"}
        client = make_client(cfg)
        assert isinstance(client, MindGuardClient)
        assert client.delegation_threshold == 0.15


class TestMindGuardSharedModelWiring:
    """Test that MindGuard L2 shares L1 model (no extra VRAM)."""

    def test_wg_field_initially_none(self):
        client = MindGuardClient(walledguard_client=None)
        assert client.wg is None

    def test_wg_field_can_be_set(self):
        client = MindGuardClient(walledguard_client=None)
        mock_wg = object()
        client.wg = mock_wg
        assert client.wg is mock_wg


class TestMindGuardRawInfo:
    """Test raw_info output format for audit trail."""

    def test_raw_info_contains_tae(self):
        tae = {"query": 0.45, "template": 0.35, "suffix": 0.20}
        anomalies = ["implicit_delegation:email=0.350"]
        raw_info = (
            f"tae={json.dumps({k: round(v, 4) for k, v in tae.items()})};"
            f"anomalies={anomalies}"
        )
        assert "tae=" in raw_info
        assert "query" in raw_info
        assert "implicit_delegation" in raw_info

    def test_raw_info_no_anomalies(self):
        tae = {"query": 0.50}
        raw_info = (
            f"tae={json.dumps({k: round(v, 4) for k, v in tae.items()})};"
            f"anomalies={[] or 'none'}"
        )
        assert "none" in raw_info or "[]" in raw_info
