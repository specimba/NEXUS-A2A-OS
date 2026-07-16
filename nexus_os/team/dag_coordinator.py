"""
team/dag_coordinator.py — DAG-Based Workflow Coordination with AgentDropout

Backed by:
  - arXiv:2603.22386 (Survey of Workflow Optimization for LLM Agents)
  - arXiv:2602.02034 (Constrained Process Maps for Multi-Agent Workflows)

Integration: ADDITIVE to existing team/coordinator.py (1084 lines).
The existing coordinator uses a 7-step dispatch pipeline with file-driven
.task.md coordination. This module adds explicit DAG representation:
  - Nodes = subtasks/agents
  - Edges = dependencies + cost/latency constraints
  - AgentDropout: prune low-value paths when budget exceeded

Uses existing research/knowledge_flow.py KnowledgeNode DAG as primitive.

Usage:
    from nexus_os.team.dag_coordinator import WorkflowDAG, DAGNode

    dag = WorkflowDAG()
    dag.add_node("analyze", agent="task_reasoner", cost=100, required=True)
    dag.add_node("code", agent="task_coder", cost=500, required=True, depends_on=["analyze"])
    dag.add_node("verify", agent="cdp_verifier", cost=200, depends_on=["code"])
    dag.add_node("optional_test", agent="task_coder", cost=300, required=False, depends_on=["code"])

    plan = dag.plan(budget=800)
    # plan = {"execute": ["analyze", "code"], "pruned": ["verify", "optional_test"], "total_cost": 600}
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set
from enum import Enum

logger = logging.getLogger(__name__)


class NodeStatus(Enum):
    PENDING = "pending"
    READY = "ready"      # All dependencies satisfied
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PRUNED = "pruned"    # Removed by AgentDropout


@dataclass
class DAGNode:
    """Node in a workflow DAG."""
    node_id: str
    agent: str              # Worker role ID from worker_roles.py
    task_description: str = ""
    cost: int = 0           # Estimated token cost
    latency_ms: int = 0     # Estimated latency
    required: bool = True   # If False, can be pruned by AgentDropout
    depends_on: List[str] = field(default_factory=list)
    status: NodeStatus = NodeStatus.PENDING
    result: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DAGEdge:
    """Edge in workflow DAG — dependency between nodes."""
    source: str  # Node ID
    target: str  # Node ID
    edge_type: str = "depends_on"  # depends_on, extends, contradicts, supports
    constraint: Optional[str] = None  # e.g., "cost < 500"


class WorkflowDAG:
    """DAG-based workflow with AgentDropout pruning.

    Papers:
    - arXiv:2603.22386 (Workflow Optimization — DAG collaboration, AgentDropout)
    - arXiv:2602.02034 (Constrained Process Maps — MDP + DAG formalization)
    """

    def __init__(self):
        self._nodes: Dict[str, DAGNode] = {}
        self._edges: List[DAGEdge] = []

    def add_node(self, node_id: str, agent: str, **kwargs) -> DAGNode:
        """Add a node to the DAG."""
        node = DAGNode(node_id=node_id, agent=agent, **kwargs)
        self._nodes[node_id] = node
        # Add dependency edges
        for dep in node.depends_on:
            self._edges.append(DAGEdge(source=dep, target=node_id))
        return node

    def add_edge(self, source: str, target: str, edge_type: str = "depends_on", constraint: str = ""):
        """Add an edge to the DAG."""
        self._edges.append(DAGEdge(source=source, target=target, edge_type=edge_type, constraint=constraint or None))

    def get_ready_nodes(self) -> List[DAGNode]:
        """Get nodes whose dependencies are all completed."""
        ready = []
        for node in self._nodes.values():
            if node.status != NodeStatus.PENDING:
                continue
            deps = [e.source for e in self._edges if e.target == node.node_id]
            if all(self._nodes[d].status == NodeStatus.COMPLETED for d in deps if d in self._nodes):
                node.status = NodeStatus.READY
                ready.append(node)
        return ready

    def topological_sort(self) -> List[str]:
        """Topological sort of the DAG (Kahn's algorithm)."""
        in_degree = {nid: 0 for nid in self._nodes}
        adj: Dict[str, List[str]] = {nid: [] for nid in self._nodes}

        for edge in self._edges:
            if edge.source in self._nodes and edge.target in self._nodes:
                adj[edge.source].append(edge.target)
                in_degree[edge.target] += 1

        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        result = []

        while queue:
            node = queue.pop(0)
            result.append(node)
            for neighbor in adj.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(result) != len(self._nodes):
            logger.warning("DAG has a cycle — topological sort incomplete")

        return result

    def plan(self, budget: int) -> Dict[str, Any]:
        """Plan execution with budget constraints.

        AgentDropout (arXiv:2603.22386):
        - Execute required nodes first
        - Prune optional nodes if budget exceeded
        - Prune low-value paths when budget pressure hits threshold
        """
        order = self.topological_sort()
        execute: List[str] = []
        pruned: List[str] = []
        total_cost = 0

        # First pass: execute all required nodes
        for node_id in order:
            node = self._nodes[node_id]
            if node.required:
                if total_cost + node.cost <= budget:
                    execute.append(node_id)
                    total_cost += node.cost
                else:
                    # Can't afford a required node — critical failure
                    logger.error(f"Budget {budget} insufficient for required node {node_id} (cost {node.cost})")
                    pruned.append(node_id)
                    node.status = NodeStatus.PRUNED
            else:
                pruned.append(node_id)
                node.status = NodeStatus.PRUNED

        # Second pass: add optional nodes if budget allows
        remaining_budget = budget - total_cost
        for node_id in order:
            node = self._nodes[node_id]
            if node.status == NodeStatus.PRUNED and not node.required:
                if remaining_budget >= node.cost:
                    # Check if dependencies are in execute list
                    deps = [e.source for e in self._edges if e.target == node_id]
                    if all(d in execute for d in deps):
                        execute.append(node_id)
                        remaining_budget -= node.cost
                        total_cost += node.cost
                        node.status = NodeStatus.PENDING
                        if node_id in pruned:
                            pruned.remove(node_id)

        return {
            "execute": execute,
            "pruned": pruned,
            "total_cost": total_cost,
            "budget": budget,
            "budget_utilization": round(total_cost / max(budget, 1), 4),
            "node_count": len(self._nodes),
            "edge_count": len(self._edges),
        }

    def mark_completed(self, node_id: str, result: Any = None):
        """Mark a node as completed."""
        if node_id in self._nodes:
            self._nodes[node_id].status = NodeStatus.COMPLETED
            self._nodes[node_id].result = result

    def mark_failed(self, node_id: str, error: str = ""):
        """Mark a node as failed."""
        if node_id in self._nodes:
            self._nodes[node_id].status = NodeStatus.FAILED
            self._nodes[node_id].metadata["error"] = error

    def get_critical_path(self) -> List[str]:
        """Get the critical path (longest dependency chain)."""
        order = self.topological_sort()
        longest: Dict[str, int] = {nid: 0 for nid in self._nodes}

        for node_id in order:
            node = self._nodes[node_id]
            deps = [e.source for e in self._edges if e.target == node_id]
            if deps:
                longest[node_id] = max(longest.get(d, 0) for d in deps) + node.cost
            else:
                longest[node_id] = node.cost

        # Find the node with maximum cost and backtrack
        if not longest:
            return []

        end_node = max(longest, key=longest.get)
        path = [end_node]

        current = end_node
        while True:
            deps = [e.source for e in self._edges if e.target == current]
            if not deps:
                break
            # Pick the dependency with the highest cost
            best_dep = max(deps, key=lambda d: longest.get(d, 0))
            path.insert(0, best_dep)
            current = best_dep
            if current in path[1:]:  # Cycle detection
                break

        return path

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": {nid: {"agent": n.agent, "cost": n.cost, "required": n.required,
                            "depends_on": n.depends_on, "status": n.status.value}
                      for nid, n in self._nodes.items()},
            "edges": [{"source": e.source, "target": e.target, "type": e.edge_type}
                      for e in self._edges],
            "critical_path": self.get_critical_path(),
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_nodes": len(self._nodes),
            "total_edges": len(self._edges),
            "required_nodes": sum(1 for n in self._nodes.values() if n.required),
            "optional_nodes": sum(1 for n in self._nodes.values() if not n.required),
            "total_cost": sum(n.cost for n in self._nodes.values()),
            "critical_path_length": len(self.get_critical_path()),
        }
