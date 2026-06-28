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
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set

import yaml

from nexus_os.archivist.compile import CompiledRecord

logger = logging.getLogger("nexus_os.archivist.fit")


# NEXUS goal relevance weights (higher = more relevant to NEXUS mission)
# All 14 topics from the unified taxonomy
GOAL_RELEVANCE = {
    "trust": 1.0,
    "memory": 1.0,
    "security": 0.95,
    "governance": 0.9,
    "benchmark": 0.85,
    "model": 0.8,
    "agent": 0.8,
    "multimodal": 0.6,
    "code": 0.85,
    "spec": 0.75,
    "rules": 0.9,
    "role": 0.7,
    "dataset": 0.75,
    "rejection": 0.85,
}


class CitationEdgeType(str, Enum):
    """5 edge types for citation graph."""
    CITES = "cites"
    EXTENDS = "extends"
    CONTRADICTS = "contradicts"
    REPLICATES = "replicates"
    APPLIES = "applies"


@dataclass
class CitationEdge:
    """A directed edge in the citation graph."""
    source_id: str           # arXiv ID or BLAKE3 hash of citing record
    target_id: str           # arXiv ID or BLAKE3 hash of cited record
    edge_type: CitationEdgeType = CitationEdgeType.CITES
    confidence: float = 1.0  # 0-1, how confident we are this edge exists
    evidence: str = ""       # How this edge was discovered


@dataclass
class CitationGraph:
    """Directed citation graph among compiled records.

    Supports 5 edge types (cites, extends, contradicts, replicates, applies)
    and provides query methods for graph analysis.
    """
    edges: List[CitationEdge] = field(default_factory=list)

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: CitationEdgeType = CitationEdgeType.CITES,
        confidence: float = 1.0,
        evidence: str = "",
    ) -> None:
        self.edges.append(CitationEdge(
            source_id=source_id,
            target_id=target_id,
            edge_type=edge_type,
            confidence=confidence,
            evidence=evidence,
        ))

    def get_citations(self, paper_id: str) -> List[CitationEdge]:
        """Get all outgoing citations from a paper."""
        return [e for e in self.edges if e.source_id == paper_id]

    def get_cited_by(self, paper_id: str) -> List[CitationEdge]:
        """Get all incoming citations to a paper."""
        return [e for e in self.edges if e.target_id == paper_id]

    def get_edge_types(self) -> Dict[str, int]:
        """Count edges by type."""
        counts: Dict[str, int] = {}
        for e in self.edges:
            counts[e.edge_type.value] = counts.get(e.edge_type.value, 0) + 1
        return counts

    def to_yaml(self) -> str:
        """Serialize graph to YAML."""
        return yaml.dump({
            "edges": [
                {
                    "source": e.source_id,
                    "target": e.target_id,
                    "type": e.edge_type.value,
                    "confidence": e.confidence,
                    "evidence": e.evidence,
                }
                for e in self.edges
            ]
        }, default_flow_style=False)

    @classmethod
    def from_compiled_records(cls, compiled: List[CompiledRecord]) -> "CitationGraph":
        """Build a citation graph from compiled records.

        Discovers edges by parsing citation_links looking for arXiv IDs
        (direct citations) and topic_link/semantic_link patterns.
        """
        graph = cls()
        arxiv_map = {}
        for c in compiled:
            aid = c.import_record.arxiv_id
            if aid:
                arxiv_map[aid] = c

        for c in compiled:
            source_id = c.import_record.arxiv_id or c.import_record.blake3_hash[:12]
            for link in c.citation_links:
                link = link.strip()
                # arXiv ID → direct citation
                if re.match(r"^\d{4}\.\d{4,5}$", link):
                    graph.add_edge(
                        source_id=source_id,
                        target_id=link,
                        edge_type=CitationEdgeType.CITES,
                        evidence="citation_link_in_record",
                    )
                elif link.startswith("topic_link:"):
                    graph.add_edge(
                        source_id=source_id,
                        target_id=link.split(":", 1)[1],
                        edge_type=CitationEdgeType.EXTENDS,
                        confidence=0.6,
                        evidence="topic_overlap",
                    )
                elif link.startswith("semantic_link:"):
                    graph.add_edge(
                        source_id=source_id,
                        target_id=link.split(":", 1)[1],
                        edge_type=CitationEdgeType.APPLIES,
                        confidence=0.4,
                        evidence="embedding_similarity",
                    )
        return graph


