"""nexus_os/nexusclaw/agent_pool.py — NEXUSCLAW Agent Registry

The Agent Pool is the central registry for all agents (internal and external)
that NEXUSCLAW can coordinate. Each agent has:
  - capabilities: what it can do
  - trust_score: current trust level (0-100 display scale)
  - status: online, busy, offline, degraded
  - lane: which lane it operates in (research, code, audit, etc.)
  - agent_type: internal (nexus_os) or external (grok, chatgpt, notion, etc.)
  - metadata: arbitrary config (API keys, endpoints, rate limits)

Agents are discovered automatically for internal components and registered
explicitly for external services. All agent registration goes through the
governance layer (trust score >= threshold required for active coordination).
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set

from nexus_os.vault.memory_channels import MemoryChannelManager, get_manager

logger = logging.getLogger("nexusclaw.agent_pool")


class AgentStatus(str, Enum):
    """Operational status of an agent in the pool."""
    ONLINE = "online"
    BUSY = "busy"
    OFFLINE = "offline"
    DEGRADED = "degraded"
    HALTED = "halted"


class AgentType(str, Enum):
    """Type of agent in the pool."""
    INTERNAL = "internal"      # NEXUS OS internal agent
    EXTERNAL_API = "external_api"  # External API-based agent (ChatGPT, Grok, etc.)
    EXTERNAL_MCP = "external_mcp"  # External MCP server
    HUMAN = "human"            # Human operator
    LEADER = "leader"          # Meta-reasoning agent that synthesizes multi-agent outputs


@dataclass
class AgentCapability:
    """A capability that an agent can perform."""
    name: str
    description: str
    lanes: Set[str] = field(default_factory=set)
    min_trust: float = 0.0  # Minimum trust score to use this capability
    max_risk: str = "critical"  # Maximum risk level this capability can handle

    @classmethod
    def from_any(cls, value: Any) -> "AgentCapability":
        if isinstance(value, cls):
            return value
        if isinstance(value, dict):
            return cls(
                name=str(value.get("name", "")),
                description=str(value.get("description", "")),
                lanes=set(value.get("lanes", set()) or set()),
                min_trust=float(value.get("min_trust", 0.0)),
                max_risk=str(value.get("max_risk", "critical")),
            )
        raise TypeError(f"unsupported capability type: {type(value).__name__}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "lanes": list(self.lanes),
            "min_trust": self.min_trust,
            "max_risk": self.max_risk,
        }


@dataclass
class AgentRecord:
    """A registered agent in the NEXUSCLAW pool."""
    agent_id: str
    name: str
    agent_type: AgentType
    status: AgentStatus
    trust_score: float  # 0-100 display scale
    lane: str
    capabilities: List[AgentCapability] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    registered_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_heartbeat: Optional[str] = None
    task_count: int = 0
    success_count: int = 0
    failure_count: int = 0

    def __post_init__(self) -> None:
        self._lock = threading.RLock()
        self.capabilities = [AgentCapability.from_any(cap) for cap in self.capabilities]

    @property
    def success_rate(self) -> float:
        with self._lock:
            if self.task_count == 0:
                return 0.0
            return self.success_count / self.task_count

    @property
    def is_available(self) -> bool:
        with self._lock:
            return self.status in {AgentStatus.ONLINE, AgentStatus.DEGRADED}

    def is_trusted(self, threshold: float = 60.0) -> bool:
        with self._lock:
            return self.trust_score >= threshold

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "agent_id": self.agent_id,
                "name": self.name,
                "agent_type": self.agent_type.value,
                "status": self.status.value,
                "trust_score": self.trust_score,
                "lane": self.lane,
                "capabilities": [c.to_dict() for c in self.capabilities],
                "metadata": self.metadata,
                "registered_at": self.registered_at,
                "last_heartbeat": self.last_heartbeat,
                "task_count": self.task_count,
                "success_count": self.success_count,
                "failure_count": self.failure_count,
                "success_rate": self.success_rate,
                "is_available": self.is_available,
            }

    def heartbeat(self) -> None:
        """Update last heartbeat timestamp."""
        with self._lock:
            self.last_heartbeat = datetime.now(timezone.utc).isoformat()

    def record_task(self, success: bool) -> None:
        """Record a task outcome."""
        with self._lock:
            self.task_count += 1
            if success:
                self.success_count += 1
            else:
                self.failure_count += 1


class AgentPool:
    """Central registry for all agents in the NEXUSCLAW ecosystem.

    Supports:
    - Internal agent auto-discovery from NEXUS OS components
    - External agent registration (API keys, endpoints, etc.)
    - Trust-score-based filtering
    - Capability-based matching
    - Lane-based isolation
    - Memory channel integration (writes agent state to META channel)
    """

    # Minimum trust score for an agent to be considered for task assignment
    MIN_TRUST_FOR_COORDINATION = 30.0
    # Minimum trust score for an agent to be assigned high-risk tasks
    MIN_TRUST_FOR_HIGH_RISK = 70.0

    def __init__(
        self,
        memory_channels: Optional[MemoryChannelManager] = None,
        skill_auditor: Optional[Any] = None,
        trust_kernel: Optional[Any] = None,
    ) -> None:
        self._agents: Dict[str, AgentRecord] = {}
        self._capabilities_index: Dict[str, Set[str]] = {}  # capability_name -> {agent_ids}
        self._lane_index: Dict[str, Set[str]] = {}  # lane -> {agent_ids}
        self.memory_channels = memory_channels or get_manager()
        self._skill_auditor = skill_auditor
        self._trust_kernel_override = trust_kernel
        self._kernel_failed = False
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # TrustKernel read-through (P2-2)
    #
    # The kernel is the single trust store. Pool records only MIRROR the
    # kernel posterior (0-1 → 0-100 display); registration seeds are
    # bootstrap priors, not truth, and update_trust records evidence
    # instead of assigning a score.
    # ------------------------------------------------------------------

    def _kernel(self):
        if self._trust_kernel_override is not None:
            return self._trust_kernel_override
        if self._kernel_failed:
            return None
        try:
            from nexus_os.governor.trust_kernel import get_trust_kernel
            return get_trust_kernel()
        except Exception:
            self._kernel_failed = True
            logger.warning(
                "TrustKernel unavailable; agent_pool falls back to local trust floats"
            )
            return None

    def _refresh_trust(self, agent: AgentRecord) -> None:
        """Mirror the kernel posterior into the record, if the kernel has state."""
        kernel = self._kernel()
        if kernel is None:
            return
        try:
            snap = kernel.get_snapshot(agent.agent_id, agent.lane)
            # Only mirror when the kernel actually holds a seeded prior or
            # evidence — never stomp a record with the blank 0.5 default.
            if snap.evidence_count > 0 or snap.alpha != 1.0 or snap.beta != 1.0:
                agent.trust_score = round(snap.trust * 100.0, 2)
        except Exception:
            logger.debug("Trust refresh failed for %s", agent.agent_id, exc_info=True)

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, agent: AgentRecord) -> AgentRecord:
        """Register an agent in the pool. Requires trust score >= 0 (any agent can register).

        If a SkillAuditor is configured and the agent's metadata contains a 'skill_path',
        the skill is audited before registration. Quarantined skills are rejected.
        """
        with self._lock:
            # SkillAuditor pre-flight gate
            skill_path = agent.metadata.get("skill_path")
            if self._skill_auditor is not None and skill_path:
                try:
                    report = self._skill_auditor.scan(skill_path)
                    if report.status == "quarantine":
                        from nexus_os.governor.skill_auditor import SkillAuditFailure
                        logger.warning(
                            "Agent %s skill audit FAILED (quarantine): %d critical findings",
                            agent.agent_id, report.summary.get("critical_findings", 0),
                        )
                        raise SkillAuditFailure(report)
                    logger.info(
                        "Agent %s skill audit passed (status=%s, findings=%d)",
                        agent.agent_id, report.status, len(report.findings),
                    )
                except FileNotFoundError:
                    logger.warning("Agent %s skill_path not found: %s — skipping audit", agent.agent_id, skill_path)

            if agent.agent_id in self._agents:
                logger.warning("Agent %s already registered, updating record", agent.agent_id)
                self._unindex_agent(self._agents[agent.agent_id])

            self._agents[agent.agent_id] = agent
            self._index_agent(agent)

            # P2-2: the record's trust_score is a bootstrap prior only —
            # seed it into the TrustKernel and mirror the posterior back.
            kernel = self._kernel()
            if kernel is not None:
                try:
                    snap = kernel.ensure_bootstrap_prior(
                        agent.agent_id, agent.lane, prior_trust=agent.trust_score,
                    )
                    agent.trust_score = round(snap.trust * 100.0, 2)
                except Exception:
                    logger.debug(
                        "TrustKernel prior seed failed for %s", agent.agent_id,
                        exc_info=True,
                    )

            # Write to META channel for audit
            self._log_to_memory(agent, "registered")

            logger.info(
                "Agent registered: %s (%s, %s, trust=%.1f, capabilities=%d)",
                agent.agent_id,
                agent.name,
                agent.agent_type.value,
                agent.trust_score,
                len(agent.capabilities),
            )
            return agent

    def unregister(self, agent_id: str) -> Optional[AgentRecord]:
        """Remove an agent from the pool."""
        with self._lock:
            agent = self._agents.pop(agent_id, None)
            if agent:
                self._unindex_agent(agent)
                self._log_to_memory(agent, "unregistered")
                logger.info("Agent unregistered: %s", agent_id)
            return agent

    def update_status(self, agent_id: str, status: AgentStatus) -> Optional[AgentRecord]:
        """Update an agent's status."""
        with self._lock:
            agent = self._agents.get(agent_id)
            if not agent:
                logger.warning("Agent %s not found for status update", agent_id)
                return None

            old_status = agent.status
            agent.status = status
            agent.heartbeat()

            self._log_to_memory(agent, f"status_change:{old_status.value}->{status.value}")
            logger.info("Agent %s status: %s -> %s", agent_id, old_status.value, status.value)
            return agent

    def update_trust(self, agent_id: str, trust_score: float) -> Optional[AgentRecord]:
        """Record a trust observation for an agent.

        P2-2: the TrustKernel is the single trust store. The score is
        recorded as observed evidence (Q = score/100) and the record
        mirrors the kernel's resulting posterior — an absolute score can
        no longer be assigned directly, so anti-grinding throttles, the
        non-compensatory floor, and the 99.5 cap all apply. If the kernel
        is unavailable the old clamped float assignment remains as a
        degraded fallback.
        """
        with self._lock:
            agent = self._agents.get(agent_id)
            if not agent:
                return None

            target = max(0.0, min(100.0, trust_score))
            kernel = self._kernel()
            if kernel is not None:
                try:
                    from nexus_os.governor.trust_kernel import TrustEvent
                    # Direction is carried by the risk/drift terms: a target
                    # below the current mirror is an observed regression
                    # (R/D_minus proportional to the drop), a target at or
                    # above it is a positive quality observation. Q is the
                    # quality of the OBSERVATION — for regressions it stays
                    # at a credible 0.7 (a low target used as Q would gate
                    # its own effect to zero). Single observations are
                    # deliberately damped by the equation until evidence
                    # accumulates (anti-grinding works in both directions).
                    drop = max(0.0, (agent.trust_score - target) / 100.0)
                    snap = kernel.record_event(TrustEvent(
                        agent_id=agent_id,
                        lane=agent.lane,
                        event_type="agent_pool_observation",
                        action="update_trust",
                        outcome="regression" if drop > 0 else "observed",
                        Q=0.7 if drop > 0 else target / 100.0,
                        R=drop,
                        D_minus=drop,
                        source="agent_pool",
                    ))
                    agent.trust_score = round(snap.trust * 100.0, 2)
                    self._log_to_memory(
                        agent, f"trust_update:kernel:{agent.trust_score:.1f}"
                    )
                    return agent
                except Exception:
                    logger.debug(
                        "TrustKernel trust update failed for %s", agent_id,
                        exc_info=True,
                    )

            agent.trust_score = target
            self._log_to_memory(agent, f"trust_update:{target:.1f}")
            return agent

    def set_skill_auditor(self, auditor: Any) -> None:
        """Set the SkillAuditor instance for pre-flight skill audits."""
        self._skill_auditor = auditor
        logger.info("SkillAuditor configured for AgentPool pre-flight gate")

    # ------------------------------------------------------------------
    # Discovery & Queries
    # ------------------------------------------------------------------

    def get(self, agent_id: str) -> Optional[AgentRecord]:
        """Get an agent by ID (trust mirrored from the kernel)."""
        with self._lock:
            agent = self._agents.get(agent_id)
            if agent is not None:
                self._refresh_trust(agent)
            return agent

    def list_all(self) -> List[AgentRecord]:
        """List all registered agents."""
        with self._lock:
            return list(self._agents.values())

    def list_available(self, lane: Optional[str] = None, min_trust: Optional[float] = None) -> List[AgentRecord]:
        """List agents that are available (online or degraded) and trusted."""
        with self._lock:
            threshold = min_trust if min_trust is not None else self.MIN_TRUST_FOR_COORDINATION
            for a in self._agents.values():
                self._refresh_trust(a)
            agents = [
                a for a in self._agents.values()
                if a.is_available and a.is_trusted(threshold)
            ]
            if lane:
                agents = [a for a in agents if a.lane == lane or lane in {lane for c in a.capabilities for lane in c.lanes}]
            return agents

    def find_by_capability(
        self,
        capability_name: str,
        lane: Optional[str] = None,
        min_trust: Optional[float] = None,
    ) -> List[AgentRecord]:
        """Find agents that have a specific capability."""
        with self._lock:
            agent_ids = self._capabilities_index.get(capability_name, set())
            agents = [self._agents[aid] for aid in agent_ids if aid in self._agents]

            # Filter by availability and trust (kernel-mirrored)
            for a in agents:
                self._refresh_trust(a)
            min_trust = min_trust if min_trust is not None else self.MIN_TRUST_FOR_COORDINATION
            agents = [a for a in agents if a.is_available and a.is_trusted(min_trust)]

            if lane:
                agents = [
                    a for a in agents 
                    if a.lane == lane or any(lane in cap.lanes for cap in a.capabilities if cap.name == capability_name)
                ]

            # Sort by trust score (descending) then success rate
            agents.sort(key=lambda a: (a.trust_score, a.success_rate), reverse=True)
            return agents

    def find_by_lanes(self, lanes: Set[str]) -> List[AgentRecord]:
        """Find agents that operate in any of the given lanes."""
        with self._lock:
            agent_ids: Set[str] = set()
            for lane in lanes:
                agent_ids.update(self._lane_index.get(lane, set()))

            agents = [self._agents[aid] for aid in agent_ids if aid in self._agents]
            agents = [a for a in agents if a.is_available]
            agents.sort(key=lambda a: a.trust_score, reverse=True)
            return agents

    # ------------------------------------------------------------------
    # Internal agent auto-discovery
    # ------------------------------------------------------------------

    def discover_internal_agents(self) -> List[AgentRecord]:
        """Auto-discover and register NEXUS OS internal agents."""
        discovered: List[AgentRecord] = []

        # Governor agent
        discovered.append(self._create_internal_agent(
            agent_id="nexus-governor",
            name="NEXUS Governor",
            lane="governance",
            capabilities=[
                AgentCapability("kaiju_auth", "KAIJU authentication gates", {"governance"}, 50.0, "high"),
                AgentCapability("trust_scoring", "Trust score calculation", {"governance", "audit"}, 50.0, "high"),
                AgentCapability("policy_check", "Policy compliance checking", {"governance"}, 30.0, "critical"),
            ],
            trust_score=95.0,
        ))

        # Vault agent
        discovered.append(self._create_internal_agent(
            agent_id="nexus-vault",
            name="NEXUS Vault",
            lane="memory",
            capabilities=[
                AgentCapability("memory_read", "Read from 8-channel memory", {"memory", "orchestration"}, 0.0, "low"),
                AgentCapability("memory_write", "Write to 8-channel memory", {"memory", "orchestration"}, 30.0, "medium"),
                AgentCapability("trust_gating", "Trust-gated memory access", {"memory", "governance"}, 50.0, "high"),
            ],
            trust_score=90.0,
        ))

        # ARCHIVIST agent
        discovered.append(self._create_internal_agent(
            agent_id="nexus-archivist",
            name="NEXUS ARCHIVIST",
            lane="research",
            capabilities=[
                AgentCapability("dossier_synthesis", "Synthesize dossiers from evidence", {"research", "audit"}, 40.0, "medium"),
                AgentCapability("paper_processing", "Process academic papers", {"research"}, 30.0, "low"),
                AgentCapability("evidence_ingest", "Ingest and classify evidence", {"research", "audit"}, 30.0, "medium"),
            ],
            trust_score=85.0,
        ))

        # Benchmark agent
        discovered.append(self._create_internal_agent(
            agent_id="nexus-benchmark",
            name="NEXUS Benchmark",
            lane="research",
            capabilities=[
                AgentCapability("track_evaluation", "Evaluate 5-track benchmarks", {"research", "governance"}, 50.0, "high"),
                AgentCapability("regression_detect", "Detect performance regressions", {"research"}, 40.0, "medium"),
            ],
            trust_score=80.0,
        ))

        # NEXUSCLAW itself
        discovered.append(self._create_internal_agent(
            agent_id="nexusclaw-orchestrator",
            name="NEXUSCLAW Orchestrator",
            lane="orchestration",
            capabilities=[
                AgentCapability("task_routing", "Route tasks to appropriate agents", {"orchestration"}, 50.0, "high"),
                AgentCapability("agent_coordination", "Coordinate multi-agent workflows", {"orchestration"}, 50.0, "high"),
                AgentCapability("message_dispatch", "Dispatch messages between agents", {"orchestration"}, 30.0, "medium"),
                AgentCapability("brainstorm", "Facilitate collaborative brainstorming", {"orchestration"}, 40.0, "medium"),
            ],
            trust_score=90.0,
        ))

        # FableReasoningEngine agent
        discovered.append(self._create_internal_agent(
            agent_id="nexus-reasoning",
            name="FableReasoningEngine",
            lane="reasoning",
            capabilities=[
                AgentCapability("pattern_extraction", "Extract reasoning patterns from CoT trajectories",
                                {"reasoning", "research"}, 0.0, "low"),
                AgentCapability("template_generation", "Generate structured reasoning templates",
                                {"reasoning", "orchestration"}, 0.0, "low"),
                AgentCapability("prompt_injection", "Inject reasoning templates into agent prompts",
                                {"reasoning", "orchestration"}, 20.0, "medium"),
                AgentCapability("training_data", "Generate DPO/CoT training data from patterns",
                                {"reasoning", "research", "finetune"}, 30.0, "medium"),
            ],
            trust_score=85.0,
        ))

        for agent in discovered:
            self.register(agent)

        return discovered

    def _create_internal_agent(
        self,
        agent_id: str,
        name: str,
        lane: str,
        capabilities: List[AgentCapability],
        trust_score: float,
    ) -> AgentRecord:
        return AgentRecord(
            agent_id=agent_id,
            name=name,
            agent_type=AgentType.INTERNAL,
            status=AgentStatus.ONLINE,
            trust_score=trust_score,
            lane=lane,
            capabilities=capabilities,
            metadata={"auto_discovered": True, "source": "nexus_os"},
        )

    # ------------------------------------------------------------------
    # External agent registration helpers
    # ------------------------------------------------------------------

    def register_external_api(
        self,
        agent_id: str,
        name: str,
        lane: str,
        capabilities: List[AgentCapability],
        api_endpoint: Optional[str] = None,
        rate_limit: Optional[str] = None,
        trust_score: float = 50.0,
    ) -> AgentRecord:
        """Register an external API-based agent (e.g., ChatGPT, Grok, Notion)."""
        agent = AgentRecord(
            agent_id=agent_id,
            name=name,
            agent_type=AgentType.EXTERNAL_API,
            status=AgentStatus.ONLINE,
            trust_score=trust_score,
            lane=lane,
            capabilities=capabilities,
            metadata={
                "api_endpoint": api_endpoint,
                "rate_limit": rate_limit,
                "source": "external_api",
            },
        )
        return self.register(agent)

    def register_human(self, agent_id: str, name: str, lane: str = "orchestration") -> AgentRecord:
        """Register a human operator."""
        agent = AgentRecord(
            agent_id=agent_id,
            name=name,
            agent_type=AgentType.HUMAN,
            status=AgentStatus.ONLINE,
            trust_score=100.0,  # Humans have full trust
            lane=lane,
            capabilities=[
                AgentCapability("human_oversight", "Human oversight and approval", set(), 100.0, "critical"),
            ],
            metadata={"source": "human"},
        )
        return self.register(agent)

    # ------------------------------------------------------------------
    # Indexing
    # ------------------------------------------------------------------

    def _index_agent(self, agent: AgentRecord) -> None:
        for cap in agent.capabilities:
            self._capabilities_index.setdefault(cap.name, set()).add(agent.agent_id)
        self._lane_index.setdefault(agent.lane, set()).add(agent.agent_id)
        for cap in agent.capabilities:
            for lane in cap.lanes:
                self._lane_index.setdefault(lane, set()).add(agent.agent_id)

    def _unindex_agent(self, agent: AgentRecord) -> None:
        for cap in agent.capabilities:
            self._capabilities_index.get(cap.name, set()).discard(agent.agent_id)
        self._lane_index.get(agent.lane, set()).discard(agent.agent_id)
        for cap in agent.capabilities:
            for lane in cap.lanes:
                self._lane_index.get(lane, set()).discard(agent.agent_id)

    # ------------------------------------------------------------------
    # Memory integration
    # ------------------------------------------------------------------

    def _log_to_memory(self, agent: AgentRecord, event: str) -> None:
        """Write agent pool events to META channel for audit."""
        try:
            self.memory_channels.append_meta(
                agent_id=agent.agent_id,
                meta_type="agent_pool_event",
                meta_value=agent.trust_score,
                content=f"Agent {agent.agent_id}: {event}",
                trust_score=100.0,  # Agent pool events are authoritative
            )
        except Exception as e:
            logger.warning("Failed to log agent pool event to memory: %s", e)

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        """Return pool statistics."""
        with self._lock:
            all_agents = self.list_all()
            available = self.list_available()
            return {
                "total_agents": len(all_agents),
                "available_agents": len(available),
                "by_type": {
                    t.value: len([a for a in all_agents if a.agent_type == t])
                    for t in AgentType
                },
                "by_status": {
                    s.value: len([a for a in all_agents if a.status == s])
                    for s in AgentStatus
                },
                "avg_trust": sum(a.trust_score for a in all_agents) / len(all_agents) if all_agents else 0.0,
                "capabilities": {k: len(v) for k, v in self._capabilities_index.items()},
            }


# Singleton pool instance
_pool_instance: Optional[AgentPool] = None


def get_agent_pool(memory_channels: Optional[MemoryChannelManager] = None) -> AgentPool:
    """Get the singleton AgentPool instance."""
    global _pool_instance
    if _pool_instance is None:
        _pool_instance = AgentPool(memory_channels=memory_channels)
    return _pool_instance
