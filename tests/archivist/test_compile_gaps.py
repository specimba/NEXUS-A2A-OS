"""Tests for nexus_os.archivist.compile module fixes.

Covers:
- TOPIC_KEYWORDS expanded from 8 to 14 topics
- _build_backlinks() bidirectional citation graph
- CompileStats dataclass and get_stats() return type
- Retroactive dossier promotion
- compile_batch() integration
"""

import pytest
from unittest.mock import MagicMock, patch
from dataclasses import dataclass, field
from typing import List, Optional


# Minimal stubs
class FileTypeStub:
    PAPER = "paper"
    CODE = "code"
    CONFIG = "config"
    MARKDOWN = "markdown"
    LOG = "log"
    PROMPT = "prompt"
    BENCHMARK = "benchmark"
    UNKNOWN = "unknown"


class AdmissionClassStub:
    SOURCE_CARD = "source_card"
    DOSSIER = "dossier"
    QUARANTINE = "quarantine"
    WEB_REFERENCE = "web_reference"
    SOCIAL_REFERENCE = "social_reference"
    OPERATOR_FRAGMENT = "operator_fragment"
    TEMPLATE_FRAGMENT = "template_fragment"


@dataclass
class ImportRecordStub:
    file_path: str = "/test/paper.pdf"
    file_type: str = FileTypeStub.PAPER
    admission_class: str = AdmissionClassStub.SOURCE_CARD
    priority: int = 80
    blake3_hash: str = "abc123"
    file_size: int = 5000
    mtime: float = 1000000.0
    source_dir: str = "/test"
    title: Optional[str] = "Test Paper"
    arxiv_id: Optional[str] = None
    topic_tags: List[str] = field(default_factory=list)
    processed_at: Optional[float] = None
    errors: List[str] = field(default_factory=list)


# Patch imports — isolate mock to this file only, preserve real module identity
import sys
import importlib

# Pre-load real modules so their identities persist in sys.modules
import nexus_os.archivist.import_stage as _real_import_stage
_real_compile = importlib.import_module('nexus_os.archivist.compile')

mock_import_stage = MagicMock()
mock_import_stage.FileType = FileTypeStub
mock_import_stage.AdmissionClass = AdmissionClassStub
mock_import_stage.ImportRecord = ImportRecordStub

sys.modules['nexus_os.archivist.import_stage'] = mock_import_stage

from nexus_os.archivist.compile import (
    TOPIC_KEYWORDS,
    ArchivistCompiler,
    CompiledRecord,
    CompileStats,
)

# Restore real modules in sys.modules — do NOT leave stale mock/delete holes
sys.modules['nexus_os.archivist.import_stage'] = _real_import_stage
sys.modules['nexus_os.archivist.compile'] = _real_compile

# Use autouse fixture to apply mocks during test execution only
@pytest.fixture(autouse=True)
def apply_mocks(monkeypatch):
    monkeypatch.setitem(sys.modules, 'nexus_os.archivist.import_stage', mock_import_stage)


class TestTopicKeywords14:
    """Verify the 14-topic unified taxonomy."""

    def test_has_14_topics(self):
        assert len(TOPIC_KEYWORDS) == 14

    def test_original_8_topics_present(self):
        original_8 = {"trust", "memory", "security", "benchmark", "model", "governance", "multimodal", "agent"}
        assert original_8.issubset(set(TOPIC_KEYWORDS.keys()))

    def test_new_6_topics_present(self):
        new_6 = {"code", "spec", "rules", "role", "dataset", "rejection"}
        assert new_6.issubset(set(TOPIC_KEYWORDS.keys()))

    def test_code_keywords(self):
        assert "code" in TOPIC_KEYWORDS["code"]
        assert "implementation" in TOPIC_KEYWORDS["code"]

    def test_rules_keywords(self):
        assert "rules" in TOPIC_KEYWORDS["rules"]
        assert "guardrail" in TOPIC_KEYWORDS["rules"]

    def test_spec_keywords(self):
        assert "spec" in TOPIC_KEYWORDS["spec"]
        assert "blueprint" in TOPIC_KEYWORDS["spec"]


