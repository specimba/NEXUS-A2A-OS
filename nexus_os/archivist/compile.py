"""nexus_os/archivist/compile.py — ARCHIVIST Compile Stage

Stage 2 of 3-stage pipeline:
- Semantic tagging (trust, memory, security, benchmark, model, governance, multimodal)
- Auto-linking: cross-reference papers by citation, topic overlap
- 7 admission classes refinement (source_card, dossier, web_reference, etc.)
- Wiki admission gate: quality threshold ≥ 500 words, structured
- Quarantine review: flag suspicious, unverified, conflicting files

Input: ImportRecord list from import.py
Output: CompiledRecord list with tags, links, dossier assignments
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from pathlib import Path

from nexus_os.archivist.import_stage import ImportRecord, FileType, AdmissionClass

logger = logging.getLogger("nexus_os.archivist.compile")


# Semantic topic tags
TOPIC_KEYWORDS = {
    "trust": {"trust", "reputation", "bayesian", "grinding", "gaming", "sigmoid", "logistic"},
    "memory": {"memory", "episodic", "semantic", "procedural", "consolidation", "retrieval", "rag", "context"},
    "security": {"security", "attack", "threat", "jailbreak", "prompt injection", "exfiltration", "cve", "vulnerability"},
    "benchmark": {"benchmark", "evaluation", "arena", "mmlu", "gpqa", "aime", "score", "metric"},
    "model": {"model", "llm", "transformer", "diffusion", "embedding", "quantization", "inference"},
    "governance": {"governance", "policy", "regulation", "compliance", "audit", "cdr", "risk"},
    "multimodal": {"multimodal", "vision", "image", "vlm", "audio", "speech"},
    "agent": {"agent", "autonomous", "tool use", "orchestration", "multi-agent", "mas"},
}


@dataclass
class CompiledRecord:
    """A record produced by the Compile stage."""
    import_record: ImportRecord
    topic_tags: List[str] = field(default_factory=list)
    citation_links: List[str] = field(default_factory=list)  # linked arXiv IDs
    dossier_topic: Optional[str] = None
    word_count: Optional[int] = None
    quality_score: float = 0.0  # 0-1
    is_wiki_admissible: bool = False
    # Refinement
    admission_class: Optional[AdmissionClass] = None
    compile_errors: List[str] = field(default_factory=list)


class ArchivistCompiler:
    """Compile stage: semantic tagging, linking, admission refinement."""

    def __init__(self):
        self._dossier_candidates: Dict[str, List[CompiledRecord]] = {}
        self._arxiv_index: Dict[str, CompiledRecord] = {}  # arXiv ID → record

    def tag_topics(self, record: ImportRecord) -> List[str]:
        """Tag record with semantic topics based on title and filename."""
        text = f"{record.title or ''} {record.file_path} {record.file_type.value}".lower()
        tags = []
        for topic, keywords in TOPIC_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                tags.append(topic)
        return tags

    def link_citations(self, record: ImportRecord) -> List[str]:
        """Find citation links (arXiv IDs) in filename."""
        links = []
        if record.arxiv_id:
            links.append(record.arxiv_id)
        # Check for referenced arXiv IDs in filename (e.g., "arxiv_2403.13031_revisited")
        matches = re.findall(r"(\d{4}\.\d{4,5})", record.file_path)
        for m in matches:
            if m != record.arxiv_id:
                links.append(m)
        return links

    def estimate_word_count(self, record: ImportRecord) -> Optional[int]:
        """Estimate word count for text files."""
        if record.file_type not in {FileType.PAPER, FileType.LOG, FileType.MARKDOWN, FileType.PROMPT}:
            return None
        try:
            with open(record.file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read(50000)  # Read first 50KB
                return len(content.split())
        except Exception:
            return None

    def assess_quality(self, record: ImportRecord, word_count: Optional[int]) -> float:
        """Assess quality score (0-1) for wiki admission."""
        score = 0.0

        # Structured content: has headings, sections
        if record.file_type == FileType.MARKDOWN:
            score += 0.3
        if record.file_type == FileType.PAPER:
            score += 0.4

        # Word count: ≥500 words = good, ≥2000 = excellent
        if word_count:
            if word_count >= 2000:
                score += 0.4
            elif word_count >= 500:
                score += 0.3
            elif word_count >= 100:
                score += 0.1

        # Source reliability: arXiv papers, canonical docs
        if record.arxiv_id:
            score += 0.2
        if record.admission_class == AdmissionClass.SOURCE_CARD:
            score += 0.1

        # Priority proxy: higher priority = more curated
        score += min(0.1, record.priority / 1200.0)

        return min(1.0, score)

    def check_wiki_admission(self, record: ImportRecord, word_count: Optional[int], quality: float) -> bool:
        """Check if record meets wiki admission criteria."""
        # Quality threshold: ≥0.5
        if quality < 0.5:
            return False
        # Word count: ≥500 for text files
        if word_count is not None and word_count < 500:
            return False
        # Not quarantined
        if record.admission_class == AdmissionClass.QUARANTINE:
            return False
        return True

    def refine_admission(self, record: ImportRecord, tags: List[str]) -> AdmissionClass:
        """Refine admission class based on compile-stage analysis."""
        # Dossier: if tagged with a topic that has 3+ candidates
        for tag in tags:
            if tag in self._dossier_candidates and len(self._dossier_candidates[tag]) >= 2:
                return AdmissionClass.DOSSIER

        # Source card: arXiv papers, high quality, canonical
        if record.arxiv_id and record.priority >= 80:
            return AdmissionClass.SOURCE_CARD

        # Template fragment: prompt strategies, reusable patterns
        if "prompt" in (record.title or "").lower() or "strategy" in (record.title or "").lower():
            return AdmissionClass.TEMPLATE_FRAGMENT

        # Social reference: community findings, discussions
        if "forum" in record.source_dir.lower() or "community" in record.source_dir.lower():
            return AdmissionClass.SOCIAL_REFERENCE

        # Default: keep original
        return record.admission_class

    def compile_record(self, record: ImportRecord) -> CompiledRecord:
        """Compile a single import record."""
        compiled = CompiledRecord(import_record=record)

        try:
            # Semantic tagging
            compiled.topic_tags = self.tag_topics(record)

            # Citation linking
            compiled.citation_links = self.link_citations(record)
            if record.arxiv_id:
                self._arxiv_index[record.arxiv_id] = compiled

            # Quality assessment
            compiled.word_count = self.estimate_word_count(record)
            compiled.quality_score = self.assess_quality(record, compiled.word_count)
            compiled.is_wiki_admissible = self.check_wiki_admission(
                record, compiled.word_count, compiled.quality_score
            )

            # Admission refinement
            compiled.admission_class = self.refine_admission(record, compiled.topic_tags)

            # Dossier assignment
            if compiled.topic_tags:
                primary_tag = compiled.topic_tags[0]
                compiled.dossier_topic = primary_tag
                if primary_tag not in self._dossier_candidates:
                    self._dossier_candidates[primary_tag] = []
                self._dossier_candidates[primary_tag].append(compiled)

        except Exception as e:
            logger.exception("Compile failed for %s: %s", record.file_path, e)
            compiled.compile_errors.append(str(e))

        return compiled

    def compile_batch(self, records: List[ImportRecord]) -> List[CompiledRecord]:
        """Compile a batch of import records."""
        compiled: List[CompiledRecord] = []
        for i, record in enumerate(records):
            c = self.compile_record(record)
            compiled.append(c)
            if i % 100 == 0:
                logger.info("Compiled %d/%d records", i, len(records))
        logger.info("Compile batch complete: %d records, %d dossier topics", len(compiled), len(self._dossier_candidates))
        return compiled

    def get_dossier_candidates(self, topic: str) -> List[CompiledRecord]:
        """Get records assigned to a dossier topic."""
        return self._dossier_candidates.get(topic, [])

    def get_wiki_admissible(self, compiled: List[CompiledRecord]) -> List[CompiledRecord]:
        """Filter records that meet wiki admission criteria."""
        return [c for c in compiled if c.is_wiki_admissible]

    def get_stats(self, compiled: List[CompiledRecord]) -> Dict[str, int]:
        """Return compile statistics."""
        stats = {
            "total": len(compiled),
            "wiki_admissible": sum(1 for c in compiled if c.is_wiki_admissible),
            "dossier_topics": len(self._dossier_candidates),
            "with_arxiv_id": sum(1 for c in compiled if c.import_record.arxiv_id),
            "errors": sum(len(c.compile_errors) for c in compiled),
        }
        for topic in self._dossier_candidates:
            stats[f"dossier_{topic}"] = len(self._dossier_candidates[topic])
        return stats
