import pytest
from nexus_os.research.knowledge_flow import FlowSearchDAG, KnowledgeNode

def test_node_validation():
    # Valid types
    KnowledgeNode(id="n1", type="search", query="search x")
    KnowledgeNode(id="n2", type="solve", query="solve y")
    KnowledgeNode(id="n3", type="answer", query="answer z")

    # Invalid type
    with pytest.raises(ValueError, match="Invalid node type"):
        KnowledgeNode(id="n4", type="invalid", query="invalid type")

    # Invalid status
    with pytest.raises(ValueError, match="Invalid status"):
        KnowledgeNode(id="n5", type="search", query="invalid status", status="invalid")


def test_dag_mutations():
    dag = FlowSearchDAG()
    
    # 1. AddNode
    n1 = KnowledgeNode(id="node1", type="search", query="search query")
    n2 = KnowledgeNode(id="node2", type="solve", query="solve query")
    assert dag.add_node(n1) is True
    assert dag.add_node(n2) is True
    assert len(dag.nodes) == 2

    # Duplicate node add should fail
    assert dag.add_node(n1) is False

    # 2. AddEdge
    assert dag.add_edge("node1", "node2") is True
    assert "node2" in dag.nodes["node1"].children
    assert "node1" in dag.nodes["node2"].parents

    # 3. ModNode
    assert dag.modify_node("node1", query="new search query", status="complete") is True
    assert dag.nodes["node1"].query == "new search query"
    assert dag.nodes["node1"].status == "complete"

    # 4. ModEdge
    n3 = KnowledgeNode(id="node3", type="answer", query="answer query")
    dag.add_node(n3)
    # Modify edge node1->node2 to node1->node3
    assert dag.modify_edge("node1", "node2", "node1", "node3") is True
    assert "node2" not in dag.nodes["node1"].children
    assert "node3" in dag.nodes["node1"].children

    # 5. DelEdge
    assert dag.delete_edge("node1", "node3") is True
    assert "node3" not in dag.nodes["node1"].children

    # 6. DelNode
    dag.add_edge("node1", "node2")
    assert dag.delete_node("node1") is True
    assert "node1" not in dag.nodes
    # Check that deleted node references are removed from neighbors
    assert "node1" not in dag.nodes["node2"].parents


def test_cycle_detection():
    dag = FlowSearchDAG()
    n1 = KnowledgeNode(id="n1", type="search", query="q1")
    n2 = KnowledgeNode(id="n2", type="solve", query="q2")
    n3 = KnowledgeNode(id="n3", type="answer", query="q3")
    
    dag.add_node(n1)
    dag.add_node(n2)
    dag.add_node(n3)

    assert dag.add_edge("n1", "n2") is True
    assert dag.add_edge("n2", "n3") is True
    # n3 -> n1 would create cycle
    assert dag.add_edge("n3", "n1") is False
    # Check that graph is still a valid DAG
    assert dag.is_valid_dag() is True
    assert "n1" not in dag.nodes["n3"].children


def test_topological_sort():
    dag = FlowSearchDAG()
    n1 = KnowledgeNode(id="n1", type="search", query="q1")
    n2 = KnowledgeNode(id="n2", type="solve", query="q2")
    n3 = KnowledgeNode(id="n3", type="answer", query="q3")
    
    dag.add_node(n1)
    dag.add_node(n2)
    dag.add_node(n3)
    
    dag.add_edge("n1", "n2")
    dag.add_edge("n2", "n3")

    sort = dag.topological_sort()
    assert sort == ["n1", "n2", "n3"]


def test_ready_nodes():
    dag = FlowSearchDAG()
    n1 = KnowledgeNode(id="n1", type="search", query="q1")
    n2 = KnowledgeNode(id="n2", type="solve", query="q2")
    n3 = KnowledgeNode(id="n3", type="answer", query="q3")
    
    dag.add_node(n1)
    dag.add_node(n2)
    dag.add_node(n3)
    
    dag.add_edge("n1", "n2")
    dag.add_edge("n2", "n3")

    # Initially, only n1 has no parents, so only n1 is ready
    ready = dag.get_ready_nodes()
    assert [n.id for n in ready] == ["n1"]

    # Mark n1 complete
    dag.modify_node("n1", status="complete")
    # Now n2 has parents met and is ready
    ready = dag.get_ready_nodes()
    assert [n.id for n in ready] == ["n2"]

    # Mark n2 complete
    dag.modify_node("n2", status="complete")
    ready = dag.get_ready_nodes()
    assert [n.id for n in ready] == ["n3"]
