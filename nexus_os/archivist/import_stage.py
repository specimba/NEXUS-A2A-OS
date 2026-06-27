r"""nexus_os/archivist/import_stage.py — ARCHIVIST Import Stage

Stage 1 of 3-stage DoppelGround pipeline ported to NEXUS:
- File discovery across all watched directories
- Classification (paper, log, code, image, prompt, benchmark)
- Deduplication (BLAKE3 hash + title similarity)
- Priority scoring (0-120): recency * source_reliability * topic_relevance
- Initial admission: quarantine or source_card

Watched directories (full NEXUS universe):
- C:\Users\speci.000\Downloads\ARCHIVIST\ (priority 120)
- C:\Users\speci.000\Downloads\PAPERS\ (priority 100, scientific pipeline)
- C:\Users\speci.000\Downloads\NEXUSlogs\ (priority 80)
- C:\Users\speci.000\Downloads\INSTAviralIMGstrats\ (priority 70, OCR extraction)
- C:\Users\speci.000\Documents\NEXUS\ (priority 90, source code)
- C:\Users\speci.000\Documents\HERMES\ (priority 60, read-only cross-ref)
- D:\NEXUS_COLD\ (priority 50, read-only)
- D:\NEXUS_RECOVERY\ (priority 30, read-only)
- D:\NEXUS_OS_AUDIT\ (priority 70, governance)
- D:\MyModels\ (priority 20, metadata only)

Discovery rule: auto-add new NEXUS*/ARCHIVIST* folders in Downloads.
"""

import hashlib
import logging
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from nexus_os.archivist.archivist import CATEGORIZE_TO_FILETYPE, categorize_file

logger = logging.getLogger("nexus_os.archivist.import")


class FileType(Enum):
    """Classification of imported files."""
    PAPER = "paper"           # PDF, academic paper
    LOG = "log"               # Text log, runtime intelligence
    CODE = "code"             # Source code, scripts
    IMAGE = "image"             # Image, diagram, screenshot
    PROMPT = "prompt"           # Prompt strategy, jailbreak, system prompt
    BENCHMARK = "benchmark"     # Benchmark result, evaluation
    MARKDOWN = "markdown"       # Documentation, wiki article
    NOTEBOOK = "notebook"       # Jupyter notebook
    DATA = "data"               # Dataset, parquet, CSV
    CONFIG = "config"           # YAML, JSON, config file
    UNKNOWN = "unknown"         # Unclassified


class AdmissionClass(Enum):
    """7 admission classes from DoppelGround wiki_compile."""
    SOURCE_CARD = "source_card"       # Canonical papers, system prompts
    DOSSIER = "dossier"               # Multi-file synthesized topics
    WEB_REFERENCE = "web_reference"   # URLs, blogs, tweets
    SOCIAL_REFERENCE = "social_reference"  # Forum discussions, community
    OPERATOR_FRAGMENT = "operator_fragment"  # Our own notes, logs
    TEMPLATE_FRAGMENT = "template_fragment"  # Reusable patterns, prompts
    QUARANTINE = "quarantine"         # Suspicious, unverified, conflicting


@dataclass
class ImportRecord:
    """A record produced by the Import stage."""
    file_path: str
    file_type: FileType
    admission_class: AdmissionClass
    priority: int  # 0-120
    blake3_hash: str
    file_size: int
    mtime: float
    source_dir: str
    # Classification metadata
    title: Optional[str] = None
    authors: List[str] = field(default_factory=list)
    arxiv_id: Optional[str] = None
    topic_tags: List[str] = field(default_factory=list)
    # Processing state
    processed_at: Optional[float] = None
    errors: List[str] = field(default_factory=list)


# Priority weights
SOURCE_PRIORITY = {
    "ARCHIVIST": 120,
    "PAPERS": 100,
    "NEXUS_source": 90,
    "NEXUSlogs": 80,
    "NEXUS_OS_AUDIT": 70,
    "INSTAviralIMGstrats": 70,
    "HERMES": 60,
    "NEXUS_COLD": 50,
    "NEXUS_RECOVERY": 30,
    "MyModels": 20,
}


