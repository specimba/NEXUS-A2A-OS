"""nexus_os/nexusclaw/research_synthesis.py - Deep Research Integration for NEXUSCLAW.

Phase D1: Integrates ARCHIVIST research dossiers into deliberation workflows.
Evidence-grounded reasoning with BLAKE3-verified research sources.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from nexus_os.nexusclaw.brainstorm import BrainstormEngine, RiskLevel


# ── Research Evidence Types ─────────────────────────────────────────────────────────

@dataclass
class ResearchFinding:
    """A single research finding from ARCHIVIST sources."""
    finding_id: str
    source_file: str
    source_url: Optional[str]
    blake3_hash: str
    content: str
    relevance_score: float = 0.0
    domain: str = "general"
    extracted_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ResearchDossier:
    """Collection of related research findings."""
    dossier_id: str
    title: str
    source_path: str
    findings: List[ResearchFinding] = field(default_factory=list)
    synthesis: Optional[str] = None
    synthesized_at: Optional[str] = None


# ── Research Integration Engine ────────────────────────────────────────────────────

class ResearchIntegrationEngine:
    """Integrates ARCHIVIST research into NEXUSCLAW deliberations."""

    # Key research directories
    ARCHIVIST_ROOT = Path("C:/Users/speci.000/Downloads/ARCHIVIST")
    RESEARCH_DOSSIERS = [
        "nexusreddeepresearchOPENAIGPT55-01.md",
        "nexusreddeepresearchOPENAIGPT55-02.md",
        "nexusreddeepresearchOPENAIGPT55-03.md",
        "DeepWiki_MCP_Integration_Report.md",
        "NEXUS_SWARM_INTELLIGENCE_COORDINATION_REPORT.md",
    ]

    def __init__(self, vault_path: Optional[Path] = None):
        self.vault_path = vault_path or Path("vault")
        self._cache: Dict[str, ResearchDossier] = {}

    def _blake3(self, data: bytes) -> str:
        try:
            import blake3
            return blake3.blake3(data).hexdigest()
        except ImportError:
            return hashlib.sha256(data).hexdigest()

    def load_dossier(self, filename: str) -> ResearchDossier:
        """Load and parse a research dossier from ARCHIVIST."""
        if filename in self._cache:
            return self._cache[filename]

        source_path = self.ARCHIVIST_ROOT / filename
        if not source_path.exists():
            return ResearchDossier(
                dossier_id=f"dossier-{uuid4().hex[:8]}",
                title=filename,
                source_path=str(source_path),
            )

        content = source_path.read_text(encoding="utf-8", errors="replace")
        finding = ResearchFinding(
            finding_id=f"finding-{uuid4().hex[:8]}",
            source_file=filename,
            source_url=None,
            blake3_hash=self._blake3(content.encode("utf-8")),
            content=content[:2000],  # Truncate for memory
            relevance_score=0.95,
            domain="deep_research",
        )

        dossier = ResearchDossier(
            dossier_id=f"dossier-{uuid4().hex[:8]}",
            title=filename.replace(".md", "").replace("_", " "),
            source_path=str(source_path),
            findings=[finding],
        )
        self._cache[filename] = dossier
        return dossier

    def synthesize_for_proposal(
        self,
        brainstorm: BrainstormEngine,
        session_id: str,
        proposal_id: str,
    ) -> str:
        """Generate research-backed synthesis for a proposal."""
        # Load relevant research
        relevant_findings = []
        for dossier_file in self.RESEARCH_DOSSIERS[:3]:
            dossier = self.load_dossier(dossier_file)
            if dossier.findings:
                relevant_findings.extend(dossier.findings[:2])

        if not relevant_findings:
            return "No relevant research available for synthesis."

        # Build synthesis
        synthesis_parts = [f"Research synthesis ({len(relevant_findings)} findings):"]
        for f in relevant_findings:
            synthesis_parts.append(f"- {f.source_file}: {f.blake3_hash[:16]}...")

        synthesis = "\n".join(synthesis_parts)

        # Log to EPISODIC
        from nexus_os.vault.memory_channels import get_manager
        manager = get_manager()
        manager.append_episodic(
            "research-synthesizer",
            f"Synthesis for {proposal_id}: {synthesis}",
            "success",
            0.0,
            0,
        )

        return synthesis

    def get_model_capabilities_report(self) -> Dict[str, Any]:
        """Extract model capability insights from research archives."""
        model_report = {
            "sources": [],
            "capabilities": {},
            "risk_scores": {},
        }

        model_guru_path = self.ARCHIVIST_ROOT / "MODEL GURU.txt"
        if model_guru_path.exists():
            content = model_guru_path.read_text(encoding="utf-8", errors="replace")
            model_report["sources"].append({
                "file": "MODEL GURU.txt",
                "blake3": self._blake3(content.encode("utf-8")),
            })

        return model_report

    def get_security_patterns(self) -> List[Dict[str, Any]]:
        """Extract security patterns from DERDDRE reports."""
        patterns = []

        derddre_path = self.ARCHIVIST_ROOT / "DERDDRE_ATTACKS_WRITEUP.md"
        if derddre_path.exists():
            content = derddre_path.read_text(encoding="utf-8", errors="replace")
            patterns.append({
                "pattern_id": f"pattern-{uuid4().hex[:8]}",
                "source": "DERDDRE_ATTACKS_WRITEUP.md",
                "blake3_hash": self._blake3(content.encode("utf-8")),
                "category": "attack_pattern",
            })

        return patterns

    def query_wiki(self, topic: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search the wiki pipeline for pages matching a topic.

        Delegates to safe_wiki_search in wiki_helpers.py for the actual
        pipeline call + fallback handling.
        """
        from nexus_os.nexusclaw.wiki_helpers import safe_wiki_search
        return safe_wiki_search(topic, limit=limit)

    def enrich_findings_from_wiki(self, findings: List[ResearchFinding]) -> List[ResearchFinding]:
        """Enrich research findings with wiki cross-references.

        For each finding, searches the wiki for related pages and attaches
        the top result's slug as a cross-reference in the content.

        Args:
            findings: List of ResearchFinding objects to enrich.

        Returns:
            The same list with enriched content (wiki references appended).
        """
        for finding in findings:
            try:
                wiki_results = self.query_wiki(finding.domain, limit=1)
                if wiki_results:
                    ref = wiki_results[0]
                    finding.content += f"\n\n[Wiki ref: {ref['title']} ({ref['slug']})]"
            except Exception:
                pass  # Non-critical enrichment; skip on failure
        return findings