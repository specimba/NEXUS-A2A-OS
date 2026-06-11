"""tests/test_nexusclaw_hardening.py - Concurrency and safety tests for NEXUSCLAW v1.

Tests cover:
  - TaskRouter concurrent updates thread safety
  - BrainstormEngine concurrent proposals, comments, and votes thread safety
  - BrainstormEngine voting quorum check enforcements
  - MessageBus external message connector dispatching
  - runner signal handler event loop fallback safety
"""

from __future__ import annotations

import asyncio
import threading
import time
import pytest
from typing import Any, Dict, List

from nexus_os.nexusclaw.agent_pool import AgentPool, AgentRecord, AgentStatus, AgentType, AgentCapability
from nexus_os.nexusclaw.task_router import TaskRouter, RoutingStrategy
from nexus_os.nexusclaw.message_bus import MessageBus, NexusMessage, MessageType, MessagePriority
from nexus_os.nexusclaw.brainstorm import BrainstormEngine, BrainstormMode, BrainstormPhase, VoteChoice
from nexus_os.nexusclaw.orchestrator import NexusClawOrchestrator
from nexus_os.nexusclaw.runner import install_signal_handlers
from nexus_os.nexusclaw.envelope import NexusClawTaskEnvelope, RiskLevel


# Mock connector for MessageBus testing
class MockConnector:
    def __init__(self):
        self.sent_messages: List[Dict[str, Any]] = []

    async def send_message(self, **kwargs) -> Any:
        self.sent_messages.append(kwargs)
        # Mock result class matching MessageResult structure
        class MockResult:
            def to_dict(self):
                return {"success": True}
        return MockResult()


@pytest.fixture
def clean_pool():
    pool = AgentPool()
    pool.discover_internal_agents()
    return pool


@pytest.fixture
def clean_router(clean_pool):
    return TaskRouter(agent_pool=clean_pool)


@pytest.fixture
def clean_bus(clean_pool):
    return MessageBus(agent_pool=clean_pool)


@pytest.fixture
def clean_brainstorm(clean_pool, clean_bus):
    return BrainstormEngine(agent_pool=clean_pool, message_bus=clean_bus)


# ------------------------------------------------------------------
# Task Router Concurrency Tests
# ------------------------------------------------------------------

def test_task_router_concurrency(clean_router):
    """Verify that TaskRouter does not crash under concurrent routing and completion operations."""
    errors = []

    def route_worker(index: int):
        try:
            task = NexusClawTaskEnvelope(
                task_id=f"concurrent-task-{index}",
                source="test-concurrency",
                lane="governance",
                intent="concurrent policy check",
                risk_level=RiskLevel.LOW,
                required_capabilities=["policy_check"],
            )
            # Concurrent routing
            clean_router.route(task, strategy=RoutingStrategy.DIRECT)
            time.sleep(0.01)
            # Concurrent load checks
            clean_router.get_agent_load("nexus-governor")
            # Concurrent completion
            clean_router.complete_assignment(f"concurrent-task-{index}", "nexus-governor", success=True)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=route_worker, args=(i,)) for i in range(50)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0, f"Encountered concurrency errors: {errors}"


# ------------------------------------------------------------------
# Brainstorm Engine Concurrency Tests
# ------------------------------------------------------------------

