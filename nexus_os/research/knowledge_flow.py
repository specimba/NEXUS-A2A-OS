import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeNode:
    """
    A single node in the FlowSearch DAG representing a knowledge search, solve, or answer task.
    """
    id: str
    type: str  # must be 'search', 'solve', or 'answer'
    query: str
    result: str = ""
    parents: List[str] = field(default_factory=list)
    children: List[str] = field(default_factory=list)
    status: str = "pending"  # pending | running | complete | failed

    def __post_init__(self):
        valid_types = {"search", "solve", "answer"}
        if self.type not in valid_types:
            raise ValueError(f"Invalid node type '{self.type}'. Must be one of {valid_types}")
        valid_statuses = {"pending", "running", "complete", "failed"}
        if self.status not in valid_statuses:
            raise ValueError(f"Invalid status '{self.status}'. Must be one of {valid_statuses}")


class FlowSearchDAG:
    """
    DAG-of-knowledge representation for incremental refinement.
    Supports 6 mutations: AddNode, DelNode, ModNode, AddEdge, DelEdge, ModEdge.
    """

    def __init__(self):
        self.nodes: Dict[str, KnowledgeNode] = {}

    def add_node(self, node: KnowledgeNode) -> bool:
        """Add a node to the DAG. Returns True if successful."""
        if node.id in self.nodes:
            logger.warning("FlowSearchDAG: Node '%s' already exists", node.id)
            return False
        self.nodes[node.id] = node
        # Ensure relations are synced
        for pid in node.parents:
            if pid in self.nodes and node.id not in self.nodes[pid].children:
                self.nodes[pid].children.append(node.id)
        for cid in node.children:
            if cid in self.nodes and node.id not in self.nodes[cid].parents:
                self.nodes[cid].parents.append(node.id)
        return True

    def delete_node(self, node_id: str) -> bool:
        """Delete a node and all its edges from the DAG. Returns True if successful."""
        if node_id not in self.nodes:
            return False
        node = self.nodes[node_id]
        # Remove reference from parents' children list
        for pid in node.parents:
            if pid in self.nodes:
                self.nodes[pid].children = [cid for cid in self.nodes[pid].children if cid != node_id]
        # Remove reference from children's parents list
        for cid in node.children:
            if cid in self.nodes:
                self.nodes[cid].parents = [pid for pid in self.nodes[cid].parents if pid != node_id]
        del self.nodes[node_id]
        return True

    def modify_node(self, node_id: str, **kwargs) -> bool:
        """Modify attributes of a node (e.g. query, status, result)."""
        if node_id not in self.nodes:
            return False
        node = self.nodes[node_id]
        for key, value in kwargs.items():
            if hasattr(node, key):
                setattr(node, key, value)
        # re-validate types/status
        node.__post_init__()
        return True

    def add_edge(self, parent_id: str, child_id: str) -> bool:
        """Add a dependency edge parent_id -> child_id. Returns True if successful."""
        if parent_id not in self.nodes or child_id not in self.nodes:
            logger.warning("FlowSearchDAG: Cannot add edge, nodes not found: %s -> %s", parent_id, child_id)
            return False
        
        # Prevent duplicate edge
        if child_id in self.nodes[parent_id].children:
            return True

        self.nodes[parent_id].children.append(child_id)
        self.nodes[child_id].parents.append(parent_id)

        # Check for cycles. If cycle exists, roll back edge addition.
        if not self.is_valid_dag():
            logger.warning("FlowSearchDAG: Cycle detected when adding edge %s -> %s", parent_id, child_id)
            self.nodes[parent_id].children.remove(child_id)
            self.nodes[child_id].parents.remove(parent_id)
            return False

        return True

    def delete_edge(self, parent_id: str, child_id: str) -> bool:
        """Remove dependency edge parent_id -> child_id."""
        if parent_id not in self.nodes or child_id not in self.nodes:
            return False
        parent = self.nodes[parent_id]
        child = self.nodes[child_id]
        if child_id in parent.children:
            parent.children.remove(child_id)
        if parent_id in child.parents:
            child.parents.remove(parent_id)
        return True

    def modify_edge(self, old_parent_id: str, old_child_id: str, new_parent_id: str, new_child_id: str) -> bool:
        """Modify an edge by deleting the old one and creating the new one."""
        if not self.delete_edge(old_parent_id, old_child_id):
            return False
        if not self.add_edge(new_parent_id, new_child_id):
            # Rollback
            self.add_edge(old_parent_id, old_child_id)
            return False
        return True

    def get_ready_nodes(self) -> List[KnowledgeNode]:
        """Return all nodes that are pending and have all their parent dependencies met."""
        ready = []
        for node in self.nodes.values():
            if node.status == "pending":
                # Check if all parents are complete
                parents_met = True
                for pid in node.parents:
                    if pid not in self.nodes or self.nodes[pid].status != "complete":
                        parents_met = False
                        break
                if parents_met:
                    ready.append(node)
        return ready

    def is_valid_dag(self) -> bool:
        """Verify the graph has no cycles and all references are valid."""
        # Check references first
        for nid, node in self.nodes.items():
            for pid in node.parents:
                if pid not in self.nodes:
                    return False
            for cid in node.children:
                if cid not in self.nodes:
                    return False

        # Cycle detection using DFS coloring
        visited = {}  # nid -> state: 0=unvisited, 1=visiting, 2=visited
        for nid in self.nodes:
            visited[nid] = 0

        def dfs(nid) -> bool:
            visited[nid] = 1  # visiting
            for cid in self.nodes[nid].children:
                if visited[cid] == 1:
                    return False  # cycle detected
                if visited[cid] == 0:
                    if not dfs(cid):
                        return False
            visited[nid] = 2  # visited
            return True

        for nid in self.nodes:
            if visited[nid] == 0:
                if not dfs(nid):
                    return False

        return True

    def topological_sort(self) -> List[str]:
        """Return node IDs sorted topologically."""
        if not self.is_valid_dag():
            raise ValueError("Graph is not a valid DAG (contains cycles)")

        visited = set()
        stack = []

        def dfs(nid):
            visited.add(nid)
            for cid in self.nodes[nid].children:
                if cid not in visited:
                    dfs(cid)
            stack.insert(0, nid)

        for nid in self.nodes:
            if nid not in visited:
                dfs(nid)

        return stack
