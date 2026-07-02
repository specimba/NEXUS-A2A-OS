from nexus_os.governor.trust_engine_v2 import CDRStage
from nexus_os.governor.trust_kernel import ResourceBudgetClass, TrustKernel, TrustSnapshot
from nexus_os.vault.governed_memory_broker import GovernedMemoryBroker
from nexus_os.vault.memory import MemoryChannel, SuperLocalMemory
from nexus_os.vault.memory_channels import MemoryChannelManager, get_manager


class FakeSemanticMemory:
    def __init__(self):
        self.calls = []

    def search(self, query, agent_id=None, limit=5, layer=None):
        self.calls.append(
            {
                "query": query,
                "agent_id": agent_id,
                "limit": limit,
                "layer": layer,
            }
        )
        return [
            {
                "id": "sem-1",
                "content": "wisdom vector cache lesson for Nexus memory routing",
                "layer": "wisdom",
                "score": 0.94,
            }
        ]


def _elevated_kernel(agent_id="agent-elevated", lane="implementation"):
    kernel = TrustKernel()
    kernel._snapshots[(agent_id, lane)] = TrustSnapshot(
        agent_id=agent_id,
        lane=lane,
        trust=0.86,
        alpha=30.0,
        beta=4.0,
        evidence_count=30,
        authority_band="elevated",
        cdr_stage=CDRStage.NORMAL.value,
    )
    return kernel


def _locked_kernel(agent_id="agent-locked", lane="implementation"):
    kernel = TrustKernel()
    kernel._snapshots[(agent_id, lane)] = TrustSnapshot(
        agent_id=agent_id,
        lane=lane,
        trust=0.74,
        alpha=20.0,
        beta=7.0,
        evidence_count=20,
        authority_band="restricted",
        cdr_stage=CDRStage.COLLAPSE.value,
        cdr_severity=CDRStage.COLLAPSE.severity,
        risk_flags=("hard_fail", "memory_poisoning"),
    )
    return kernel


def test_cold_start_budget_limits_memory_to_local_hot_and_canonical_paths():
    hot = SuperLocalMemory()
    hot.store(MemoryChannel.CONTEXT, "nexus trust memory", "hot local signal")
    tracks = get_manager()
    tracks.append_episodic(
        "agent-cold",
        "first task observed",
        outcome="success",
        duration_ms=11,
        token_count=22,
    )
    tracks.append_trust("agent-cold", "orchestration", trust_score=0.5, evidence_count=0, writer_trust=100.0)
    semantic = FakeSemanticMemory()

    broker = GovernedMemoryBroker(
        trust_kernel=TrustKernel(),
        hot_memory=hot,
        channel_memory=tracks,
        semantic_memory=semantic,
    )

    context = broker.build_context(
        agent_id="agent-cold",
        lane="orchestration",
        query="nexus trust memory",
        requested_tokens=800,
    )

    assert context.plan.budget_class == ResourceBudgetClass.CONSTRAINED.value
    assert "hot_superlocal" in context.plan.enabled_paths
    assert "canonical_5track" in context.plan.enabled_paths
    assert context.semantic_entries == []
    assert semantic.calls == []
    assert "semantic_mem0:trust_depth_below_semantic_floor" in context.plan.denied_paths
    assert "hot local signal" in context.context_text


def test_elevated_budget_can_use_semantic_recall_when_explicitly_injected():
    hot = SuperLocalMemory()
    hot.store(MemoryChannel.CONTEXT, "nexus memory routing", "hot S-P-E-W clue")
    tracks = get_manager()
    tracks.append_episodic(
        "agent-elevated",
        "completed governed memory routing task",
        outcome="success",
        duration_ms=18,
        token_count=33,
    )
    tracks.append_trust("agent-elevated", "implementation", trust_score=0.86, evidence_count=30, writer_trust=100.0)
    tracks.append_procedural("agent-elevated", "python security skill", ["python", "security"], confidence=0.92, trust_score=85.0)
    semantic = FakeSemanticMemory()

    broker = GovernedMemoryBroker(
        trust_kernel=_elevated_kernel(),
        hot_memory=hot,
        channel_memory=tracks,
        semantic_memory=semantic,
    )

    context = broker.build_context(
        agent_id="agent-elevated",
        lane="implementation",
        query="nexus memory routing",
        requested_tokens=600,
    )

    assert context.plan.budget_class == ResourceBudgetClass.ELEVATED.value
    assert context.plan.semantic_limit == 8
    assert semantic.calls == [
        {
            "query": "nexus memory routing",
            "agent_id": "agent-elevated",
            "limit": 8,
            "layer": None,
        }
    ]
    assert "semantic_mem0" in context.plan.enabled_paths
    assert "wisdom vector cache lesson" in context.context_text
    assert "cloud_cold:disabled_by_default" in context.plan.denied_paths


def test_semantic_path_is_denied_when_not_configured_even_for_elevated_agent():
    broker = GovernedMemoryBroker(
        trust_kernel=_elevated_kernel(),
        hot_memory=SuperLocalMemory(),
        channel_memory=get_manager(),
    )

    context = broker.build_context(
        agent_id="agent-elevated",
        lane="implementation",
        query="memory routing",
    )

    assert context.semantic_entries == []
    assert "semantic_mem0:not_configured" in context.plan.denied_paths


def test_locked_budget_returns_no_context_or_memory_reads():
    hot = SuperLocalMemory()
    hot.store(MemoryChannel.CONTEXT, "nexus memory routing", "must not leak")
    semantic = FakeSemanticMemory()
    broker = GovernedMemoryBroker(
        trust_kernel=_locked_kernel(),
        hot_memory=hot,
        channel_memory=get_manager(),
        semantic_memory=semantic,
    )

    context = broker.build_context(
        agent_id="agent-locked",
        lane="implementation",
        query="nexus memory routing",
    )

    assert context.plan.budget_class == ResourceBudgetClass.LOCKED.value
    assert context.hot_entries == []
    assert context.track_records == {}
    assert context.semantic_entries == []
    assert context.context_text == ""
    assert semantic.calls == []
    assert "hot_superlocal:trust_budget_locked" in context.plan.denied_paths


def test_context_text_is_clipped_by_trust_token_budget():
    hot = SuperLocalMemory()
    hot.store(MemoryChannel.CONTEXT, "memory", "x" * 2000)
    broker = GovernedMemoryBroker(
        trust_kernel=_elevated_kernel(),
        hot_memory=hot,
        channel_memory=get_manager(),
    )

    context = broker.build_context(
        agent_id="agent-elevated",
        lane="implementation",
        query="memory",
        requested_tokens=40,
    )

    assert len(context.context_text) <= 160
    assert "[context clipped by TrustKernel memory budget]" in context.context_text
