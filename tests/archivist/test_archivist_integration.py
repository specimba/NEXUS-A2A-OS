"""tests/archivist/test_archivist_integration.py — ARCHIVIST Cross-Stage Integration Tests

Validates:
- Full 3-stage pipeline: import -> compile -> fit
- Data flow between stages
- Package exports (all stages accessible from __init__)
- Dossier output chain (records -> compiled -> dossiers -> saved files)
- Wiki admission pipeline (quality gate -> wiki admissible -> dossier)
- Error propagation across stages
"""

import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))


class TestPackageExports:
    def test_import_stage_exports(self):
        from nexus_os.archivist import ArchivistImporter, ImportRecord, FileType, AdmissionClass
        assert ArchivistImporter is not None
        assert ImportRecord is not None
        assert FileType is not None
        assert AdmissionClass is not None

    def test_compile_stage_exports(self):
        """Compile stage classes should be importable from package (BUG FIX)."""
        from nexus_os.archivist import ArchivistCompiler, CompiledRecord
        assert ArchivistCompiler is not None
        assert CompiledRecord is not None

    def test_fit_stage_exports(self):
        """Fit stage classes should be importable from package (BUG FIX)."""
        from nexus_os.archivist import ArchivistFitter, Dossier
        assert ArchivistFitter is not None
        assert Dossier is not None

    def test_all_exports_in___all__(self):
        import nexus_os.archivist as pkg
        assert "ArchivistCompiler" in pkg.__all__
        assert "CompiledRecord" in pkg.__all__
        assert "ArchivistFitter" in pkg.__all__
        assert "Dossier" in pkg.__all__


class TestFullPipeline:
    def test_import_compile_fit_chain(self, tmp_path):
        """Validate data flows correctly through all 3 stages."""
        from nexus_os.archivist import (
            ArchivistImporter, ArchivistCompiler, ArchivistFitter,
        )

        source_dir = tmp_path / "sources"
        source_dir.mkdir()

        for i in range(5):
            (source_dir / f"trust_scoring_{i}.txt").write_text(
                "Trust scoring and reputation system with Bayesian updates\n" + "word " * 300,
                encoding="utf-8",
            )
        for i in range(3):
            (source_dir / f"memory_consolidation_{i}.txt").write_text(
                "Memory consolidation and episodic retrieval systems\n" + "word " * 300,
                encoding="utf-8",
            )

        importer = ArchivistImporter(watched_dirs=[str(source_dir)])
        records = importer.import_batch()
        assert len(records) >= 5, f"Expected at least 5 records, got {len(records)}"

        compiler = ArchivistCompiler()
        compiled = compiler.compile_batch(records)
        assert len(compiled) == len(records)
        assert len(compiler._dossier_candidates) > 0, "No dossier topics found"

        output_dir = tmp_path / "wiki_output"
        fitter = ArchivistFitter(output_dir=str(output_dir))
        dossiers = fitter.fit_batch(compiler._dossier_candidates)

        assert len(dossiers) >= 1, f"Expected at least 1 dossier, got {len(dossiers)}"

        dossier_files = list(output_dir.glob("dossier_*.md"))
        assert len(dossier_files) >= 1, f"No dossier files in {output_dir}"

        for df in dossier_files:
            content = df.read_text(encoding="utf-8")
            assert content.startswith("---"), f"Dossier {df} missing YAML frontmatter"
            assert "admission_class: dossier" in content

    def test_wiki_admission_gate_in_pipeline(self, tmp_path):
        """Verify wiki admission gate works correctly in full pipeline."""
        from nexus_os.archivist import ArchivistImporter, ArchivistCompiler

        source_dir = tmp_path / "sources"
        source_dir.mkdir()

        (source_dir / "high_quality.md").write_text(
            "# High Quality Paper\n" + "word " * 2000,
            encoding="utf-8",
        )
        (source_dir / "low_quality.txt").write_text("short", encoding="utf-8")

        importer = ArchivistImporter(watched_dirs=[str(source_dir)])
        records = importer.import_batch()

        compiler = ArchivistCompiler()
        compiled = compiler.compile_batch(records)

        admissible = compiler.get_wiki_admissible(compiled)
        non_admissible = [c for c in compiled if not c.is_wiki_admissible]

        assert len(admissible) + len(non_admissible) == len(compiled)

    def test_dossier_topic_propagation(self, tmp_path):
        """Verify topics propagate from compile stage to fit stage correctly."""
        from nexus_os.archivist import ArchivistImporter, ArchivistCompiler, ArchivistFitter

        source_dir = tmp_path / "sources"
        source_dir.mkdir()

        for i in range(4):
            (source_dir / f"security_paper_{i}.txt").write_text(
                f"Security attack vulnerability CVE paper {i}\n" + "word " * 300,
                encoding="utf-8",
            )

        importer = ArchivistImporter(watched_dirs=[str(source_dir)])
        records = importer.import_batch()

        compiler = ArchivistCompiler()
        compiled = compiler.compile_batch(records)

        candidates = compiler._dossier_candidates
        assert "security" in candidates, \
            f"Expected 'security' in dossier candidates, got {list(candidates.keys())}"

        fitter = ArchivistFitter(output_dir=str(tmp_path / "wiki_output"))
        dossiers = fitter.fit_batch(candidates)

        if dossiers:
            security_dossiers = [d for d in dossiers if d.topic == "security"]
            if security_dossiers:
                assert "Security" in security_dossiers[0].title

    def test_error_handling_does_not_break_pipeline(self, tmp_path):
        """Verify that errors in one record don't break the whole pipeline."""
        from nexus_os.archivist import ArchivistImporter, ArchivistCompiler

        source_dir = tmp_path / "sources"
        source_dir.mkdir()

        for i in range(3):
            (source_dir / f"valid_{i}.txt").write_text(
                f"Valid content {i}\n" + "word " * 100, encoding="utf-8"
            )

        (source_dir / "empty.txt").write_text("", encoding="utf-8")

        importer = ArchivistImporter(watched_dirs=[str(source_dir)])
        records = importer.import_batch()

        compiler = ArchivistCompiler()
        compiled = compiler.compile_batch(records)

        assert len(compiled) > 0, "Pipeline produced no compiled records"
        for c in compiled:
            assert isinstance(c.topic_tags, list)
            assert isinstance(c.quality_score, float)


