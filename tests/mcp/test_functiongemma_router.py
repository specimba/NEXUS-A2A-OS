"""Offline contract tests for the local FunctionGemma-compatible router."""

from __future__ import annotations

import json

from nexus_os.mcp.functiongemma_router import FunctionGemmaRouter, MINIMUM_CONFIDENCE


class _Response:
    def __init__(self, payload: dict, ok: bool = True):
        self._payload = payload
        self.ok = ok

    def json(self):
        return {"response": json.dumps(self._payload)}

    def raise_for_status(self):
        if not self.ok:
            raise RuntimeError("unexpected test response")


def _post_with(payload: dict):
    def post(*_args, **_kwargs):
        return _Response(payload)

    return post


def test_low_confidence_is_blocked_at_documented_admission_threshold(monkeypatch):
    monkeypatch.setattr(
        "nexus_os.mcp.functiongemma_router.requests.post",
        _post_with({"intent": "EXECUTION", "confidence": MINIMUM_CONFIDENCE - 0.01}),
    )

    result = FunctionGemmaRouter().classify("restart the relay")

    assert result == {
        "intent": "BLOCKED",
        "confidence": MINIMUM_CONFIDENCE - 0.01,
        "reasoning": "below_admission_threshold",
    }


def test_unknown_intent_and_invalid_confidence_fail_closed(monkeypatch):
    router = FunctionGemmaRouter()
    monkeypatch.setattr(
        "nexus_os.mcp.functiongemma_router.requests.post",
        _post_with({"intent": "PROMOTE", "confidence": 0.99}),
    )
    assert router.classify("promote model") == {
        "intent": "BLOCKED",
        "confidence": 0.0,
        "reasoning": "classification_error",
    }
    assert router._healthy is False

    monkeypatch.setattr(
        "nexus_os.mcp.functiongemma_router.requests.post",
        _post_with({"intent": "EXECUTION", "confidence": "nan"}),
    )
    assert router.classify("run") == {
        "intent": "BLOCKED",
        "confidence": 0.0,
        "reasoning": "classification_error",
    }


def test_governance_connector_runs_only_after_valid_high_confidence_classification(monkeypatch):
    class _Mcp:
        def __init__(self):
            self.calls = []

        def propose_skill(self, *args):
            self.calls.append(args)
            return {"status": "proposed"}

    mcp = _Mcp()
    monkeypatch.setattr(
        "nexus_os.mcp.functiongemma_router.requests.post",
        _post_with({"intent": "GOVERNANCE", "confidence": 0.91, "reasoning": "proposal"}),
    )

    result = FunctionGemmaRouter().route("propose a skill", mcp_engine=mcp)

    assert result["allowed"] is True
    assert result["action"] == "proposed_to_governance"
    assert len(mcp.calls) == 1


def test_route_rechecks_untrusted_classifier_shape_before_connectors(monkeypatch):
    class _Mcp:
        def propose_skill(self, *_args):
            raise AssertionError("unknown classifier output must never reach governance")

    router = FunctionGemmaRouter()
    monkeypatch.setattr(
        router,
        "classify",
        lambda _query: {"intent": "PROMOTE", "confidence": 0.99, "reasoning": "bad"},
    )

    result = router.route("promote model", mcp_engine=_Mcp())

    assert result["intent"] == "BLOCKED"
    assert result["allowed"] is False
    assert result["action"] == "blocked"
