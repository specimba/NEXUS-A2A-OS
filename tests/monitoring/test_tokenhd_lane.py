"""TokenHD supervised lane (nexus_os/monitoring/tokenhd_lane.py, papers10)."""
from __future__ import annotations

import pytest

from nexus_os.monitoring.calibrated_hallucination_detector import (
    CalibratedHallucinationDetector,
)
from nexus_os.monitoring.tokenhd_lane import (
    DEFAULT_FLAG_THRESHOLD,
    HTTPTokenHDClassifier,
    StubTokenHDClassifier,
    TokenHDUnavailable,
    assess_tokenhd,
    group_spans,
    resolve_classifier,
    risk_score_from_tokenhd,
)

CLEAN = ["The", " answer", " is", " four", "."]
MIXED = ["The", " area", " is", " <<HALLU>>7", " because", " <<HALLU>>math", "."]


# ------------------------------------------------------------ pure module


def test_group_spans_consecutive_and_gaps():
    assert group_spans([]) == []
    assert group_spans([3]) == [(3, 3)]
    assert group_spans([1, 2, 3, 7, 9, 10]) == [(1, 3), (7, 7), (9, 10)]


def test_assess_scores_every_token_and_flags_above_threshold():
    sig = assess_tokenhd("ctx", MIXED, StubTokenHDClassifier())
    assert len(sig.token_scores) == len(MIXED)
    assert sig.flagged_indices == [3, 5]
    assert sig.spans == [(3, 3), (5, 5)]
    assert sig.max_score == pytest.approx(0.9)
    assert sig.threshold == DEFAULT_FLAG_THRESHOLD


def test_assess_empty_tokens_is_zero_signal():
    sig = assess_tokenhd("ctx", [], StubTokenHDClassifier())
    assert sig.token_scores == []
    assert risk_score_from_tokenhd(sig) == 0.0


def test_assess_clamps_scores_into_unit_interval():
    class Wild:
        name = "wild"

        def score_tokens(self, context, tokens):
            return [-0.5, 1.7]

    sig = assess_tokenhd("ctx", ["a", "b"], Wild())
    assert sig.token_scores == [0.0, 1.0]


def test_assess_rejects_length_contract_violation():
    class Short:
        name = "short"

        def score_tokens(self, context, tokens):
            return [0.1]

    with pytest.raises(ValueError):
        assess_tokenhd("ctx", ["a", "b"], Short())


def test_risk_blends_peak_and_density():
    clean = assess_tokenhd("ctx", CLEAN, StubTokenHDClassifier())
    dirty = assess_tokenhd("ctx", MIXED, StubTokenHDClassifier())
    assert risk_score_from_tokenhd(clean) < 0.1
    assert risk_score_from_tokenhd(dirty) > 0.5
    assert risk_score_from_tokenhd(dirty) <= 1.0


def test_resolve_classifier_priority(monkeypatch):
    stub = StubTokenHDClassifier()
    assert resolve_classifier(stub) is stub
    monkeypatch.setenv("NEXUS_TOKENHD_ENDPOINT", "http://127.0.0.1:9/score")
    resolved = resolve_classifier(None)
    assert isinstance(resolved, HTTPTokenHDClassifier)
    assert resolved.endpoint == "http://127.0.0.1:9/score"
    monkeypatch.delenv("NEXUS_TOKENHD_ENDPOINT")
    assert resolve_classifier(None) is None


def test_http_classifier_fails_safe_as_unavailable():
    clf = HTTPTokenHDClassifier("http://127.0.0.1:9/score", timeout=0.2)
    with pytest.raises(TokenHDUnavailable):
        clf.score_tokens("ctx", ["a"])


# -------------------------------------------------------- CHD integration


def _detector(**kw):
    return CalibratedHallucinationDetector(adaptive=False, bebop_weight=0.0, **kw)


def test_lane_dark_by_default():
    d = _detector()
    result = d.assess(topk_probs=[0.5, 0.3, 0.2], token_text=" <<HALLU>>x")
    assert result["tokenhd"]["enabled"] is False
    assert result["tokenhd"]["risk"] == 0.0
    assert not any(r.startswith("tokenhd") for r in result["reasons"])
    assert d.get_stats()["tokenhd_contributions"] == 0


def test_lane_contributes_when_enabled_with_stub():
    d = _detector(tokenhd_weight=0.3, tokenhd_classifier=StubTokenHDClassifier())
    d.assess(topk_probs=[0.5, 0.3, 0.2], token_text="The", context_text="Q?")
    result = d.assess(topk_probs=[0.5, 0.3, 0.2], token_text=" <<HALLU>>7")
    assert result["tokenhd"]["enabled"] is True
    assert result["tokenhd"]["flagged"] == 1
    assert result["tokenhd"]["risk"] > 0.5
    assert any(r.startswith("tokenhd_flagged") for r in result["reasons"])
    assert result["score"] >= round(0.3 * result["tokenhd"]["risk"], 3) - 1e-3
    assert d.get_stats()["tokenhd_contributions"] == 1


def test_lane_clean_window_adds_nothing():
    d = _detector(tokenhd_weight=0.3, tokenhd_classifier=StubTokenHDClassifier())
    result = d.assess(topk_probs=[0.5, 0.3, 0.2], token_text="fine")
    assert result["tokenhd"]["flagged"] == 0
    assert not any(r.startswith("tokenhd") for r in result["reasons"])


def test_lane_fails_safe_on_classifier_error():
    class Broken:
        name = "broken"

        def score_tokens(self, context, tokens):
            raise TokenHDUnavailable("detector down")

    d = _detector(tokenhd_weight=0.3, tokenhd_classifier=Broken())
    result = d.assess(topk_probs=[0.5, 0.3, 0.2], token_text="x")
    assert result["risk"] == "low"
    assert result["tokenhd"]["risk"] == 0.0
    assert d.get_stats()["tokenhd_failures"] == 1


def test_reset_window_at_generation_boundary():
    d = _detector(tokenhd_weight=0.3, tokenhd_classifier=StubTokenHDClassifier())
    d.assess(token_text=" <<HALLU>>bad")
    d.reset_tokenhd_window(context_text="new question")
    result = d.assess(token_text="clean")
    assert result["tokenhd"]["flagged"] == 0
    assert d._tokenhd_context == "new question"


def test_weight_without_classifier_stays_dark(monkeypatch):
    monkeypatch.delenv("NEXUS_TOKENHD_ENDPOINT", raising=False)
    d = _detector(tokenhd_weight=0.3)
    result = d.assess(topk_probs=[0.5, 0.3, 0.2], token_text="x")
    assert result["tokenhd"]["enabled"] is False
    assert result["tokenhd"]["risk"] == 0.0
