"""Tests for nexus_os.archivist.doppelground_bridge module.

Covers:
- DGSourceKind enum (12 kinds)
- SOURCE_KIND_TO_CHANNEL mapping
- DoppelGroundBridge.infer_source_kind()
- DoppelGroundBridge.bridge_compiled() (with mocked vault)
- DoppelGroundBridge.bridge_batch()
- DoppelGroundBridge.bridge_dossiers()
- DoppelGroundBridge.get_stats() / reset_stats()
- Singleton get_bridge()
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from dataclasses import dataclass, field
from typing import List, Optional


# --- Minimal stubs for ImportRecord / CompiledRecord / FileType / AdmissionClass ---

class FileTypeStub:
    PAPER = "paper"
    LOG = "log"
    CODE = "code"
    IMAGE = "image"
    PROMPT = "prompt"
    BENCHMARK = "benchmark"
    MARKDOWN = "markdown"
    NOTEBOOK = "notebook"
    DATA = "data"
    CONFIG = "config"
    UNKNOWN = "unknown"


class AdmissionClassStub:
    SOURCE_CARD = "source_card"
    DOSSIER = "dossier"
    WEB_REFERENCE = "web_reference"
    SOCIAL_REFERENCE = "social_reference"
    OPERATOR_FRAGMENT = "operator_fragment"
    TEMPLATE_FRAGMENT = "template_fragment"
    QUARANTINE = "quarantine"


@dataclass
class ImportRecordStub:
    file_path: str = "/test/file.py"
    file_type: FileTypeStub = FileTypeStub.CODE
    admission_class: AdmissionClassStub = AdmissionClassStub.SOURCE_CARD
    priority: int = 80
    blake3_hash: str = "abc123def456"
    file_size: int = 1024
    mtime: float = 1000000.0
    source_dir: str = "/test"
    title: Optional[str] = "Test Code File"
    arxiv_id: Optional[str] = None
    topic_tags: List[str] = field(default_factory=list)
    processed_at: Optional[float] = None
    errors: List[str] = field(default_factory=list)


@dataclass
class CompiledRecordStub:
    import_record: ImportRecordStub = field(default_factory=ImportRecordStub)
    topic_tags: List[str] = field(default_factory=lambda: ["code"])
    citation_links: List[str] = field(default_factory=list)
    dossier_topic: Optional[str] = "code"
    word_count: Optional[int] = 1000
    quality_score: float = 0.8
    is_wiki_admissible: bool = True
    admission_class: Optional[str] = None
    compile_errors: List[str] = field(default_factory=list)


@dataclass
class DossierStub:
    topic: str = "memory"
    title: str = "Dossier: Memory"
    content: str = "Test dossier content"
    source_records: list = field(default_factory=list)
    tags: List[str] = field(default_factory=lambda: ["memory", "trust"])
    source_paper_ids: List[str] = field(default_factory=list)
    confidence: float = 0.9
    priority: int = 110
    nexus_relevance: float = 0.85
    generated_at: str = "2026-06-23T00:00:00Z"


# Patch imports — isolate mock to this file only, preserve real module identity
import sys

# Pre-load real modules so their identities persist
import nexus_os.archivist.import_stage as _real_import_stage
import nexus_os.vault.memory_channels as _real_memory_channels

# Mock the import_stage module
mock_import_stage = MagicMock()
mock_import_stage.FileType = FileTypeStub
mock_import_stage.AdmissionClass = AdmissionClassStub
mock_import_stage.ImportRecord = ImportRecordStub

# Mock the vault memory_channels
mock_memory_channels = MagicMock()

# Set up temporary modules for import time
sys.modules['nexus_os.archivist.import_stage'] = mock_import_stage
sys.modules['nexus_os.vault.memory_channels'] = mock_memory_channels

from nexus_os.archivist.doppelground_bridge import (
    DoppelGroundBridge,
    DGSourceKind,
    SOURCE_KIND_TO_CHANNEL,
    BridgeResult,
    get_bridge,
)

# Restore real modules — do NOT leave holes that change class identities
sys.modules['nexus_os.archivist.import_stage'] = _real_import_stage
sys.modules['nexus_os.vault.memory_channels'] = _real_memory_channels

# Use autouse fixture to apply mocks during test execution
@pytest.fixture(autouse=True)
def apply_mocks(monkeypatch):
    monkeypatch.setitem(sys.modules, 'nexus_os.archivist.import_stage', mock_import_stage)
    monkeypatch.setitem(sys.modules, 'nexus_os.vault.memory_channels', mock_memory_channels)


class TestDGSourceKind:
    """Test the DGSourceKind enum."""

    def test_twelve_source_kinds(self):
        """DGSourceKind must have exactly 12 members."""
        assert len(DGSourceKind) == 12

    def test_all_expected_kinds(self):
        expected = {
            "rules", "config", "mission", "doc", "deep_research", "spec",
            "code", "test", "skill", "rejection_example", "role", "golden_dataset",
        }
        actual = {kind.value for kind in DGSourceKind}
        assert actual == expected

    def test_str_enum_behavior(self):
        assert DGSourceKind.RULES == "rules"
        assert DGSourceKind.CODE == "code"


class TestSourceKindToChannelMapping:
    """Test the source_kind → vault channel mapping."""

    def test_rules_maps_to_trust_channel_5(self):
        assert SOURCE_KIND_TO_CHANNEL["rules"] == 5

    def test_config_maps_to_trust_channel_5(self):
        assert SOURCE_KIND_TO_CHANNEL["config"] == 5

    def test_mission_maps_to_semantic_channel_3(self):
        assert SOURCE_KIND_TO_CHANNEL["mission"] == 3

    def test_doc_maps_to_semantic_channel_3(self):
        assert SOURCE_KIND_TO_CHANNEL["doc"] == 3

    def test_deep_research_maps_to_semantic_channel_3(self):
        assert SOURCE_KIND_TO_CHANNEL["deep_research"] == 3

    def test_spec_maps_to_semantic_channel_3(self):
        assert SOURCE_KIND_TO_CHANNEL["spec"] == 3

    def test_code_maps_to_procedural_channel_4(self):
        assert SOURCE_KIND_TO_CHANNEL["code"] == 4

    def test_test_maps_to_procedural_channel_4(self):
        assert SOURCE_KIND_TO_CHANNEL["test"] == 4

    def test_skill_maps_to_procedural_channel_4(self):
        assert SOURCE_KIND_TO_CHANNEL["skill"] == 4

    def test_rejection_example_maps_to_episodic_channel_2(self):
        assert SOURCE_KIND_TO_CHANNEL["rejection_example"] == 2

    def test_role_maps_to_task_channel_6(self):
        assert SOURCE_KIND_TO_CHANNEL["role"] == 6

    def test_golden_dataset_maps_to_meta_channel_7(self):
        assert SOURCE_KIND_TO_CHANNEL["golden_dataset"] == 7

    def test_all_12_kinds_have_mapping(self):
        for kind in DGSourceKind:
            assert kind.value in SOURCE_KIND_TO_CHANNEL, f"Missing mapping for {kind.value}"


class TestInferSourceKind:
    """Test DoppelGroundBridge.infer_source_kind()."""

    def setup_method(self):
        self.bridge = DoppelGroundBridge()

    def test_code_tag_maps_to_code(self):
        record = CompiledRecordStub(topic_tags=["code"])
        assert self.bridge.infer_source_kind(record) == "code"

    def test_rules_tag_maps_to_rules(self):
        record = CompiledRecordStub(topic_tags=["rules"])
        assert self.bridge.infer_source_kind(record) == "rules"

    def test_rejection_tag_maps_to_rejection_example(self):
        record = CompiledRecordStub(topic_tags=["rejection"])
        assert self.bridge.infer_source_kind(record) == "rejection_example"

    def test_governance_tag_maps_to_rules(self):
        """governance topic should map to rules (policy)."""
        record = CompiledRecordStub(topic_tags=["governance"])
        assert self.bridge.infer_source_kind(record) == "rules"

    def test_security_tag_maps_to_rules(self):
        """security topic should map to rules (guardrails)."""
        record = CompiledRecordStub(topic_tags=["security"])
        assert self.bridge.infer_source_kind(record) == "rules"

    def test_benchmark_tag_maps_to_golden_dataset(self):
        """benchmark topic should map to golden_dataset."""
        record = CompiledRecordStub(topic_tags=["benchmark"])
        assert self.bridge.infer_source_kind(record) == "golden_dataset"

    def test_no_matching_tag_defaults_to_doc(self):
        """Unknown topic tags should default to 'doc'."""
        record = CompiledRecordStub(
            import_record=ImportRecordStub(file_type="unknown"),
            topic_tags=["unknown_topic_xyz"]
        )
        assert self.bridge.infer_source_kind(record) == "doc"

    def test_empty_tags_defaults_to_doc(self):
        record = CompiledRecordStub(
            import_record=ImportRecordStub(file_type="unknown"),
            topic_tags=[]
        )
        assert self.bridge.infer_source_kind(record) == "doc"


class TestBridgeCompiled:
    """Test DoppelGroundBridge.bridge_compiled()."""

    def setup_method(self):
        self.bridge = DoppelGroundBridge()
        # Mock the vault manager
        self.mock_manager = MagicMock()
        self.mock_record = MagicMock()
        self.mock_record.record_id = "cr-test12345678"
        self.mock_manager.append_semantic.return_value = self.mock_record
        self.mock_manager.append_trust.return_value = self.mock_record
        self.mock_manager.append_procedural.return_value = self.mock_record
        self.mock_manager.append_episodic.return_value = self.mock_record
        self.mock_manager.append_task.return_value = self.mock_record
        self.mock_manager.append_meta.return_value = self.mock_record
        self.bridge._manager = self.mock_manager

    def test_semantic_write_accepted(self):
        """Code tagged record should write to PROCEDURAL channel."""
        record = CompiledRecordStub(topic_tags=["code"])
        result = self.bridge.bridge_compiled(record)
        assert result.accepted is True
        assert result.source_kind == "code"
        assert result.target_channel == 4  # PROCEDURAL
        assert result.record_id == "cr-test12345678"

    def test_rules_write_goes_to_trust(self):
        record = CompiledRecordStub(topic_tags=["rules"])
        result = self.bridge.bridge_compiled(record)
        assert result.accepted is True
        assert result.target_channel == 5  # TRUST

    def test_vault_rejection_returns_not_accepted(self):
        """If vault write returns None (trust gate), bridge should report rejection."""
        self.mock_manager.append_semantic.return_value = None
        record = CompiledRecordStub(topic_tags=["memory"])
        result = self.bridge.bridge_compiled(record)
        assert result.accepted is False
        assert "trust_gate" in result.reason

    def test_exception_returns_error_result(self):
        """Vault exception should not crash the bridge."""
        self.mock_manager.append_semantic.side_effect = RuntimeError("vault down")
        record = CompiledRecordStub(topic_tags=["memory"])
        result = self.bridge.bridge_compiled(record)
        assert result.accepted is False
        assert "exception" in result.reason

    def test_stats_tracked(self):
        record = CompiledRecordStub(topic_tags=["code"])
        self.bridge.bridge_compiled(record)
        stats = self.bridge.get_stats()
        assert stats["bridged"] == 1
        assert stats["rejected"] == 0
        assert stats["errors"] == 0


class TestBridgeBatch:
    """Test DoppelGroundBridge.bridge_batch()."""

    def setup_method(self):
        self.bridge = DoppelGroundBridge()
        self.mock_manager = MagicMock()
        self.mock_record = MagicMock()
        self.mock_record.record_id = "cr-batch1234567"
        self.mock_manager.append_semantic.return_value = self.mock_record
        self.mock_manager.append_trust.return_value = self.mock_record
        self.mock_manager.append_procedural.return_value = self.mock_record
        self.mock_manager.append_episodic.return_value = self.mock_record
        self.mock_manager.append_task.return_value = self.mock_record
        self.mock_manager.append_meta.return_value = self.mock_record
        self.bridge._manager = self.mock_manager

    def test_batch_processes_multiple_records(self):
        records = [
            CompiledRecordStub(topic_tags=["code"]),
            CompiledRecordStub(topic_tags=["rules"]),
            CompiledRecordStub(topic_tags=["memory"]),
        ]
        results = self.bridge.bridge_batch(records)
        assert len(results) == 3
        assert all(r.accepted for r in results)

    def test_empty_batch_returns_empty(self):
        results = self.bridge.bridge_batch([])
        assert results == []


class TestBridgeDossiers:
    """Test DoppelGroundBridge.bridge_dossiers()."""

    def setup_method(self):
        self.bridge = DoppelGroundBridge()
        self.mock_manager = MagicMock()
        self.mock_record = MagicMock()
        self.mock_record.record_id = "cr-dossier12345"
        self.mock_manager.append_semantic.return_value = self.mock_record
        self.bridge._manager = self.mock_manager

    def test_dossier_always_goes_to_semantic_channel_3(self):
        dossier = DossierStub(topic="memory")
        results = self.bridge.bridge_dossiers([dossier])
        assert len(results) == 1
        assert results[0].accepted is True
        assert results[0].target_channel == 3  # SEMANTIC
        assert results[0].source_kind == "dossier"

    def test_dossier_vault_rejection(self):
        self.mock_manager.append_semantic.return_value = None
        dossier = DossierStub()
        results = self.bridge.bridge_dossiers([dossier])
        assert results[0].accepted is False
        assert "trust_gate" in results[0].reason


class TestGetStatsAndReset:
    """Test bridge stats tracking."""

    def test_initial_stats(self):
        bridge = DoppelGroundBridge()
        stats = bridge.get_stats()
        assert stats == {"bridged": 0, "rejected": 0, "errors": 0}

    def test_reset_stats(self):
        bridge = DoppelGroundBridge()
        bridge._stats["bridged"] = 10
        bridge.reset_stats()
        assert bridge.get_stats() == {"bridged": 0, "rejected": 0, "errors": 0}


class TestGetBridgeSingleton:
    """Test the singleton accessor."""

    def test_get_bridge_returns_instance(self):
        # Reset singleton
        import nexus_os.archivist.doppelground_bridge as mod
        mod._bridge = None
        bridge = get_bridge()
        assert isinstance(bridge, DoppelGroundBridge)

    def test_get_bridge_returns_same_instance(self):
        import nexus_os.archivist.doppelground_bridge as mod
        mod._bridge = None
        b1 = get_bridge()
        b2 = get_bridge()
        assert b1 is b2
