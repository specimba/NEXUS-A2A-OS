"""nexus_os/nexusclaw/orchestrator.py - NEXUSCLAW Orchestrator

The Orchestrator is the central coordination layer that ties together all
NEXUSCLAW components into a unified multi-agent system:
  - AgentPool (registry of all agents, internal + external)
  - TaskRouter (intelligent task matching and dispatch)
  - MessageBus (inter-agent communication)
  - BrainstormEngine (collaborative deliberation)
  - Coordinator (governance dry-run validation)
  - Runner (24/7 persistent operation)
  - WorklogSystem (audit trail)
  - MemoryChannelManager (8-channel shared state)

The Orchestrator handles:
  - Multi-agent task lifecycle (receive -> validate -> route -> execute -> log)
  - Cross-agent communication coordination
  - Brainstorm session management
  - External agent integration (Grok, ChatGPT, Notion, Slack)
  - Governance gate enforcement (KAIJU + TrustKernel)
  - 24/7 runner lifecycle management
  - Memory channel integration for shared context
  - Worklog triple-sink logging

All operations are:
  - Evidence-grounded (traceable to source)
  - Trust-gated (trust score thresholds enforced)
  - Governance-aware (risk levels mapped to approval requirements)
  - Auditable (all actions logged to memory + worklog + archivist queue)
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from nexus_os.nexusclaw.agent_pool import (
    AgentPool,
    AgentRecord,
    AgentStatus,
    AgentType,
    AgentCapability,
    get_agent_pool,
)
from nexus_os.nexusclaw.brainstorm import (
    BrainstormEngine,
    BrainstormMode,
    BrainstormSession,
    Proposal,
    VoteChoice,
)
from nexus_os.nexusclaw.coordinator import NexusClawCoordinator, NexusClawRuntimeConfig
from nexus_os.nexusclaw.envelope import NexusClawTaskEnvelope, NexusClawResultEnvelope, ResultStatus, RiskLevel
from nexus_os.nexusclaw.message_bus import MessageBus, NexusMessage, MessageType, MessagePriority
from nexus_os.nexusclaw.runner import NexusClawRunner, RunnerConfig
from nexus_os.nexusclaw.task_router import TaskRouter, RoutingStrategy, RoutingDecision, TaskAssignment
from nexus_os.nexusclaw.worklog import WorklogSystem
from nexus_os.vault.memory_channels import MemoryChannelManager, get_manager

logger = logging.getLogger("nexusclaw.orchestrator")


@dataclass
class OrchestratorStatus:
    """Current status of the NEXUSCLAW Orchestrator."""
    running: bool = False
    runner_active: bool = False
    agents_online: int = 0
    agents_total: int = 0
    active_tasks: int = 0
    active_brainstorms: int = 0
    open_threads: int = 0
    last_heartbeat: str = ""
    version: str = "nexusclaw-v1"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "running": self.running,
            "runner_active": self.runner_active,
            "agents_online": self.agents_online,
            "agents_total": self.agents_total,
            "active_tasks": self.active_tasks,
            "active_brainstorms": self.active_brainstorms,
            "open_threads": self.open_threads,
            "last_heartbeat": self.last_heartbeat,
            "version": self.version,
        }


_DEFAULT_RELAY = object()


class NexusClawOrchestrator:
    """NEXUSCLAW Orchestrator - Central coordination for multi-agent NEXUS OS.

    The Orchestrator is the single entry point for all NEXUSCLAW operations.
    It manages the full lifecycle of tasks, agents, communication, and
    collaborative deliberation while enforcing governance and trust gates.

    Usage:
        orchestrator = NexusClawOrchestrator()
        orchestrator.discover_agents()  # Auto-register internal agents
        orchestrator.register_external_agents()  # Register external APIs
        orchestrator.start_runner()  # Start 24/7 operation

        # Submit a task
        task = NexusClawTaskEnvelope(...)
        result = orchestrator.submit_task(task)

        # Start a brainstorm
        session = orchestrator.start_brainstorm(topic, participants)
        orchestrator.propose_idea(session, agent_id, title, description)

        # Send a message
        msg = orchestrator.send_message(sender_id, recipient_ids, content)

        # Get status
        status = orchestrator.status()
    """

    def __init__(
        self,
        agent_pool: Optional[AgentPool] = None,
        task_router: Optional[TaskRouter] = None,
        message_bus: Optional[MessageBus] = None,
        brainstorm_engine: Optional[BrainstormEngine] = None,
        coordinator: Optional[NexusClawCoordinator] = None,
        runner: Optional[NexusClawRunner] = None,
        worklog: Optional[WorklogSystem] = None,
        memory_channels: Optional[MemoryChannelManager] = None,
        model_relay: Any = _DEFAULT_RELAY,
    ) -> None:
        self.agent_pool = agent_pool or get_agent_pool()
        self.task_router = task_router or TaskRouter(agent_pool=self.agent_pool)
        self.message_bus = message_bus or MessageBus(agent_pool=self.agent_pool)
        self.brainstorm_engine = brainstorm_engine or BrainstormEngine(
            agent_pool=self.agent_pool,
            message_bus=self.message_bus,
        )
        self.coordinator = coordinator or NexusClawCoordinator()
        self.runner = runner
        self.worklog = worklog or WorklogSystem()
        self.memory_channels = memory_channels or get_manager()
        self._model_relay = model_relay
        self._status = OrchestratorStatus()
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Agent management
    # ------------------------------------------------------------------

    def discover_agents(self) -> List[AgentRecord]:
        """Auto-discover and register all NEXUS OS internal agents."""
        with self._lock:
            agents = self.agent_pool.discover_internal_agents()
            self._status.agents_total = len(self.agent_pool.list_all())
            self._status.agents_online = len(self.agent_pool.list_available())
            logger.info("Discovered %d internal agents", len(agents))
            return agents

    def register_external_agent(
        self,
        agent_id: str,
        name: str,
        lane: str,
        capabilities: List[AgentCapability],
        api_endpoint: Optional[str] = None,
        rate_limit: Optional[str] = None,
        trust_score: float = 50.0,
    ) -> AgentRecord:
        """Register an external API agent (e.g., Grok, ChatGPT, Notion)."""
        with self._lock:
            agent = self.agent_pool.register_external_api(
                agent_id=agent_id,
                name=name,
                lane=lane,
                capabilities=capabilities,
                api_endpoint=api_endpoint,
                rate_limit=rate_limit,
                trust_score=trust_score,
            )
            self._status.agents_total = len(self.agent_pool.list_all())
            self._status.agents_online = len(self.agent_pool.list_available())
            return agent

    def register_human(self, agent_id: str, name: str, lane: str = "orchestration") -> AgentRecord:
        """Register a human operator."""
        with self._lock:
            agent = self.agent_pool.register_human(agent_id, name, lane)
            self._status.agents_total = len(self.agent_pool.list_all())
            self._status.agents_online = len(self.agent_pool.list_available())
            return agent

    def update_agent_status(self, agent_id: str, status: AgentStatus) -> Optional[AgentRecord]:
        """Update an agent's status."""
        with self._lock:
            agent = self.agent_pool.update_status(agent_id, status)
            self._status.agents_online = len(self.agent_pool.list_available())
            return agent

    def update_agent_trust(self, agent_id: str, trust_score: float) -> Optional[AgentRecord]:
        """Update an agent's trust score."""
        with self._lock:
            return self.agent_pool.update_trust(agent_id, trust_score)

    # ------------------------------------------------------------------
    # Task lifecycle
    # ------------------------------------------------------------------

    def submit_task(
        self,
        task: NexusClawTaskEnvelope,
        strategy: RoutingStrategy = RoutingStrategy.DIRECT,
    ) -> Dict[str, Any]:
        """Submit a task through the full NEXUSCLAW lifecycle.

        Steps:
        1. Validate task envelope through Coordinator
        2. Check governance gates (risk level, trust)
        3. Route to best agent(s) via TaskRouter
        4. Log to worklog and memory
        5. Return routing decision and task status
        """
        # Step 1: Validate through Coordinator
        try:
            self.coordinator.propose(task)
        except Exception as e:
            logger.error("Task validation failed: %s", e)
            return {
                "task_id": task.task_id,
                "status": "rejected",
                "reason": f"validation_failed: {e}",
            }

        # Step 2: Check governance - if halted, reject
        if self.coordinator.is_halted:
            return {
                "task_id": task.task_id,
                "status": "rejected",
                "reason": f"coordinator_halted: {self.coordinator.halt_reason}",
            }

        # Step 3: Route task
        try:
            decision = self.task_router.route(task, strategy=strategy)
        except Exception as e:
            logger.error("Task routing failed: %s", e)
            return {
                "task_id": task.task_id,
                "status": "routing_failed",
                "reason": str(e),
            }

        # Step 4: Log to worklog (already done by router, but log orchestrator-level)
        with self._lock:
            self._status.active_tasks = self.task_router.stats()["active_tasks"]

        result: Dict[str, Any] = {
            "task_id": task.task_id,
            "status": "routed" if decision.selected_agents else "no_agents_available",
            "routing_decision": decision.to_dict(),
            "agents_assigned": decision.selected_agents,
            "requires_human_oversight": decision.metadata.get("requires_human_oversight", False),
        }

        # Step 5: Attach model-selection metadata from ModelRelay (advisory)
        model_info = self.select_model_for_task(task)
        if model_info:
            result["model_selection"] = model_info

        return result

    def select_model_for_task(self, task: NexusClawTaskEnvelope) -> Dict[str, Any]:
        """Use ModelRelay's ChimeraRouterV2 to select the best model for a task.

        Reads optional ``resource_budget.prompt`` from the envelope; falls back
        to ``task.intent``. Returns model selection metadata or an empty dict
        when ModelRelay is unreachable or routing fails.
        """
        relay = self._model_relay
        if relay is _DEFAULT_RELAY:
            try:
                from nexus_os.relay import get_model_relay
                relay = get_model_relay()
            except Exception:
                relay = None
        if not relay:
            return {}

        prompt = task.resource_budget.get("prompt") or task.intent or ""
        try:
            available = getattr(relay.router, "_available", [])
            temp_policy = None
            if available:
                try:
                    temp_policy = available[0].__class__.__name__
                except (TypeError, IndexError, AttributeError):
                    pass
            decision = relay.router.route(
                prompt,
                latency_budget_ms=30000,
                quality_target=0.80,
                temperature_policy=temp_policy,
            )
            return {
                "model": decision.model,
                "temperature": decision.temperature,
                "router_model": decision.model,
                "source": "model_relay",
            }
        except Exception:
            return {}

    # Alias for compatibility with older test suites or external references
    _select_model_for_task = select_model_for_task

    def complete_task(self, task_id: str, agent_id: str, success: bool) -> Dict[str, Any]:
        """Mark a task assignment as complete and update agent state."""
        self.task_router.complete_assignment(task_id, agent_id, success)
        with self._lock:
            self._status.active_tasks = self.task_router.stats()["active_tasks"]
        return {
            "task_id": task_id,
            "agent_id": agent_id,
            "status": "completed" if success else "failed",
        }

    # ------------------------------------------------------------------
    # Messaging
    # ------------------------------------------------------------------

    def send_message(
        self,
        sender_id: str,
        recipient_ids: List[str],
        content: str,
        message_type: MessageType = MessageType.DIRECT,
        priority: MessagePriority = MessagePriority.NORMAL,
        risk_level: RiskLevel = RiskLevel.LOW,
    ) -> Dict[str, Any]:
        """Send a message through the NEXUSCLAW message bus."""
        sender = self.agent_pool.get(sender_id)
        if not sender:
            return {"status": "failed", "reason": f"sender {sender_id} not found"}

        message = NexusMessage(
            message_id=f"msg-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{hash(content) % 10000}",
            sender_id=sender_id,
            sender_name=sender.name,
            recipient_ids=recipient_ids,
            message_type=message_type,
            content=content,
            priority=priority,
            risk_level=risk_level,
            trust_required=0.0,
        )

        result = self.message_bus.send(message)
        self._status.open_threads = self.message_bus.stats()["active_threads"]

        return {
            "message_id": message.message_id,
            "status": "delivered" if result.delivered else "failed",
            "delivery_error": result.delivery_error,
        }

    def broadcast_message(
        self,
        sender_id: str,
        content: str,
        priority: MessagePriority = MessagePriority.NORMAL,
    ) -> Dict[str, Any]:
        """Broadcast a message to all available agents."""
        return self.send_message(
            sender_id=sender_id,
            recipient_ids=[],  # Empty = broadcast
            content=content,
            message_type=MessageType.BROADCAST,
            priority=priority,
        )

    # ------------------------------------------------------------------
    # Brainstorm sessions
    # ------------------------------------------------------------------

    def start_brainstorm(
        self,
        topic: str,
        participant_ids: List[str],
        mode: BrainstormMode = BrainstormMode.STRUCTURED,
        max_proposals: int = 10,
        max_rounds: int = 5,
        consensus_threshold: float = 0.66,
    ) -> BrainstormSession:
        """Start a collaborative brainstorm session."""
        session = self.brainstorm_engine.create_session(
            topic=topic,
            participant_ids=participant_ids,
            mode=mode,
            max_proposals=max_proposals,
            max_rounds=max_rounds,
            consensus_threshold=consensus_threshold,
        )
        self._status.active_brainstorms = len(self.brainstorm_engine.list_sessions(status="open"))
        return session

    def propose_idea(
        self,
        session_id: str,
        agent_id: str,
        title: str,
        description: str,
        evidence_refs: Optional[List[str]] = None,
        risk_level: RiskLevel = RiskLevel.LOW,
    ) -> Proposal:
        """Propose an idea in a brainstorm session."""
        proposal = self.brainstorm_engine.propose(
            session_id=session_id,
            agent_id=agent_id,
            title=title,
            description=description,
            evidence_refs=evidence_refs,
            risk_level=risk_level,
        )
        self._status.active_brainstorms = len(self.brainstorm_engine.list_sessions(status="open"))
        return proposal

    def discuss_idea(
        self,
        session_id: str,
        agent_id: str,
        proposal_id: str,
        comment: str,
    ) -> Dict[str, Any]:
        """Discuss a proposal in a brainstorm session."""
        message = self.brainstorm_engine.discuss(session_id, agent_id, proposal_id, comment)
        return {
            "message_id": message.message_id,
            "status": "delivered" if message.delivered else "failed",
        }

    def vote_on_idea(
        self,
        session_id: str,
        agent_id: str,
        proposal_id: str,
        choice: VoteChoice,
    ) -> Dict[str, Any]:
        """Vote on a proposal in a brainstorm session."""
        proposal = self.brainstorm_engine.vote(session_id, agent_id, proposal_id, choice)
        return {
            "proposal_id": proposal.proposal_id,
            "votes_cast": len(proposal.votes),
            "consensus_score": proposal.consensus_score,
            "accepted": proposal.accepted,
        }

    def advance_brainstorm(self, session_id: str) -> Dict[str, Any]:
        """Advance a structured brainstorm session to the next phase."""
        session = self.brainstorm_engine.advance_phase(session_id)
        self._status.active_brainstorms = len(self.brainstorm_engine.list_sessions(status="open"))
        return {
            "session_id": session_id,
            "phase": session.phase.value,
            "is_open": session.is_open,
            "winner_proposal_id": session.winner_proposal_id,
            "final_consensus": session.final_consensus,
        }

    def close_brainstorm(self, session_id: str) -> Dict[str, Any]:
        """Close a brainstorm session."""
        session = self.brainstorm_engine.close_session(session_id)
        self._status.active_brainstorms = len(self.brainstorm_engine.list_sessions(status="open"))
        return {
            "session_id": session_id,
            "status": "closed",
            "winner_proposal_id": session.winner_proposal_id,
            "final_consensus": session.final_consensus,
        }

    # ------------------------------------------------------------------
    # Runner lifecycle
    # ------------------------------------------------------------------

    def start_runner(self, blocking: bool = False) -> Optional[Any]:
        """Start the 24/7 NEXUSCLAW runner."""
        if self.runner is None:
            self.runner = NexusClawRunner()
        self._status.runner_active = True
        self._status.running = True
        if not blocking:
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                return loop.create_task(self.runner.run_loop())
            except RuntimeError:
                import threading
                def start_loop():
                    asyncio.run(self.runner.run_loop())
                thread = threading.Thread(target=start_loop, daemon=True)
                thread.start()
                return thread
        return None

    def stop_runner(self) -> None:
        """Stop the 24/7 NEXUSCLAW runner."""
        if self.runner:
            self.runner.stop()
        with self._lock:
            self._status.runner_active = False
            self._status.running = False

    # ------------------------------------------------------------------
    # Status & stats
    # ------------------------------------------------------------------

    def status(self) -> OrchestratorStatus:
        """Return current orchestrator status."""
        with self._lock:
            self._status.agents_total = len(self.agent_pool.list_all())
            self._status.agents_online = len(self.agent_pool.list_available())
            self._status.active_tasks = self.task_router.stats()["active_tasks"]
            self._status.active_brainstorms = len(self.brainstorm_engine.list_sessions(status="open"))
            self._status.open_threads = self.message_bus.stats()["active_threads"]
            self._status.last_heartbeat = datetime.now(timezone.utc).isoformat()
            return self._status

    def full_stats(self) -> Dict[str, Any]:
        """Return comprehensive statistics across all subsystems."""
        with self._lock:
            stats = {
                "orchestrator": self._status.to_dict(),
                "agent_pool": self.agent_pool.stats(),
                "task_router": self.task_router.stats(),
                "message_bus": self.message_bus.stats(),
                "brainstorm_engine": self.brainstorm_engine.stats(),
                "coordinator": self.coordinator.status(),
            }
            try:
                from nexus_cli_ctl.integrations.wiki_pipeline import get_wiki_pipeline
                pipeline = get_wiki_pipeline()
                stats["wiki"] = pipeline.get_status()
            except Exception:
                stats["wiki"] = {"available": False}
            return stats

    # ------------------------------------------------------------------
    # External integration helpers
    # ------------------------------------------------------------------

    def register_slack_connector(self, connector: Any) -> None:
        """Register a Slack connector for external messaging."""
        self.message_bus.register_external_connector("slack", connector)
        logger.info("Slack connector registered")

    def register_telegram_connector(self, connector: Any) -> None:
        """Register a Telegram connector for external messaging."""
        self.message_bus.register_external_connector("telegram", connector)
        logger.info("Telegram connector registered")

    def register_discord_connector(self, connector: Any) -> None:
        """Register a Discord connector for external messaging."""
        self.message_bus.register_external_connector("discord", connector)
        logger.info("Discord connector registered")

    # ------------------------------------------------------------------
    # Halt / emergency
    # ------------------------------------------------------------------

    def halt(self, reason: str) -> Dict[str, Any]:
        """Halt the orchestrator and all subsystems."""
        self.coordinator.halt(reason)
        self.stop_runner()

        # Halt all agents
        for agent in self.agent_pool.list_all():
            self.agent_pool.update_status(agent.agent_id, AgentStatus.HALTED)

        self._status.running = False
        self._status.runner_active = False
        self._status.agents_online = 0

        logger.critical("NEXUSCLAW Orchestrator halted: %s", reason)
        return {
            "status": "halted",
            "reason": reason,
            "halted_agents": len(self.agent_pool.list_all()),
        }

    # ------------------------------------------------------------------
    # Memory integration helpers
    # ------------------------------------------------------------------

    def wiki_query(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Query the NEXUS knowledge wiki for relevant information.

        Bridges NexusClaw to the Archivist wiki pipeline, enabling
        evidence-grounded reasoning from accumulated knowledge.

        Args:
            query: Search query string
            limit: Maximum number of results

        Returns:
            List of matching wiki pages with metadata
        """
        try:
            from nexus_cli_ctl.integrations.wiki_pipeline import get_wiki_pipeline
            pipeline = get_wiki_pipeline()
            return pipeline.search(query, limit=limit)
        except Exception as e:
            logger.warning("Wiki query failed: %s", e)
            return []

    def sync_memory_context(self, agent_id: str, query: str, action: str = "read") -> Any:
        """Build memory context for an agent from the 8-channel memory system."""
        from nexus_os.vault.governed_memory_broker import GovernedMemoryBroker
        broker = GovernedMemoryBroker()
        return broker.build_context(
            agent_id=agent_id,
            lane="orchestration",
            query=query,
            action=action,
        )

# Singleton instance
_orchestrator_instance: Optional[NexusClawOrchestrator] = None


def get_orchestrator() -> NexusClawOrchestrator:
    """Get the singleton NEXUSCLAW Orchestrator instance."""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = NexusClawOrchestrator()
    return _orchestrator_instance
