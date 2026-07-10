"""Tests for evidence-graded trust in the DoppelGround bridge (Wave 2.3).

The bridge previously defaulted every vault write to trust=90.0, which
"passes all current channel trust gates" -- letting DG-sourced intel bypass
the vault's write gates. Trust is now computed per record from evidence
grade (E0/E1, continuity writer-fence vocabulary) and provenance:

- E0 / missing / unknown grade -> TRUST_E0 (25.0), below every gated
  channel threshold (fail-closed).
- E1 (verified)                -> [65.0, 79.0] band, scaled by quality.
- trust >= 90 requires an explicit ``operator_grade`` on the record, or an
  explicit constructor-level operator override -- never a default.

Gate-enforcement tests here run against a REAL MemoryChannelManager (no
mocked vault) so the vault's CHANNEL_WRITE_TRUST gates actually fire.
"""

import pytest
from dataclasses import dataclass, field
from typing import List, Optional

from nexus_os.archivist.doppelground_bridge import (
    DoppelGroundBridge,
    TRUST_E0,
    TRUST_E1_BASE,
    TRUST_E1_SPAN,
)
from nexus_os.vault.memory_channels import (
    CHANNEL_WRITE_TRUST,
    MemoryChannel,
    MemoryChannelManager,
)

BRIDGE_AGENT_ID = "doppelground-bridge"

# Every gated (non-zero) vault write threshold.
GATED_THRESHOLDS = {ch: t for ch, t in CHANNEL_WRITE_TRUST.items() if t > 0}
LOWEST_GATE = min(GATED_THRESHOLDS.values())


# --- Real-dataclass stubs (getattr semantics must match real records) ----

@dataclass
class ImportRecordStub:
    file_path: str = "/dg/test_record.md"
    file_type: str = "unknown"
    priority: int = 80
    blake3_hash: str = "abc123def4567890"
    title: Optional[str] = "DG Trust Test Record"
    arxiv_id: Optional[str] = None
    evidence_grade: Optional[str] = None
    operator_grade: Optional[float] = None


@dataclass
class CompiledRecordStub:
    import_record: ImportRecordStub = field(default_factory=ImportRecordStub)
    topic_tags: List[str] = field(default_factory=lambda: ["memory"])
    citation_links: List[str] = field(default_factory=list)
    dossier_topic: Optional[str] = "memory"
    word_count: Optional[int] = 500
    quality_score: float = 0.0
    is_wiki_admissible: bool = True
    compile_errors: List[str] = field(default_factory=list)
    evidence_grade: Optional[str] = None
    operator_grade: Optional[float] = None


@dataclass
class DossierStub:
    topic: str = "memory"
    title: str = "Dossier: Memory"
    content: str = "Test dossier content"
    tags: List[str] = field(default_factory=lambda: ["memory"])
    quality_score: float = 0.0
    evidence_grade: Optional[str] = None
    operator_grade: Optional[float] = None


@pytest.fixture(autouse=True)
def _no_semantic_backend(monkeypatch):
    """Keep the real vault hermetic: no ChromaDB/hybrid backend spin-up."""
    import nexus_os.vault.semantic_backend as sb
    monkeypatch.setattr(sb, "get_semantic_backend", lambda: None)


def make_real_bridge(**kwargs) -> DoppelGroundBridge:
    """Bridge wired to a FRESH real MemoryChannelManager (gates active)."""
    bridge = DoppelGroundBridge(**kwargs)
    bridge._manager = MemoryChannelManager()
    return bridge


def channel_buffer(bridge: DoppelGroundBridge, channel: MemoryChannel):
    return bridge._manager._buffers[BRIDGE_AGENT_ID][channel]


# --- compute_trust() unit semantics ---------------------------------------

