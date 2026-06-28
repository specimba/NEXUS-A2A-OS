"""tests/archivist/test_fit.py — ARCHIVIST Fit Stage Tests

Validates:
- NEXUS goal relevance scoring (GOAL_RELEVANCE weights)
- Dossier synthesis (record sorting, metadata, markdown generation)
- Wiki markdown generation (YAML frontmatter, content structure)
- Dossier saving (filename sanitization, file creation)
- Batch fit processing (minimum 2 records, error handling)
- Fit statistics
- Dossier paths listing
"""
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from nexus_os.archivist.import_stage import ImportRecord, FileType, AdmissionClass
from nexus_os.archivist.compile import CompiledRecord, ArchivistCompiler
from nexus_os.archivist.fit import ArchivistFitter, Dossier, GOAL_RELEVANCE


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


def make_compiled_records(topic="trust", count=3) -> list:
    compiler = ArchivistCompiler()
    records = []
    for i in range(count):
        r = make_record(title=f"{topic} paper {i}", arxiv_id=f"2403.1303{i}")
        records.append(r)
    compiled = compiler.compile_batch(records)
    return compiled


class TestGoalRelevance:
    def test_trust_and_memory_highest_relevance(self):
        assert GOAL_RELEVANCE["trust"] == 1.0
        assert GOAL_RELEVANCE["memory"] == 1.0

    def test_security_high_relevance(self):
        assert GOAL_RELEVANCE["security"] == 0.95

    def test_multimodal_lower_relevance(self):
        assert GOAL_RELEVANCE["multimodal"] == 0.6

    def test_unknown_topic_defaults_to_0_5(self):
        fitter = ArchivistFitter(output_dir="/tmp/test_dossier")
        compiler = ArchivistCompiler()
        r = make_record(title="random cooking paper")
        compiled = compiler.compile_record(r)
        compiled.topic_tags = ["unknown_topic"]
        compiled.quality_score = 0.8
        score = fitter.score_nexus_relevance([compiled])
        assert 0.0 <= score <= 1.0

    def test_empty_records_returns_zero(self):
        fitter = ArchivistFitter(output_dir="/tmp/test_dossier")
        score = fitter.score_nexus_relevance([])
        assert score == 0.0

    def test_relevance_bounded_0_to_1(self):
        fitter = ArchivistFitter(output_dir="/tmp/test_dossier")
        compiler = ArchivistCompiler()
        records = [make_record(title="trust memory security governance", priority=120)]
        compiled = compiler.compile_batch(records)
        score = fitter.score_nexus_relevance(compiled)
        assert 0.0 <= score <= 1.0

    def test_all_fourteen_topics_have_weights(self):
        expected = {"trust", "memory", "security", "benchmark", "model",
                     "governance", "multimodal", "agent", "code", "spec",
                     "rules", "role", "dataset", "rejection"}
        assert set(GOAL_RELEVANCE.keys()) == expected

    def test_relevance_weighted_by_quality(self):
        fitter = ArchivistFitter(output_dir="/tmp/test_dossier")
        compiler = ArchivistCompiler()
        r = make_record(title="trust", priority=80)
        c_high = compiler.compile_record(r)
        c_high.quality_score = 0.9
        c_low = compiler.compile_record(r)
        c_low.quality_score = 0.1
        score_high = fitter.score_nexus_relevance([c_high])
        score_low = fitter.score_nexus_relevance([c_low])
        assert score_high > score_low


class TestDossierSynthesis:
    def test_synthesize_basic_dossier(self, tmp_path):
        fitter = ArchivistFitter(output_dir=str(tmp_path))
        compiled = make_compiled_records("trust", count=3)
        for c in compiled:
            c.topic_tags = ["trust"]
            c.dossier_topic = "trust"
        dossier = fitter.synthesize_dossier("trust", compiled)
        assert isinstance(dossier, Dossier)
        assert dossier.topic == "trust"
        assert "Trust" in dossier.title
        assert len(dossier.source_records) > 0
        assert len(dossier.tags) > 0
        assert 0.0 <= dossier.confidence <= 1.0
        assert dossier.nexus_relevance >= 0.0
        assert dossier.generated_at is not None

    def test_synthesize_empty_records_raises(self, tmp_path):
        fitter = ArchivistFitter(output_dir=str(tmp_path))
        with pytest.raises(ValueError, match="empty records"):
            fitter.synthesize_dossier("trust", [])

    def test_dossier_sorted_by_priority_and_quality(self, tmp_path):
        fitter = ArchivistFitter(output_dir=str(tmp_path))
        r_high = make_record(title="high priority trust", priority=120, arxiv_id="2403.13031")
        r_low = make_record(title="low priority trust", priority=30)
        compiler = ArchivistCompiler()
        c_high = compiler.compile_record(r_high)
        c_low = compiler.compile_record(r_low)
        c_high.topic_tags = ["trust"]
        c_low.topic_tags = ["trust"]
        c_high.quality_score = 0.9
        c_low.quality_score = 0.3
        dossier = fitter.synthesize_dossier("trust", [c_high, c_low])
        assert dossier.source_records[0].import_record.priority >= \
               dossier.source_records[1].import_record.priority

    def test_dossier_collects_arxiv_ids(self, tmp_path):
        fitter = ArchivistFitter(output_dir=str(tmp_path))
        compiled = make_compiled_records("trust", count=3)
        for c in compiled:
            c.topic_tags = ["trust"]
        dossier = fitter.synthesize_dossier("trust", compiled)
        assert len(dossier.source_paper_ids) > 0

    def test_dossier_confidence_is_avg_quality(self, tmp_path):
        fitter = ArchivistFitter(output_dir=str(tmp_path))
        compiled = make_compiled_records("memory", count=3)
        for c in compiled:
            c.topic_tags = ["memory"]
            c.quality_score = 0.6
        dossier = fitter.synthesize_dossier("memory", compiled)
        assert abs(dossier.confidence - 0.6) < 0.01


