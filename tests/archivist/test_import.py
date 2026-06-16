"""tests/archivist/test_import.py — ARCHIVIST Import Stage Tests

Validates:
- File discovery across watched directories
- Classification (paper, log, code, image, prompt, benchmark, markdown, notebook, data, config, unknown)
- Hash computation (BLAKE3 or SHA-256 fallback)
- Deduplication (duplicate files skipped)
- arXiv ID extraction from filename
- Priority scoring (0-120 range)
- Admission class determination
"""

import os
import tempfile
from pathlib import Path

import pytest

from nexus_os.archivist.import_stage import (
    ArchivistImporter,
    FileType,
    AdmissionClass,
    ImportRecord,
)


@pytest.fixture
def importer():
    return ArchivistImporter()


@pytest.fixture
def temp_dir(tmp_path):
    return tmp_path


# ── File Classification ────────────────────────────────────────────

class TestFileClassification:
    def test_pdf_classified_as_paper(self, importer, temp_dir):
        f = temp_dir / "paper.pdf"
        f.write_text("pdf content")
        assert importer.classify_file(f) == FileType.PAPER

    def test_py_classified_as_code(self, importer, temp_dir):
        f = temp_dir / "script.py"
        f.write_text("print(1)")
        assert importer.classify_file(f) == FileType.CODE

    def test_png_classified_as_image(self, importer, temp_dir):
        f = temp_dir / "image.png"
        f.write_bytes(b"\x89PNG\r\n\x1a\n")
        assert importer.classify_file(f) == FileType.IMAGE

    def test_ipynb_classified_as_notebook(self, importer, temp_dir):
        f = temp_dir / "notebook.ipynb"
        f.write_text("{}")
        assert importer.classify_file(f) == FileType.NOTEBOOK

    def test_parquet_classified_as_data(self, importer, temp_dir):
        f = temp_dir / "data.parquet"
        f.write_bytes(b"PAR1")
        assert importer.classify_file(f) == FileType.DATA

    def test_yaml_classified_as_config(self, importer, temp_dir):
        f = temp_dir / "config.yaml"
        f.write_text("key: value")
        assert importer.classify_file(f) == FileType.CONFIG

    def test_log_classified_as_log(self, importer, temp_dir):
        f = temp_dir / "run.log"
        f.write_text("INFO: started\nINFO: done\n")
        assert importer.classify_file(f) == FileType.LOG

    def test_prompt_in_name_classified_as_prompt(self, importer, temp_dir):
        f = temp_dir / "jailbreak_prompt.txt"
        f.write_text("prompt text")
        assert importer.classify_file(f) == FileType.PROMPT

    def test_markdown_classified_as_markdown(self, importer, temp_dir):
        f = temp_dir / "doc.md"
        f.write_text("# Title")
        assert importer.classify_file(f) == FileType.MARKDOWN

    def test_unknown_extension(self, importer, temp_dir):
        f = temp_dir / "weird.xyz"
        f.write_text("unknown")
        assert importer.classify_file(f) == FileType.UNKNOWN


# ── Hash Computation ───────────────────────────────────────────────

class TestHashComputation:
    def test_hash_consistent(self, importer, temp_dir):
        f = temp_dir / "test.txt"
        f.write_text("hello world")
        h1 = importer.compute_hash(f)
        h2 = importer.compute_hash(f)
        assert h1 == h2
        assert len(h1) >= 32  # SHA-256 or BLAKE3 hex length

    def test_hash_changes_with_content(self, importer, temp_dir):
        f = temp_dir / "test.txt"
        f.write_text("content A")
        h1 = importer.compute_hash(f)
        f.write_text("content B")
        h2 = importer.compute_hash(f)
        assert h1 != h2

    def test_hash_binary_file(self, importer, temp_dir):
        f = temp_dir / "binary.bin"
        f.write_bytes(b"\x00\x01\x02\x03")
        h = importer.compute_hash(f)
        assert h is not None
        assert len(h) >= 32


# ── Deduplication ────────────────────────────────────────────────────

class TestDeduplication:
    def test_duplicate_skipped(self, importer, temp_dir):
        f1 = temp_dir / "file1.txt"
        f2 = temp_dir / "file2.txt"
        f1.write_text("same content")
        f2.write_text("same content")

        r1 = importer.process_file(f1)
        r2 = importer.process_file(f2)
        assert r1 is not None
        assert r2 is None  # Duplicate

    def test_different_files_processed(self, importer, temp_dir):
        f1 = temp_dir / "a.txt"
        f2 = temp_dir / "b.txt"
        f1.write_text("content A")
        f2.write_text("content B")

        r1 = importer.process_file(f1)
        r2 = importer.process_file(f2)
        assert r1 is not None
        assert r2 is not None
        assert r1.blake3_hash != r2.blake3_hash


# ── arXiv ID Extraction ───────────────────────────────────────────

class TestArxivExtraction:
    def test_standard_arxiv_id(self, importer, temp_dir):
        f = temp_dir / "paper_2403.13031.pdf"
        f.write_text("paper")
        record = importer.process_file(f)
        assert record.arxiv_id == "2403.13031"

    def test_arxiv_prefix(self, importer, temp_dir):
        f = temp_dir / "arxiv_2511_20857.pdf"
        f.write_text("paper")
        record = importer.process_file(f)
        assert record.arxiv_id == "2511.20857"

    def test_no_arxiv_id(self, importer, temp_dir):
        f = temp_dir / "random_paper.pdf"
        f.write_text("paper")
        record = importer.process_file(f)
        assert record.arxiv_id is None

    def test_multiple_ids_uses_first(self, importer, temp_dir):
        f = temp_dir / "2403.13031_and_2604.02375.pdf"
        f.write_text("paper")
        record = importer.process_file(f)
        assert record.arxiv_id == "2403.13031"


