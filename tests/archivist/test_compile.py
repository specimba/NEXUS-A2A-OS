"""tests/archivist/test_compile.py — ARCHIVIST Compile Stage Tests

Validates:
- Semantic topic tagging (8 TOPIC_KEYWORDS)
- Citation linking (arXiv ID extraction from filenames)
- Word count estimation (text files, binary skip, error handling)
- Quality assessment scoring (0-1 range, thresholds)
- Wiki admission gate (quality, word count, quarantine checks)
- Admission refinement (dossier, source_card, template, social, default)
- Retroactive dossier promotion (first-2-records bug fix)
- Batch compilation
- Statistics reporting (with and without compiled arg)
- Compile error handling (partial records on failure)
"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from nexus_os.archivist.import_stage import ImportRecord, FileType, AdmissionClass
from nexus_os.archivist.compile import ArchivistCompiler, CompiledRecord, TOPIC_KEYWORDS


def make_record(title="test paper", file_path="test.pdf", file_type=FileType.PAPER,
                admission_class=AdmissionClass.WEB_REFERENCE, priority=80,
                arxiv_id=None, source_dir="Downloads") -> ImportRecord:
    return ImportRecord(
        file_path=file_path,
        file_type=file_type,
        admission_class=admission_class,
        priority=priority,
        blake3_hash="abc123",
        file_size=1000,
        mtime=1700000000.0,
        source_dir=source_dir,
        title=title,
        arxiv_id=arxiv_id,
    )


class TestTopicTagging:
    def test_trust_keywords(self):
        compiler = ArchivistCompiler()
        r = make_record(title="Bayesian trust reputation system")
        tags = compiler.tag_topics(r)
        assert "trust" in tags

    def test_memory_keywords(self):
        compiler = ArchivistCompiler()
        r = make_record(title="Episodic memory consolidation RAG")
        tags = compiler.tag_topics(r)
        assert "memory" in tags

    def test_security_keywords(self):
        compiler = ArchivistCompiler()
        r = make_record(title="Prompt injection jailbreak attack")
        tags = compiler.tag_topics(r)
        assert "security" in tags

    def test_benchmark_keywords(self):
        compiler = ArchivistCompiler()
        r = make_record(title="Benchmark evaluation MMLU GPQA")
        tags = compiler.tag_topics(r)
        assert "benchmark" in tags

    def test_model_keywords(self):
        compiler = ArchivistCompiler()
        r = make_record(title="LLM transformer model quantization")
        tags = compiler.tag_topics(r)
        assert "model" in tags

    def test_governance_keywords(self):
        compiler = ArchivistCompiler()
        r = make_record(title="Governance policy compliance audit")
        tags = compiler.tag_topics(r)
        assert "governance" in tags

    def test_multimodal_keywords(self):
        compiler = ArchivistCompiler()
        r = make_record(title="Multimodal vision VLM audio")
        tags = compiler.tag_topics(r)
        assert "multimodal" in tags

    def test_agent_keywords(self):
        compiler = ArchivistCompiler()
        r = make_record(title="Autonomous agent multi-agent orchestration")
        tags = compiler.tag_topics(r)
        assert "agent" in tags

    def test_multiple_tags(self):
        compiler = ArchivistCompiler()
        r = make_record(title="Trust-based memory governance for LLM agents")
        tags = compiler.tag_topics(r)
        assert "trust" in tags
        assert "memory" in tags
        assert "governance" in tags
        assert "agent" in tags

    def test_no_matching_tags(self):
        compiler = ArchivistCompiler()
        r = make_record(title="Unrelated topic about cooking recipes")
        tags = compiler.tag_topics(r)
        assert tags == []

    def test_tag_from_filename(self):
        compiler = ArchivistCompiler()
        r = make_record(title="", file_path="security_audit_report.pdf")
        tags = compiler.tag_topics(r)
        assert "security" in tags

    def test_tag_from_file_type_value(self):
        compiler = ArchivistCompiler()
        r = make_record(title="random topic", file_type=FileType.BENCHMARK)
        tags = compiler.tag_topics(r)
        assert "benchmark" in tags

    def test_case_insensitive_tagging(self):
        compiler = ArchivistCompiler()
        r = make_record(title="SECURITY THREAT Attack vulnerability")
        tags = compiler.tag_topics(r)
        assert "security" in tags

    def test_all_fourteen_topics_in_keywords(self):
        assert len(TOPIC_KEYWORDS) == 14
        expected = {"trust", "memory", "security", "benchmark", "model",
                     "governance", "multimodal", "agent", "code", "spec",
                     "rules", "role", "dataset", "rejection"}
        assert set(TOPIC_KEYWORDS.keys()) == expected


class TestCitationLinking:
    def test_arxiv_id_in_record(self):
        compiler = ArchivistCompiler()
        r = make_record(arxiv_id="2403.13031")
        links = compiler.link_citations(r)
        assert "2403.13031" in links

    def test_arxiv_id_in_filename(self):
        compiler = ArchivistCompiler()
        r = make_record(file_path="paper_2511.20857_revisited.pdf", arxiv_id="2403.13031")
        links = compiler.link_citations(r)
        assert "2403.13031" in links
        assert "2511.20857" in links

    def test_no_citations(self):
        compiler = ArchivistCompiler()
        r = make_record(file_path="basic_report.pdf")
        links = compiler.link_citations(r)
        assert links == []

    def test_duplicate_arxiv_id_excluded(self):
        compiler = ArchivistCompiler()
        r = make_record(file_path="2403.13031_summary.pdf", arxiv_id="2403.13031")
        links = compiler.link_citations(r)
        assert links.count("2403.13031") == 1


class TestWordCountEstimation:
    def test_text_file_word_count(self, tmp_path):
        compiler = ArchivistCompiler()
        f = tmp_path / "doc.md"
        f.write_text("# Title\n" + "word " * 500, encoding="utf-8")
        r = make_record(file_path=str(f), file_type=FileType.MARKDOWN)
        wc = compiler.estimate_word_count(r)
        assert wc is not None
        assert wc >= 500

    def test_binary_file_returns_none(self):
        compiler = ArchivistCompiler()
        r = make_record(file_type=FileType.IMAGE)
        wc = compiler.estimate_word_count(r)
        assert wc is None

    def test_nonexistent_file_returns_none(self, tmp_path):
        compiler = ArchivistCompiler()
        r = make_record(file_path=str(tmp_path / "nonexistent.txt"), file_type=FileType.LOG)
        wc = compiler.estimate_word_count(r)
        assert wc is None

    def test_data_file_returns_none(self):
        compiler = ArchivistCompiler()
        r = make_record(file_type=FileType.DATA)
        wc = compiler.estimate_word_count(r)
        assert wc is None

    def test_code_file_returns_none(self):
        compiler = ArchivistCompiler()
        r = make_record(file_type=FileType.CODE)
        wc = compiler.estimate_word_count(r)
        assert wc is None

    def test_image_file_returns_none(self):
        compiler = ArchivistCompiler()
        r = make_record(file_type=FileType.IMAGE)
        wc = compiler.estimate_word_count(r)
        assert wc is None

    def test_prompt_file_returns_count(self, tmp_path):
        compiler = ArchivistCompiler()
        f = tmp_path / "prompt.txt"
        f.write_text("word " * 100, encoding="utf-8")
        r = make_record(file_path=str(f), file_type=FileType.PROMPT)
        wc = compiler.estimate_word_count(r)
        assert wc is not None
        assert wc >= 100


class TestQualityAssessment:
    def test_perfect_quality(self):
        compiler = ArchivistCompiler()
        r = make_record(file_type=FileType.PAPER, arxiv_id="2403.13031",
                        admission_class=AdmissionClass.SOURCE_CARD)
        q = compiler.assess_quality(r, word_count=3000)
        assert q >= 0.9

    def test_minimal_quality(self):
        compiler = ArchivistCompiler()
        r = make_record(file_type=FileType.UNKNOWN, priority=10)
        q = compiler.assess_quality(r, word_count=None)
        assert q < 0.3

    def test_quality_bounded_0_to_1(self):
        compiler = ArchivistCompiler()
        for wc in [None, 0, 100, 500, 2000, 50000]:
            for ft in FileType:
                r = make_record(file_type=ft, priority=120, arxiv_id="2403.13031")
                q = compiler.assess_quality(r, word_count=wc)
                assert 0.0 <= q <= 1.0, f"Quality out of range for {ft} wc={wc}: {q}"

    def test_markdown_gets_structure_boost(self):
        compiler = ArchivistCompiler()
        r_md = make_record(file_type=FileType.MARKDOWN)
        r_log = make_record(file_type=FileType.LOG)
        q_md = compiler.assess_quality(r_md, word_count=500)
        q_log = compiler.assess_quality(r_log, word_count=500)
        assert q_md > q_log

    def test_word_count_2000_higher_than_500(self):
        compiler = ArchivistCompiler()
        r = make_record(file_type=FileType.PAPER)
        q_low = compiler.assess_quality(r, word_count=500)
        q_high = compiler.assess_quality(r, word_count=2000)
        assert q_high > q_low

    def test_arxiv_id_boosts_quality(self):
        compiler = ArchivistCompiler()
        r_no = make_record(arxiv_id=None, file_type=FileType.PAPER)
        r_yes = make_record(arxiv_id="2403.13031", file_type=FileType.PAPER)
        q_no = compiler.assess_quality(r_no, word_count=500)
        q_yes = compiler.assess_quality(r_yes, word_count=500)
        assert q_yes > q_no


class TestWikiAdmission:
    def test_admissible_record(self):
        compiler = ArchivistCompiler()
        r = make_record(file_type=FileType.PAPER, arxiv_id="2403.13031")
        q = compiler.assess_quality(r, word_count=2000)
        assert compiler.check_wiki_admission(r, 2000, q) is True

    def test_low_quality_rejected(self):
        compiler = ArchivistCompiler()
        r = make_record(file_type=FileType.UNKNOWN, priority=10)
        assert compiler.check_wiki_admission(r, None, 0.1) is False

    def test_too_short_rejected(self):
        compiler = ArchivistCompiler()
        r = make_record(file_type=FileType.PAPER)
        assert compiler.check_wiki_admission(r, 100, 0.8) is False

    def test_quarantined_rejected(self):
        compiler = ArchivistCompiler()
        r = make_record(admission_class=AdmissionClass.QUARANTINE)
        assert compiler.check_wiki_admission(r, 2000, 0.9) is False

    def test_none_word_count_passes_if_quality_ok(self):
        compiler = ArchivistCompiler()
        r = make_record(file_type=FileType.PAPER, arxiv_id="2403.13031")
        assert compiler.check_wiki_admission(r, None, 0.6) is True

    def test_quality_exactly_at_threshold(self):
        compiler = ArchivistCompiler()
        r = make_record(file_type=FileType.PAPER, admission_class=AdmissionClass.WEB_REFERENCE)
        assert compiler.check_wiki_admission(r, 500, 0.5) is True
        assert compiler.check_wiki_admission(r, 500, 0.49) is False


class TestAdmissionRefinement:
    def test_dossier_promotion(self):
        compiler = ArchivistCompiler()
        r1 = make_record(title="trust scoring")
        r2 = make_record(title="trust framework")
        compiler._dossier_candidates["trust"] = [
            CompiledRecord(import_record=r1, topic_tags=["trust"]),
            CompiledRecord(import_record=r2, topic_tags=["trust"]),
        ]
        r3 = make_record(title="trust evaluation")
        result = compiler.refine_admission(r3, ["trust"])
        assert result == AdmissionClass.DOSSIER

    def test_source_card_for_arxiv(self):
        compiler = ArchivistCompiler()
        r = make_record(arxiv_id="2403.13031", priority=80)
        result = compiler.refine_admission(r, [])
        assert result == AdmissionClass.SOURCE_CARD

    def test_template_fragment_for_prompt(self):
        compiler = ArchivistCompiler()
        r = make_record(title="Prompt strategy guide")
        result = compiler.refine_admission(r, [])
        assert result == AdmissionClass.TEMPLATE_FRAGMENT

    def test_social_reference_for_forum(self):
        compiler = ArchivistCompiler()
        r = make_record(source_dir="community_forum")
        result = compiler.refine_admission(r, [])
        assert result == AdmissionClass.SOCIAL_REFERENCE

    def test_default_keeps_original(self):
        compiler = ArchivistCompiler()
        r = make_record(admission_class=AdmissionClass.WEB_REFERENCE)
        result = compiler.refine_admission(r, [])
        assert result == AdmissionClass.WEB_REFERENCE

    def test_low_priority_arxiv_not_source_card(self):
        compiler = ArchivistCompiler()
        r = make_record(arxiv_id="2403.13031", priority=30)
        result = compiler.refine_admission(r, [])
        assert result != AdmissionClass.SOURCE_CARD


class TestRetroactiveDossierPromotion:
    def test_early_records_promoted_when_topic_qualifies(self):
        compiler = ArchivistCompiler()
        records = []
        for i in range(5):
            r = make_record(title=f"trust paper {i}")
            records.append(r)
        compiled = compiler.compile_batch(records)
        trust_records = [c for c in compiled if "trust" in c.topic_tags]
        assert len(trust_records) >= 3
        for r in trust_records:
            assert r.admission_class == AdmissionClass.DOSSIER, \
                f"Record {r.import_record.title} not promoted to DOSSIER"

    def test_no_promotion_when_topic_too_small(self):
        compiler = ArchivistCompiler()
        records = [make_record(title="solo trust paper")]
        compiled = compiler.compile_batch(records)
        for c in compiled:
            assert c.admission_class != AdmissionClass.DOSSIER

    def test_promotion_count_returned(self):
        compiler = ArchivistCompiler()
        records = [make_record(title=f"trust paper {i}") for i in range(4)]
        compiled = compiler.compile_batch(records)
        promoted = compiler._retroactively_promote_dossiers(compiled)
        assert promoted >= 0


class TestBatchCompilation:
    def test_compile_batch_populates_fields(self):
        compiler = ArchivistCompiler()
        records = [
            make_record(title="memory consolidation", file_path="mem.pdf", file_type=FileType.PAPER),
            make_record(title="trust scoring system", file_path="trust.pdf", file_type=FileType.PAPER),
        ]
        compiled = compiler.compile_batch(records)
        assert len(compiled) == 2
        for c in compiled:
            assert isinstance(c, CompiledRecord)
            assert c.import_record is not None
            assert isinstance(c.topic_tags, list)
            assert isinstance(c.quality_score, float)
            assert 0.0 <= c.quality_score <= 1.0

    def test_compile_batch_empty(self):
        compiler = ArchivistCompiler()
        compiled = compiler.compile_batch([])
        assert compiled == []

    def test_compile_error_partial_record(self):
        compiler = ArchivistCompiler()
        r = make_record(file_path="/nonexistent/path/that/will/fail/word_count.txt",
                        file_type=FileType.LOG)
        compiled = compiler.compile_record(r)
        assert isinstance(compiled, CompiledRecord)


class TestCompilerStats:
    def test_stats_with_compiled_arg(self):
        compiler = ArchivistCompiler()
        records = [make_record(title="trust"), make_record(title="memory")]
        compiled = compiler.compile_batch(records)
        stats = compiler.get_stats(compiled)
        assert "total" in stats
        assert stats["total"] == 2
        assert "wiki_admissible" in stats
        assert "dossier_topics" in stats

    def test_stats_without_compiled_arg(self):
        compiler = ArchivistCompiler()
        records = [make_record(title="trust")]
        compiler.compile_batch(records)
        stats = compiler.get_stats()
        assert "total" in stats
        assert stats["total"] >= 1

    def test_stats_empty(self):
        compiler = ArchivistCompiler()
        stats = compiler.get_stats()
        assert stats["total"] == 0
        assert stats["dossier_topics"] == 0

    def test_stats_includes_arxiv_count(self):
        compiler = ArchivistCompiler()
        records = [make_record(title="trust", arxiv_id="2403.13031")]
        compiled = compiler.compile_batch(records)
        stats = compiler.get_stats(compiled)
        assert stats["with_arxiv_id"] == 1


class TestDossierCandidates:
    def test_get_dossier_candidates_existing(self):
        compiler = ArchivistCompiler()
        records = [make_record(title="trust framework")]
        compiler.compile_batch(records)
        candidates = compiler.get_dossier_candidates("trust")
        assert len(candidates) >= 1

    def test_get_dossier_candidates_nonexistent(self):
        compiler = ArchivistCompiler()
        candidates = compiler.get_dossier_candidates("nonexistent_topic")
        assert candidates == []

    def test_wiki_admissible_filter(self):
        compiler = ArchivistCompiler()
        records = [
            make_record(title="high quality trust", file_type=FileType.PAPER,
                        arxiv_id="2403.13031"),
            make_record(title="low quality", file_type=FileType.UNKNOWN, priority=5,
                        admission_class=AdmissionClass.QUARANTINE),
        ]
        compiled = compiler.compile_batch(records)
        admissible = compiler.get_wiki_admissible(compiled)
        for c in admissible:
            assert c.is_wiki_admissible is True

    def test_arxiv_index_populated(self):
        compiler = ArchivistCompiler()
        r = make_record(title="trust paper", arxiv_id="2403.13031")
        compiler.compile_record(r)
        assert "2403.13031" in compiler._arxiv_index