# 8-channel memory context for LLM synthesis prompts
DOSSIER_SYNTHESIS_PROMPT = """You are NEXUS ARCHIVIST Fit stage, synthesizing a knowledge dossier from compiled evidence records.

Topic: {topic}
Number of sources: {source_count}
Confidence score: {confidence:.2f}
Citation graph edges: {citation_edges}

Source records (up to 15):
{source_list}

Write a structured wiki article covering:
1. **Overview** — what this topic is about and why it matters for NEXUS OS
2. **Key Findings** — synthesized insights across all sources, grouped by theme
3. **Contradictions & Open Questions** — where sources disagree or gaps exist
4. **NEXUS Relevance** — how this applies to the NEXUS OS architecture (trust, memory, security, governance)
5. **References** — numbered list of source papers

Use clear Markdown. Be specific — cite source indices like [1], [2] inline.
Do not invent facts not supported by the sources below.
If there are too few sources to synthesize, say so and provide a summary instead.
"""


@dataclass
class LLMSynthesisResult:
    """Result of LLM-powered dossier synthesis."""
    success: bool
    content: str
    model_used: str = ""
    tokens_used: int = 0
    error: str = ""


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
        self._citation_graph: Optional[CitationGraph] = None

    def build_citation_graph(self, records: List[CompiledRecord]) -> CitationGraph:
        """Build a citation graph from compiled records."""
        return CitationGraph.from_compiled_records(records)

    def score_nexus_relevance(self, compiled: List[CompiledRecord]) -> float:
        """Score how relevant a set of records is to NEXUS goals."""
        if not compiled:
            return 0.0

        total_relevance = 0.0
        for c in compiled:
            record_relevance = 0.0
            for tag in c.topic_tags:
                record_relevance += GOAL_RELEVANCE.get(tag, 0.5)
            total_relevance += record_relevance * c.quality_score * (c.import_record.priority / 120.0)

        avg_relevance = total_relevance / len(compiled)
        return min(1.0, avg_relevance)

    def _build_llm_prompt(
        self,
        topic: str,
        records: List[CompiledRecord],
        citation_graph: Optional[CitationGraph] = None,
    ) -> str:
        """Build the LLM synthesis prompt from records."""
        source_lines = []
        for i, r in enumerate(records[:15], 1):
            ir = r.import_record
            title = ir.title or Path(ir.file_path).name
            tags = ", ".join(r.topic_tags or [])
            source_lines.append(
                f"[{i}] {title}\n"
                f"    Type: {getattr(ir.file_type, 'value', ir.file_type)}\n"
                f"    Tags: {tags}\n"
                f"    arXiv: {ir.arxiv_id or 'N/A'}\n"
                f"    Quality: {r.quality_score:.2f}\n"
                f"    Priority: {ir.priority}\n"
                f"    File: {ir.file_path}\n"
            )

        graph_edges = 0
        if citation_graph:
            graph_edges = len(citation_graph.edges)

        return DOSSIER_SYNTHESIS_PROMPT.format(
            topic=topic,
            source_count=len(records),
            confidence=sum(r.quality_score for r in records) / len(records) if records else 0,
            citation_edges=graph_edges,
            source_list="\n".join(source_lines),
        )

    def llm_synthesize_dossier(
        self,
        topic: str,
        records: List[CompiledRecord],
        citation_graph: Optional[CitationGraph] = None,
    ) -> LLMSynthesisResult:
        """Attempt LLM-powered dossier synthesis via GMR model routing.

        Falls back gracefully if GMR is unavailable, returning a result
        with success=False and the fallback content seeded from metadata.

        This is a best-effort synthesis — the actual LLM call is wrapped
        in try/except so the pipeline never blocks on model availability.
        """
        prompt = self._build_llm_prompt(topic, records, citation_graph)

        # Try GMR model routing
        try:
            from nexus_os.engine.gmr import GMRRouter
            router = GMRRouter()
            response = router.route(
                prompt=prompt,
                task_type="dossier_synthesis",
                max_tokens=4096,
                temperature=0.3,
            )
            if response and response.get("content"):
                return LLMSynthesisResult(
                    success=True,
                    content=response["content"],
                    model_used=response.get("model", "unknown"),
                    tokens_used=response.get("tokens_used", 0),
                )
        except ImportError:
            logger.info("GMR not available, using metadata synthesis for topic '%s'", topic)
        except Exception as e:
            logger.warning("LLM synthesis failed for topic '%s': %s", topic, e)

        # Fallback: structured metadata synthesis
        fallback = self._generate_dossier_markdown(topic, records, set(), [], citation_graph)
        return LLMSynthesisResult(
            success=False,
            content=fallback,
            error="GMR unavailable, used metadata fallback",
        )

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

    def synthesize_dossier(
        self,
        topic: str,
        records: List[CompiledRecord],
        enable_llm: bool = True,
    ) -> Dossier:
        """Synthesize a dossier from related compiled records.

        Uses LLM-powered synthesis when GMR is available (enable_llm=True),
        falling back to structured metadata-based markdown generation.

        Args:
            topic: Dossier topic tag.
            records: Compiled records for this topic.
            enable_llm: Whether to attempt LLM synthesis.

        Returns:
            Dossier with synthesized content.
        """
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

        # Build citation graph
        citation_graph = self.build_citation_graph(sorted_records)

        # Compute scores
        avg_confidence = sum(r.quality_score for r in sorted_records) / len(sorted_records)
        max_priority = max(r.import_record.priority for r in sorted_records)
        nexus_relevance = self.score_nexus_relevance(sorted_records)

        # Generate content via LLM (or fallback to metadata summary)
        if enable_llm:
            llm_result = self.llm_synthesize_dossier(topic, sorted_records, citation_graph)
            content = llm_result.content
        else:
            content = self._generate_dossier_markdown(
                topic, sorted_records, all_tags, all_arxiv_ids, citation_graph
            )

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
        citation_graph: Optional[CitationGraph] = None,
    ) -> str:
        """Generate markdown content for a dossier."""
        lines = []
        lines.append("# Dossier: " + topic.title().replace("_", " "))
        lines.append("")
        lines.append(f"**Topic:** {topic}")
        lines.append(f"**Sources:** {len(records)} records")
        lines.append(f"**Confidence:** {sum(r.quality_score for r in records) / len(records):.2f}")
        if citation_graph:
            edge_counts = citation_graph.get_edge_types()
            lines.append(f"**Citation Graph:** {len(citation_graph.edges)} edges")
            for etype, count in edge_counts.items():
                lines.append(f"  - {etype}: {count}")
        lines.append("")
        lines.append("## Sources")
        lines.append("")
        for i, r in enumerate(records[:10], 1):
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
        lines.append("*Synthesized from compiled record metadata:*")
        lines.append("")
        for tag in sorted(tags):
            count = sum(1 for r in records if tag in r.topic_tags)
            lines.append(f"- **{tag}**: {count} source(s) address this topic")
        lines.append("")
        lines.append("### Source Quality Distribution")
        high_quality = sum(1 for r in records if r.quality_score >= 0.7)
        med_quality = sum(1 for r in records if 0.5 <= r.quality_score < 0.7)
        low_quality = sum(1 for r in records if r.quality_score < 0.5)
        lines.append(f"- High quality (>=0.7): {high_quality}")
        lines.append(f"- Medium quality (0.5-0.7): {med_quality}")
        lines.append(f"- Low quality (<0.5): {low_quality}")
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
        self.output_dir.mkdir(parents=True, exist_ok=True)
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

        # Build a unified citation graph from all candidates
        all_records = []
        for records in dossier_candidates.values():
            all_records.extend(records)
        self._citation_graph = self.build_citation_graph(all_records)

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

        if self._citation_graph:
            edge_counts = self._citation_graph.get_edge_types()
            logger.info(
                "Fit batch complete: %d dossiers generated, citation graph: %s",
                len(dossiers), edge_counts,
            )
        return dossiers

    def get_stats(self) -> Dict:
        """Return fit statistics."""
        stats = {
            "dossiers_generated": len(self._dossiers),
            "total_source_records": sum(len(d.source_records) for d in self._dossiers),
        }
        if self._citation_graph:
            edge_counts = self._citation_graph.get_edge_types()
            stats["citation_edges"] = sum(edge_counts.values())
            for etype, count in edge_counts.items():
                stats[f"citation_{etype}"] = count
        return stats

    def get_citation_graph(self) -> Optional[CitationGraph]:
        """Return the citation graph from the last fit_batch call."""
        return self._citation_graph

    def get_citation_graph_yaml(self) -> str:
        """Return the citation graph as YAML string."""
        if self._citation_graph:
            return self._citation_graph.to_yaml()
        return "citation_graph: []"

    def get_dossier_paths(self) -> List[Path]:
        """Return paths of all generated dossier files."""
        return list(self.output_dir.glob("dossier_*.md"))
