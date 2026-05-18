"""TrustKernel gating for memory writes."""

from types import SimpleNamespace

import pytest

from nexus_os.governor.trust_kernel import TrustDecisionKind
from nexus_os.vault.memory_adapter import Mem0Adapter


class _FakeDecision:
    def __init__(self, decision: TrustDecisionKind, reason: str = "test decision"):
        self.decision = decision
        self.reason = reason

    def to_dict(self):
        return {
            "decision": self.decision.value,
            "reason": self.reason,
            "snapshot": {"agent_id": "agent-a", "lane": "implementation"},
            "source": "fake_trust_kernel",
        }


class _FakeTrustKernel:
    def __init__(self, decision: TrustDecisionKind):
        self._decision = decision
        self.evaluations = []
        self.events = []

    def evaluate(self, **kwargs):
        self.evaluations.append(kwargs)
        return _FakeDecision(self._decision)

    def record_event(self, event):
        self.events.append(event)
        return SimpleNamespace(to_dict=lambda: {})


def test_memory_store_records_trust_event_on_allowed_write(tmp_path):
    kernel = _FakeTrustKernel(TrustDecisionKind.ALLOW)
    adapter = Mem0Adapter(
        config={
            "force_local": True,
            "storage_path": str(tmp_path / "memories.json"),
            "trust_kernel": kernel,
        }
    )

    memory_id = adapter.store("agent-a", "Store useful learning", layer="project")
    stored = adapter._get_memory(memory_id)

    assert kernel.evaluations[0]["action"] == "write"
    assert kernel.evaluations[0]["lane"] == "vault_write"
    assert kernel.events[0].event_type == "memory_write"
    assert stored["metadata"]["trust_decision"]["decision"] == "allow"


def test_memory_store_blocks_low_trust_write(tmp_path):
    kernel = _FakeTrustKernel(TrustDecisionKind.DENY)
    adapter = Mem0Adapter(
        config={
            "force_local": True,
            "storage_path": str(tmp_path / "memories.json"),
            "trust_kernel": kernel,
        }
    )

    with pytest.raises(PermissionError, match="Memory write blocked by TrustKernel"):
        adapter.store("agent-a", "Unsafe write", layer="project")

    assert kernel.evaluations
    assert kernel.events == []