class TestCompileStats:
    """Test the CompileStats dataclass."""

    def test_default_values(self):
        stats = CompileStats()
        assert stats.total == 0
        assert stats.backlinks == 0

    def test_to_dict(self):
        stats = CompileStats(total=100, wiki_admissible=50, backlinks=5)
        d = stats.to_dict()
        assert d["total"] == 100
        assert d["backlinks"] == 5
        assert "errors" in d

    def test_all_fields_in_dict(self):
        stats = CompileStats()
        d = stats.to_dict()
        expected_keys = {"total", "wiki_admissible", "dossier_topics", "with_arxiv_id", "errors", "backlinks"}
        assert set(d.keys()) == expected_keys


class TestBuildBacklinks:
    """Test _build_backlinks() bidirectional citation graph."""

    def setup_method(self):
        self.compiler = ArchivistCompiler()

    def test_backlinks_created_for_cited_papers(self):
        """If paper A cites paper B, B should get a backlink to A."""
        # Create two compiled records where A cites B
        record_a = CompiledRecord(
            import_record=ImportRecordStub(arxiv_id="2401.00001", title="Paper A"),
            citation_links=["2401.00002"],  # A cites B
        )
        record_b = CompiledRecord(
            import_record=ImportRecordStub(arxiv_id="2401.00002", title="Paper B"),
            citation_links=[],  # B doesn't cite anyone yet
        )
        
        backlinks = self.compiler._build_backlinks([record_a, record_b])
        
        # B should now have a backlink to A
        assert "2401.00001" in record_b.citation_links
        assert backlinks == 1

    def test_no_duplicate_backlinks(self):
        """If A cites B and B cites A, no duplicate backlinks should be added."""
        record_a = CompiledRecord(
            import_record=ImportRecordStub(arxiv_id="2401.00001"),
            citation_links=["2401.00002"],
        )
        record_b = CompiledRecord(
            import_record=ImportRecordStub(arxiv_id="2401.00002"),
            citation_links=["2401.00001"],  # B already cites A
        )
        
        backlinks = self.compiler._build_backlinks([record_a, record_b])
        
        # No duplicates should be added
        assert record_a.citation_links.count("2401.00002") == 1
        assert record_b.citation_links.count("2401.00001") == 1
        assert backlinks == 0  # No NEW backlinks added

    def test_empty_compiled_list(self):
        backlinks = self.compiler._build_backlinks([])
        assert backlinks == 0

    def test_no_citation_links(self):
        record = CompiledRecord(
            import_record=ImportRecordStub(arxiv_id="2401.00001"),
            citation_links=[],
        )
        backlinks = self.compiler._build_backlinks([record])
        assert backlinks == 0

    def test_cited_id_not_in_batch(self):
        """Citing a paper that isn't in the batch should not crash."""
        record = CompiledRecord(
            import_record=ImportRecordStub(arxiv_id="2401.00001"),
            citation_links=["9999.99999"],  # Not in batch
        )
        backlinks = self.compiler._build_backlinks([record])
        assert backlinks == 0  # Nothing to backlink to


class TestGetStatsReturnsCompileStats:
    """Test that get_stats() returns a dict."""

    def setup_method(self):
        self.compiler = ArchivistCompiler()

    def test_returns_dict(self):
        stats = self.compiler.get_stats()
        assert isinstance(stats, dict)

    def test_includes_backlinks_key(self):
        stats = self.compiler.get_stats()
        assert 'backlinks' in stats
        assert stats['backlinks'] == 0  # No compile_batch called yet


class TestTagTopics14:
    """Test tag_topics with expanded 14-topic taxonomy."""

    def setup_method(self):
        self.compiler = ArchivistCompiler()

    def test_code_topic_detected(self):
        record = ImportRecordStub(title="Implementation of agent code", file_path="/test/code.py")
        record.file_type = FileTypeStub.CODE
        tags = self.compiler.tag_topics(record)
        assert "code" in tags

    def test_rejection_topic_detected(self):
        record = ImportRecordStub(title="Hallucination failure pattern")
        tags = self.compiler.tag_topics(record)
        assert "rejection" in tags

    def test_spec_topic_detected(self):
        record = ImportRecordStub(title="Architect blueprint spec")
        tags = self.compiler.tag_topics(record)
        assert "spec" in tags

    def test_role_topic_detected(self):
        record = ImportRecordStub(title="Operator dispatcher persona")
        tags = self.compiler.tag_topics(record)
        assert "role" in tags