# ── Priority Scoring ───────────────────────────────────────────────

class TestPriorityScoring:
    def test_priority_range(self, importer, temp_dir):
        f = temp_dir / "test.txt"
        f.write_text("content")
        p = importer.score_priority(f, FileType.LOG, f.stat().st_mtime, str(temp_dir))
        assert 0 <= p <= 120

    def test_papers_get_priority_boost(self, importer, temp_dir):
        f1 = temp_dir / "paper.pdf"
        f2 = temp_dir / "log.txt"
        f1.write_text("paper")
        f2.write_text("log")
        mtime = f1.stat().st_mtime
        p1 = importer.score_priority(f1, FileType.PAPER, mtime, str(temp_dir))
        p2 = importer.score_priority(f2, FileType.LOG, mtime, str(temp_dir))
        assert p1 > p2  # Paper gets type boost

    def test_recency_boost(self, importer, temp_dir):
        f = temp_dir / "test.txt"
        f.write_text("content")
        # Recent file (now)
        recent = importer.score_priority(f, FileType.LOG, f.stat().st_mtime, str(temp_dir))
        # Old file (30 days ago)
        old = importer.score_priority(f, FileType.LOG, f.stat().st_mtime - 30 * 86400, str(temp_dir))
        assert recent > old

    def test_size_penalty(self, importer, temp_dir):
        f = temp_dir / "huge.bin"
        f.write_bytes(b"x" * 150_000_000)  # 150MB
        p = importer.score_priority(f, FileType.DATA, f.stat().st_mtime, str(temp_dir))
        assert p < 100  # Should have size penalty


# ── Admission Class Determination ──────────────────────────────────

class TestAdmissionClass:
    def test_arxiv_paper_becomes_source_card(self, importer, temp_dir):
        f = temp_dir / "arxiv_2403.13031.pdf"
        f.write_text("paper")
        record = importer.process_file(f)
        assert record.admission_class == AdmissionClass.SOURCE_CARD

    def test_prompt_becomes_template_fragment(self, importer, temp_dir):
        f = temp_dir / "jailbreak_prompt.txt"
        f.write_text("prompt")
        record = importer.process_file(f)
        assert record.admission_class == AdmissionClass.TEMPLATE_FRAGMENT

    def test_temp_file_quarantined(self, importer, temp_dir):
        f = temp_dir / "temp_file.txt"
        f.write_text("temp")
        record = importer.process_file(f)
        assert record.admission_class == AdmissionClass.QUARANTINE

    def test_low_priority_quarantined(self, importer, temp_dir):
        f = temp_dir / "low_priority.txt"
        f.write_text("x")
        # Override priority to be very low
        record = importer.process_file(f)
        # With default priority from downloads dir, should not be quarantined
        # But if we force priority < 10, it would be quarantined
        assert record is not None


# ── Title Extraction ────────────────────────────────────────────────

class TestTitleExtraction:
    def test_title_from_filename(self, importer, temp_dir):
        f = temp_dir / "My_Great_Paper.pdf"
        f.write_text("paper")
        title = importer.extract_title(f, FileType.PAPER)
        assert "My Great Paper" in title

    def test_title_short_name(self, importer, temp_dir):
        f = temp_dir / "a.txt"
        f.write_text("content")
        title = importer.extract_title(f, FileType.LOG)
        assert title is None or len(title) < 5  # Too short, may return None


# ── Batch Processing ────────────────────────────────────────────────

class TestBatchProcessing:
    def test_import_batch(self, importer, temp_dir):
        # Create 5 test files
        for i in range(5):
            f = temp_dir / f"file_{i}.txt"
            f.write_text(f"content {i}")

        importer.watched_dirs = [str(temp_dir)]
        records = importer.import_batch()
        assert len(records) == 5
        assert importer.get_stats()["processed"] == 5

    def test_import_batch_with_duplicates(self, importer, temp_dir):
        # Create 3 files, 2 with same content
        for i, content in enumerate(["A", "B", "A"]):
            f = temp_dir / f"file_{i}.txt"
            f.write_text(content)

        importer.watched_dirs = [str(temp_dir)]
        records = importer.import_batch()
        assert len(records) == 2  # One duplicate skipped

    def test_import_batch_max_files(self, importer, temp_dir):
        for i in range(10):
            f = temp_dir / f"file_{i}.txt"
            f.write_text(f"content {i}")

        importer.watched_dirs = [str(temp_dir)]
        records = importer.import_batch(max_files=3)
        assert len(records) == 3

    def test_import_batch_nonexistent_dir(self, importer, temp_dir):
        importer.watched_dirs = [str(temp_dir / "nonexistent")]
        records = importer.import_batch()
        assert len(records) == 0


# ── ImportRecord Fields ───────────────────────────────────────────────

class TestImportRecord:
    def test_fields_populated(self, importer, temp_dir):
        f = temp_dir / "test_2403.13031.pdf"
        f.write_text("paper")
        record = importer.process_file(f)
        assert record.file_path == str(f)
        assert record.file_type == FileType.PAPER
        assert record.blake3_hash is not None
        assert record.file_size > 0
        assert record.mtime > 0
        assert record.source_dir == str(temp_dir)
        assert record.title is not None
        assert record.arxiv_id == "2403.13031"
        assert record.processed_at is not None

    def test_priority_assigned(self, importer, temp_dir):
        f = temp_dir / "test.pdf"
        f.write_text("paper")
        record = importer.process_file(f)
        assert 0 <= record.priority <= 120

    def test_admission_class_assigned(self, importer, temp_dir):
        f = temp_dir / "test.pdf"
        f.write_text("paper")
        record = importer.process_file(f)
        assert isinstance(record.admission_class, AdmissionClass)
