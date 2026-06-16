"""Tests for BrainstormEngine HeavySkill-inspired parallel reasoning + deliberation synthesis."""

import pytest

from nexus_os.nexusclaw.agent_pool import AgentPool, AgentRecord, AgentStatus, AgentType, AgentCapability
from nexus_os.nexusclaw.brainstorm import (
    BrainstormEngine,
    BrainstormMode,
    BrainstormPhase,
    DeliberationResult,
    ParallelReasoningConfig,
    ParallelTrajectory,
    Proposal,
    RiskLevel,
)
from nexus_os.nexusclaw.message_bus import MessageBus


@pytest.fixture
def agents():
    """Create a set of test agents."""
    return {
        "agent-1": AgentRecord(
            agent_id="agent-1",
            name="Alpha",
            agent_type=AgentType.INTERNAL,
            status=AgentStatus.ONLINE,
            trust_score=85.0,
            lane="research",
            capabilities=[AgentCapability(name="reasoning", description="Can reason")],
        ),
        "agent-2": AgentRecord(
            agent_id="agent-2",
            name="Beta",
            agent_type=AgentType.INTERNAL,
            status=AgentStatus.ONLINE,
            trust_score=75.0,
            lane="code",
            capabilities=[AgentCapability(name="coding", description="Can code")],
        ),
        "agent-3": AgentRecord(
            agent_id="agent-3",
            name="Gamma",
            agent_type=AgentType.INTERNAL,
            status=AgentStatus.ONLINE,
            trust_score=65.0,
            lane="audit",
            capabilities=[AgentCapability(name="auditing", description="Can audit")],
        ),
        "agent-4": AgentRecord(
            agent_id="agent-4",
            name="Delta",
            agent_type=AgentType.INTERNAL,
            status=AgentStatus.ONLINE,
            trust_score=95.0,
            lane="governance",
            capabilities=[AgentCapability(name="governance", description="Can govern")],
        ),
    }


@pytest.fixture
def brainstorm_engine(agents):
    """Fresh BrainstormEngine with populated agent pool."""
    pool = AgentPool()
    for agent in agents.values():
        pool.register(agent)
    bus = MessageBus(agent_pool=pool)
    engine = BrainstormEngine(agent_pool=pool, message_bus=bus)
    return engine, pool


class TestParallelReasoningConfig:
    def test_defaults(self):
        cfg = ParallelReasoningConfig()
        assert cfg.k == 8
        assert cfg.summary_k == 4
        assert cfg.iterations == 1
        assert cfg.auto_trigger is True
        assert cfg.min_participants_for_normal == 3

    def test_custom_values(self):
        cfg = ParallelReasoningConfig(k=4, summary_k=2, iterations=2, auto_trigger=False)
        assert cfg.k == 4
        assert cfg.summary_k == 2
        assert cfg.iterations == 2
        assert cfg.auto_trigger is False


class TestParallelTrajectory:
    def test_to_dict(self):
        t = ParallelTrajectory(
            trajectory_id="t1",
            proposal_id="p1",
            agent_id="a1",
            agent_name="Agent1",
            reasoning_text="Some reasoning",
            confidence=0.85,
        )
        d = t.to_dict()
        assert d["trajectory_id"] == "t1"
        assert d["confidence"] == 0.85
        assert "Some reasoning" in d["reasoning_text"]


class TestDeliberationResult:
    def test_to_dict(self):
        r = DeliberationResult(
            result_id="r1",
            proposal_id="p1",
            synthesized_answer="Approve",
            answer_distribution={"approve": 5, "needs_work": 3},
            cross_validation_notes=["Majority approved."],
            identified_errors=[],
            final_confidence=0.75,
            trajectories_used=8,
        )
        d = r.to_dict()
        assert d["final_confidence"] == 0.75
        assert d["trajectories_used"] == 8
        assert d["answer_distribution"]["approve"] == 5


