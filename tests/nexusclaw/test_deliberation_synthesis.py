"""tests/nexusclaw/test_deliberation_synthesis.py — Structured Deliberation Tests"""

import pytest
from nexus_os.nexusclaw.deliberation_synthesis import (
    DeliberationSynthesizer,
    SynthesisConfig,
    SynthesisVerdict,
    StructuredDeliberation,
    TrajectoryEvaluation,
)


@pytest.fixture
def synth():
    return DeliberationSynthesizer(config=SynthesisConfig(use_model_relay=False))


@pytest.fixture
def mock_trajectories():
    class MockTraj:
        def __init__(self, tid, agent, text, confidence, emphasis="general", metadata=None):
            self.trajectory_id = tid
            self.agent_name = agent
            self.reasoning_text = text
            self.confidence = confidence
            self.metadata = metadata or {"emphasis": emphasis}

    return [
        MockTraj("t1", "agent1", "reasoning about code quality", 0.85, "correctness"),
        MockTraj("t2", "agent1", "reasoning about security", 0.90, "security"),
        MockTraj("t3", "agent2", "reasoning about perf", 0.75, "performance"),
        MockTraj("t4", "agent2", "reasoning about maintainability", 0.65, "maintainability"),
        MockTraj("t5", "agent3", "reasoning about governance", 0.55, "governance"),
    ]


class TestDeliberationSynthesizer:
    def test_empty_trajectories(self, synth):
        result = synth.synthesize("p1", "Empty", "no trajs", [])
        assert result.verdict == SynthesisVerdict.INCONCLUSIVE
        assert result.final_confidence == 0.0
        assert result.trajectories_used == 0

    def test_synthesize_with_trajectories(self, synth, mock_trajectories):
        result = synth.synthesize("p1", "Test Proposal", "a test", mock_trajectories)
        assert result.proposal_id == "p1"
        assert result.proposal_title == "Test Proposal"
        assert result.trajectories_used == 5
        assert 0.0 <= result.final_confidence <= 1.0
        assert result.verdict in SynthesisVerdict

    def test_answer_distribution(self, synth, mock_trajectories):
        result = synth.synthesize("p1", "Test", "desc", mock_trajectories)
        assert sum(result.answer_distribution.values()) == 5
        assert "approve" in result.answer_distribution or "approve_with_concerns" in result.answer_distribution

    def test_cross_validation_notes(self, synth, mock_trajectories):
        result = synth.synthesize("p1", "Test", "desc", mock_trajectories)
        assert len(result.cross_validation_notes) >= 1

    def test_consensus_points(self, synth, mock_trajectories):
        result = synth.synthesize("p1", "Test", "desc", mock_trajectories)
        assert isinstance(result.consensus_points, list)

    def test_remaining_concerns(self, synth, mock_trajectories):
        result = synth.synthesize("p1", "Test", "desc", mock_trajectories)
        assert isinstance(result.remaining_concerns, list)

    def test_to_dict(self, synth, mock_trajectories):
        result = synth.synthesize("p1", "Test", "desc", mock_trajectories)
        d = result.to_dict()
        assert d["proposal_id"] == "p1"
        assert "verdict" in d
        assert "final_confidence" in d
        assert "trajectories_used" in d
        assert "answer_distribution" in d


class TestSynthesisVerdict:
    def test_all_verdicts(self):
        assert SynthesisVerdict.APPROVE.value == "approve"
        assert SynthesisVerdict.APPROVE_WITH_CONCERNS.value == "approve_with_concerns"
        assert SynthesisVerdict.NEEDS_REVISION.value == "needs_revision"
        assert SynthesisVerdict.REJECT.value == "reject"
        assert SynthesisVerdict.INCONCLUSIVE.value == "inconclusive"


class TestTrajectoryEvaluation:
    def test_defaults(self):
        e = TrajectoryEvaluation(trajectory_id="t1", agent_name="a1", reasoning_text="text", emphasis="gen", score=0.8)
        assert e.strengths == []
        assert e.weaknesses == []
        assert e.trajectory_id == "t1"

    def test_trajectory_evaluation_create(self):
        e = TrajectoryEvaluation(
            trajectory_id="t1",
            agent_name="agent1",
            reasoning_text="detailed analysis",
            emphasis="security",
            score=0.85,
            strengths=["good logic"],
            weaknesses=["missing evidence"],
            verdict=SynthesisVerdict.APPROVE_WITH_CONCERNS,
        )
        assert e.verdict == SynthesisVerdict.APPROVE_WITH_CONCERNS
        assert e.strengths == ["good logic"]


