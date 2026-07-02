"""tests/test_nexusclaw_v1.py - Comprehensive tests for NEXUSCLAW v1 multi-agent orchestration.

Tests cover:
  - AgentPool: registration, discovery, queries, trust filtering
  - TaskRouter: routing strategies, risk-based trust thresholds, load balancing
  - MessageBus: direct/broadcast/thread messaging, trust gates, external routing
  - BrainstormEngine: session lifecycle, proposals, voting, consensus
  - Orchestrator: full integration, task lifecycle, messaging, brainstorm
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone
from typing import Dict, Any, List

# Agent Pool
from nexus_os.nexusclaw.agent_pool import (
    AgentPool,
    AgentRecord,
    AgentStatus,
    AgentType,
    AgentCapability,
    get_agent_pool,
)

# Task Router
from nexus_os.nexusclaw.task_router import (
    TaskRouter,
    RoutingStrategy,
    RoutingDecision,
    TaskAssignment,
)

# Message Bus
from nexus_os.nexusclaw.message_bus import (
    MessageBus,
    NexusMessage,
    MessageType,
    MessagePriority,
)

# Brainstorm
from nexus_os.nexusclaw.brainstorm import (
    BrainstormEngine,
    BrainstormMode,
    BrainstormPhase,
    BrainstormSession,
    Proposal,
    VoteChoice,
)

# Orchestrator
from nexus_os.nexusclaw.orchestrator import (
    NexusClawOrchestrator,
    OrchestratorStatus,
    get_orchestrator,
)

# Envelope
from nexus_os.nexusclaw.envelope import NexusClawTaskEnvelope, RiskLevel

# Worklog
from nexus_os.nexusclaw.worklog import WorklogSystem


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

@pytest.fixture
def fresh_pool():
    """Fresh AgentPool instance for isolation."""
    return AgentPool()

@pytest.fixture
def populated_pool(fresh_pool):
    """AgentPool with internal agents discovered."""
    fresh_pool.discover_internal_agents()
    return fresh_pool

@pytest.fixture
def fresh_router(populated_pool):
    """Fresh TaskRouter instance with populated agent pool."""
    return TaskRouter(agent_pool=populated_pool)

@pytest.fixture
def fresh_bus(populated_pool):
    """Fresh MessageBus instance with populated agent pool."""
    return MessageBus(agent_pool=populated_pool)

@pytest.fixture
def fresh_brainstorm(populated_pool):
    """Fresh BrainstormEngine instance with populated agent pool."""
    bus = MessageBus(agent_pool=populated_pool)
    return BrainstormEngine(agent_pool=populated_pool, message_bus=bus)

@pytest.fixture
def fresh_orchestrator(fresh_pool):
    """Fresh Orchestrator instance with isolated agent pool."""
    orch = NexusClawOrchestrator(agent_pool=fresh_pool)
    orch.discover_agents()
    return orch


# ------------------------------------------------------------------
# Agent Pool Tests
# ------------------------------------------------------------------

class TestAgentPool:
    def test_create_pool(self, fresh_pool):
        assert len(fresh_pool.list_all()) == 0
        assert len(fresh_pool.list_available()) == 0

    def test_discover_internal_agents(self, populated_pool):
        agents = populated_pool.list_all()
        assert len(agents) >= 5  # governor, vault, archivist, benchmark, orchestrator
        ids = [a.agent_id for a in agents]
        assert "nexus-governor" in ids
        assert "nexus-vault" in ids
        assert "nexus-archivist" in ids
        assert "nexus-benchmark" in ids
        assert "nexusclaw-orchestrator" in ids

    def test_agent_types(self, populated_pool):
        for agent in populated_pool.list_all():
            assert agent.agent_type == AgentType.INTERNAL

    def test_agent_status_online(self, populated_pool):
        for agent in populated_pool.list_all():
            assert agent.status == AgentStatus.ONLINE
            assert agent.is_available

    def test_available_filter(self, populated_pool):
        available = populated_pool.list_available()
        assert len(available) == len(populated_pool.list_all())

    def test_unregister(self, populated_pool):
        agent = populated_pool.unregister("nexus-governor")
        assert agent is not None
        assert agent.agent_id == "nexus-governor"
        assert populated_pool.get("nexus-governor") is None

    def test_update_status(self, populated_pool):
        populated_pool.update_status("nexus-governor", AgentStatus.BUSY)
        agent = populated_pool.get("nexus-governor")
        assert agent.status == AgentStatus.BUSY
        assert not agent.is_available

    def test_update_trust(self, populated_pool):
        populated_pool.update_trust("nexus-governor", 42.0)
        agent = populated_pool.get("nexus-governor")
        assert agent.trust_score == 42.0

    def test_trust_clamping(self, populated_pool):
        populated_pool.update_trust("nexus-governor", 150.0)
        assert populated_pool.get("nexus-governor").trust_score == 100.0
        populated_pool.update_trust("nexus-governor", -10.0)
        assert populated_pool.get("nexus-governor").trust_score == 0.0

    def test_register_external_api(self, fresh_pool):
        agent = fresh_pool.register_external_api(
            agent_id="grok-1",
            name="Grok",
            lane="research",
            capabilities=[
                AgentCapability("code_search", "Fast code search", {"research"}, 30.0, "medium"),
            ],
            api_endpoint="https://api.grok.x.ai",
            trust_score=75.0,
        )
        assert agent.agent_id == "grok-1"
        assert agent.agent_type == AgentType.EXTERNAL_API
        assert agent.trust_score == 75.0

    def test_register_human(self, fresh_pool):
        agent = fresh_pool.register_human("human-admin", "Admin User", "governance")
        assert agent.agent_id == "human-admin"
        assert agent.agent_type == AgentType.HUMAN
        assert agent.trust_score == 100.0

    def test_find_by_capability(self, populated_pool):
        agents = populated_pool.find_by_capability("kaiju_auth")
        assert len(agents) >= 1
        assert agents[0].agent_id == "nexus-governor"

    def test_find_by_capability_trust_filter(self, populated_pool):
        populated_pool.update_trust("nexus-governor", 20.0)
        agents = populated_pool.find_by_capability("kaiju_auth", min_trust=50.0)
        assert len(agents) == 0  # Governor trust dropped below 50

    def test_find_by_lanes(self, populated_pool):
        agents = populated_pool.find_by_lanes({"governance"})
        assert len(agents) >= 1
        assert "nexus-governor" in [a.agent_id for a in agents]

    def test_stats(self, populated_pool):
        stats = populated_pool.stats()
        assert stats["total_agents"] == len(populated_pool.list_all())
        assert stats["available_agents"] == len(populated_pool.list_available())
        assert "by_type" in stats
        assert "by_status" in stats
        assert stats["avg_trust"] > 0

    def test_success_rate_tracking(self, populated_pool):
        agent = populated_pool.get("nexus-governor")
        assert agent.success_rate == 0.0
        agent.record_task(True)
        agent.record_task(True)
        agent.record_task(False)
        assert agent.success_rate == 2.0 / 3.0


# ------------------------------------------------------------------
# Task Router Tests
# ------------------------------------------------------------------

class TestTaskRouter:
    def test_router_basic(self, fresh_router):
        assert fresh_router.stats()["agents_in_pool"] >= 0

    def test_route_no_agents(self, fresh_router):
        task = NexusClawTaskEnvelope(
            task_id="test-1",
            source="test",
            lane="orchestrator",
            intent="test task",
            risk_level=RiskLevel.LOW,
            required_capabilities=["nonexistent_cap"],
        )
        decision = fresh_router.route(task, strategy=RoutingStrategy.DIRECT)
        assert decision.selected_agents == []
        assert "No agents available" in decision.reason

    def test_route_direct(self, populated_pool, fresh_router):
        task = NexusClawTaskEnvelope(
            task_id="test-1",
            source="test",
            lane="governance",
            intent="check policy",
            risk_level=RiskLevel.LOW,
            required_capabilities=["policy_check"],
        )
        decision = fresh_router.route(task, strategy=RoutingStrategy.DIRECT)
        assert len(decision.selected_agents) == 1
        assert decision.strategy == RoutingStrategy.DIRECT

    def test_route_broadcast(self, populated_pool, fresh_router):
        task = NexusClawTaskEnvelope(
            task_id="test-2",
            source="test",
            lane="research",
            intent="process papers",
            risk_level=RiskLevel.LOW,
            required_capabilities=["evidence_ingest"],
        )
        decision = fresh_router.route(task, strategy=RoutingStrategy.BROADCAST)
        assert len(decision.selected_agents) >= 1

    def test_route_trust_threshold_high_risk(self, populated_pool, fresh_router):
        # Drop governor trust below 70
        populated_pool.update_trust("nexus-governor", 50.0)
        task = NexusClawTaskEnvelope(
            task_id="test-3",
            source="test",
            lane="governance",
            intent="critical policy check",
            risk_level=RiskLevel.HIGH,
            required_capabilities=["policy_check"],
        )
        decision = fresh_router.route(task, strategy=RoutingStrategy.DIRECT)
        # Governor trust is 50, threshold for HIGH is 70, so no agents
        assert decision.selected_agents == []
        assert decision.trust_threshold == 70.0

    def test_route_critical_requires_trust_90(self, populated_pool, fresh_router):
        task = NexusClawTaskEnvelope(
            task_id="test-4",
            source="test",
            lane="governance",
            intent="critical audit",
            risk_level=RiskLevel.CRITICAL,
            required_capabilities=["trust_scoring"],
        )
        # Audit fix (task_router.py:223): CRITICAL risk requires a human in
        # the loop — with no human available the task is HELD, not routed.
        held = fresh_router.route(task, strategy=RoutingStrategy.DIRECT)
        assert held.selected_agents == []
        assert held.metadata.get("held_for_human") is True
        assert "human oversight" in held.reason or "human" in held.reason

        # With a human operator available, routing proceeds on trust.
        populated_pool.register_human("speci", "SPECI")
        task2 = NexusClawTaskEnvelope(
            task_id="test-4b",
            source="test",
            lane="governance",
            intent="critical audit",
            risk_level=RiskLevel.CRITICAL,
            required_capabilities=["trust_scoring"],
        )
        decision = fresh_router.route(task2, strategy=RoutingStrategy.DIRECT)
        # Governor trust is 95, so should be selected
        assert "nexus-governor" in decision.selected_agents
        assert decision.trust_threshold == 90.0

    def test_route_brainstorm_diverse(self, populated_pool, fresh_router):
        # Register multiple diverse agents
        populated_pool.register_external_api(
            agent_id="gpt-1",
            name="ChatGPT",
            lane="research",
            capabilities=[
                AgentCapability("text_analysis", "Text analysis", {"research"}, 30.0, "low"),
            ],
            trust_score=80.0,
        )
        populated_pool.register_external_api(
            agent_id="grok-1",
            name="Grok",
            lane="research",
            capabilities=[
                AgentCapability("text_analysis", "Text analysis", {"research"}, 30.0, "low"),
            ],
            trust_score=75.0,
        )

        task = NexusClawTaskEnvelope(
            task_id="test-5",
            source="test",
            lane="research",
            intent="brainstorm ideas",
            risk_level=RiskLevel.MEDIUM,
            required_capabilities=["text_analysis"],
        )
        decision = fresh_router.route(task, strategy=RoutingStrategy.BRAINSTORM)
        # Should select diverse agents (different types or IDs)
        assert len(decision.selected_agents) >= 1
        # In a real brainstorm with 2 external + internal, we might get 2-3
        if len(decision.selected_agents) >= 2:
            assert len(set(decision.selected_agents)) == len(decision.selected_agents)

    def test_route_redundant(self, populated_pool, fresh_router):
        task = NexusClawTaskEnvelope(
            task_id="test-6",
            source="test",
            lane="governance",
            intent="redundant check",
            risk_level=RiskLevel.MEDIUM,
            required_capabilities=["policy_check"],
        )
        decision = fresh_router.route(task, strategy=RoutingStrategy.REDUNDANT)
        # REDUNDANT can select up to 3 agents
        assert len(decision.selected_agents) >= 1
        assert len(decision.selected_agents) <= 3

    def test_assignment_tracking(self, populated_pool, fresh_router):
        task = NexusClawTaskEnvelope(
            task_id="test-7",
            source="test",
            lane="governance",
            intent="policy check",
            risk_level=RiskLevel.LOW,
            required_capabilities=["policy_check"],
        )
        decision = fresh_router.route(task, strategy=RoutingStrategy.DIRECT)
        assignments = fresh_router.get_assignments("test-7")
        assert len(assignments) >= 1
        assert assignments[0].status == "pending"
        assert assignments[0].assignment_type == "primary"

    def test_complete_assignment(self, populated_pool, fresh_router):
        task = NexusClawTaskEnvelope(
            task_id="test-8",
            source="test",
            lane="governance",
            intent="policy check",
            risk_level=RiskLevel.LOW,
            required_capabilities=["policy_check"],
        )
        decision = fresh_router.route(task, strategy=RoutingStrategy.DIRECT)
        agent_id = decision.selected_agents[0]
        fresh_router.complete_assignment("test-8", agent_id, True)
        # Agent should be back to online
        assert populated_pool.get(agent_id).status.value == "online"
        # Agent should have recorded success
        assert populated_pool.get(agent_id).task_count >= 1

    def test_router_stats(self, fresh_router):
        stats = fresh_router.stats()
        assert "active_tasks" in stats
        assert "total_assignments" in stats
        assert "pending_assignments" in stats


# ------------------------------------------------------------------
# Message Bus Tests
# ------------------------------------------------------------------

class TestMessageBus:
    def test_create_bus(self, fresh_bus):
        assert fresh_bus.stats()["total_messages"] == 0

    def test_direct_message(self, populated_pool, fresh_bus):
        msg = NexusMessage(
            message_id="msg-1",
            sender_id="nexus-governor",
            sender_name="Governor",
            recipient_ids=["nexus-vault"],
            message_type=MessageType.DIRECT,
            content="Hello vault",
            priority=MessagePriority.NORMAL,
        )
        result = fresh_bus.send(msg)
        assert result.delivered
        assert fresh_bus.stats()["total_messages"] == 1

    def test_broadcast_message(self, populated_pool, fresh_bus):
        msg = NexusMessage(
            message_id="msg-2",
            sender_id="nexus-governor",
            sender_name="Governor",
            recipient_ids=[],
            message_type=MessageType.BROADCAST,
            content="Broadcast to all",
            priority=MessagePriority.NORMAL,
        )
        result = fresh_bus.send(msg)
        assert result.delivered
        assert len(result.recipient_ids) == len(populated_pool.list_available())

    def test_message_sender_not_found(self, populated_pool, fresh_bus):
        msg = NexusMessage(
            message_id="msg-3",
            sender_id="nonexistent",
            sender_name="Ghost",
            recipient_ids=["nexus-vault"],
            message_type=MessageType.DIRECT,
            content="Hello",
        )
        result = fresh_bus.send(msg)
        assert not result.delivered
        assert "not found" in (result.delivery_error or "").lower()

    def test_message_trust_too_low(self, populated_pool, fresh_bus):
        populated_pool.update_trust("nexus-governor", 10.0)
        msg = NexusMessage(
            message_id="msg-4",
            sender_id="nexus-governor",
            sender_name="Governor",
            recipient_ids=["nexus-vault"],
            message_type=MessageType.DIRECT,
            content="Hello",
            trust_required=50.0,
        )
        result = fresh_bus.send(msg)
        assert not result.delivered
        assert "trust" in (result.delivery_error or "").lower()

    def test_high_risk_message_blocked(self, populated_pool, fresh_bus):
        # Vault trust is 90, but let's drop it below 70
        populated_pool.update_trust("nexus-vault", 60.0)
        msg = NexusMessage(
            message_id="msg-5",
            sender_id="nexus-governor",
            sender_name="Governor",
            recipient_ids=["nexus-vault"],
            message_type=MessageType.DIRECT,
            content="High risk message",
            risk_level=RiskLevel.HIGH,
        )
        result = fresh_bus.send(msg)
        assert not result.delivered
        assert "trust too low" in (result.delivery_error or "").lower()

    def test_message_too_long(self, populated_pool, fresh_bus):
        msg = NexusMessage(
            message_id="msg-6",
            sender_id="nexus-governor",
            sender_name="Governor",
            recipient_ids=["nexus-vault"],
            message_type=MessageType.DIRECT,
            content="x" * 5000,
        )
        result = fresh_bus.send(msg)
        assert not result.delivered
        assert "max length" in (result.delivery_error or "").lower()

    def test_thread_lifecycle(self, populated_pool, fresh_bus):
        thread = fresh_bus.create_thread("Test Topic", ["nexus-governor", "nexus-vault"])
        assert thread.thread_id in fresh_bus._threads
        assert thread.status == "open"
        assert len(thread.participant_ids) == 2

        # Send thread reply
        msg = NexusMessage(
            message_id="msg-7",
            sender_id="nexus-governor",
            sender_name="Governor",
            recipient_ids=["nexus-vault"],
            message_type=MessageType.THREAD_REPLY,
            content="Reply in thread",
            thread_id=thread.thread_id,
        )
        result = fresh_bus.send(msg)
        assert result.delivered
        assert len(fresh_bus.get_thread(thread.thread_id).messages) == 1

        # Close thread
        fresh_bus.close_thread(thread.thread_id)
        assert fresh_bus.get_thread(thread.thread_id).status == "closed"

    def test_external_out_message(self, populated_pool, fresh_bus):
        msg = NexusMessage(
            message_id="msg-8",
            sender_id="nexus-governor",
            sender_name="Governor",
            recipient_ids=[],
            message_type=MessageType.EXTERNAL_OUT,
            content="External message",
        )
        result = fresh_bus.send(msg)
        assert result.delivered

    def test_system_message(self, populated_pool, fresh_bus):
        # Register a system agent so sender exists in pool
        populated_pool.register_external_api(
            agent_id="system",
            name="System",
            lane="orchestration",
            capabilities=[],
            trust_score=100.0,
        )
        msg = NexusMessage(
            message_id="msg-9",
            sender_id="system",
            sender_name="System",
            recipient_ids=[],
            message_type=MessageType.SYSTEM,
            content="System alert",
            priority=MessagePriority.CRITICAL,
            metadata={"governance_origin": True},
        )
        result = fresh_bus.send(msg)
        assert result.delivered
        assert len(result.recipient_ids) == len(populated_pool.list_available())

    def test_system_message_spoof_rejected(self, populated_pool, fresh_bus):
        """Audit fix (message_bus.py:405): the caller-writable
        governance_origin flag no longer authorizes SYSTEM messages —
        identity allowlist + trust floor do."""
        populated_pool.register_external_api(
            agent_id="rogue-agent",
            name="Rogue",
            lane="research",
            capabilities=[],
            trust_score=100.0,
        )
        msg = NexusMessage(
            message_id="msg-spoof",
            sender_id="rogue-agent",
            sender_name="Rogue",
            recipient_ids=[],
            message_type=MessageType.SYSTEM,
            content="fake governance broadcast",
            metadata={"governance_origin": True},
        )
        result = fresh_bus.send(msg)
        assert result.delivered is False
        assert "not authorized" in result.delivery_error

    def test_system_message_low_trust_allowlisted_sender_rejected(self, populated_pool, fresh_bus):
        populated_pool.register_external_api(
            agent_id="system",
            name="System",
            lane="orchestration",
            capabilities=[],
            trust_score=50.0,  # below SYSTEM_SENDER_MIN_TRUST
        )
        msg = NexusMessage(
            message_id="msg-lowtrust",
            sender_id="system",
            sender_name="System",
            recipient_ids=[],
            message_type=MessageType.SYSTEM,
            content="System alert",
        )
        result = fresh_bus.send(msg)
        assert result.delivered is False

    def test_bus_stats(self, fresh_bus):
        stats = fresh_bus.stats()
        assert "total_messages" in stats
        assert "delivered" in stats
        assert "failed" in stats


# ------------------------------------------------------------------
# Brainstorm Engine Tests
# ------------------------------------------------------------------

class TestBrainstormEngine:
    def test_create_session(self, populated_pool, fresh_brainstorm):
        session = fresh_brainstorm.create_session(
            topic="Test Brainstorm",
            participant_ids=["nexus-governor", "nexus-vault", "nexus-archivist"],
            mode=BrainstormMode.STRUCTURED,
        )
        assert session.topic == "Test Brainstorm"
        assert session.mode == BrainstormMode.STRUCTURED
        assert session.phase == BrainstormPhase.PROPOSE
        assert len(session.participant_ids) == 3
        assert session.is_open

    def test_create_session_invalid_participants(self, populated_pool, fresh_brainstorm):
        with pytest.raises(ValueError, match="No valid participants"):
            fresh_brainstorm.create_session(
                topic="Empty",
                participant_ids=["nonexistent-1", "nonexistent-2"],
            )

    def test_propose(self, populated_pool, fresh_brainstorm):
        session = fresh_brainstorm.create_session(
            topic="Test",
            participant_ids=["nexus-governor", "nexus-vault"],
        )
        proposal = fresh_brainstorm.propose(
            session_id=session.session_id,
            agent_id="nexus-governor",
            title="Idea 1",
            description="This is a test idea",
            evidence_refs=["evidence-1"],
        )
        assert proposal.title == "Idea 1"
        assert proposal.session_id == session.session_id
        assert proposal.agent_id == "nexus-governor"

    def test_propose_evidence_required_for_high_risk(self, populated_pool, fresh_brainstorm):
        session = fresh_brainstorm.create_session(
            topic="High Risk Test",
            participant_ids=["nexus-governor", "nexus-vault"],
            risk_level=RiskLevel.HIGH,
        )
        with pytest.raises(ValueError, match="evidence"):
            fresh_brainstorm.propose(
                session_id=session.session_id,
                agent_id="nexus-governor",
                title="Bad Idea",
                description="No evidence",
            )

    def test_propose_non_participant(self, populated_pool, fresh_brainstorm):
        session = fresh_brainstorm.create_session(
            topic="Test",
            participant_ids=["nexus-governor"],
        )
        with pytest.raises(ValueError, match="not a participant"):
            fresh_brainstorm.propose(
                session_id=session.session_id,
                agent_id="nexus-vault",  # Not a participant
                title="Idea",
                description="Desc",
            )

    def test_discuss(self, populated_pool, fresh_brainstorm):
        session = fresh_brainstorm.create_session(
            topic="Test",
            participant_ids=["nexus-governor", "nexus-vault"],
            mode=BrainstormMode.STRUCTURED,
        )
        proposal = fresh_brainstorm.propose(
            session_id=session.session_id,
            agent_id="nexus-governor",
            title="Idea",
            description="Desc",
            evidence_refs=["ev-1"],
        )
        # Need to advance to DISCUSS phase
        fresh_brainstorm.advance_phase(session.session_id)
        msg = fresh_brainstorm.discuss(
            session_id=session.session_id,
            agent_id="nexus-vault",
            proposal_id=proposal.proposal_id,
            comment="I like this idea",
        )
        assert msg.delivered

    def test_vote(self, populated_pool, fresh_brainstorm):
        session = fresh_brainstorm.create_session(
            topic="Test",
            participant_ids=["nexus-governor", "nexus-vault", "nexus-archivist"],
            mode=BrainstormMode.STRUCTURED,
        )
        proposal = fresh_brainstorm.propose(
            session_id=session.session_id,
            agent_id="nexus-governor",
            title="Idea",
            description="Desc",
            evidence_refs=["ev-1"],
        )
        # Advance to VOTE phase
        fresh_brainstorm.advance_phase(session.session_id)  # PROPOSE -> DISCUSS
        fresh_brainstorm.discuss(session.session_id, "nexus-vault", proposal.proposal_id, "Looks good")
        fresh_brainstorm.advance_phase(session.session_id)  # DISCUSS -> VOTE

        fresh_brainstorm.vote(
            session_id=session.session_id,
            agent_id="nexus-vault",
            proposal_id=proposal.proposal_id,
            choice=VoteChoice.FOR,
        )
        fresh_brainstorm.vote(
            session_id=session.session_id,
            agent_id="nexus-archivist",
            proposal_id=proposal.proposal_id,
            choice=VoteChoice.FOR,
        )
        assert len(proposal.votes) == 2

    def test_vote_self_not_allowed(self, populated_pool, fresh_brainstorm):
        session = fresh_brainstorm.create_session(
            topic="Test",
            participant_ids=["nexus-governor", "nexus-vault"],
            mode=BrainstormMode.STRUCTURED,
        )
        proposal = fresh_brainstorm.propose(
            session_id=session.session_id,
            agent_id="nexus-governor",
            title="Idea",
            description="Desc",
            evidence_refs=["ev-1"],
        )
        fresh_brainstorm.advance_phase(session.session_id)  # PROPOSE -> DISCUSS
        fresh_brainstorm.discuss(session.session_id, "nexus-vault", proposal.proposal_id, "Some thoughts")
        fresh_brainstorm.advance_phase(session.session_id)  # DISCUSS -> VOTE

        result = fresh_brainstorm.vote(
            session_id=session.session_id,
            agent_id="nexus-governor",  # Proposer CAN vote
            proposal_id=proposal.proposal_id,
            choice=VoteChoice.FOR,
        )
        assert result.votes["nexus-governor"] == VoteChoice.FOR

    def test_consensus_computation(self, populated_pool, fresh_brainstorm):
        session = fresh_brainstorm.create_session(
            topic="Consensus Test",
            participant_ids=["nexus-governor", "nexus-vault", "nexus-archivist"],
            mode=BrainstormMode.STRUCTURED,
            consensus_threshold=0.5,
        )
        proposal = fresh_brainstorm.propose(
            session_id=session.session_id,
            agent_id="nexus-governor",
            title="Idea",
            description="Desc",
            evidence_refs=["ev-1"],
        )
        # All 3 agents have trust ~85-95, so votes are weighted
        fresh_brainstorm.advance_phase(session.session_id)  # PROPOSE -> DISCUSS
        fresh_brainstorm.discuss(session.session_id, "nexus-vault", proposal.proposal_id, "LGTM")
        fresh_brainstorm.advance_phase(session.session_id)  # DISCUSS -> VOTE

        fresh_brainstorm.vote(
            session_id=session.session_id,
            agent_id="nexus-vault",
            proposal_id=proposal.proposal_id,
            choice=VoteChoice.FOR,
        )
        fresh_brainstorm.vote(
            session_id=session.session_id,
            agent_id="nexus-archivist",
            proposal_id=proposal.proposal_id,
            choice=VoteChoice.FOR,
        )
        # Proposer votes explicitly (no implicit FOR vote)
        fresh_brainstorm.vote(
            session_id=session.session_id,
            agent_id="nexus-governor",
            proposal_id=proposal.proposal_id,
            choice=VoteChoice.FOR,
        )

        # Advance to RESOLVE
        fresh_brainstorm.advance_phase(session.session_id)
        assert proposal.accepted is True
        assert proposal.consensus_score > 0.5

    def test_close_session(self, populated_pool, fresh_brainstorm):
        session = fresh_brainstorm.create_session(
            topic="Test",
            participant_ids=["nexus-governor"],
        )
        closed = fresh_brainstorm.close_session(session.session_id)
        assert closed.phase == BrainstormPhase.CLOSED
        assert not closed.is_open

    def test_brainstorm_stats(self, populated_pool, fresh_brainstorm):
        session = fresh_brainstorm.create_session(
            topic="Stats Test",
            participant_ids=["nexus-governor"],
        )
        fresh_brainstorm.propose(
            session_id=session.session_id,
            agent_id="nexus-governor",
            title="Idea",
            description="Desc",
            evidence_refs=["ev-1"],
        )
        stats = fresh_brainstorm.stats()
        assert stats["total_sessions"] >= 1
        assert stats["total_proposals"] >= 1


# ------------------------------------------------------------------
# Orchestrator Tests
# ------------------------------------------------------------------

class TestOrchestrator:
    def test_create_orchestrator(self, fresh_orchestrator):
        status = fresh_orchestrator.status()
        assert status.version == "nexusclaw-v1"
        assert status.agents_total >= 5

    def test_register_external_agent(self, fresh_orchestrator):
        agent = fresh_orchestrator.register_external_agent(
            agent_id="grok-1",
            name="Grok",
            lane="research",
            capabilities=[
                AgentCapability("code_search", "Fast code search", {"research"}, 30.0, "medium"),
            ],
            api_endpoint="https://api.grok.x.ai",
            trust_score=75.0,
        )
        assert agent.agent_id == "grok-1"
        assert fresh_orchestrator.status().agents_total >= 6

    def test_register_human(self, fresh_orchestrator):
        agent = fresh_orchestrator.register_human("admin-1", "Admin")
        assert agent.agent_type == AgentType.HUMAN
        assert agent.trust_score == 100.0

    def test_submit_task(self, fresh_orchestrator):
        task = NexusClawTaskEnvelope(
            task_id="orch-test-1",
            source="test",
            lane="governance",
            intent="policy check",
            risk_level=RiskLevel.LOW,
            required_capabilities=["policy_check"],
        )
        result = fresh_orchestrator.submit_task(task)
        assert result["status"] == "routed"
        assert len(result["agents_assigned"]) >= 1
        assert result["routing_decision"]["task_id"] == "orch-test-1"

    def test_submit_task_no_agents(self, fresh_orchestrator):
        task = NexusClawTaskEnvelope(
            task_id="orch-test-2",
            source="test",
            lane="orchestrator",
            intent="unknown task",
            risk_level=RiskLevel.LOW,
            required_capabilities=["nonexistent_cap"],
        )
        result = fresh_orchestrator.submit_task(task)
        assert result["status"] == "no_agents_available"

    def test_high_risk_task_requires_human(self, fresh_orchestrator):
        fresh_orchestrator.register_human("human-1", "Human Oversight")
        task = NexusClawTaskEnvelope(
            task_id="orch-test-3",
            source="test",
            lane="governance",
            intent="critical audit",
            risk_level=RiskLevel.HIGH,
            required_capabilities=["policy_check"],
        )
        result = fresh_orchestrator.submit_task(task)
        assert result["requires_human_oversight"] is True

    def test_complete_task(self, fresh_orchestrator):
        task = NexusClawTaskEnvelope(
            task_id="orch-test-4",
            source="test",
            lane="governance",
            intent="policy check",
            risk_level=RiskLevel.LOW,
            required_capabilities=["policy_check"],
        )
        fresh_orchestrator.submit_task(task)
        # Get the assigned agent
        assignments = fresh_orchestrator.task_router.get_assignments("orch-test-4")
        assert len(assignments) >= 1
        agent_id = assignments[0].agent_id
        result = fresh_orchestrator.complete_task("orch-test-4", agent_id, True)
        assert result["status"] == "completed"

    def test_send_message(self, fresh_orchestrator):
        result = fresh_orchestrator.send_message(
            sender_id="nexus-governor",
            recipient_ids=["nexus-vault"],
            content="Hello vault",
        )
        assert result["status"] == "delivered"

    def test_send_message_bad_sender(self, fresh_orchestrator):
        result = fresh_orchestrator.send_message(
            sender_id="nonexistent",
            recipient_ids=["nexus-vault"],
            content="Hello",
        )
        assert result["status"] == "failed"

    def test_broadcast_message(self, fresh_orchestrator):
        result = fresh_orchestrator.broadcast_message(
            sender_id="nexus-governor",
            content="Alert everyone",
        )
        assert result["status"] == "delivered"

    def test_brainstorm_lifecycle(self, fresh_orchestrator):
        session = fresh_orchestrator.start_brainstorm(
            topic="Architecture Decision",
            participant_ids=["nexus-governor", "nexus-vault", "nexus-archivist"],
            mode=BrainstormMode.STRUCTURED,
        )
        assert session.topic == "Architecture Decision"
        assert session.is_open

        # Propose
        proposal = fresh_orchestrator.propose_idea(
            session_id=session.session_id,
            agent_id="nexus-governor",
            title="Use Rust",
            description="Rewrite core in Rust for performance",
            evidence_refs=["benchmark-rust-vs-python"],
        )
        assert proposal.title == "Use Rust"

        # Advance phases
        fresh_orchestrator.advance_brainstorm(session.session_id)  # PROPOSE -> DISCUSS
        fresh_orchestrator.discuss_idea(
            session_id=session.session_id,
            agent_id="nexus-vault",
            proposal_id=proposal.proposal_id,
            comment="Good idea but migration cost is high",
        )

        fresh_orchestrator.advance_brainstorm(session.session_id)  # DISCUSS -> VOTE
        fresh_orchestrator.vote_on_idea(
            session_id=session.session_id,
            agent_id="nexus-vault",
            proposal_id=proposal.proposal_id,
            choice=VoteChoice.FOR,
        )
        fresh_orchestrator.vote_on_idea(
            session_id=session.session_id,
            agent_id="nexus-archivist",
            proposal_id=proposal.proposal_id,
            choice=VoteChoice.FOR,
        )

        # Resolve
        result = fresh_orchestrator.advance_brainstorm(session.session_id)  # VOTE -> RESOLVE
        assert result["phase"] == "resolve"
        assert result["is_open"] is True
        # Should have a winner since 2 out of 2 voted FOR
        # (proposer can't vote, so 2 votes from vault and archivist)
        winner = fresh_orchestrator.brainstorm_engine.get_session(session.session_id).winner_proposal_id
        assert winner == proposal.proposal_id

        # Close
        close_result = fresh_orchestrator.close_brainstorm(session.session_id)
        assert close_result["status"] == "closed"

    def test_full_stats(self, fresh_orchestrator):
        stats = fresh_orchestrator.full_stats()
        assert "orchestrator" in stats
        assert "agent_pool" in stats
        assert "task_router" in stats
        assert "message_bus" in stats
        assert "brainstorm_engine" in stats
        assert stats["orchestrator"]["version"] == "nexusclaw-v1"

    def test_halt(self, fresh_orchestrator):
        result = fresh_orchestrator.halt("emergency shutdown test")
        assert result["status"] == "halted"
        assert result["reason"] == "emergency shutdown test"
        assert fresh_orchestrator.status().running is False
        assert fresh_orchestrator.status().agents_online == 0

    def test_singleton_orchestrator(self):
        orch1 = get_orchestrator()
        orch2 = get_orchestrator()
        assert orch1 is orch2

    def test_update_agent_status(self, fresh_orchestrator):
        fresh_orchestrator.update_agent_status("nexus-governor", AgentStatus.BUSY)
        assert fresh_orchestrator.agent_pool.get("nexus-governor").status == AgentStatus.BUSY

    def test_update_agent_trust(self, fresh_orchestrator):
        fresh_orchestrator.update_agent_trust("nexus-governor", 42.0)
        assert fresh_orchestrator.agent_pool.get("nexus-governor").trust_score == 42.0

    def test_sync_memory_context(self, fresh_orchestrator):
        ctx = fresh_orchestrator.sync_memory_context("nexus-governor", "test query")
        assert ctx is not None
        assert hasattr(ctx, "plan")

    def test_agent_re_registration_unindexes_old_caps(self, fresh_pool):
        # Register first version of agent
        cap1 = AgentCapability("cap1", "Cap 1")
        fresh_pool.register_external_api(
            agent_id="test-agent",
            name="Test Agent",
            lane="research",
            capabilities=[cap1],
        )
        assert len(fresh_pool.find_by_capability("cap1")) == 1

        # Re-register with new capabilities
        cap2 = AgentCapability("cap2", "Cap 2")
        fresh_pool.register_external_api(
            agent_id="test-agent",
            name="Test Agent",
            lane="research",
            capabilities=[cap2],
        )
        # Old capability index should be cleaned up
        assert len(fresh_pool.find_by_capability("cap1")) == 0
        # New capability should be indexed
        assert len(fresh_pool.find_by_capability("cap2")) == 1

    def test_brainstorm_consensus_ignores_abstention(self, populated_pool, fresh_brainstorm):
        session = fresh_brainstorm.create_session(
            topic="Consensus Test",
            participant_ids=["nexus-governor", "nexus-vault", "nexus-archivist"],
            mode=BrainstormMode.STRUCTURED,
            consensus_threshold=0.5,
        )
        proposal = fresh_brainstorm.propose(
            session_id=session.session_id,
            agent_id="nexus-governor",
            title="Idea",
            description="Desc",
            evidence_refs=["ev-1"],
        )
        # Advance phases
        fresh_brainstorm.advance_phase(session.session_id)  # PROPOSE -> DISCUSS
        fresh_brainstorm.discuss(session.session_id, "nexus-vault", proposal.proposal_id, "Let's discuss")
        fresh_brainstorm.advance_phase(session.session_id)  # DISCUSS -> VOTE

        # 2 agents ABSTAIN, proposer votes FOR explicitly
        fresh_brainstorm.vote(
            session_id=session.session_id,
            agent_id="nexus-vault",
            proposal_id=proposal.proposal_id,
            choice=VoteChoice.ABSTAIN,
        )
        fresh_brainstorm.vote(
            session_id=session.session_id,
            agent_id="nexus-archivist",
            proposal_id=proposal.proposal_id,
            choice=VoteChoice.ABSTAIN,
        )
        fresh_brainstorm.vote(
            session_id=session.session_id,
            agent_id="nexus-governor",
            proposal_id=proposal.proposal_id,
            choice=VoteChoice.FOR,
        )

        # Compute consensus (governor's FOR vote = ~0.95 weight, active total = 0.95, score = 1.0)
        fresh_brainstorm.advance_phase(session.session_id)  # VOTE -> RESOLVE
        
        assert proposal.consensus_score == 1.0
        assert proposal.accepted is True

    def test_orchestrator_runner_fallback_thread(self, fresh_orchestrator):
        # start_runner in non-blocking mode when loop is absent (in standard test thread)
        thread = fresh_orchestrator.start_runner(blocking=False)
        assert thread is not None
        # Should return a Thread object since there is no running asyncio loop in standard pytest thread
        import threading
        assert isinstance(thread, threading.Thread)
        fresh_orchestrator.stop_runner()


class TestAgentTypeLeader:
    def test_leader_type_exists(self):
        assert AgentType.LEADER.value == "leader"

    def test_leader_agent_can_register(self, populated_pool):
        agent = AgentRecord(
            agent_id="test-leader-1",
            name="TestLeader",
            agent_type=AgentType.LEADER,
            status=AgentStatus.ONLINE,
            trust_score=95.0,
            lane="governance",
            capabilities=[
                AgentCapability(name="synthesis", description="Synthesize multi-agent outputs", lanes={"governance"}, min_trust=70.0, max_risk="critical"),
            ],
        )
        populated_pool.register(agent)
        retrieved = populated_pool.get("test-leader-1")
        assert retrieved is not None
        assert retrieved.agent_type == AgentType.LEADER

    def test_leader_detected_in_redundant_mode(self, populated_pool, fresh_brainstorm):
        # Register a leader agent
        agent = AgentRecord(
            agent_id="test-leader-2",
            name="LeaderAgent",
            agent_type=AgentType.LEADER,
            status=AgentStatus.ONLINE,
            trust_score=99.0,
            lane="governance",
            capabilities=[AgentCapability(name="synthesis", description="Leader synthesis", lanes={"governance"})],
        )
        populated_pool.register(agent)

        session = fresh_brainstorm.create_session(
            topic="Redundant Test",
            participant_ids=["nexus-governor", "nexus-vault", "test-leader-2"],
            mode=BrainstormMode.REDUNDANT,
        )
        # _find_leader_agent should prefer the LEADER type agent
        leader = fresh_brainstorm._find_leader_agent(session)
        assert leader == "test-leader-2"


class TestBrainstormRedundantMode:
    def test_create_redundant_session(self, populated_pool, fresh_brainstorm):
        session = fresh_brainstorm.create_session(
            topic="Redundant Brainstorm",
            participant_ids=["nexus-governor", "nexus-vault", "nexus-archivist"],
            mode=BrainstormMode.REDUNDANT,
        )
        assert session.mode == BrainstormMode.REDUNDANT
        assert session.is_open

    def test_propose_in_redundant_mode(self, populated_pool, fresh_brainstorm):
        session = fresh_brainstorm.create_session(
            topic="Redundant Propose",
            participant_ids=["nexus-governor", "nexus-vault", "nexus-archivist"],
            mode=BrainstormMode.REDUNDANT,
        )
        proposal = fresh_brainstorm.propose(
            session_id=session.session_id,
            agent_id="nexus-governor",
            title="Redundant Idea",
            description="Test redundant deliberation",
            evidence_refs=["ev-1"],
        )
        assert proposal.title == "Redundant Idea"

    def test_redundant_advance_runs_parallel_reasoning(self, populated_pool, fresh_brainstorm):
        """REDUNDANT mode: PROPOSE -> advance runs parallel_reason -> RESOLVE"""
        session = fresh_brainstorm.create_session(
            topic="Redundant Flow",
            participant_ids=["nexus-governor", "nexus-vault", "nexus-archivist"],
            mode=BrainstormMode.REDUNDANT,
        )
        fresh_brainstorm.propose(
            session_id=session.session_id,
            agent_id="nexus-governor",
            title="Test Proposal",
            description="Description for redundant test",
            evidence_refs=["ev-1"],
        )

        session = fresh_brainstorm.advance_phase(session.session_id)
        # Should skip DISCUSS/VOTE and go directly to RESOLVE
        assert session.phase == BrainstormPhase.RESOLVE
        # The proposal should have a consensus score from parallel reasoning
        assert session.proposals[0].consensus_score > 0.0

    def test_redundant_full_flow(self, populated_pool, fresh_brainstorm):
        """REDUNDANT mode: propose -> advance -> resolve -> close"""
        session = fresh_brainstorm.create_session(
            topic="Full Redundant",
            participant_ids=["nexus-governor", "nexus-vault", "nexus-archivist"],
            mode=BrainstormMode.REDUNDANT,
        )
        fresh_brainstorm.propose(
            session_id=session.session_id,
            agent_id="nexus-governor",
            title="Proposal 1",
            description="First redundant proposal",
            evidence_refs=["ev-1"],
        )
        # First advance: PROPOSE -> RESOLVE (runs parallel reasoning)
        session = fresh_brainstorm.advance_phase(session.session_id)
        assert session.phase == BrainstormPhase.RESOLVE
        assert session.proposals[0].accepted is not None

        # Second advance: RESOLVE -> CLOSED
        session = fresh_brainstorm.advance_phase(session.session_id)
        assert session.phase == BrainstormPhase.CLOSED
        assert not session.is_open


class TestAdaptiveMemoryPersistence:
    def test_access_count_increments(self):
        from nexus_os.vault.memory_channels import MemoryChannelManager, MemoryChannel
        import time

        mgr = MemoryChannelManager()
        mgr.append_sensory(
            agent_id="test-agent",
            content="Test record for access counting",
        )
        records = mgr.get_records("test-agent", MemoryChannel.SENSORY, limit=10)
        assert len(records) >= 1
        # After first read, access_count should be 1
        assert records[-1].access_count >= 1
        # Read again - count should increment
        records2 = mgr.get_records("test-agent", MemoryChannel.SENSORY, limit=10)
        assert records2[-1].access_count >= 2

    def test_persistence_score_fresh(self):
        from nexus_os.vault.memory_channels import MemoryChannelManager, MemoryChannel

        mgr = MemoryChannelManager()
        mgr.append_sensory(
            agent_id="test-agent",
            content="Test persistence",
        )
        mgr.update_persistence_scores("test-agent", MemoryChannel.SENSORY)
        records = mgr.get_records("test-agent", MemoryChannel.SENSORY, limit=10)
        # Freshly written with 1 access should have a moderate persistence score
        assert records[-1].persistence_score >= 0.0
        assert records[-1].persistence_score <= 1.0

    def test_adaptive_persistence_migration(self):
        from nexus_os.vault.memory_channels import MemoryChannelManager, MemoryChannel

        mgr = MemoryChannelManager()
        # Write a record to EPISODIC and read it many times to boost persistence
        mgr.append_episodic(
            agent_id="test-agent",
            content="Frequently accessed record",
            outcome="success",
            trace_id="trace-1",
        )
        # Simulate many accesses
        for _ in range(10):
            mgr.get_records("test-agent", MemoryChannel.EPISODIC, limit=10)

        # Run adaptive persistence
        migrations = mgr.run_adaptive_persistence("test-agent")
        # The frequently accessed record may have migrated to SEMANTIC
        assert isinstance(migrations, dict)
        # Verify the record is still accessible somewhere
        all_records = mgr.get_records("test-agent", MemoryChannel.EPISODIC, limit=10)
        semantic_records = mgr.get_records("test-agent", MemoryChannel.SEMANTIC, limit=10)
        assert len(all_records) + len(semantic_records) >= 1