class TestParallelReasoningIntegration:
    def test_parallel_reason_generates_trajectories(self, brainstorm_engine, agents):
        engine, pool = brainstorm_engine
        session = engine.create_session(
            topic="Critical Decision",
            participant_ids=["agent-1", "agent-2", "agent-3"],
            mode=BrainstormMode.STRUCTURED,
            risk_level=RiskLevel.CRITICAL,
            trust_threshold=0.0,
        )
        proposal = engine.propose(
            session_id=session.session_id,
            agent_id="agent-1",
            title="Critical Proposal",
            description="This is a critical proposal.",
            evidence_refs=["ev-1"],
            risk_level=RiskLevel.CRITICAL,
        )
        trajectories = engine.parallel_reason(session.session_id, proposal.proposal_id)
        assert len(trajectories) > 0
        assert len(trajectories) <= 8
        agent_ids = {t.agent_id for t in trajectories}
        assert "agent-1" not in agent_ids

    def test_parallel_reason_with_single_participant(self, brainstorm_engine, agents):
        engine, pool = brainstorm_engine
        session = engine.create_session(
            topic="Solo Decision",
            participant_ids=["agent-1"],
            mode=BrainstormMode.STRUCTURED,
            risk_level=RiskLevel.CRITICAL,
            trust_threshold=0.0,
        )
        proposal = engine.propose(
            session_id=session.session_id,
            agent_id="agent-1",
            title="Solo Proposal",
            description="Only one agent.",
            evidence_refs=["ev-1"],
            risk_level=RiskLevel.CRITICAL,
        )
        trajectories = engine.parallel_reason(session.session_id, proposal.proposal_id)
        assert len(trajectories) == 8
        # All trajectories come from the solo participant
        assert all(t.agent_id == "agent-1" for t in trajectories)

    def test_parallel_reason_with_two_participants(self, brainstorm_engine, agents):
        engine, pool = brainstorm_engine
        session = engine.create_session(
            topic="Pair Decision",
            participant_ids=["agent-1", "agent-2"],
            mode=BrainstormMode.STRUCTURED,
            risk_level=RiskLevel.CRITICAL,
            trust_threshold=0.0,
        )
        proposal = engine.propose(
            session_id=session.session_id,
            agent_id="agent-1",
            title="Pair Proposal",
            description="Two agents.",
            evidence_refs=["ev-1"],
            risk_level=RiskLevel.CRITICAL,
        )
        cfg = ParallelReasoningConfig(k=4)
        trajectories = engine.parallel_reason(session.session_id, proposal.proposal_id, cfg)
        assert len(trajectories) > 0
        assert all(t.agent_id == "agent-2" for t in trajectories)
        assert len(trajectories) == 4

    def test_parallel_reason_trajectories_have_diverse_emphasis(self, brainstorm_engine, agents):
        engine, pool = brainstorm_engine
        session = engine.create_session(
            topic="Diverse Decision",
            participant_ids=["agent-1", "agent-2", "agent-3"],
            mode=BrainstormMode.STRUCTURED,
            risk_level=RiskLevel.CRITICAL,
            trust_threshold=0.0,
        )
        proposal = engine.propose(
            session_id=session.session_id,
            agent_id="agent-1",
            title="Diverse Proposal",
            description="Test.",
            evidence_refs=["ev-1"],
            risk_level=RiskLevel.CRITICAL,
        )
        cfg = ParallelReasoningConfig(k=8)
        trajectories = engine.parallel_reason(session.session_id, proposal.proposal_id, cfg)
        emphasis_set = {t.metadata.get("emphasis") for t in trajectories}
        assert len(emphasis_set) >= 2

    def test_parallel_reason_confidence_range(self, brainstorm_engine, agents):
        engine, pool = brainstorm_engine
        session = engine.create_session(
            topic="Confidence Test",
            participant_ids=["agent-1", "agent-2"],
            mode=BrainstormMode.STRUCTURED,
            risk_level=RiskLevel.CRITICAL,
            trust_threshold=0.0,
        )
        proposal = engine.propose(
            session_id=session.session_id,
            agent_id="agent-1",
            title="Confidence Proposal",
            description="Test.",
            evidence_refs=["ev-1"],
            risk_level=RiskLevel.CRITICAL,
        )
        trajectories = engine.parallel_reason(session.session_id, proposal.proposal_id)
        for t in trajectories:
            assert 0.1 <= t.confidence <= 0.99


