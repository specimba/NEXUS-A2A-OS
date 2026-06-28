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
from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path

import numpy as np

from nexus_os.archivist.import_stage import ImportRecord, FileType, AdmissionClass
from nexus_os.archivist.taxonomy import TOPIC_KEYWORDS

logger = logging.getLogger("nexus_os.archivist.compile")



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


@dataclass
class CompileStats:
    """Compile stage statistics snapshot.

    Backward-compatible dataclass: supports both attribute access
    (stats.total) and dict-style access (stats["total"]) / membership
    checks ("total" in stats).
    """
    total: int = 0
    wiki_admissible: int = 0
    dossier_topics: int = 0
    with_arxiv_id: int = 0
    errors: int = 0
    backlinks: int = 0

    def to_dict(self) -> Dict[str, int]:
        return {
            "total": self.total,
            "wiki_admissible": self.wiki_admissible,
            "dossier_topics": self.dossier_topics,
            "with_arxiv_id": self.with_arxiv_id,
            "errors": self.errors,
            "backlinks": self.backlinks,
        }

    def __getitem__(self, key: str) -> int:
        try:
            return getattr(self, key)
        except AttributeError:
            raise KeyError(key)

    def __contains__(self, key: str) -> bool:
        return key in self.to_dict()

    def __iter__(self):
        return iter(self.to_dict())

    def __len__(self) -> int:
        return len(self.to_dict())

    def keys(self):
        return self.to_dict().keys()

    def values(self):
        return self.to_dict().values()

    def items(self):
        return self.to_dict().items()