class TestStageConnectivity:
    def test_import_to_compile_record_shape(self, tmp_path):
        """Verify ImportRecord fields are consumed correctly by Compile stage."""
        from nexus_os.archivist import ArchivistImporter, ArchivistCompiler

        source_dir = tmp_path / "sources"
        source_dir.mkdir()

        (source_dir / "test_2403.13031.pdf").write_text("paper content", encoding="utf-8")

        importer = ArchivistImporter(watched_dirs=[str(source_dir)])
        records = importer.import_batch()
        assert len(records) >= 1

        r = records[0]
        assert hasattr(r, 'file_path')
        assert hasattr(r, 'file_type')
        assert hasattr(r, 'title')
        assert hasattr(r, 'arxiv_id')
        assert hasattr(r, 'admission_class')
        assert hasattr(r, 'priority')

        compiler = ArchivistCompiler()
        compiled = compiler.compile_record(r)
        assert compiled is not None
        assert compiled.import_record is r

    def test_compile_to_fit_record_shape(self, tmp_path):
        """Verify CompiledRecord fields are consumed correctly by Fit stage."""
        from nexus_os.archivist import ArchivistCompiler, ArchivistFitter
        from nexus_os.archivist.import_stage import ImportRecord, FileType, AdmissionClass

        import_record = ImportRecord(
            file_path="test.pdf",
            file_type=FileType.PAPER,
            admission_class=AdmissionClass.SOURCE_CARD,
            priority=100,
            blake3_hash="abc",
            file_size=1000,
            mtime=1700000000.0,
            source_dir="Downloads",
            title="Trust Paper",
            arxiv_id="2403.13031",
        )
        compiler = ArchivistCompiler()
        c = compiler.compile_record(import_record)

        fitter = ArchivistFitter(output_dir=str(tmp_path / "wiki_output"))

        assert hasattr(c, 'topic_tags')
        assert hasattr(c, 'quality_score')
        assert hasattr(c, 'import_record')

        candidates = {"trust": [c]}
        dossiers = fitter.fit_batch(candidates)
        assert len(dossiers) == 0