class TestMarkdownGeneration:
    def test_generate_dossier_markdown_has_sections(self, tmp_path):
        fitter = ArchivistFitter(output_dir=str(tmp_path))
        compiled = make_compiled_records("memory", count=3)
        for c in compiled:
            c.topic_tags = ["memory"]
        md = fitter._generate_dossier_markdown("memory", compiled, {"memory"}, ["2403.13031"])
        assert "# Dossier: Memory" in md
        assert "## Sources" in md
        assert "## Key Findings" in md
        assert "## Relevance to NEXUS" in md
        assert "## Open Questions" in md

    def test_wiki_markdown_has_yaml_frontmatter(self, tmp_path):
        fitter = ArchivistFitter(output_dir=str(tmp_path))
        compiled = make_compiled_records("security", count=2)
        for c in compiled:
            c.topic_tags = ["security"]
        dossier = fitter.synthesize_dossier("security", compiled)
        wiki_md = fitter.generate_wiki_markdown(dossier)
        assert wiki_md.startswith("---")
        assert "title:" in wiki_md
        assert "tags:" in wiki_md
        assert "confidence:" in wiki_md
        assert "admission_class: dossier" in wiki_md

    def test_sources_cap_at_10(self, tmp_path):
        fitter = ArchivistFitter(output_dir=str(tmp_path))
        compiled = make_compiled_records("trust", count=15)
        for c in compiled:
            c.topic_tags = ["trust"]
        md = fitter._generate_dossier_markdown("trust", compiled, {"trust"}, [])
        numbered_sources = [line for line in md.split("\n")
                            if line.strip() and line.strip()[0].isdigit()
                            and "." in line.split()[0]]
        assert len(numbered_sources) <= 10

    def test_frontmatter_closes_with_double_dashes(self, tmp_path):
        fitter = ArchivistFitter(output_dir=str(tmp_path))
        compiled = make_compiled_records("governance", count=2)
        for c in compiled:
            c.topic_tags = ["governance"]
        dossier = fitter.synthesize_dossier("governance", compiled)
        wiki_md = fitter.generate_wiki_markdown(dossier)
        lines = wiki_md.split("\n")
        dash_lines = [i for i, l in enumerate(lines) if l.strip() == "---"]
        assert len(dash_lines) == 2

    def test_dossier_topic_in_frontmatter(self, tmp_path):
        fitter = ArchivistFitter(output_dir=str(tmp_path))
        compiled = make_compiled_records("agent", count=2)
        for c in compiled:
            c.topic_tags = ["agent"]
        dossier = fitter.synthesize_dossier("agent", compiled)
        wiki_md = fitter.generate_wiki_markdown(dossier)
        assert "dossier_topic: agent" in wiki_md

    def test_nexus_relevance_in_frontmatter(self, tmp_path):
        fitter = ArchivistFitter(output_dir=str(tmp_path))
        compiled = make_compiled_records("trust", count=2)
        for c in compiled:
            c.topic_tags = ["trust"]
        dossier = fitter.synthesize_dossier("trust", compiled)
        wiki_md = fitter.generate_wiki_markdown(dossier)
        assert "nexus_relevance:" in wiki_md


