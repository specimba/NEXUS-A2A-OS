"""tests/nexusclaw/conftest.py — NEXUSCLAW test fixtures and evidence infrastructure.

Provides:
  - Realistic agent simulation (mock LLM responses, trust profiles)
  - Evidence logging with BLAKE3 hashes and VAP proof chains
  - Memory channel snapshots for state verification
  - Deterministic time control for timeout/escalation tests
  - Multi-agent swarm simulation fixtures
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

import pytest

from nexus_os.nexusclaw.agent_pool import AgentPool, AgentRecord, AgentStatus, AgentType, get_agent_pool
from nexus_os.nexusclaw.message_bus import MessageBus, NexusMessage, MessageType, MessagePriority
from nexus_os.nexusclaw.task_router import TaskRouter, TaskAssignment, RoutingStrategy, get_task_router
from nexus_os.nexusclaw.orchestrator import NexusClawOrchestrator
from nexus_os.nexusclaw.brainstorm import BrainstormEngine, Proposal, RiskLevel
from nexus_os.nexusclaw.envelope import NexusClawTaskEnvelope
from nexus_os.vault.memory_channels import MemoryChannelManager, get_manager
from nexus_os.governor.trust_engine_v2 import TrustEngineV2
from nexus_os.governor.skill_auditor import SkillAuditor


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nexusclaw.tests")


# ── Evidence Logging Infrastructure ───────────────────────────────────────────


@dataclass
class TestEvidence:
    """Evidence record for a test execution with cryptographic proof."""
    test_name: str
    timestamp: str
    blake3_hash: str
    sha256_hash: str
    artifacts: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    vap_proof_chain: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_name": self.test_name,
            "timestamp": self.timestamp,
            "blake3_hash": self.blake3_hash,
            "sha256_hash": self.sha256_hash,
            "artifacts": self.artifacts,
            "metadata": self.metadata,
            "vap_proof_chain": self.vap_proof_chain,
        }


class EvidenceLogger:
    """Logs test evidence with cryptographic integrity and VAP proof chains."""

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._proof_chain: List[str] = []

    def log_evidence(
        self,
        test_name: str,
        artifacts: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TestEvidence:
        """Log evidence with BLAKE3/SHA256 hashes and VAP proof chain."""
        timestamp = datetime.now(timezone.utc).isoformat()

        # Serialize artifacts deterministically
        serialized = json.dumps(artifacts, sort_keys=True, separators=(",", ":"))
        blake3_hash = self._blake3(serialized.encode("utf-8"))
        sha256_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()

        # Append to VAP proof chain
        proof_entry = f"{timestamp}:{blake3_hash}"
        self._proof_chain.append(proof_entry)

        evidence = TestEvidence(
            test_name=test_name,
            timestamp=timestamp,
            blake3_hash=blake3_hash,
            sha256_hash=sha256_hash,
            artifacts=artifacts,
            metadata=metadata or {},
            vap_proof_chain=list(self._proof_chain),
        )

        # Write evidence file
        evidence_file = self.output_dir / f"{test_name}_{int(time.time() * 1000)}.json"
        with open(evidence_file, "w", encoding="utf-8") as f:
            json.dump(evidence.to_dict(), f, indent=2, ensure_ascii=False)

        logger.info(
            "Evidence logged: %s (BLAKE3=%s, SHA256=%s)",
            test_name, blake3_hash[:16], sha256_hash[:16],
        )
        return evidence

    @staticmethod
    def _blake3(data: bytes) -> str:
        """Compute BLAKE3 hash (pure Python fallback if blake3 not installed)."""
        try:
            import blake3
            return blake3.blake3(data).hexdigest()
        except ImportError:
            # Fallback to SHA256 if blake3 not available
            return hashlib.sha256(data).hexdigest()

    def get_proof_chain(self) -> List[str]:
        return list(self._proof_chain)

    def export_vap_report(self, output_path: Path) -> None:
        """Export VAP proof chain report."""
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "proof_chain_length": len(self._proof_chain),
            "proof_chain": self._proof_chain,
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)


# ── Agent Simulation Fixtures ─────────────────────────────────────────────────


@dataclass
class MockAgentProfile:
    """Simulated agent profile for testing."""
    agent_id: str
    name: str
    agent_type: AgentType
    lane: str
    trust_score: float
    capabilities: List[str]  # List of capability names
    success_rate: float
    avg_response_time_ms: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_agent_record(self) -> AgentRecord:
        from nexus_os.nexusclaw.agent_pool import AgentCapability
        caps = [AgentCapability(name=cap, description=f"Capability: {cap}", lanes={self.lane}) for cap in self.capabilities]
        return AgentRecord(
            agent_id=self.agent_id,
            name=self.name,
            agent_type=self.agent_type,
            lane=self.lane,
            trust_score=self.trust_score,
            capabilities=caps,
            status=AgentStatus.ONLINE,
            metadata=self.metadata,
        )


# Pre-defined agent profiles for realistic simulation
MOCK_AGENT_PROFILES = {
    "code_specialist": MockAgentProfile(
        agent_id="agent-code-001",
        name="CodeWarden",
        agent_type=AgentType.INTERNAL,
        lane="operations",
        trust_score=85.0,
        capabilities=["code_review", "refactoring", "debugging", "testing"],
        success_rate=0.92,
        avg_response_time_ms=450.0,
        metadata={"skill_path": "skills/code_review.yaml"},
    ),
    "security_analyst": MockAgentProfile(
        agent_id="agent-sec-001",
        name="Guardian",
        agent_type=AgentType.INTERNAL,
        lane="security",
        trust_score=90.0,
        capabilities=["threat_detection", "vulnerability_scan", "compliance_audit"],
        success_rate=0.95,
        avg_response_time_ms=600.0,
        metadata={"skill_path": "skills/security_audit.yaml"},
    ),
    "research_assistant": MockAgentProfile(
        agent_id="agent-res-001",
        name="Scholar",
        agent_type=AgentType.INTERNAL,
        lane="research",
        trust_score=75.0,
        capabilities=["deep_research", "summarization", "citation_extraction"],
        success_rate=0.88,
        avg_response_time_ms=800.0,
        metadata={"skill_path": "skills/research.yaml"},
    ),
    "governance_oracle": MockAgentProfile(
        agent_id="agent-gov-001",
        name="Kaiju",
        agent_type=AgentType.INTERNAL,
        lane="governance",
        trust_score=99.0,
        capabilities=["policy_enforcement", "trust_evaluation", "compliance_check"],
        success_rate=0.99,
        avg_response_time_ms=200.0,
        metadata={"skill_path": "skills/governance.yaml"},
    ),
    "low_trust_worker": MockAgentProfile(
        agent_id="agent-low-001",
        name="Rookie",
        agent_type=AgentType.INTERNAL,
        lane="operations",
        trust_score=35.0,
        capabilities=["data_entry", "basic_processing"],
        success_rate=0.65,
        avg_response_time_ms=1200.0,
        metadata={},
    ),
}


@pytest.fixture
def evidence_logger(tmp_path: Path) -> EvidenceLogger:
    """Create an evidence logger for the test."""
    evidence_dir = tmp_path / "evidence"
    return EvidenceLogger(evidence_dir)


@pytest.fixture
def agent_pool_fixture() -> AgentPool:
    """Create a fresh AgentPool instance with memory channels."""
    memory_mgr = get_manager()
    pool = get_agent_pool(memory_channels=memory_mgr)
    # Reset singleton for clean test state
    from nexus_os.nexusclaw import agent_pool
    agent_pool._pool_instance = pool
    return pool


@pytest.fixture
def message_bus_fixture(agent_pool_fixture: AgentPool) -> MessageBus:
    """Create a fresh MessageBus instance."""
    bus = MessageBus(agent_pool=agent_pool_fixture)
    return bus


@pytest.fixture
def task_router_fixture(agent_pool_fixture: AgentPool) -> TaskRouter:
    """Create a fresh TaskRouter instance."""
    from nexus_os.nexusclaw import task_router
    # Reset singleton to ensure fresh router with our agent pool
    task_router._task_router_instance = None
    router = get_task_router()
    router.agent_pool = agent_pool_fixture
    return router


@pytest.fixture
def brainstorm_fixture(agent_pool_fixture: AgentPool) -> BrainstormEngine:
    """Create a fresh BrainstormEngine instance."""
    engine = BrainstormEngine(agent_pool=agent_pool_fixture)
    return engine


@pytest.fixture
def registered_agents(agent_pool_fixture: AgentPool) -> Dict[str, AgentRecord]:
    """Register all mock agent profiles and return them."""
    registered = {}
    for profile in MOCK_AGENT_PROFILES.values():
        record = profile.to_agent_record()
        agent_pool_fixture.register(record)
        registered[profile.agent_id] = record
    return registered


@pytest.fixture
def orchestrator_fixture(
    agent_pool_fixture: AgentPool,
    message_bus_fixture: MessageBus,
    task_router_fixture: TaskRouter,
) -> NexusClawOrchestrator:
    """Create a fully wired Orchestrator instance."""
    orchestrator = NexusClawOrchestrator(
        agent_pool=agent_pool_fixture,
        message_bus=message_bus_fixture,
        task_router=task_router_fixture,
    )
    return orchestrator


@pytest.fixture
def trust_engine_fixture() -> TrustEngineV2:
    """Create a TrustEngineV2 instance (stateless mode)."""
    return TrustEngineV2(vault=None, baseline=25.0)


@pytest.fixture
def skill_auditor_fixture() -> SkillAuditor:
    """Create a SkillAuditor instance."""
    return SkillAuditor()


# ── Helper Functions ──────────────────────────────────────────────────────────


def create_mock_task(
    task_id: Optional[str] = None,
    source: str = "test",
    lane: str = "operations",
    intent: str = "Test task for validation",
    required_capabilities: Optional[List[str]] = None,
    risk_level: RiskLevel = RiskLevel.LOW,
) -> NexusClawTaskEnvelope:
    """Create a mock task envelope for testing."""
    return NexusClawTaskEnvelope(
        task_id=task_id or f"task-{uuid4().hex[:8]}",
        source=source,
        lane=lane,
        intent=intent,
        risk_level=risk_level,
        required_capabilities=required_capabilities or [],
    )


def create_mock_proposal(
    proposal_id: Optional[str] = None,
    session_id: str = "test-session",
    agent_id: str = "test-agent",
    agent_name: str = "Test Agent",
    title: str = "Test Proposal",
    description: str = "A test proposal",
    risk_level: RiskLevel = RiskLevel.MEDIUM,
    evidence_refs: Optional[List[str]] = None,
) -> Proposal:
    """Create a mock brainstorm proposal."""
    return Proposal(
        proposal_id=proposal_id or f"prop-{uuid4().hex[:8]}",
        session_id=session_id,
        agent_id=agent_id,
        agent_name=agent_name,
        title=title,
        description=description,
        risk_level=risk_level,
        evidence_refs=evidence_refs or [],
    )


def snapshot_memory_channels(manager: MemoryChannelManager, agent_id: str) -> Dict[str, Any]:
    """Snapshot all memory channels for an agent."""
    snapshot = {}
    for channel in manager._buffers.get(agent_id, {}).keys():
        records = manager._buffers[agent_id][channel]
        snapshot[channel.name] = [
            {
                "channel": r.channel.name if hasattr(r, 'channel') else str(channel),
                "content": r.content[:100] if len(r.content) > 100 else r.content,
                "timestamp": r.timestamp,
            }
            for r in records
        ]
    return snapshot


# ── Pytest Hooks ──────────────────────────────────────────────────────────────


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires multiple components)"
    )
    config.addinivalue_line(
        "markers", "e2e: mark test as end-to-end test (full orchestrator workflow)"
    )
    config.addinivalue_line(
        "markers", "stress: mark test as stress/load test"
    )
    config.addinivalue_line(
        "markers", "governance: mark test as governance/trust test"
    )
    config.addinivalue_line(
        "markers", "swarm: mark test as swarm coordination test"
    )
    config.addinivalue_line(
        "markers", "phase_d: mark test as Phase D evidence integration test"
    )