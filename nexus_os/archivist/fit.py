"""nexus_os/archivist/fit.py — ARCHIVIST Fit Stage

Stage 3 of 3-stage pipeline:
- Dossier synthesis: merge related papers into wiki articles
- Project-fit scoring: how relevant to NEXOS goals?
- Wiki markdown generation with frontmatter (title, tags, source, priority, admission_class)
- Feed to SEMANTIC channel (3) of memory architecture

Output format: Markdown with YAML frontmatter, compatible with NEXUS wiki dashboard.

Frontmatter schema:
---
title: "Dossier: Memory Architecture for LLM Agents"
tags: [memory, trust, semantic, episodic, consolidation]
source_paper_ids: ["arxiv:2511.20857", "arxiv:2603.07670", "arxiv:2510.18866"]
confidence: 0.85
priority: 110
admission_class: dossier
dossier_topic: memory
nexus_relevance: 0.92
generated_at: 2026-06-11T04:20:00Z
---
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from nexus_os.archivist.compile import CompiledRecord

logger = logging.getLogger("nexus_os.archivist.fit")


# NEXUS goal relevance weights (higher = more relevant to NEXUS mission)
GOAL_RELEVANCE = {
    "trust": 1.0,
    "memory": 1.0,
    "security": 0.95,
    "governance": 0.9,
    "benchmark": 0.85,
    "model": 0.8,
    "agent": 0.8,
    "multimodal": 0.6,
}


@dataclass
class Dossier:
    """A synthesized dossier for wiki publication."""
    topic: str
    title: str
    content: str  # Markdown content
    source_records: List[CompiledRecord] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    source_paper_ids: List[str] = field(default_factory=list)
    confidence: float = 0.0
    priority: int = 0
    nexus_relevance: float = 0.0
    generated_at: Optional[str] = None


class ArchivistFitter:
    """Fit stage: dossier synthesis, wiki markdown generation, SEMANTIC channel feed."""

    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = Path(output_dir) if output_dir else Path(__file__).parent / "wiki_output"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._dossiers: List[Dossier] = []

    def score_nexus_relevance(self, compiled: List[CompiledRecord]) -> float:
        """Score how relevant a set of records is to NEXUS goals."""
        if not compiled:
            return 0.0

        total_relevance = 0.0
        for c in compiled:
            record_relevance = 0.0
            for tag in c.topic_tags:
                record_relevance += GOAL_RELEVANCE.get(tag, 0.5)
            # Weight by quality and priority
            total_relevance += record_relevance * c.quality_score * (c.import_record.priority / 120.0)

        # Normalize by count
        avg_relevance = total_relevance / len(compiled)
        return min(1.0, avg_relevance)

    def synthesize_dossier(self, topic: str, records: List[CompiledRecord]) -> Dossier:
        """Synthesize a dossier from related compiled records."""
        if not records:
            raise ValueError("Cannot synthesize dossier from empty records")

        # Sort by priority and quality
        sorted_records = sorted(
            records,
            key=lambda r: (r.import_record.priority, r.quality_score),
            reverse=True,
        )

        # Collect metadata
        all_tags = set()
        all_arxiv_ids = []
        for r in sorted_records:
            all_tags.update(r.topic_tags)
            if r.import_record.arxiv_id:
                all_arxiv_ids.append(r.import_record.arxiv_id)

        # Compute scores
        avg_confidence = sum(r.quality_score for r in sorted_records) / len(sorted_records)
        max_priority = max(r.import_record.priority for r in sorted_records)
        nexus_relevance = self.score_nexus_relevance(sorted_records)

        # Generate markdown content
        content = self._generate_dossier_markdown(topic, sorted_records, all_tags, all_arxiv_ids)

        dossier = Dossier(
            topic=topic,
            title=f"Dossier: {topic.title().replace('_', ' ')}",
            content=content,
            source_records=sorted_records,
            tags=list(all_tags),
            source_paper_ids=all_arxiv_ids,
            confidence=round(avg_confidence, 3),
            priority=min(120, max_priority + 10),  # Dossier gets +10 priority
            nexus_relevance=round(nexus_relevance, 3),
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

        return dossier

    def _generate_dossier_markdown(
        self,
        topic: str,
        records: List[CompiledRecord],
        tags: set,
        arxiv_ids: List[str],
    ) -> str:
        """Generate markdown content for a dossier."""
        lines = []
        lines.append("# Dossier: " + topic.title().replace("_", " "))
        lines.append("")
        lines.append(f"**Topic:** {topic}")
        lines.append(f"**Sources:** {len(records)} records")
        lines.append(f"**Confidence:** {sum(r.quality_score for r in records) / len(records):.2f}")
        lines.append("")
        lines.append("## Sources")
        lines.append("")
        for i, r in enumerate(records[:10], 1):  # Top 10 sources
            title = r.import_record.title or Path(r.import_record.file_path).name
            lines.append(f"{i}. **{title}**")
            lines.append(f"   - Type: {r.import_record.file_type.value}")
            lines.append(f"   - Priority: {r.import_record.priority}")
            lines.append(f"   - Quality: {r.quality_score:.2f}")
            if r.import_record.arxiv_id:
                lines.append(f"   - arXiv: {r.import_record.arxiv_id}")
            lines.append(f"   - Path: `{r.import_record.file_path}`")
            lines.append("")
        lines.append("")
        lines.append("## Key Findings")
        lines.append("")
        # Placeholder for LLM-generated synthesis (future work)
        lines.append("*Synthesis pending: structured summary of key findings across sources.*")
        lines.append("")
        lines.append("## Relevance to NEXUS")
        lines.append("")
        relevance_tags = [t for t in tags if t in GOAL_RELEVANCE]
        if relevance_tags:
            lines.append(f"High relevance to: {', '.join(relevance_tags)}")
        lines.append("")
        lines.append("## Open Questions")
        lines.append("")
        lines.append("- *How does this relate to the 8-channel memory architecture?*")
        lines.append("- *What are the actionable design patterns for NEXUS implementation?*")
        lines.append("")
        lines.append("---")
        lines.append(f"*Generated by NEXUS ARCHIVIST Fit stage at {datetime.now(timezone.utc).isoformat()}*")

        return "\n".join(lines)

    def generate_wiki_markdown(self, dossier: Dossier) -> str:
        """Generate wiki-ready markdown with YAML frontmatter."""
        frontmatter = {
            "title": dossier.title,
            "tags": dossier.tags,
            "source_paper_ids": dossier.source_paper_ids,
            "confidence": dossier.confidence,
            "priority": dossier.priority,
            "admission_class": "dossier",
            "dossier_topic": dossier.topic,
            "nexus_relevance": dossier.nexus_relevance,
            "generated_at": dossier.generated_at,
        }

        # YAML frontmatter
        lines = ["---"]
        for key, value in frontmatter.items():
            if isinstance(value, list):
                lines.append(f"{key}:")
                for item in value:
                    lines.append(f"  - {item}")
            else:
                lines.append(f"{key}: {value}")
        lines.append("---")
        lines.append("")
        lines.append(dossier.content)

        return "\n".join(lines)

    def save_dossier(self, dossier: Dossier) -> Path:
        """Save dossier to wiki output directory."""
        filename = f"dossier_{dossier.topic}.md"
        # Sanitize filename
        filename = "".join(c if c.isalnum() or c in "._-" else "_" for c in filename)
        filepath = self.output_dir / filename

        markdown = self.generate_wiki_markdown(dossier)
        filepath.write_text(markdown, encoding="utf-8")

        logger.info("Saved dossier: %s (topic=%s, sources=%d)", filepath, dossier.topic, len(dossier.source_records))
        return filepath

    def fit_batch(self, dossier_candidates: Dict[str, List[CompiledRecord]]) -> List[Dossier]:
        """Process all dossier candidates and generate wiki articles."""
        dossiers: List[Dossier] = []
        for topic, records in dossier_candidates.items():
            if len(records) < 2:
                continue  # Need at least 2 sources for a dossier
            try:
                dossier = self.synthesize_dossier(topic, records)
                self.save_dossier(dossier)
                dossiers.append(dossier)
                self._dossiers.append(dossier)
            except Exception as e:
                logger.exception("Dossier synthesis failed for topic %s: %s", topic, e)

        logger.info("Fit batch complete: %d dossiers generated", len(dossiers))
        return dossiers

    def get_stats(self) -> Dict[str, int]:
        """Return fit statistics."""
        return {
            "dossiers_generated": len(self._dossiers),
            "total_source_records": sum(len(d.source_records) for d in self._dossiers),
        }

    def get_dossier_paths(self) -> List[Path]:
        """Return paths of all generated dossier files."""
        return list(self.output_dir.glob("dossier_*.md"))