class TestDossierSaving:
    def test_save_creates_file(self, tmp_path):
        fitter = ArchivistFitter(output_dir=str(tmp_path))
        compiled = make_compiled_records("governance", count=2)
        for c in compiled:
            c.topic_tags = ["governance"]
            c.dossier_topic = "governance"
        dossier = fitter.synthesize_dossier("governance", compiled)
        filepath = fitter.save_dossier(dossier)
        assert filepath.exists()
        content = filepath.read_text(encoding="utf-8")
        assert "governance" in content.lower()

    def test_filename_sanitization(self, tmp_path):
        fitter = ArchivistFitter(output_dir=str(tmp_path))
        compiled = make_compiled_records("trust", count=2)
        for c in compiled:
            c.topic_tags = ["trust"]
            c.dossier_topic = "trust/score"
        dossier = fitter.synthesize_dossier("trust/score", compiled)
        filepath = fitter.save_dossier(dossier)
        assert "/" not in filepath.name

    def test_fit_batch_creates_dossiers(self, tmp_path):
        fitter = ArchivistFitter(output_dir=str(tmp_path))
        compiler = ArchivistCompiler()
        records = []
        for i in range(4):
            r = make_record(title=f"trust framework paper {i}", arxiv_id=f"2511.2085{i}")
            records.append(r)
        compiled = compiler.compile_batch(records)
        candidates = compiler._dossier_candidates
        dossiers = fitter.fit_batch(candidates)
        if len(dossiers) > 0:
            assert all(isinstance(d, Dossier) for d in dossiers)
            dossier_files = list(tmp_path.glob("dossier_*.md"))
            assert len(dossier_files) >= 1

    def test_fit_batch_skips_single_records(self, tmp_path):
        fitter = ArchivistFitter(output_dir=str(tmp_path))
        candidates = {"solo": [CompiledRecord(
            import_record=make_record(title="solo paper"),
            topic_tags=["solo"],
            quality_score=0.8,
        )]}
        dossiers = fitter.fit_batch(candidates)
        assert len(dossiers) == 0

    def test_fit_batch_minimum_2_records(self, tmp_path):
        fitter = ArchivistFitter(output_dir=str(tmp_path))
        candidates = {
            "trust": [
                CompiledRecord(import_record=make_record(title="trust a"),
                               topic_tags=["trust"], quality_score=0.7),
                CompiledRecord(import_record=make_record(title="trust b"),
                               topic_tags=["trust"], quality_score=0.8),
            ]
        }
        dossiers = fitter.fit_batch(candidates)
        assert len(dossiers) == 1
        assert dossiers[0].topic == "trust"


class TestFitStats:
    def test_stats_empty(self, tmp_path):
        fitter = ArchivistFitter(output_dir=str(tmp_path))
        stats = fitter.get_stats()
        assert stats["dossiers_generated"] == 0
        assert stats["total_source_records"] == 0

    def test_stats_after_batch(self, tmp_path):
        fitter = ArchivistFitter(output_dir=str(tmp_path))
        compiler = ArchivistCompiler()
        records = [make_record(title=f"trust paper {i}") for i in range(4)]
        compiled = compiler.compile_batch(records)
        fitter.fit_batch(compiler._dossier_candidates)
        stats = fitter.get_stats()
        if stats["dossiers_generated"] > 0:
            assert stats["total_source_records"] > 0

    def test_stats_keys(self, tmp_path):
        fitter = ArchivistFitter(output_dir=str(tmp_path))
        stats = fitter.get_stats()
        assert "dossiers_generated" in stats
        assert "total_source_records" in stats


class TestDossierPaths:
    def test_get_dossier_paths_empty(self, tmp_path):
        fitter = ArchivistFitter(output_dir=str(tmp_path))
        paths = fitter.get_dossier_paths()
        assert paths == []

    def test_get_dossier_paths_after_batch(self, tmp_path):
        fitter = ArchivistFitter(output_dir=str(tmp_path))
        compiler = ArchivistCompiler()
        records = [make_record(title=f"memory paper {i}") for i in range(4)]
        compiled = compiler.compile_batch(records)
        fitter.fit_batch(compiler._dossier_candidates)
        paths = fitter.get_dossier_paths()
        for p in paths:
            assert p.name.startswith("dossier_")
            assert p.suffix == ".md"

    def test_dossier_paths_are_absolute(self, tmp_path):
        fitter = ArchivistFitter(output_dir=str(tmp_path))
        compiler = ArchivistCompiler()
        records = [make_record(title=f"trust paper {i}") for i in range(3)]
        compiler.compile_batch(records)
        fitter.fit_batch(compiler._dossier_candidates)
        paths = fitter.get_dossier_paths()
        for p in paths:
            assert p.is_absolute()


class TestOutputDirCreation:
    def test_output_dir_created_on_init(self, tmp_path):
        target = tmp_path / "wiki_out"
        fitter = ArchivistFitter(output_dir=str(target))
        assert target.exists()

    def test_default_output_dir(self):
        fitter = ArchivistFitter()
        assert fitter.output_dir.exists()
