"""nexus_os/nexusclaw/task_router.py - NEXUSCLAW Task Router

The Task Router matches tasks to the best available agents based on:
  - Required capabilities
  - Trust score (risk-level-dependent thresholds)
  - Lane matching
  - Availability and load balancing
  - Historical success rates

Routing strategies: DIRECT, BROADCAST, BRAINSTORM, REDUNDANT.
All decisions are logged to worklog and memory channels.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set

from nexus_os.nexusclaw.agent_pool import AgentPool, AgentRecord, AgentStatus, get_agent_pool
from nexus_os.nexusclaw.envelope import NexusClawTaskEnvelope, RiskLevel
from nexus_os.nexusclaw.worklog import WorklogSystem, get_worklog
from nexus_os.vault.memory_channels import MemoryChannelManager, get_manager

logger = logging.getLogger("nexusclaw.task_router")


class RoutingStrategy(str, Enum):
    DIRECT = "direct"
    BROADCAST = "broadcast"
    BRAINSTORM = "brainstorm"
    REDUNDANT = "redundant"


@dataclass
class RoutingDecision:
    task_id: str
    strategy: RoutingStrategy
    selected_agents: List[str]
    rejected_agents: List[str]
    reason: str
    risk_level: str
    trust_threshold: float
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "strategy": self.strategy.value,
            "selected_agents": self.selected_agents,
            "rejected_agents": self.rejected_agents,
            "reason": self.reason,
            "risk_level": self.risk_level,
            "trust_threshold": self.trust_threshold,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class TaskAssignment:
    task_id: str
    agent_id: str
    agent_name: str
    assignment_type: str
    expected_duration_ms: float = 0.0
    retry_count: int = 0
    status: str = "pending"


class TaskRouter:
    """Intelligent task routing for NEXUSCLAW multi-agent coordination."""

    RISK_TRUST_THRESHOLDS = {
        RiskLevel.LOW: 0.0,
        RiskLevel.MEDIUM: 30.0,
        RiskLevel.HIGH: 70.0,
        RiskLevel.CRITICAL: 90.0,
    }

    RISK_REQUIRES_HUMAN = {
        RiskLevel.LOW: False,
        RiskLevel.MEDIUM: False,
        RiskLevel.HIGH: True,
        RiskLevel.CRITICAL: True,
    }

    MAX_AGENTS = {
        RoutingStrategy.DIRECT: 1,
        RoutingStrategy.BROADCAST: 10,
        RoutingStrategy.BRAINSTORM: 5,
        RoutingStrategy.REDUNDANT: 3,
    }

    def __init__(
        self,
        agent_pool: Optional[AgentPool] = None,
        worklog: Optional[WorklogSystem] = None,
        memory_channels: Optional[MemoryChannelManager] = None,
    ) -> None:
        self.agent_pool = agent_pool or get_agent_pool()
        self.worklog = worklog or get_worklog()
        self.memory_channels = memory_channels or get_manager()
        self._assignments: Dict[str, List[TaskAssignment]] = {}
        self._lock = threading.RLock()

    def route(
        self,
        task: NexusClawTaskEnvelope,
        strategy: RoutingStrategy = RoutingStrategy.DIRECT,
        preferred_agents: Optional[List[str]] = None,
    ) -> RoutingDecision:
        """Route a task to the best available agents."""
        with self._lock:
            risk_level = task.risk_level if isinstance(task.risk_level, RiskLevel) else RiskLevel(str(task.risk_level).lower())
            trust_threshold = self.RISK_TRUST_THRESHOLDS.get(risk_level, 0.0)
            requires_human = self.RISK_REQUIRES_HUMAN.get(risk_level, False)

            # Step 1: Find agents matching required capabilities
            candidates = self._find_candidates(task, trust_threshold)

            # Step 2: Apply preferred agents filter if specified
            if preferred_agents:
                candidates = [c for c in candidates if c.agent_id in preferred_agents]

            # Step 3: Check human-in-the-loop requirement for high/critical tasks
            if requires_human and not any(c.agent_type.value == "human" for c in candidates):
                logger.warning("Task %s is %s risk but no human agent available", task.task_id, risk_level.value)

            # Step 4: Apply strategy to select agents
            max_agents = self.MAX_AGENTS.get(strategy, 1)
            selected, rejected = self._apply_strategy(candidates, strategy, max_agents)

            # Step 5: Build decision
            reason = self._build_reason(task, strategy, selected, rejected, trust_threshold)
            decision = RoutingDecision(
                task_id=task.task_id,
                strategy=strategy,
                selected_agents=[a.agent_id for a in selected],
                rejected_agents=[a.agent_id for a in rejected],
                reason=reason,
                risk_level=risk_level.value,
                trust_threshold=trust_threshold,
                metadata={
                    "requires_human_oversight": requires_human,
                    "lane": task.lane,
                    "intent": task.intent,
                    "candidate_count": len(candidates),
                    "selected_count": len(selected),
                },
            )

            # Step 6: Create assignments and mark agents busy
            self._create_assignments(task, selected, strategy)

            # Step 7: Log to worklog and memory
            self._log_routing_decision(decision, task)

            return decision

    def _find_candidates(self, task: NexusClawTaskEnvelope, trust_threshold: float) -> List[AgentRecord]:
        """Find agents that can handle this task."""
        candidates: List[AgentRecord] = []
        seen: Set[str] = set()

        # Search by required capabilities
        for cap_name in task.required_capabilities:
            agents = self.agent_pool.find_by_capability(cap_name, lane=task.lane, min_trust=trust_threshold)
            for agent in agents:
                if agent.agent_id not in seen:
                    seen.add(agent.agent_id)
                    candidates.append(agent)

        # If no capability matches and no explicit capabilities were required, search by lane
        if not candidates and task.lane and not task.required_capabilities:
            agents = self.agent_pool.find_by_lanes({task.lane})
            for agent in agents:
                if agent.agent_id not in seen and agent.is_trusted(trust_threshold):
                    seen.add(agent.agent_id)
                    candidates.append(agent)

        # Fallback: any available agent if trust threshold is low and no capabilities required
        if not candidates and trust_threshold <= 30.0 and not task.required_capabilities:
            candidates = self.agent_pool.list_available(lane=task.lane, min_trust=trust_threshold)

        # Sort by: trust_score desc, success_rate desc, task_count asc (load balancing)
        candidates.sort(key=lambda a: (a.trust_score, a.success_rate, -a.task_count), reverse=True)
        return candidates

    def _apply_strategy(
        self,
        candidates: List[AgentRecord],
        strategy: RoutingStrategy,
        max_agents: int,
    ) -> tuple[List[AgentRecord], List[AgentRecord]]:
        """Apply routing strategy to select agents from candidates."""
        if not candidates:
            return [], []

        if strategy == RoutingStrategy.DIRECT:
            selected = candidates[:1]
            rejected = candidates[1:]
        elif strategy == RoutingStrategy.BROADCAST:
            selected = candidates[:max_agents]
            rejected = candidates[max_agents:]
        elif strategy == RoutingStrategy.BRAINSTORM:
            selected = self._select_diverse(candidates, max_agents)
            selected_ids = {a.agent_id for a in selected}
            rejected = [a for a in candidates if a.agent_id not in selected_ids]
        elif strategy == RoutingStrategy.REDUNDANT:
            selected = self._select_diverse(candidates, max_agents)
            selected_ids = {a.agent_id for a in selected}
            rejected = [a for a in candidates if a.agent_id not in selected_ids]
        else:
            selected = candidates[:1]
            rejected = candidates[1:]

        return selected, rejected

    def _select_diverse(self, candidates: List[AgentRecord], max_agents: int) -> List[AgentRecord]:
        """Select a diverse set of agents (different types, lanes)."""
        selected: List[AgentRecord] = []
        used_types: Set[str] = set()
        used_lanes: Set[str] = set()

        for agent in candidates:
            if len(selected) >= max_agents:
                break
            # Prefer agents with different types or lanes
            if agent.agent_type.value not in used_types or agent.lane not in used_lanes or len(selected) < 2:
                selected.append(agent)
                used_types.add(agent.agent_type.value)
                used_lanes.add(agent.lane)
            elif len(selected) < max_agents:
                selected.append(agent)

        return selected

    def _build_reason(
        self,
        task: NexusClawTaskEnvelope,
        strategy: RoutingStrategy,
        selected: List[AgentRecord],
        rejected: List[AgentRecord],
        trust_threshold: float,
    ) -> str:
        """Build a human-readable reason for the routing decision."""
        if not selected:
            return f"No agents available for task {task.task_id} (lane={task.lane}, trust_threshold={trust_threshold})"

        agent_names = ", ".join(f"{a.name}({a.trust_score:.0f})" for a in selected)
        return (
            f"Task {task.task_id} routed via {strategy.value} to {len(selected)} agent(s): {agent_names}. "
            f"Trust threshold: {trust_threshold}. Lane: {task.lane}. "
            f"{len(rejected)} agent(s) matched but were not selected."
        )

    def _create_assignments(
        self,
        task: NexusClawTaskEnvelope,
        selected: List[AgentRecord],
        strategy: RoutingStrategy,
    ) -> None:
        """Create task assignments and mark agents as busy."""
        assignments: List[TaskAssignment] = []
        for i, agent in enumerate(selected):
            if strategy in (RoutingStrategy.BRAINSTORM, RoutingStrategy.REDUNDANT):
                assignment_type = "collaborative" if i == 0 else "backup"
            else:
                assignment_type = "primary" if i == 0 else "backup"

            assignment = TaskAssignment(
                task_id=task.task_id,
                agent_id=agent.agent_id,
                agent_name=agent.name,
                assignment_type=assignment_type,
                expected_duration_ms=task.resource_budget.get("expected_duration_ms", 0.0),
            )
            assignments.append(assignment)

            # Mark agent as busy
            self.agent_pool.update_status(agent.agent_id, AgentStatus.BUSY)

        self._assignments[task.task_id] = assignments

    def complete_assignment(self, task_id: str, agent_id: str, success: bool) -> None:
        """Mark an assignment as complete and update agent status/trust."""
        with self._lock:
            assignments = self._assignments.get(task_id, [])
            for assignment in assignments:
                if assignment.agent_id == agent_id:
                    assignment.status = "completed" if success else "failed"

            # Update agent status back to online
            self.agent_pool.update_status(agent_id, AgentStatus.ONLINE)

            # Record task outcome for trust updates
            agent = self.agent_pool.get(agent_id)
            if agent:
                agent.record_task(success)

            # Check if all assignments for this task are complete
            if all(a.status in ("completed", "failed") for a in assignments):
                self._finalize_task(task_id)

    def _finalize_task(self, task_id: str) -> None:
        """Finalize a task when all assignments are complete."""
        assignments = self._assignments.pop(task_id, [])
        completed = sum(1 for a in assignments if a.status == "completed")
        failed = sum(1 for a in assignments if a.status == "failed")
        logger.info("Task %s finalized: %d completed, %d failed", task_id, completed, failed)

    def _log_routing_decision(self, decision: RoutingDecision, task: NexusClawTaskEnvelope) -> None:
        """Log routing decision to worklog and memory."""
        try:
            self.worklog.log_task(
                agent_id="nexusclaw-router",
                task_id=task.task_id,
                intent=f"route_task:{task.intent}",
                status="routed" if decision.selected_agents else "no_agents",
                duration_ms=0.0,
                evidence=[decision.reason],
                metadata={
                    "routing_decision": decision.to_dict(),
                    "task_envelope": task.to_dict(),
                },
            )
        except Exception as e:
            logger.warning("Failed to log routing decision to worklog: %s", e)

        # Write to TASK channel
        try:
            self.memory_channels.append_task(
                agent_id="nexusclaw-router",
                task_id=task.task_id,
                task_status="routed" if decision.selected_agents else "unrouted",
                content=decision.reason,
                trust_score=100.0,
            )
        except Exception as e:
            logger.warning("Failed to log routing decision to memory: %s", e)

    def get_assignments(self, task_id: str) -> List[TaskAssignment]:
        """Get all assignments for a task."""
        with self._lock:
            return list(self._assignments.get(task_id, []))

    def get_agent_load(self, agent_id: str) -> int:
        """Get the number of active assignments for an agent."""
        with self._lock:
            count = 0
            for assignments in self._assignments.values():
                for a in assignments:
                    if a.agent_id == agent_id and a.status == "pending":
                        count += 1
            return count

    def stats(self) -> Dict[str, Any]:
        """Return router statistics."""
        with self._lock:
            total_assignments = sum(len(a) for a in self._assignments.values())
            pending = sum(
                1 for assignments in self._assignments.values()
                for a in assignments if a.status == "pending"
            )
            return {
                "active_tasks": len(self._assignments),
                "total_assignments": total_assignments,
                "pending_assignments": pending,
                "agents_in_pool": len(self.agent_pool.list_all()),
                "available_agents": len(self.agent_pool.list_available()),
            }
