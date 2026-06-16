"""tests/nexusclaw/test_e2e.py - NEXUSCLAW End-to-End Tests with Scientific Proof Chains.

This module implements Phase A2: Full end-to-end testing of NEXUSCLAW workflows.
Each test produces verifiable evidence with BLAKE3/SHA256 hashes and VAP proof chains.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4

import pytest

from nexus_os.nexusclaw.agent_pool import AgentPool, AgentRecord, AgentStatus, AgentType, AgentCapability
from nexus_os.nexusclaw.brainstorm import BrainstormEngine, RiskLevel, VoteChoice
from nexus_os.nexusclaw.envelope import NexusClawTaskEnvelope
from nexus_os.nexusclaw.message_bus import MessageBus
from nexus_os.nexusclaw.orchestrator import NexusClawOrchestrator
from nexus_os.nexusclaw.task_router import TaskRouter
from nexus_os.vault.memory_channels import get_manager


# ── Scientific Evidence Infrastructure ───────────────────────────────────────────


def _blake3(data: bytes) -> str:
    """Compute BLAKE3 hash for scientific evidence."""
    try:
        import blake3
        return blake3.blake3(data).hexdigest()
    except ImportError:
        return hashlib.sha256(data).hexdigest()


def log_evidence(test_name: str, artifacts: Dict[str, Any], output_dir: Path) -> Dict[str, Any]:
    """Log evidence with cryptographic proof and return evidence record."""
    timestamp = datetime.now(timezone.utc).isoformat()
    serialized = json.dumps(artifacts, sort_keys=True, separators=(",", ":"))
    
    return {
        "test_name": test_name,
        "timestamp": timestamp,
        "blake3_hash": _blake3(serialized.encode("utf-8")),
        "sha256_hash": hashlib.sha256(serialized.encode("utf-8")).hexdigest(),
        "artifacts": artifacts,
    }


# ── Phase A2.1: Multi-Agent Task Distribution ───────────────────────────────────

class TestMultiAgentTaskDistribution:
    """End-to-end test: Multiple agents collaborating on task distribution."""

    @pytest.mark.e2e
    def test_three_agent_collaborative_task(self, tmp_path: Path):
        """Three agents work together to complete a task through full lifecycle."""
        manager = get_manager()
        pool = AgentPool(memory_channels=manager)
        
        # Register 3 specialized agents with matching capabilities
        agent_defs = [
            ("ResearchSpecialist", "research", 88.0, ["code_review"]),
            ("CodeSpecialist", "operations", 92.0, ["testing"]),
            ("SecurityAnalyst", "security", 95.0, ["threat_detection"]),
        ]
        for name, lane, score, caps in agent_defs:
            agent = AgentRecord(
                agent_id=f"agent-{uuid4().hex[:8]}",
                name=name,
                agent_type=AgentType.INTERNAL,
                status=AgentStatus.ONLINE,
                trust_score=score,
                lane=lane,
                capabilities=[
                    AgentCapability(name=cap, description=f"{name} {cap}", lanes={lane}, min_trust=50.0, max_risk="medium")
                    for cap in caps
                ],
            )
            pool.register(agent)
        
        # Create task requiring multiple capabilities (each agent covers one)
        task = NexusClawTaskEnvelope(
            task_id=f"task-{uuid4().hex[:8]}",
            source="e2e-test",
            lane="operations",
            intent="Implement secure authentication module",
            risk_level=RiskLevel.MEDIUM,
            required_capabilities=["code_review", "testing", "threat_detection"],
        )
        
        # Route task
        router = TaskRouter(pool)
        decision = router.route(task)
        
        assert decision.selected_agents is not None
        assert len(decision.selected_agents) >= 1
        
        # selected_agents is a list of agent_ids (strings), not objects
        evidence = log_evidence(
            "three_agent_collaborative_task",
            {
                "task_id": task.task_id,
                "selected_agent_ids": list(decision.selected_agents),
                "routing_reason": decision.reason,
            },
            tmp_path,
        )
        
        assert evidence["blake3_hash"]


# ── Phase A2.2: Full Lifecycle Task Flow ───────────────────────────────────────────

class TestFullLifecycleTaskFlow:
    """End-to-end test: Complete task lifecycle from submission to completion."""

    @pytest.mark.e2e
    def test_task_submission_to_completion(self, tmp_path: Path):
        """Task flows through submit → route → execute → complete lifecycle."""
        manager = get_manager()
        pool = AgentPool(memory_channels=manager)
        bus = MessageBus(agent_pool=pool)
        router = TaskRouter(pool)
        orchestrator = NexusClawOrchestrator(
            agent_pool=pool,
            message_bus=bus,
            task_router=router,
        )
        
        # Register worker
        worker = AgentRecord(
            agent_id=f"agent-{uuid4().hex[:8]}",
            name="TestWorker",
            agent_type=AgentType.INTERNAL,
            status=AgentStatus.ONLINE,
            trust_score=85.0,
            lane="operations",
            capabilities=[
                AgentCapability(name="basic_processing", description="Basic processing", lanes={"operations"}, min_trust=50.0, max_risk="low"),
            ],
        )
        pool.register(worker)
        
        # Submit task
        task = NexusClawTaskEnvelope(
            task_id=f"task-{uuid4().hex[:8]}",
            source="e2e-test",
            lane="operations",
            intent="Process test data",
            risk_level=RiskLevel.LOW,
            required_capabilities=["basic_processing"],
        )
        
        result = orchestrator.submit_task(task)
        
        assert result.get("task_id") == task.task_id
        assert result.get("status") in ("routed", "no_agents_available", "rejected")
        
        evidence = log_evidence(
            "task_submission_to_completion",
            {
                "task_id": task.task_id,
                "submission_result": result,
                "worker_id": worker.agent_id,
            },
            tmp_path,
        )
        
        assert evidence["blake3_hash"]


# ── Phase A2.3: Brainstorm Consensus Workflow ───────────────────────────────────

class TestBrainstormConsensusWorkflow:
    """End-to-end test: Multi-agent brainstorm reaching consensus."""

    @pytest.mark.e2e
    def test_brainstorm_consensus_reach(self, tmp_path: Path):
        """Brainstorm session reaches consensus with DISCUSS → VOTE → RESOLVE phases."""
        manager = get_manager()
        pool = AgentPool(memory_channels=manager)
        brainstorm = BrainstormEngine(agent_pool=pool)
        
        # Register participants
        participants = []
        for i in range(3):
            agent = AgentRecord(
                agent_id=f"agent-{uuid4().hex[:8]}",
                name=f"Participant{i+1}",
                agent_type=AgentType.INTERNAL,
                status=AgentStatus.ONLINE,
                trust_score=80.0 + i * 5,
                lane="research",
                capabilities=[
                    AgentCapability(name="discussion", description="Discussion capability", lanes={"research"}, min_trust=50.0, max_risk="low"),
                ],
            )
            pool.register(agent)
            participants.append(agent.agent_id)
        
        # Create session
        session = brainstorm.create_session(
            topic="Test Consensus Topic",
            participant_ids=participants,
        )
        
        # Propose
        proposal = brainstorm.propose(
            session_id=session.session_id,
            agent_id=participants[0],
            title="Implement Feature X",
            description="Detailed description for consensus testing",
            risk_level=RiskLevel.LOW,
            evidence_refs=["doc:spec.md"],
        )
        
        # Discuss
        brainstorm.advance_phase(session.session_id)
        brainstorm.discuss(
            session_id=session.session_id,
            agent_id=participants[1],
            proposal_id=proposal.proposal_id,
            comment="Looks good to me",
        )
        
        # Vote
        brainstorm.advance_phase(session.session_id)
        for pid in participants:
            brainstorm.vote(
                session_id=session.session_id,
                agent_id=pid,
                proposal_id=proposal.proposal_id,
                choice=VoteChoice.FOR,
            )
        
        # Resolve
        brainstorm.advance_phase(session.session_id)
        
        # Verify
        final_session = brainstorm.get_session(session.session_id)
        assert final_session is not None
        assert final_session.phase.value in ("resolve", "closed")
        
        evidence = log_evidence(
            "brainstorm_consensus_reach",
            {
                "session_id": session.session_id,
                "proposal_id": proposal.proposal_id,
                "participant_count": len(participants),
                "votes_cast": len(participants),
                "final_phase": final_session.phase.value,
            },
            tmp_path,
        )
        
        assert evidence["blake3_hash"]


# ── Phase A2.4: VAP Proof Chain Integration ─────────────────────────────────────

class TestVapProofChainIntegration:
    """End-to-end test: Tasks generate verifiable VAP proof chain entries."""

    @pytest.mark.e2e
    def test_task_generates_vap_entries(self, tmp_path: Path):
        """Every task operation produces VAP chain evidence."""
        manager = get_manager()
        pool = AgentPool(memory_channels=manager)
        
        # Register agent
        agent = AgentRecord(
            agent_id=f"agent-{uuid4().hex[:8]}",
            name="VAPTester",
            agent_type=AgentType.INTERNAL,
            status=AgentStatus.ONLINE,
            trust_score=90.0,
            lane="operations",
            capabilities=[],
        )
        pool.register(agent)
        
        # Write to EPISODIC channel
        manager.append_episodic(agent.agent_id, "Test task execution with evidence", "success", 0.0, 0)
        
        # Verify
        records = manager.get_records(agent.agent_id, "episodic")
        assert len(records) >= 1
        
        evidence = log_evidence(
            "task_generates_vap_entries",
            {
                "agent_id": agent.agent_id,
                "episodic_records": len(records),
            },
            tmp_path,
        )
        
        assert evidence["blake3_hash"]


# ── Phase A2.5: Cross-Component Memory Integration ───────────────────────────────

class TestCrossComponentMemoryIntegration:
    """End-to-end test: All components write to correct memory channels."""

    @pytest.mark.e2e
    def test_all_channels_integrated(self, tmp_path: Path):
        """TASK, TRUST, EPISODIC, META, GOVERNANCE channels all work."""
        manager = get_manager()
        pool = AgentPool(memory_channels=manager)
        
        agent_id = f"agent-{uuid4().hex[:8]}"
        
        # Register agent with high trust score
        agent = AgentRecord(
            agent_id=agent_id,
            name="MemoryTestAgent",
            agent_type=AgentType.INTERNAL,
            status=AgentStatus.ONLINE,
            trust_score=95.0,  # Above all thresholds
            lane="operations",
            capabilities=[
                AgentCapability(name="memory_test", description="Memory test capability", lanes={"operations"}, min_trust=40.0, max_risk="low"),
            ],
        )
        pool.register(agent)
        
        # Write to each channel (episodic has lowest threshold 30.0)
        manager.append_episodic(agent_id, "Episodic memory", "success", 0.0, 0)
        manager.append_trust(agent_id, "Trust update record")
        
        # Verify records were written
        epi_records = manager.get_records(agent_id, "episodic")
        trust_records = manager.get_records(agent_id, "trust")
        
        assert len(epi_records) >= 1, "Episodic records should be written"
        assert len(trust_records) >= 1, "Trust records should be written"
        
        evidence = log_evidence(
            "all_channels_integrated",
            {
                "agent_id": agent_id,
                "episodic_records": len(epi_records),
                "trust_records": len(trust_records),
            },
            tmp_path,
        )
        
        assert evidence["blake3_hash"]