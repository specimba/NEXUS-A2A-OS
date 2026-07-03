"""tests/gmr/test_peer_review.py — judge attribution in flipped-triple scoring (P2-3)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from nexus_os.gmr.peer_review import LLMPeerReview


class TestJudgeAttribution:
    """Scores carry an explicit judge index. The old positional
    re-partition (k % num_judges) scrambled attribution: each judge
    appends two consecutive scores per triplet, and a failed judge call
    shifts the whole sequence."""

    def test_pairs_carry_correct_judge_even_when_one_judge_fails(self, monkeypatch):
        pr = LLMPeerReview(judges=["judge-a", "judge-b"])

        def fake_call(self, judge, prompt, a, b, c):
            if judge == "judge-b":
                return None  # failed judge used to shift positional attribution
            return (4.0, 3.0, 2.0)

        monkeypatch.setattr(LLMPeerReview, "_call_judge", fake_call)
        scores = pr.flipped_triple_scoring("q", ["c0", "c1", "c2"])
        all_pairs = [p for lst in scores.values() for p in lst]
        assert all_pairs, "expected scores from the working judge"
        # Every recorded score must be attributed to judge 0 (judge-a)
        assert {j for j, _ in all_pairs} == {0}

    def test_both_judges_attributed_distinctly(self, monkeypatch):
        pr = LLMPeerReview(judges=["judge-a", "judge-b"])

        def fake_call(self, judge, prompt, a, b, c):
            return (5.0, 5.0, 5.0) if judge == "judge-a" else (1.0, 1.0, 1.0)

        monkeypatch.setattr(LLMPeerReview, "_call_judge", fake_call)
        scores = pr.flipped_triple_scoring("q", ["c0", "c1", "c2"])
        for pairs in scores.values():
            for j_idx, val in pairs:
                expected = 5.0 if j_idx == 0 else 1.0
                assert val == expected, (
                    f"judge {j_idx} attributed a score of {val}; attribution scrambled"
                )

    def test_select_best_weighted_end_to_end(self, monkeypatch):
        pr = LLMPeerReview(judges=["judge-a", "judge-b"])

        def fake_call(self, judge, prompt, a, b, c):
            # Both judges consistently prefer whichever slot holds "good"
            return tuple(4.5 if "good" in cand else 2.0 for cand in (a, b, c))

        monkeypatch.setattr(LLMPeerReview, "_call_judge", fake_call)
        best, idx = pr.select_best("q", ["bad answer", "good answer", "meh answer"],
                                   use_weighted=True)
        assert idx == 1
        assert best == "good answer"

    def test_simple_average_path_unpacks_pairs(self, monkeypatch):
        pr = LLMPeerReview(judges=["judge-a"])

        def fake_call(self, judge, prompt, a, b, c):
            return tuple(4.5 if "good" in cand else 2.0 for cand in (a, b, c))

        monkeypatch.setattr(LLMPeerReview, "_call_judge", fake_call)
        best, idx = pr.select_best("q", ["bad", "good", "meh"], use_weighted=False)
        assert idx == 1

    def test_heuristic_fallback_when_all_judges_fail(self, monkeypatch):
        pr = LLMPeerReview(judges=["judge-a", "judge-b"])
        monkeypatch.setattr(LLMPeerReview, "_call_judge",
                            lambda self, *a, **k: None)
        substantive = (
            "A detailed, structured answer covering the mechanism, edge cases, "
            "and a worked example with clear reasoning throughout the response."
        )
        best, idx = pr.select_best("q", ["", substantive], use_weighted=True)
        assert idx == 1