class ArchivistCompiler:
    """Compile stage: semantic tagging, linking, admission refinement."""

    def __init__(self, enable_embedding: bool = True):
        self._dossier_candidates: Dict[str, List[CompiledRecord]] = {}
        self._arxiv_index: Dict[str, CompiledRecord] = {}  # arXiv ID → record
        self._last_backlinks: int = 0
        self._enable_embedding = enable_embedding
        self._vectorizer = None  # Lazy init

    def tag_topics(self, record: ImportRecord) -> List[str]:
        """Tag record with semantic topics based on title and filename."""
        file_type_str = record.file_type.value if hasattr(record.file_type, 'value') else str(record.file_type)
        text = f"{record.title or ''} {record.file_path} {file_type_str}".lower()
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

    def _get_vectorizer(self):
        """Lazy-initialize TF-IDF vectorizer for embedding-based classification."""
        if self._vectorizer is None and self._enable_embedding:
            try:
                from sklearn.feature_extraction.text import TfidfVectorizer
                self._vectorizer = TfidfVectorizer(max_features=5000, stop_words="english")
            except ImportError:
                logger.warning("sklearn not available, embedding classifier disabled")
                self._enable_embedding = False
        return self._vectorizer

    def hybrid_classify_topics(self, record: ImportRecord) -> Tuple[List[str], Dict[str, float]]:
        """Hybrid topic classification: rule-based (0.6) + embedding-based (0.4).

        Rule path: keyword matching against TOPIC_KEYWORDS (same as tag_topics).
        Embedding path: TF-IDF cosine similarity between record text and topic
        keyword centroids.

        Returns:
            (tags_list, scores_dict) where scores_dict maps topic → combined score.
        """
        text = self._build_classification_text(record)
        combined: Dict[str, float] = {}

        # ── Rule-based pass (weight 0.6) ──
        for topic, keywords in TOPIC_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                combined[topic] = combined.get(topic, 0.0) + 0.6

        # ── Embedding-based pass (weight 0.4) ──
        vec = self._get_vectorizer()
        if vec is not None and len(text) > 20:
            try:
                from sklearn.feature_extraction.text import TfidfVectorizer as _T
                from sklearn.metrics.pairwise import cosine_similarity

                all_texts = [text]
                topic_anchor_texts = []
                for topic in TOPIC_KEYWORDS:
                    topic_anchor_texts.append(" ".join(TOPIC_KEYWORDS[topic]))

                corpus = all_texts + topic_anchor_texts
                tfidf = _T(max_features=5000, stop_words="english")
                tfidf_matrix = tfidf.fit_transform(corpus)

                record_vec = tfidf_matrix[0:1]
                topic_vecs = tfidf_matrix[1:]

                similarities = cosine_similarity(record_vec, topic_vecs).flatten()
                for i, topic in enumerate(TOPIC_KEYWORDS):
                    embed_score = similarities[i] * 0.4
                    if embed_score >= 0.05:
                        combined[topic] = combined.get(topic, 0.0) + embed_score

            except Exception as e:
                logger.debug("Embedding classification failed: %s", e)

        # Filter by threshold 0.30
        tags = [
            tag for tag, score in sorted(combined.items(), key=lambda x: -x[1])
            if score >= 0.30
        ]
        return tags[:5], combined

    def _build_classification_text(self, record: ImportRecord) -> str:
        """Build the text string used for classification."""
        file_type_str = (
            record.file_type.value
            if hasattr(record.file_type, "value")
            else str(record.file_type)
        )
        parts = [
            record.title or "",
            record.file_path or "",
            file_type_str,
        ]
        if record.topic_tags:
            parts.extend(record.topic_tags)
        text = " ".join(parts).lower()
        return text

    def auto_link_records(
        self, compiled: List[CompiledRecord], threshold: float = 0.30
    ) -> int:
        """Auto-link compiled records by topic overlap and citation relationships.

        Creates bidirectional links between records sharing ≥2 topic tags,
        or having high embedding similarity. Returns count of links created.

        Edge types:
        - direct citation: arXiv ID citation (existing citation_links)
        - topic overlap: 2+ shared tags → ``topic_link``
        - semantic: embedding similarity ≥ threshold → ``semantic_link``
        """
        links_added = 0

        # Built-in citation backlinks are done in _build_backlinks already.
        # This adds topic-overlap and semantic links.

        # Topic overlap links
        topic_to_records: Dict[str, List[CompiledRecord]] = {}
        for c in compiled:
            for tag in (c.topic_tags or []):
                if tag not in topic_to_records:
                    topic_to_records[tag] = []
                topic_to_records[tag].append(c)

        for c in compiled:
            for tag in (c.topic_tags or []):
                peers = topic_to_records.get(tag, [])
                for peer in peers:
                    if peer is c:
                        continue
                    shared = set(c.topic_tags or []) & set(peer.topic_tags or [])
                    if len(shared) >= 2:
                        key = f"topic_link:{tag}"
                        if key not in c.citation_links:
                            c.citation_links.append(key)
                            links_added += 1

        # Semantic links via embedding similarity
        vec = self._get_vectorizer()
        if vec is not None and len(compiled) >= 2:
            try:
                from sklearn.feature_extraction.text import TfidfVectorizer as _T
                from sklearn.metrics.pairwise import cosine_similarity

                texts = [self._build_classification_text(c.import_record) for c in compiled]
                tfidf = _T(max_features=5000, stop_words="english")
                matrix = tfidf.fit_transform(texts)
                sim_matrix = cosine_similarity(matrix)

                for i in range(len(compiled)):
                    for j in range(i + 1, len(compiled)):
                        sim = sim_matrix[i][j]
                        if sim >= threshold:
                            key_i = f"semantic_link:{compiled[j].import_record.arxiv_id or compiled[j].import_record.blake3_hash[:12]}"
                            key_j = f"semantic_link:{compiled[i].import_record.arxiv_id or compiled[i].import_record.blake3_hash[:12]}"
                            if key_i not in compiled[i].citation_links:
                                compiled[i].citation_links.append(key_i)
                                links_added += 1
                            if key_j not in compiled[j].citation_links:
                                compiled[j].citation_links.append(key_j)
                                links_added += 1
            except Exception as e:
                logger.debug("Semantic linking failed: %s", e)

        if links_added:
            logger.info("Auto-linked %d records (%d links)", len(compiled), links_added)
        return links_added

    def estimate_word_count(self, record: ImportRecord) -> Optional[int]:
        """Estimate word count for text files."""
        if record.file_type not in {FileType.PAPER, FileType.LOG, FileType.MARKDOWN, FileType.PROMPT}:
            return None
        try:
            with open(record.file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read(50000)  # Read first 50KB
                return len(content.split())
        except UnicodeDecodeError:
            return None  # Expected for binary files
        except Exception as e:
            logger.debug("Word count estimation failed for %s: %s", record.file_path, e)
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
            # Semantic tagging (hybrid: rule 0.6 + embedding 0.4)
            compiled.topic_tags, _ = self.hybrid_classify_topics(record)

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
        # Retroactively promote early records that missed the dossier threshold
        self._retroactively_promote_dossiers(compiled)
        # Build reverse citation links
        backlinks = self._build_backlinks(compiled)
        # Auto-link records by topic overlap and semantic similarity
        auto_links = self.auto_link_records(compiled)
        self._last_backlinks = backlinks + auto_links
        return compiled

    def _retroactively_promote_dossiers(self, compiled: List[CompiledRecord]) -> int:
        """Retroactively promote early records to DOSSIER admission class.

        The first 2 records per topic are added to _dossier_candidates before
        refine_admission() can detect the threshold. This method fixes them.
        Returns count of promoted records.
        """
        promoted = 0
        for topic, candidates in self._dossier_candidates.items():
            if len(candidates) >= 3:  # Only promote if topic qualifies for dossier
                for record in candidates:
                    if record.admission_class != AdmissionClass.DOSSIER:
                        record.admission_class = AdmissionClass.DOSSIER
                        promoted += 1
        if promoted:
            logger.info("Retroactively promoted %d early records to DOSSIER", promoted)
        return promoted

    def _build_backlinks(self, compiled: List[CompiledRecord]) -> int:
        """Construct reverse citation links after all records are compiled.

        Forward links are set by link_citations() during compile_record().
        This pass adds the reverse: if A.citation_links contains B's arXiv ID,
        then B gets a backlink to A's arXiv ID.

        Returns the count of backlinks added.
        """
        backlinks_added = 0
        arxiv_to_record: Dict[str, CompiledRecord] = {}
        for c in compiled:
            if c.import_record.arxiv_id:
                arxiv_to_record[c.import_record.arxiv_id] = c

        for c in compiled:
            for cited_id in c.citation_links:
                cited_record = arxiv_to_record.get(cited_id)
                if cited_record and c.import_record.arxiv_id:
                    if c.import_record.arxiv_id not in cited_record.citation_links:
                        cited_record.citation_links.append(c.import_record.arxiv_id)
                        backlinks_added += 1

        if backlinks_added:
            logger.info("Built %d backlinks across %d compiled records", backlinks_added, len(compiled))
        return backlinks_added

    def get_dossier_candidates(self, topic: str) -> List[CompiledRecord]:
        """Get records assigned to a dossier topic."""
        return self._dossier_candidates.get(topic, [])

    def get_wiki_admissible(self, compiled: List[CompiledRecord]) -> List[CompiledRecord]:
        """Filter records that meet wiki admission criteria."""
        return [c for c in compiled if c.is_wiki_admissible]

    def get_stats(self, compiled: Optional[List[CompiledRecord]] = None) -> Dict:
        """Return compile statistics as a dict."""
        if compiled is None:
            compiled = [r for candidates in self._dossier_candidates.values() for r in candidates]
        stats = CompileStats(
            total=len(compiled),
            wiki_admissible=sum(1 for c in compiled if c.is_wiki_admissible),
            dossier_topics=len(self._dossier_candidates),
            with_arxiv_id=sum(1 for c in compiled if c.import_record.arxiv_id),
            errors=sum(len(c.compile_errors) for c in compiled),
            backlinks=self._last_backlinks,
        )
        return stats.to_dict()