class TestDeliberationSynthesis:
    def test_synthesis_approves_high_confidence(self, brainstorm_engine, agents):
        engine, pool = brainstorm_engine
        session = engine.create_session(
            topic="Approve Test",
            participant_ids=["agent-1", "agent-2"],
            mode=BrainstormMode.STRUCTURED,
            risk_level=RiskLevel.CRITICAL,
            trust_threshold=0.0,
        )
        proposal = engine.propose(
            session_id=session.session_id,
            agent_id="agent-1",
            title="Approve Proposal",
            description="Should be approved.",
            evidence_refs=["ev-1"],
            risk_level=RiskLevel.CRITICAL,
        )
        trajectories = [
            ParallelTrajectory(
                trajectory_id=f"t{i}", proposal_id=proposal.proposal_id,
                agent_id="agent-2", agent_name="Agent2",
                reasoning_text="Looks good.", confidence=0.85,
            )
            for i in range(5)
        ]
        result = engine.deliberation_synthesize(
            session.session_id, proposal.proposal_id, trajectories,
        )
        assert result.final_confidence >= 0.6
        assert "APPROVES" in result.synthesized_answer
        assert result.answer_distribution.get("approve", 0) >= 1

    def test_synthesis_rejects_low_confidence(self, brainstorm_engine, agents):
        engine, pool = brainstorm_engine
        session = engine.create_session(
            topic="Reject Test",
            participant_ids=["agent-1", "agent-2"],
            mode=BrainstormMode.STRUCTURED,
            risk_level=RiskLevel.CRITICAL,
            trust_threshold=0.0,
        )
        proposal = engine.propose(
            session_id=session.session_id,
            agent_id="agent-1",
            title="Reject Proposal",
            description="Should be rejected.",
            evidence_refs=["ev-1"],
            risk_level=RiskLevel.CRITICAL,
        )
        trajectories = [
            ParallelTrajectory(
                trajectory_id=f"t{i}", proposal_id=proposal.proposal_id,
                agent_id="agent-2", agent_name="Agent2",
                reasoning_text="Not sure.", confidence=0.5,
            )
            for i in range(5)
        ]
        result = engine.deliberation_synthesize(
            session.session_id, proposal.proposal_id, trajectories,
        )
        assert result.final_confidence > 0.6
        assert "REJECTS" in result.synthesized_answer

    def test_synthesis_empty_trajectories(self, brainstorm_engine, agents):
        engine, pool = brainstorm_engine
        session = engine.create_session(
            topic="Empty Test",
            participant_ids=["agent-1"],
            mode=BrainstormMode.STRUCTURED,
            risk_level=RiskLevel.CRITICAL,
            trust_threshold=0.0,
        )
        proposal = engine.propose(
            session_id=session.session_id,
            agent_id="agent-1",
            title="Empty Proposal",
            description="No trajectories.",
            evidence_refs=["ev-1"],
            risk_level=RiskLevel.CRITICAL,
        )
        result = engine.deliberation_synthesize(
            session.session_id, proposal.proposal_id, [],
        )
        assert result.final_confidence == 0.0
        assert result.trajectories_used == 0
        assert "No trajectories" in result.synthesized_answer

    def test_synthesis_critical_needs_high_confidence(self, brainstorm_engine, agents):
        engine, pool = brainstorm_engine
        session = engine.create_session(
            topic="Critical Consensus",
            participant_ids=["agent-1", "agent-2"],
            mode=BrainstormMode.STRUCTURED,
            risk_level=RiskLevel.CRITICAL,
            trust_threshold=0.0,
        )
        proposal = engine.propose(
            session_id=session.session_id,
            agent_id="agent-1",
            title="Critical Proposal",
            description="Needs consensus.",
            evidence_refs=["ev-1"],
            risk_level=RiskLevel.CRITICAL,
        )
        trajectories = [
            ParallelTrajectory(
                trajectory_id=f"t{i}", proposal_id=proposal.proposal_id,
                agent_id="agent-2", agent_name="Agent2",
                reasoning_text="Mixed.", confidence=0.6 if i < 3 else 0.8,
            )
            for i in range(5)
        ]
        result = engine.deliberation_synthesize(
            session.session_id, proposal.proposal_id, trajectories,
        )
        assert any("CRITICAL" in err for err in result.identified_errors)