class TestComputeTrust:

    def setup_method(self):
        self.bridge = DoppelGroundBridge()

    def test_e0_below_every_gated_threshold(self):
        rec = CompiledRecordStub(evidence_grade="E0")
        trust = self.bridge.compute_trust(rec)
        assert trust == TRUST_E0
        assert trust < LOWEST_GATE, (
            "E0 trust must be below every gated channel threshold"
        )

    def test_missing_grade_treated_as_e0(self):
        rec = CompiledRecordStub(evidence_grade=None)
        assert self.bridge.compute_trust(rec) == TRUST_E0

    def test_unknown_grade_treated_as_e0(self):
        for bogus in ("E9", "verified", "", "  ", "high"):
            rec = CompiledRecordStub(evidence_grade=bogus)
            assert self.bridge.compute_trust(rec) == TRUST_E0, bogus

    def test_e1_lands_in_65_79_band(self):
        rec = CompiledRecordStub(evidence_grade="E1", quality_score=0.5)
        trust = self.bridge.compute_trust(rec)
        assert 65.0 <= trust <= 79.0
        assert trust == pytest.approx(TRUST_E1_BASE + TRUST_E1_SPAN * 0.5)

    def test_e1_band_extremes_and_quality_clamp(self):
        low = self.bridge.compute_trust(
            CompiledRecordStub(evidence_grade="E1", quality_score=0.0))
        high = self.bridge.compute_trust(
            CompiledRecordStub(evidence_grade="E1", quality_score=1.0))
        over = self.bridge.compute_trust(
            CompiledRecordStub(evidence_grade="E1", quality_score=5.0))
        assert low == pytest.approx(65.0)
        assert high == pytest.approx(79.0)
        assert over == pytest.approx(79.0)  # quality clamped to [0, 1]

    def test_e1_never_reaches_procedural_or_trust_gates(self):
        for q in (0.0, 0.3, 0.5, 1.0, 99.0):
            trust = self.bridge.compute_trust(
                CompiledRecordStub(evidence_grade="E1", quality_score=q))
            assert trust < CHANNEL_WRITE_TRUST[MemoryChannel.PROCEDURAL]
            assert trust < CHANNEL_WRITE_TRUST[MemoryChannel.TRUST]

    def test_e1_grade_is_case_insensitive(self):
        rec = CompiledRecordStub(evidence_grade=" e1 ", quality_score=0.5)
        assert self.bridge.compute_trust(rec) == pytest.approx(72.0)

    def test_never_auto_90_without_operator_grade(self):
        for grade in (None, "E0", "E1", "E9"):
            rec = CompiledRecordStub(evidence_grade=grade, quality_score=1.0)
            assert self.bridge.compute_trust(rec) < 90.0

    def test_operator_grade_enables_high_trust(self):
        rec = CompiledRecordStub(evidence_grade="E0", operator_grade=95.0)
        assert self.bridge.compute_trust(rec) == 95.0

    def test_operator_grade_clamped_to_0_100(self):
        assert self.bridge.compute_trust(
            CompiledRecordStub(operator_grade=150.0)) == 100.0
        assert self.bridge.compute_trust(
            CompiledRecordStub(operator_grade=-5.0)) == 0.0

    def test_operator_grade_read_from_import_record(self):
        rec = CompiledRecordStub(
            import_record=ImportRecordStub(operator_grade=92.0))
        assert self.bridge.compute_trust(rec) == 92.0

    def test_evidence_grade_read_from_import_record(self):
        rec = CompiledRecordStub(
            import_record=ImportRecordStub(evidence_grade="E1"),
            quality_score=0.5,
        )
        assert self.bridge.compute_trust(rec) == pytest.approx(72.0)

    def test_invalid_operator_grade_falls_back_to_evidence(self):
        rec = CompiledRecordStub(
            evidence_grade="E1", quality_score=0.5,
            operator_grade="not-a-number",
        )
        assert self.bridge.compute_trust(rec) == pytest.approx(72.0)

    def test_constructor_override_still_honored(self):
        bridge = DoppelGroundBridge(trust_score_default=90.0)
        rec = CompiledRecordStub(evidence_grade="E0")
        assert bridge.compute_trust(rec) == 90.0

    def test_default_is_compute_not_flat_ninety(self):
        assert DoppelGroundBridge()._trust_default is None


# --- Gate enforcement against a REAL vault manager ------------------------

