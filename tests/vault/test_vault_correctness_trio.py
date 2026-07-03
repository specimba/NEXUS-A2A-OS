"""tests/vault/test_vault_correctness_trio.py — P2-6: three audit-flagged
vault correctness bugs, one test class each."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from nexus_os.vault.memory_channels import (
    CHANNEL_WRITE_TRUST,
    ChannelRecord,
    MemoryChannel,
    MemoryChannelManager,
)
from nexus_os.vault.persistent_trust_memory import PersistentMemoryTracks
from nexus_os.vault.semantic_backend import ChromaBackend


class TestAdaptivePersistenceTrustGate:
    """Upward channel migration is a write and must clear the same trust
    gate as a direct append — access-frequency grinding must not promote
    low-trust content into PROCEDURAL/TRUST."""

    def _eidetic_record(self, channel: MemoryChannel) -> ChannelRecord:
        r = ChannelRecord(channel=channel, agent_id="agent-a", content="x")
        r.persistence_score = 0.5
        r.access_count = 1000  # drives persistence_score toward eidetic
        r.last_access = __import__("time").time()
        return r

    def test_low_trust_agent_cannot_promote_into_gated_channel(self):
        m = MemoryChannelManager()
        m.append_trust(
            agent_id="agent-a", lane="general", trust_score=0.10,
            evidence_count=1, content="low trust", writer_trust=100.0,
        )
        m._buffers["agent-a"][MemoryChannel.SEMANTIC].append(
            self._eidetic_record(MemoryChannel.SEMANTIC)
        )
        migrations = m.run_adaptive_persistence("agent-a")
        # SEMANTIC → PROCEDURAL requires trust >= 80; agent has 10.
        assert migrations.get(MemoryChannel.PROCEDURAL.value, 0) == 0
        assert len(m._buffers["agent-a"][MemoryChannel.SEMANTIC]) == 1

    def test_high_trust_agent_can_promote(self):
        m = MemoryChannelManager()
        m.append_trust(
            agent_id="agent-a", lane="general", trust_score=0.95,
            evidence_count=10, content="high trust", writer_trust=100.0,
        )
        m._buffers["agent-a"][MemoryChannel.SEMANTIC].append(
            self._eidetic_record(MemoryChannel.SEMANTIC)
        )
        migrations = m.run_adaptive_persistence("agent-a")
        assert migrations.get(MemoryChannel.PROCEDURAL.value, 0) == 1

    def test_no_trust_history_blocks_promotion(self):
        """Fail-closed: unknown agents cannot climb channels."""
        m = MemoryChannelManager()
        m._buffers["agent-b"][MemoryChannel.EPISODIC].append(
            self._eidetic_record(MemoryChannel.EPISODIC)
        )
        migrations = m.run_adaptive_persistence("agent-b")
        assert migrations.get(MemoryChannel.SEMANTIC.value, 0) == 0

    def test_downward_fade_ungated(self):
        m = MemoryChannelManager()
        r = ChannelRecord(channel=MemoryChannel.EPISODIC, agent_id="agent-c", content="x")
        r.persistence_score = 0.0
        r.access_count = 0
        r.last_access = __import__("time").time() - 3600 * 24 * 30
        m._buffers["agent-c"][MemoryChannel.EPISODIC].append(r)
        migrations = m.run_adaptive_persistence("agent-c")
        assert migrations.get(MemoryChannel.WORKING.value, 0) == 1


class TestGovernanceFlagsSerializable:
    """persistent_trust_memory.py: the first governance event used to crash
    _save() with 'Object of type set is not JSON serializable'."""

    def test_first_governance_event_persists(self, tmp_path):
        p = tmp_path / "trust_memory.json"
        pmt = PersistentMemoryTracks(path=p)
        pmt.record_governance_event("agent-a", "violation", "canary detail")
        # Survived _save(); file round-trips
        raw = json.loads(p.read_text(encoding="utf-8"))
        assert raw["governance_memory"]["agent-a"]["events"][0]["type"] == "violation"

    def test_reload_preserves_governance(self, tmp_path):
        p = tmp_path / "trust_memory.json"
        pmt = PersistentMemoryTracks(path=p)
        pmt.record_governance_event("agent-a", "violation")
        pmt2 = PersistentMemoryTracks(path=p)
        assert pmt2.get_governance_summary("agent-a")["events"] == 1


class TestSemanticScoreNotInverted:
    """semantic_backend: an exact match (distance 0) used to score 0.0 —
    the worst score — so perfect hits ranked last."""

    def _results(self):
        return {
            "ids": [["exact", "near", "far"]],
            "distances": [[0.0, 0.5, 5.0]],
            "documents": [["exact doc", "near doc", "far doc"]],
            "metadatas": [[{}, {}, {}]],
        }

    def test_exact_match_scores_highest(self):
        mapped = ChromaBackend._map_chroma_results(self._results())
        by_id = {r.id: r.score for r in mapped}
        assert by_id["exact"] == pytest.approx(1.0)
        assert by_id["exact"] > by_id["near"] > by_id["far"]

    def test_ranking_by_score_puts_exact_first(self):
        mapped = ChromaBackend._map_chroma_results(self._results())
        ranked = sorted(mapped, key=lambda r: r.score, reverse=True)
        assert ranked[0].id == "exact"
