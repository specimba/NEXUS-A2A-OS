"""tests/nexusclaw/test_heavyskill_relay.py — HeavySkill ModelRelay adapter tests"""

import pytest
from nexus_os.nexusclaw.heavyskill_relay import (
    ModelRelayHeavySkill,
    TrajectoryScore,
    SynthesisOutput,
    TRAJECTORY_EMPHASES,
    SCORING_SYSTEM_PROMPT,
    SYNTHESIS_SYSTEM_PROMPT,
    get_heavy_relay,
)


@pytest.fixture
def relay():
    return ModelRelayHeavySkill(relay_url="http://127.0.0.1:1", timeout=1.0)


class TestModelRelayHeavySkill:
    def test_check_availability_unreachable(self, relay):
        assert relay.check_availability() is False
        assert relay._available is False

    def test_reset_availability(self, relay):
        relay.check_availability()
        assert relay._available is False
        relay.reset_availability()
        assert relay._available is None

    def test_availability_cached(self, relay):
        relay._available = True
        assert relay.check_availability() is True

    def test_generate_trajectory_returns_none_when_unavailable(self, relay):
        result = relay.generate_trajectory("title", "desc", ["ref1"], "emphasis")
        assert result is None

    def test_generate_trajectories_list(self, relay):
        results = relay.generate_trajectories("title", "desc", ["ref1"], k=4)
        assert len(results) == 4
        assert all(r is None for r in results)  # All failed due to unavailable relay

    def test_score_trajectory_returns_none_when_unavailable(self, relay):
        result = relay.score_trajectory("some reasoning text")
        assert result is None

    def test_score_trajectories_with_fallback(self, relay):
        texts = ["traj1", "traj2"]
        ids = ["t1", "t2"]
        scores = relay.score_trajectories(texts, ids)
        assert len(scores) == 2
        for s in scores:
            assert 0.0 <= s.score <= 1.0
            assert isinstance(s.trajectory_id, str)

    def test_synthesize_returns_none_when_unavailable(self, relay):
        result = relay.synthesize("title", "desc", ["t1"], [TrajectoryScore("t1", 0.7)])
        assert result is None


class TestMockFallback:
    def test_generate_mock_trajectory(self, relay):
        text = relay.generate_mock_trajectory(
            "agent1", "Proposal Title", "description", ["ref1"],
            trust_score=75.0, index=0, k=8,
        )
        assert "[Trajectory 1/8 by agent1]" in text
        assert "Proposal Title" in text
        assert TRAJECTORY_EMPHASES[0] in text

    def test_mock_trajectory_cycles_emphasis(self, relay):
        t0 = relay.generate_mock_trajectory("a", "t", "d", [], 50, 0, 8)
        t7 = relay.generate_mock_trajectory("a", "t", "d", [], 50, 7, 8)
        assert TRAJECTORY_EMPHASES[0] in t0
        assert TRAJECTORY_EMPHASES[7] in t7

    def test_mock_trajectory_wraps_emphasis(self, relay):
        # index > len(emphases) should wrap around
        t8 = relay.generate_mock_trajectory("a", "t", "d", [], 50, 8, 8)
        assert TRAJECTORY_EMPHASES[0] in t8  # wraps to first

    def test_score_mock_variation(self, relay):
        s0 = relay.score_mock(80.0, 0)
        s1 = relay.score_mock(80.0, 1)
        assert s0 != s1  # Different indices produce different scores

    def test_score_mock_bounds(self, relay):
        for trust in [0, 50, 100]:
            for i in range(8):
                s = relay.score_mock(trust, i)
                assert 0.1 <= s <= 0.99

    def test_synthesize_mock_approve(self, relay):
        result = relay.synthesize_mock("Test", 8, [0.8, 0.9, 0.85, 0.75, 0.8, 0.9, 0.85, 0.8], 8, TRAJECTORY_EMPHASES[:8])
        assert "APPROVES" in result.synthesized_answer
        assert result.final_confidence >= 0.6
        assert len(result.cross_validation_notes) >= 1

    def test_synthesize_mock_reject(self, relay):
        result = relay.synthesize_mock("Test", 8, [0.3, 0.4, 0.2, 0.35, 0.3, 0.4, 0.2, 0.35], 8, TRAJECTORY_EMPHASES[:8])
        assert "REJECTS" in result.synthesized_answer
        # When approval_ratio ≈ 0, mock gives final_conf = 1.0 - 0.0 = 1.0 (certain rejection)
        assert result.final_confidence >= 0.5

    def test_synthesize_mock_with_gaps(self, relay):
        result = relay.synthesize_mock("Test", 5, [0.8, 0.85, 0.9, 0.7, 0.75], 8, TRAJECTORY_EMPHASES[:5])
        assert result.remaining_concerns  # Should flag missing trajectories


class TestConstants:
    def test_trajectory_emphases_length(self):
        assert len(TRAJECTORY_EMPHASES) == 8

    def test_scoring_prompt_has_json_keys(self):
        assert "score" in SCORING_SYSTEM_PROMPT
        assert "strengths" in SCORING_SYSTEM_PROMPT
        assert "weaknesses" in SCORING_SYSTEM_PROMPT

    def test_synthesis_prompt_has_json_keys(self):
        assert "synthesized_answer" in SYNTHESIS_SYSTEM_PROMPT
        assert "final_confidence" in SYNTHESIS_SYSTEM_PROMPT
        assert "consensus_points" in SYNTHESIS_SYSTEM_PROMPT


class TestTrajectoryScore:
    def test_defaults(self):
        s = TrajectoryScore(trajectory_id="t1", score=0.85)
        assert s.trajectory_id == "t1"
        assert s.score == 0.85
        assert s.strengths == []
        assert s.weaknesses == []
        assert s.cross_validate is True

    def test_full(self):
        s = TrajectoryScore("t1", 0.75, strengths=["a"], weaknesses=["b"], cross_validate=False)
        assert s.strengths == ["a"]
        assert s.cross_validate is False


class TestSynthesisOutput:
    def test_defaults(self):
        s = SynthesisOutput(synthesized_answer="ok", final_confidence=0.8)
        assert s.synthesized_answer == "ok"
        assert s.final_confidence == 0.8
        assert s.consensus_points == []
        assert s.remaining_concerns == []


class TestSingleton:
    def test_singleton_consistent(self):
        r1 = get_heavy_relay()
        r2 = get_heavy_relay()
        assert r1 is r2