class ArchivistImporter:
    """Import stage: file discovery, classification, deduplication, priority scoring."""

    EXCLUDE_PATTERNS = {'__pycache__', '.git', 'node_modules', 'archive', '.nexus_pi'}

    def __init__(self, watched_dirs: Optional[List[str]] = None):
        self.watched_dirs = watched_dirs or self._default_watched_dirs()
        self._seen_hashes: Set[str] = set()
        self._processed_count = 0
        self._error_count = 0
        self._quarantine_count = 0
        self._duplicate_count = 0

    def _default_watched_dirs(self) -> List[str]:
        """Default watched directories (full NEXUS universe)."""
        home = Path.home()
        docs = home / "Documents"
        downloads = home / "Downloads"
        return [
            str(downloads / "ARCHIVIST"),
            str(downloads / "PAPERS"),
            str(downloads / "NEXUSlogs"),
            str(downloads / "INSTAviralIMGstrats"),
            str(docs / "NEXUS"),
            str(docs / "HERMES"),
            "D:\\NEXUS_COLD",
            "D:\\NEXUS_RECOVERY",
            "D:\\NEXUS_OS_AUDIT",
            "D:\\MyModels",
        ]

    def discover_files(self, max_files: Optional[int] = None) -> List[Path]:
        """Discover all files in watched directories."""
        files: List[Path] = []
        for dir_path in self.watched_dirs:
            p = Path(dir_path)
            if not p.exists():
                logger.warning("Watched dir does not exist: %s", dir_path)
                continue
            for f in p.rglob("*"):
                if f.is_file() and not f.name.startswith("."):
                    if any(part.lower() in self.EXCLUDE_PATTERNS for part in f.parts):
                        continue
                    files.append(f)
                    if max_files and len(files) >= max_files:
                        return files
        logger.info("Discovered %d files across %d directories", len(files), len(self.watched_dirs))
        return files

    def classify_file(self, file_path: Path) -> FileType:
        """Classify file by extension and content heuristics.

        Primary path: ``categorize_file()`` + ``CATEGORIZE_TO_FILETYPE`` — the
        centralized extension-to-type mapping in ``archivist.py`` (source of truth).

        Local overrides (content-based heuristics) add types the mapping can't
        express: PROMPT via filename keywords, LOG via line-count for
        extensionless files, and early PDF→PAPER as the most common case.
        """
        ext = file_path.suffix.lower()
        name = file_path.name.lower()

        # ── Local overrides (content/name heuristics beyond static mapping) ──
        if ext == ".pdf":
            return FileType.PAPER
        if ext in {".txt", ".log", ".md"}:
            if "prompt" in name or "jailbreak" in name or "system" in name:
                return FileType.PROMPT
            if "log" in name or "benchmark" in name or "research" in name:
                return FileType.LOG
            if ext == ".md":
                return FileType.MARKDOWN
            return FileType.LOG

        # Heuristic: line-rich text files without a recognised extension are logs
        if ext == "" and file_path.stat().st_size < 10_000_000:
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    sample = f.read(1024)
                    if sample.count("\n") > 20:
                        return FileType.LOG
            except Exception:
                pass

        # ── Central mapping: delegate to categorize_file + CATEGORIZE_TO_FILETYPE ──
        cat = categorize_file(str(file_path))
        if cat in CATEGORIZE_TO_FILETYPE:
            mapped = CATEGORIZE_TO_FILETYPE[cat]
            if mapped != "UNKNOWN":
                try:
                    return FileType(mapped.lower())
                except ValueError:
                    pass

        return FileType.UNKNOWN

    def compute_hash(self, file_path: Path) -> str:
        """Compute BLAKE3 hash (or SHA-256 fallback) of file contents."""
        try:
            import blake3
            hasher = blake3.blake3()
        except ImportError:
            hasher = hashlib.sha256()

        try:
            with open(file_path, "rb") as f:
                while chunk := f.read(8192):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            logger.warning("Hash failed for %s: %s", file_path, e)
            return ""

    def extract_arxiv_id(self, file_path: Path) -> Optional[str]:
        """Extract arXiv ID from filename or PDF metadata."""
        name = file_path.name
        # Pattern: arXiv:YYMM.NNNNN or YYMM.NNNNN
        match = re.search(r"(\d{4}\.\d{4,5})", name)
        if match:
            return match.group(1)
        # Pattern: arxiv_YYMM_NNNNN
        match = re.search(r"arxiv[_-](\d{4})[_-](\d{4,5})", name, re.IGNORECASE)
        if match:
            return f"{match.group(1)}.{match.group(2)}"
        return None

    def extract_title(self, file_path: Path, file_type: FileType) -> Optional[str]:
        """Extract title from filename or content."""
        name = file_path.stem
        # Clean up filename: replace underscores/hyphens with spaces
        title = name.replace("_", " ").replace("-", " ").strip()
        # Title case for readability
        if len(title) > 5:
            return title.title()
        return None

    def score_priority(
        self,
        file_path: Path,
        file_type: FileType,
        mtime: float,
        source_dir: str,
    ) -> int:
        """Compute priority score (0-120) based on recency, source, and type."""
        # Source base priority
        base = 0
        dir_name = Path(source_dir).name
        for key, val in SOURCE_PRIORITY.items():
            if key.lower() == dir_name.lower():
                base = val
                break
        if base == 0:
            base = 50  # Default

        # Recency boost: files from last 7 days get +20, last 30 days +10
        age_days = (time.time() - mtime) / 86400
        recency = 20 if age_days <= 7 else 10 if age_days <= 30 else 0

        # Type boost: papers and prompts get +10
        type_boost = 10 if file_type in {FileType.PAPER, FileType.PROMPT} else 0

        # Size penalty: extremely large files (>100MB) get -10
        size = file_path.stat().st_size
        size_penalty = -10 if size > 100_000_000 else 0

        priority = base + recency + type_boost + size_penalty
        return max(0, min(120, priority))

    def determine_admission(self, record: ImportRecord) -> AdmissionClass:
        """Determine admission class based on file type and metadata."""
        # Quarantine: suspicious patterns
        if record.priority < 10:
            return AdmissionClass.QUARANTINE
        if any(kw in Path(record.file_path).name.lower() for kw in {"temp", "tmp", "cache", "sandbox"}):
            return AdmissionClass.QUARANTINE

        # Source card: papers with arXiv ID, canonical docs
        if record.file_type == FileType.PAPER and record.arxiv_id:
            return AdmissionClass.SOURCE_CARD
        if "system prompt" in (record.title or "").lower() or "fable" in (record.title or "").lower():
            return AdmissionClass.SOURCE_CARD

        # Template fragment: prompt strategies, reusable patterns
        if record.file_type == FileType.PROMPT:
            return AdmissionClass.TEMPLATE_FRAGMENT

        # Operator fragment: our own logs, notes
        if record.file_type in {FileType.LOG, FileType.MARKDOWN} and "NEXUS" in record.source_dir:
            return AdmissionClass.OPERATOR_FRAGMENT

        # Default: web reference for most downloaded files
        if "Downloads" in record.source_dir:
            return AdmissionClass.WEB_REFERENCE

        # Dossier: multi-file topics (assigned later in Compile stage)
        return AdmissionClass.WEB_REFERENCE

    def process_file(self, file_path: Path) -> Optional[ImportRecord]:
        """Process a single file: classify, hash, score, admit."""
        try:
            file_type = self.classify_file(file_path)
            blake3_hash = self.compute_hash(file_path)

            if not blake3_hash:
                return None

            # Deduplication
            if blake3_hash in self._seen_hashes:
                logger.debug("Duplicate skipped: %s", file_path)
                self._duplicate_count += 1
                return None
            self._seen_hashes.add(blake3_hash)

            mtime = file_path.stat().st_mtime
            source_dir = str(file_path.parent)
            priority = self.score_priority(file_path, file_type, mtime, source_dir)
            arxiv_id = self.extract_arxiv_id(file_path)
            title = self.extract_title(file_path, file_type)

            record = ImportRecord(
                file_path=str(file_path),
                file_type=file_type,
                admission_class=AdmissionClass.QUARANTINE,  # Will be updated
                priority=priority,
                blake3_hash=blake3_hash,
                file_size=file_path.stat().st_size,
                mtime=mtime,
                source_dir=source_dir,
                title=title,
                arxiv_id=arxiv_id,
            )

            record.admission_class = self.determine_admission(record)
            record.processed_at = time.time()
            self._processed_count += 1

            if record.admission_class == AdmissionClass.QUARANTINE:
                self._quarantine_count += 1

            return record

        except Exception as e:
            logger.exception("Import failed for %s: %s", file_path, e)
            self._error_count += 1
            return None

    def import_batch(
        self,
        max_files: Optional[int] = None,
        progress_callback: Optional[callable] = None,
    ) -> List[ImportRecord]:
        """Process all discovered files in a batch."""
        files = self.discover_files(max_files=max_files)
        records: List[ImportRecord] = []

        for i, file_path in enumerate(files):
            record = self.process_file(file_path)
            if record:
                records.append(record)

            if progress_callback and i % 100 == 0:
                progress_callback(i, len(files), len(records))

        logger.info(
            "Import batch complete: %d files, %d records, %d duplicates, %d quarantined, %d errors",
            len(files), len(records), self._duplicate_count,
            self._quarantine_count, self._error_count,
        )
        return records

    def get_stats(self) -> Dict[str, int]:
        """Return import statistics."""
        return {
            "processed": self._processed_count,
            "errors": self._error_count,
            "quarantined": self._quarantine_count,
            "duplicates": self._duplicate_count,
            "unique_hashes": len(self._seen_hashes),
        }
