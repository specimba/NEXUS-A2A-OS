"""
governor/capability_registry.py — Per-Agent Capability Tracking

Backed by:
  - arXiv:2604.11839 (Aethelgard: Learned Capability Governance)
  - arXiv:2504.21034 (SAGA: Security Architecture)

Integration: ADDITIVE to existing governor/privilege_control.py (Progent)
and governor/skill_auditor.py (4-stage skill audit).
The existing system enforces policies at execution time.
This module tracks what capabilities agents ACTUALLY USE vs what they CAN access,
enabling the Aethelgard 15x overprovision ratio problem to be detected.

Aethelgard key insight: "every available tool exposed to every session
by default, regardless of the task" — 15x overprovision ratio.
This module measures and reduces that ratio.

Usage:
    from nexus_os.governor.capability_registry import CapabilityRegistry

    registry = CapabilityRegistry()
    registry.register_agent("agent-A", allowed_tools=["shell", "file_write", "network"])
    registry.record_usage("agent-A", "shell")  # Agent A used shell
    report = registry.get_overprovision_report()
    # report = {"agent-A": {"allowed": 3, "used": 1, "overprovision_ratio": 3.0}}
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timezone
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class AgentCapabilityRecord:
    """Per-agent capability tracking record."""
    agent_id: str
    allowed_tools: Set[str] = field(default_factory=set)
    used_tools: Set[str] = field(default_factory=set)
    tool_usage_count: Dict[str, int] = field(default_factory=dict)
    last_used: Dict[str, str] = field(default_factory=dict)  # tool → ISO timestamp
    registered_at: str = ""

    @property
    def overprovision_ratio(self) -> float:
        """How many more tools are allowed than used.

        Aethelgard reports 15x as typical. Target: <3x.
        """
        if not self.used_tools:
            return float(len(self.allowed_tools)) if self.allowed_tools else 0.0
        return len(self.allowed_tools) / max(len(self.used_tools), 1)

    @property
    def unused_tools(self) -> Set[str]:
        return self.allowed_tools - self.used_tools

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "allowed_tools": sorted(self.allowed_tools),
            "used_tools": sorted(self.used_tools),
            "unused_tools": sorted(self.unused_tools),
            "tool_usage_count": dict(self.tool_usage_count),
            "overprovision_ratio": round(self.overprovision_ratio, 2),
            "registered_at": self.registered_at,
        }


class CapabilityRegistry:
    """Registry tracking agent capabilities vs actual usage.

    Paper: arXiv:2604.11839 (Aethelgard — Learned Capability Governance)

    Aethelgard's 4-layer architecture:
    - Layer 1: Capability Governor (dynamically scopes which tools agent sees)
    - Layer 2: RL Learning Policy (PPO to learn minimum viable skill set)
    - Layer 3: Safety Router (intercepts tool calls before execution)
    - Layer 4: Audit Log (accumulated audit data)

    This module implements Layers 1 and 4 (tracking + reporting).
    Layers 2 and 3 require integration with existing Progent privilege_control.py.
    """

    def __init__(self):
        self._agents: Dict[str, AgentCapabilityRecord] = {}

    def register_agent(
        self,
        agent_id: str,
        allowed_tools: List[str],
    ) -> AgentCapabilityRecord:
        """Register an agent with its allowed tool set."""
        record = AgentCapabilityRecord(
            agent_id=agent_id,
            allowed_tools=set(allowed_tools),
            registered_at=datetime.now(timezone.utc).isoformat(),
        )
        self._agents[agent_id] = record
        logger.info(f"Registered agent {agent_id} with {len(allowed_tools)} allowed tools")
        return record

    def record_usage(self, agent_id: str, tool: str):
        """Record that an agent used a specific tool."""
        if agent_id not in self._agents:
            self._agents[agent_id] = AgentCapabilityRecord(agent_id=agent_id)

        record = self._agents[agent_id]
        record.used_tools.add(tool)
        record.tool_usage_count[tool] = record.tool_usage_count.get(tool, 0) + 1
        record.last_used[tool] = datetime.now(timezone.utc).isoformat()

    def get_agent(self, agent_id: str) -> Optional[AgentCapabilityRecord]:
        return self._agents.get(agent_id)

    def get_overprovision_report(self) -> Dict[str, Any]:
        """Get overprovision report for all agents.

        Aethelgard target: reduce 15x overprovision to <3x.
        """
        reports = {}
        high_overprovision = []

        for agent_id, record in self._agents.items():
            ratio = record.overprovision_ratio
            reports[agent_id] = {
                "allowed_count": len(record.allowed_tools),
                "used_count": len(record.used_tools),
                "overprovision_ratio": round(ratio, 2),
                "unused_tools": sorted(record.unused_tools),
            }
            if ratio > 5.0:
                high_overprovision.append(agent_id)

        # Compute recommended minimum viable capability set per agent
        recommendations = {}
        for agent_id, record in self._agents.items():
            if record.used_tools and record.overprovision_ratio > 3.0:
                # Recommend: only allow tools that have been used
                recommendations[agent_id] = {
                    "current_allowed": sorted(record.allowed_tools),
                    "recommended_allowed": sorted(record.used_tools),
                    "removable": sorted(record.unused_tools),
                    "potential_reduction": len(record.unused_tools),
                }

        return {
            "agents": reports,
            "high_overprovision_agents": high_overprovision,
            "average_overprovision": (
                sum(r["overprovision_ratio"] for r in reports.values()) / len(reports)
                if reports else 0.0
            ),
            "recommendations": recommendations,
        }

    def suggest_minimum_capabilities(self, agent_id: str) -> List[str]:
        """Suggest minimum viable capability set for an agent.

        Aethelgard Layer 1: dynamically scope which tools agent sees.
        Uses actual usage history to suggest pruning.
        """
        record = self._agents.get(agent_id)
        if not record or not record.used_tools:
            return list(record.allowed_tools) if record else []

        # Return only tools that have been used at least once
        # plus any tools that are safety-required (guards, audit)
        safety_required = {"audit_log", "governance_check", "token_guard"}
        return sorted(record.used_tools | (record.allowed_tools & safety_required))

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_agents": len(self._agents),
            "total_tools_allowed": sum(len(r.allowed_tools) for r in self._agents.values()),
            "total_tools_used": sum(len(r.used_tools) for r in self._agents.values()),
            "avg_overprovision": (
                sum(r.overprovision_ratio for r in self._agents.values()) / len(self._agents)
                if self._agents else 0.0
            ),
        }