def test_brainstorm_engine_concurrency(clean_brainstorm, clean_pool):
    """Verify that BrainstormEngine handles concurrent proposals, comments, and votes."""
    errors = []
    
    session = clean_brainstorm.create_session(
        topic="Concurrent deliberation topic",
        participant_ids=["nexus-governor", "nexus-vault", "nexus-archivist"],
        mode=BrainstormMode.STRUCTURED,
    )

    def brainstorm_worker(index: int):
        try:
            # Alternate propose, comment, and vote actions to create concurrent mutations
            if index % 3 == 0:
                clean_brainstorm.propose(
                    session_id=session.session_id,
                    agent_id="nexus-governor",
                    title=f"Idea {index}",
                    description="Concurrent description",
                    evidence_refs=["ev-1"],
                )
            elif index % 3 == 1:
                # Need to check proposals before commenting
                with clean_brainstorm._lock:
                    props = list(session.proposals)
                if props:
                    clean_brainstorm.discuss(
                        session_id=session.session_id,
                        agent_id="nexus-vault",
                        proposal_id=props[0].proposal_id,
                        comment=f"Comment {index}",
                    )
            else:
                with clean_brainstorm._lock:
                    props = list(session.proposals)
                if props:
                    clean_brainstorm.vote(
                        session_id=session.session_id,
                        agent_id="nexus-archivist",
                        proposal_id=props[0].proposal_id,
                        choice=VoteChoice.FOR,
                    )
        except Exception as e:
            # Disregard ValueError related to phase enforcements (e.g. proposing in discuss phase)
            if not isinstance(e, ValueError):
                errors.append(e)

    threads = [threading.Thread(target=brainstorm_worker, args=(i,)) for i in range(50)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0, f"Encountered brainstorm concurrency errors: {errors}"


# ------------------------------------------------------------------
# Brainstorm voting quorum enforcements
# ------------------------------------------------------------------

def test_brainstorm_quorum_enforcement(clean_brainstorm):
    """Verify that structured sessions cannot resolve without meeting the voting quorum."""
    session = clean_brainstorm.create_session(
        topic="Consensus Quorum Test",
        participant_ids=["nexus-governor", "nexus-vault", "nexus-archivist"],
        mode=BrainstormMode.STRUCTURED,
    )
    proposal = clean_brainstorm.propose(
        session_id=session.session_id,
        agent_id="nexus-governor",
        title="Quorum Idea",
        description="Must be voted on",
        evidence_refs=["ev-1"],
    )

    # Transition from PROPOSE -> DISCUSS
    clean_brainstorm.advance_phase(session.session_id)
    # Transition from DISCUSS -> VOTE
    clean_brainstorm.advance_phase(session.session_id)

    # Attempt to transition from VOTE -> RESOLVE with ZERO other participant votes
    with pytest.raises(ValueError, match="Quorum not met"):
        clean_brainstorm.advance_phase(session.session_id)

    # Now, cast a vote from another participant (nexus-vault)
    clean_brainstorm.vote(
        session_id=session.session_id,
        agent_id="nexus-vault",
        proposal_id=proposal.proposal_id,
        choice=VoteChoice.FOR,
    )

    # Attempt to transition to RESOLVE again; should succeed now that quorum is met
    session = clean_brainstorm.advance_phase(session.session_id)
    assert session.phase == BrainstormPhase.RESOLVE
    assert proposal.accepted is True


# ------------------------------------------------------------------
# Message Bus External Messaging Bridge
# ------------------------------------------------------------------

def test_message_bus_external_connector_dispatch(clean_bus):
    """Verify that sending an EXTERNAL_OUT message triggers the registered connector."""
    mock_slack = MockConnector()
    clean_bus.register_external_connector("slack", mock_slack)

    message = NexusMessage(
        message_id="msg-ext-test-1",
        sender_id="nexus-governor",
        sender_name="Governor",
        recipient_ids=[],
        message_type=MessageType.EXTERNAL_OUT,
        content="Notify channel about policy changes",
        priority=MessagePriority.NORMAL,
        metadata={"platform": "slack", "target": "general-channel"},
    )

    result = clean_bus.send(message)
    assert result.delivered is True
    assert result.metadata.get("external_connector_dispatched") is True
    
    # Wait briefly for background thread/coroutine execution
    time.sleep(0.1)
    
    assert len(mock_slack.sent_messages) == 1
    assert mock_slack.sent_messages[0]["channel"] == "general-channel"
    assert mock_slack.sent_messages[0]["text"] == "Notify channel about policy changes"


# ------------------------------------------------------------------
# Runner Signal Handler event loop fallback
# ------------------------------------------------------------------

def test_runner_signal_handlers_fallback():
    """Verify that install_signal_handlers does not raise RuntimeError outside main loop thread."""
    # Running inside standard test execution thread (no active asyncio loop)
    # The call should log a warning but execute with exit code 0.
    try:
        install_signal_handlers()
        success = True
    except RuntimeError:
        success = False

    assert success is True
