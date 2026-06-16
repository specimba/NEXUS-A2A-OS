"""nexus_os/nexusclaw/task_router.py - NEXUSCLAW Task Router

The Task Router matches tasks to the best available agents based on:
  - Required capabilities
  - Trust score (risk-level-dependent thresholds)
  - Lane matching
  - Availability and load balancing
  - Historical success rates

Routing strategies: DIRECT, BROADCAST, BRAINSTORM, REDUNDANT.
Includes failure-aware routing (capability mask on failure)
and 3-tier escalation timeout (retry -> re-route -> rollback).
"""

from __future__ import annotations

import heapq
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

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
    escalation_tier: int = 0
    escalation_timeout_ms: float = 0.0
    assigned_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


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

    FAILURE_EXCLUSION_WINDOW = 60.0
    ESCALATION_DEFAULTS = {0: 30_000, 1: 60_000, 2: 120_000}

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
        self._task_queue: List[Tuple[int, int, NexusClawTaskEnvelope, RoutingStrategy, Optional[List[str]]]] = []
        self._queue_counter: int = 0
        self._failure_history: Dict[str, List[Tuple[float, str]]] = {}
        self._task_envelopes: Dict[str, Tuple[NexusClawTaskEnvelope, RoutingStrategy, Optional[List[str]]]] = {}
        self._escalation_monitor: Optional[threading.Thread] = None
        self._escalation_running = False
        self._escalation_interval = 5.0
        self._lock = threading.RLock()

    @staticmethod
    def _priority_for_risk(risk: RiskLevel) -> int:
        """Map risk level to priority (0=highest, 3=lowest)."""
        mapping = {
            RiskLevel.CRITICAL: 0,
            RiskLevel.HIGH: 1,
            RiskLevel.MEDIUM: 2,
            RiskLevel.LOW: 3,
        }
        return mapping.get(risk, 3)

    def enqueue(
        self,
        task: NexusClawTaskEnvelope,
        strategy: RoutingStrategy = RoutingStrategy.DIRECT,
        preferred_agents: Optional[List[str]] = None,
    ) -> int:
        """Add a task to the priority queue. Returns queue depth after insertion."""
        with self._lock:
            priority = self._priority_for_risk(
                task.risk_level if isinstance(task.risk_level, RiskLevel) else RiskLevel(str(task.risk_level).lower())
            )
            heapq.heappush(
                self._task_queue,
                (priority, self._queue_counter, task, strategy, preferred_agents),
            )
            self._queue_counter += 1
            depth = len(self._task_queue)
            logger.debug("Task %s enqueued (priority=%d, depth=%d)", task.task_id, priority, depth)
            return depth

    def process_next(self) -> Optional[RoutingDecision]:
        """Dequeue and route the highest-priority pending task."""
        with self._lock:
            if not self._task_queue:
                return None
            _, _, task, strategy, preferred_agents = heapq.heappop(self._task_queue)
        return self.route(task, strategy=strategy, preferred_agents=preferred_agents)

    def drain_queue(
        self,
        stop_condition: Optional[Callable[[], bool]] = None,
        max_batch: int = 0,
    ) -> List[RoutingDecision]:
        """Process all (or up to max_batch) queued tasks in priority order."""
        decisions: List[RoutingDecision] = []
        while self._task_queue:
            if stop_condition and stop_condition():
                break
            if 0 < max_batch <= len(decisions):
                break
            decision = self.process_next()
            if decision is not None:
                decisions.append(decision)
        return decisions

    @property
    def queue_size(self) -> int:
        """Number of tasks waiting in the priority queue."""
        with self._lock:
            return len(self._task_queue)

    @property
    def queue_by_priority(self) -> Dict[str, int]:
        """Count of queued tasks by priority level."""
        with self._lock:
            counts: Dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
            for priority, _, _, _, _ in self._task_queue:
                label = {0: "critical", 1: "high", 2: "medium", 3: "low"}.get(priority, "low")
                counts[label] += 1
            return counts

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
            self._task_envelopes[task.task_id] = (task, strategy, preferred_agents)

            # Step 7: Log to worklog and memory
            self._log_routing_decision(decision, task)

            return decision

    def _find_candidates(self, task: NexusClawTaskEnvelope, trust_threshold: float) -> List[AgentRecord]:
        """Find agents that can handle this task. Failure-aware: excludes agents
        who recently failed at matching capabilities (unless no alternative exists)."""
        candidates: List[AgentRecord] = []
        seen: Set[str] = set()

        # Search by required capabilities
        for cap_name in task.required_capabilities:
            agents = self.agent_pool.find_by_capability(cap_name, lane=task.lane, min_trust=trust_threshold)
            for agent in agents:
                if agent.agent_id not in seen:
                    seen.add(agent.agent_id)
                    candidates.append(agent)

        # If no capability matches, fall back to trusted lane agents — but only
        # when the task did not explicitly require specific capabilities. When
        # capabilities are specified, a miss means no trusted agent can fulfill
        # the requirement, and lane-only fallback would be capability-blind.
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

        # Failure-aware: deprioritize agents with recent failures on required capabilities
        if task.required_capabilities and len(candidates) > 1:
            failure_free = [
                c for c in candidates
                if not (self._get_failure_mask(c.agent_id) & set(task.required_capabilities))
            ]
            if failure_free:
                candidates = failure_free

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

    def _get_failure_mask(self, agent_id: str) -> Set[str]:
        """Return set of capability names this agent recently failed at."""
        now = time.monotonic()
        failures = self._failure_history.get(agent_id, [])
        return {
            cap for ts, cap in failures
            if now - ts < self.FAILURE_EXCLUSION_WINDOW
        }

    def complete_assignment(self, task_id: str, agent_id: str, success: bool) -> None:
        """Mark an assignment as complete and update agent status/trust."""
        with self._lock:
            assignments = self._assignments.get(task_id, [])
            matched = None
            for assignment in assignments:
                if assignment.agent_id == agent_id:
                    assignment.status = "completed" if success else "failed"
                    matched = assignment

            # Failure-aware routing: record capability failures
            if not success and matched is not None:
                agent = self.agent_pool.get(agent_id)
                if agent:
                    for cap in agent.capabilities:
                        self._failure_history.setdefault(agent_id, []).append((time.monotonic(), cap.name))

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
        self._task_envelopes.pop(task_id, None)
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

    # ------------------------------------------------------------------
    # 3-Tier Escalation Monitor
    # ------------------------------------------------------------------

    def start_escalation_monitor(self) -> None:
        """Start the background escalation monitor thread."""
        with self._lock:
            if self._escalation_running:
                return
            self._escalation_running = True
            self._escalation_monitor = threading.Thread(
                target=self._escalation_loop, daemon=True, name="taskrouter-escalation"
            )
            self._escalation_monitor.start()
            logger.info("Escalation monitor started")

    def stop_escalation_monitor(self) -> None:
        """Stop the background escalation monitor thread."""
        with self._lock:
            self._escalation_running = False

    def _escalation_loop(self) -> None:
        """Background loop that checks for timed-out pending assignments."""
        while self._escalation_running:
            self._check_pending_escalations()
            time.sleep(self._escalation_interval)

    def _check_pending_escalations(self) -> None:
        """Find and escalate timed-out pending assignments."""
        with self._lock:
            now = datetime.now(timezone.utc)
            for task_id, assignments in list(self._assignments.items()):
                for a in assignments:
                    if a.status != "pending":
                        continue
                    elapsed_ms = (now - datetime.fromisoformat(a.assigned_at)).total_seconds() * 1000
                    timeout = self.ESCALATION_DEFAULTS.get(a.escalation_tier, 120_000)
                    if elapsed_ms >= timeout:
                        self._escalate_assignment(task_id, a)

    def _escalate_assignment(self, task_id: str, assignment: TaskAssignment) -> None:
        """Execute 3-tier escalation for a timed-out assignment.

        Tier 0→1 (soft retry): Re-submit same task to same agent, increment retry.
        Tier 1→2 (re-route): Release failed agent, route to alternative via BROADCAST.
        Tier 2→3 (rollback): Mark all assignments as failed, finalize the task.
        """
        tier = assignment.escalation_tier
        if tier >= 3:
            return  # Already at max escalation

        if tier <= 0:
            # Soft retry: increment retry, keep same agent
            assignment.retry_count += 1
            assignment.escalation_tier = 1
            assignment.assigned_at = datetime.now(timezone.utc).isoformat()
            logger.info("Escalation Tier 1 (retry): task=%s agent=%s retry=%d", task_id, assignment.agent_id, assignment.retry_count)
        elif tier == 1:
            # Re-route: release failed agent, find alternative
            self.agent_pool.update_status(assignment.agent_id, AgentStatus.ONLINE)
            assignment.status = "escalated"

            envelope_entry = self._task_envelopes.get(task_id)
            if envelope_entry:
                task, strategy, preferred = envelope_entry
                candidates = self._find_candidates(task, self.RISK_TRUST_THRESHOLDS.get(task.risk_level, 0.0))
                candidates = [c for c in candidates if c.agent_id != assignment.agent_id]
                if candidates:
                    new_agent = candidates[0]
                    new_assignment = TaskAssignment(
                        task_id=task_id,
                        agent_id=new_agent.agent_id,
                        agent_name=new_agent.name,
                        assignment_type="re_routed",
                        retry_count=0,
                        escalation_tier=2,
                    )
                    self._assignments[task_id].append(new_assignment)
                    self.agent_pool.update_status(new_agent.agent_id, AgentStatus.BUSY)
                    logger.info("Escalation Tier 2 (re-route): task=%s %s→%s", task_id, assignment.agent_id, new_agent.agent_id)
                else:
                    assignment.escalation_tier = 3
                    self._force_rollback(task_id)
            else:
                assignment.escalation_tier = 3
                self._force_rollback(task_id)
        elif tier == 2:
            self._force_rollback(task_id)

    def _force_rollback(self, task_id: str) -> None:
        """Roll back a task: mark all pending assignments as failed and finalize."""
        assignments = self._assignments.get(task_id, [])
        for a in assignments:
            if a.status == "pending":
                a.status = "failed"
            self.agent_pool.update_status(a.agent_id, AgentStatus.ONLINE)
        self._finalize_task(task_id)
        logger.warning("Escalation Tier 3 (rollback): task %s force-failed", task_id)

    def stats(self) -> Dict[str, Any]:
        """Return router statistics."""
        with self._lock:
            total_assignments = sum(len(a) for a in self._assignments.values())
            pending = sum(
                1 for assignments in self._assignments.values()
                for a in assignments if a.status == "pending"
            )
            qbp = self.queue_by_priority
            escalated = sum(1 for assignments in self._assignments.values() for a in assignments if a.status == "escalated")
            return {
                "active_tasks": len(self._assignments),
                "total_assignments": total_assignments,
                "pending_assignments": pending,
                "escalated_assignments": escalated,
                "agents_in_pool": len(self.agent_pool.list_all()),
                "available_agents": len(self.agent_pool.list_available()),
                "queued_tasks": len(self._task_queue),
                "queued_by_priority": qbp,
                "escalation_monitor_running": self._escalation_running,
                "failure_tracked_agents": len(self._failure_history),
            }


# Singleton
_task_router_instance: Optional[TaskRouter] = None


def get_task_router() -> TaskRouter:
    global _task_router_instance
    if _task_router_instance is None:
        _task_router_instance = TaskRouter()
    return _task_router_instance