class TestStructedDeliberationEdgeCases:
    def test_high_confidence_approves(self, synth):
        class HighConfTraj:
            def __init__(self):
                self.trajectory_id = "h1"
                self.agent_name = "expert"
                self.reasoning_text = "excellent reasoning"
                self.confidence = 0.95
                self.metadata = {"emphasis": "correctness"}

        result = synth.synthesize("p1", "Great Idea", "solid", [HighConfTraj() for _ in range(5)])
        assert result.verdict in (SynthesisVerdict.APPROVE, SynthesisVerdict.APPROVE_WITH_CONCERNS)
        assert result.final_confidence >= 0.6

    def test_all_reject_verdict(self, synth):
        class LowConfTraj:
            def __init__(self):
                self.trajectory_id = "l1"
                self.agent_name = "novice"
                self.reasoning_text = "weak reasoning"
                self.confidence = 0.2
                self.metadata = {"emphasis": "general"}

        result = synth.synthesize("p1", "Bad Idea", "flawed", [LowConfTraj() for _ in range(5)])
        assert result.verdict in (SynthesisVerdict.REJECT, SynthesisVerdict.INCONCLUSIVE)
        assert result.trajectories_used == 5
        assert sum(result.answer_distribution.values()) == 5

    def test_single_trajectory(self, synth):
        class SingleTraj:
            def __init__(self):
                self.trajectory_id = "s1"
                self.agent_name = "solo"
                self.reasoning_text = "only one opinion"
                self.confidence = 0.7
                self.metadata = {"emphasis": "general"}

        result = synth.synthesize("p1", "Lone Proposal", "single", [SingleTraj()])
        assert result.trajectories_used == 1
        assert isinstance(result.synthesized_answer, str)

    def test_risk_level_critical(self, synth):
        class MockTraj:
            def __init__(self):
                self.trajectory_id = "r1"
                self.agent_name = "agent"
                self.reasoning_text = "moderate reasoning"
                self.confidence = 0.65
                self.metadata = {"emphasis": "general"}

        class MockRiskLevel:
            value = "CRITICAL"

        result = synth.synthesize("p1", "Critical Decision", "high stakes", [MockTraj() for _ in range(5)], risk_level=MockRiskLevel())
        assert result.trajectories_used == 5

    def test_synthesize_without_trajectory_metadata(self, synth):
        class NoMetaTraj:
            def __init__(self):
                self.trajectory_id = "n1"
                self.agent_name = "agent"
                self.reasoning_text = "no metadata"
                self.confidence = 0.7
                self.metadata = None

        result = synth.synthesize("p1", "No Meta", "desc", [NoMetaTraj()])
        assert result.trajectories_used == 1

    def test_mixed_verdicts(self, synth):
        class MixedTraj:
            def __init__(self, tid, conf):
                self.trajectory_id = tid
                self.agent_name = "agent"
                self.reasoning_text = f"traj {tid}"
                self.confidence = conf
                self.metadata = {"emphasis": f"angle_{tid}"}

        trajs = [MixedTraj(f"m{i}", c) for i, c in enumerate([0.9, 0.8, 0.5, 0.3, 0.1])]
        result = synth.synthesize("p1", "Mixed", "varied", trajs)
        dist = result.answer_distribution
        assert sum(dist.values()) == 5


class TestSynthesisConfig:
    def test_default_config(self):
        cfg = SynthesisConfig()
        assert cfg.approve_confidence_threshold == 0.7
        assert cfg.approval_ratio_threshold == 0.55
        assert cfg.use_model_relay is True

    def test_custom_config(self):
        cfg = SynthesisConfig(approve_confidence_threshold=0.8, approval_ratio_threshold=0.6, use_model_relay=False)
        assert cfg.approve_confidence_threshold == 0.8
        assert cfg.approval_ratio_threshold == 0.6
        assert cfg.use_model_relay is False