class TestGateEnforcementRealVault:

    def test_e0_write_to_gated_channel_rejected(self):
        """THE negative test: E0 record must FAIL the gated-channel write."""
        bridge = make_real_bridge()
        rec = CompiledRecordStub(topic_tags=["memory"], evidence_grade="E0")
        result = bridge.bridge_compiled(rec)
        assert result.target_channel == 3  # SEMANTIC, gate 65
        assert result.accepted is False
        assert "trust_gate" in result.reason
        assert channel_buffer(bridge, MemoryChannel.SEMANTIC) == []
        assert bridge.get_stats()["rejected"] == 1

    def test_missing_grade_rejected_fail_closed(self):
        bridge = make_real_bridge()
        rec = CompiledRecordStub(topic_tags=["memory"], evidence_grade=None)
        result = bridge.bridge_compiled(rec)
        assert result.accepted is False
        assert "trust_gate" in result.reason

    def test_e0_rules_rejected_at_trust_channel_gate_90(self):
        bridge = make_real_bridge()
        rec = CompiledRecordStub(topic_tags=["rules"], evidence_grade="E0")
        result = bridge.bridge_compiled(rec)
        assert result.target_channel == 5  # TRUST, gate 90 on writer_trust
        assert result.accepted is False
        assert channel_buffer(bridge, MemoryChannel.TRUST) == []

    def test_e0_rejection_example_rejected_at_episodic_gate(self):
        bridge = make_real_bridge()
        rec = CompiledRecordStub(topic_tags=["rejection"], evidence_grade="E0")
        result = bridge.bridge_compiled(rec)
        assert result.target_channel == 2  # EPISODIC, gate 30
        assert result.accepted is False
        assert channel_buffer(bridge, MemoryChannel.EPISODIC) == []

    def test_e1_semantic_write_accepted_in_band(self):
        bridge = make_real_bridge()
        rec = CompiledRecordStub(
            topic_tags=["memory"], evidence_grade="E1", quality_score=0.5)
        assert 65.0 <= bridge.compute_trust(rec) <= 79.0
        result = bridge.bridge_compiled(rec)
        assert result.accepted is True
        assert result.target_channel == 3
        assert len(channel_buffer(bridge, MemoryChannel.SEMANTIC)) == 1

    def test_e1_code_rejected_at_procedural_gate_80(self):
        bridge = make_real_bridge()
        rec = CompiledRecordStub(
            topic_tags=["code"], evidence_grade="E1", quality_score=1.0)
        result = bridge.bridge_compiled(rec)
        assert result.target_channel == 4  # PROCEDURAL, gate 80; E1 max 79
        assert result.accepted is False
        assert channel_buffer(bridge, MemoryChannel.PROCEDURAL) == []

    def test_operator_graded_rules_accepted_at_trust_channel(self):
        bridge = make_real_bridge()
        rec = CompiledRecordStub(
            topic_tags=["rules"], evidence_grade="E0", operator_grade=95.0)
        result = bridge.bridge_compiled(rec)
        assert result.target_channel == 5
        assert result.accepted is True
        assert len(channel_buffer(bridge, MemoryChannel.TRUST)) == 1

    def test_constructor_operator_override_accepts_e0(self):
        bridge = make_real_bridge(trust_score_default=90.0)
        rec = CompiledRecordStub(topic_tags=["memory"], evidence_grade="E0")
        result = bridge.bridge_compiled(rec)
        assert result.accepted is True

    def test_e0_dossier_rejected(self):
        bridge = make_real_bridge()
        dossier = DossierStub(evidence_grade="E0")
        results = bridge.bridge_dossiers([dossier])
        assert results[0].accepted is False
        assert "trust_gate" in results[0].reason

    def test_e1_dossier_accepted(self):
        bridge = make_real_bridge()
        dossier = DossierStub(evidence_grade="E1", quality_score=0.5)
        results = bridge.bridge_dossiers([dossier])
        assert results[0].accepted is True
        assert len(channel_buffer(bridge, MemoryChannel.SEMANTIC)) == 1