class TestParallelReasoningOneShot:
    def test_run_parallel_reasoning_for_proposal(self, brainstorm_engine, agents):
        engine, pool = brainstorm_engine
        session = engine.create_session(
            topic="OneShot",
            participant_ids=["agent-1", "agent-2", "agent-3"],
            mode=BrainstormMode.STRUCTURED,
            risk_level=RiskLevel.CRITICAL,
            trust_threshold=0.0,
        )
        proposal = engine.propose(
            session_id=session.session_id,
            agent_id="agent-1",
            title="OneShot Proposal",
            description="Test.",
            evidence_refs=["ev-1"],
            risk_level=RiskLevel.CRITICAL,
        )
        result = engine.run_parallel_reasoning_for_proposal(
            session.session_id, proposal.proposal_id,
            config=ParallelReasoningConfig(k=3),
        )
        assert isinstance(result, DeliberationResult)
        assert result.trajectories_used > 0


class TestAutoTriggerParallelReasoning:
    def test_auto_trigger_on_critical_low_participants(self, brainstorm_engine, agents):
        engine, pool = brainstorm_engine
        session = engine.create_session(
            topic="AutoTrigger",
            participant_ids=["agent-1", "agent-2"],
            mode=BrainstormMode.STRUCTURED,
            risk_level=RiskLevel.CRITICAL,
            trust_threshold=0.0,
        )
        proposal = engine.propose(
            session_id=session.session_id,
            agent_id="agent-1",
            title="AutoTrigger Proposal",
            description="Should trigger parallel reasoning.",
            evidence_refs=["ev-1"],
            risk_level=RiskLevel.CRITICAL,
        )
        session = engine.advance_phase(session.session_id)
        assert session.phase == BrainstormPhase.DISCUSS
        assert len(session.proposals) == 1

    def test_no_auto_trigger_on_high_participants(self, brainstorm_engine, agents):
        engine, pool = brainstorm_engine
        session = engine.create_session(
            topic="NoAutoTrigger",
            participant_ids=["agent-1", "agent-2", "agent-3", "agent-4"],
            mode=BrainstormMode.STRUCTURED,
            risk_level=RiskLevel.CRITICAL,
            trust_threshold=0.0,
        )
        proposal = engine.propose(
            session_id=session.session_id,
            agent_id="agent-1",
            title="NoAutoTrigger Proposal",
            description="Should NOT trigger parallel reasoning (4 participants >= 3).",
            evidence_refs=["ev-1"],
            risk_level=RiskLevel.CRITICAL,
        )
        session = engine.advance_phase(session.session_id)
        assert session.phase == BrainstormPhase.DISCUSS

    def test_no_auto_trigger_on_low_risk(self, brainstorm_engine, agents):
        engine, pool = brainstorm_engine
        session = engine.create_session(
            topic="LowRisk",
            participant_ids=["agent-1", "agent-2"],
            mode=BrainstormMode.STRUCTURED,
            risk_level=RiskLevel.MEDIUM,
            trust_threshold=0.0,
        )
        proposal = engine.propose(
            session_id=session.session_id,
            agent_id="agent-1",
            title="LowRisk Proposal",
            description="Low risk, should not trigger.",
            risk_level=RiskLevel.LOW,
        )
        session = engine.advance_phase(session.session_id)
        assert session.phase == BrainstormPhase.DISCUSS

    def test_auto_trigger_logs_to_memory(self, brainstorm_engine, agents):
        engine, pool = brainstorm_engine
        session = engine.create_session(
            topic="MemoryLog",
            participant_ids=["agent-1", "agent-2"],
            mode=BrainstormMode.STRUCTURED,
            risk_level=RiskLevel.CRITICAL,
            trust_threshold=0.0,
        )
        proposal = engine.propose(
            session_id=session.session_id,
            agent_id="agent-1",
            title="MemoryLog Proposal",
            description="Should log to memory.",
            evidence_refs=["ev-1"],
            risk_level=RiskLevel.CRITICAL,
        )
        engine.advance_phase(session.session_id)
        assert session.phase == BrainstormPhase.DISCUSS
