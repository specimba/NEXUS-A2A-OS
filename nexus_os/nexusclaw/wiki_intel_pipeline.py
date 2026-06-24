"""nexus_os/nexusclaw/wiki_intel_pipeline.py — DoppelGround → LLMwiki → intel dossiers


Unified pipeline that takes raw evidence + research synthesis output and
produces standardized, provenance-bearing wiki dossiers for Archivist/Vault.
Non-destructive: does not rewrite or delete existing wiki pages.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence

logger = logging.getLogger("nexus_os.nexusclaw.wiki_intel_pipeline")


@dataclass(frozen=True)
class DossierProvenance:
    source_artifacts: List[str]
    claim_count: int = 0
    verified_claim_count: int = 0
    rejected_claim_count: int = 0
    source_kind: str = "doc"
    channel: str = "semantic"
    trust_score_default: float = 90.0
    last_updated: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    stable_fingerprint: str = ""


@dataclass(frozen=True)
class WikiDossier:
    dossier_id: str
    title: str
    source_kind: str
    channel: str
    content: str
    provenance: DossierProvenance
    vap_integrity: Optional[str] = None
    canonical_ref: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        payload = asdict(self)
        payload["provenance"] = asdict(self.provenance)
        return payload  # type: ignore[return-value]


@dataclass(frozen=True)
class WikiEnrichmentResult:
    topic: str
    wiki_refs: List[Dict[str, str]]
    cross_ref_added: bool = False


_SOURCE_TO_CHANNEL: Dict[str, str] = {
    "rules": "trust",
    "config": "trust",
    "mission": "semantic",
    "doc": "semantic",
    "deep_research": "semantic",
    "spec": "semantic",
    "code": "procedural",
    "test": "procedural",
    "skill": "procedural",
    "rejection_example": "episodic",
    "role": "task",
    "golden_dataset": "meta",
}


def _channel_for_source_kind(source_kind: str) -> str:
    return _SOURCE_TO_CHANNEL.get(source_kind, "semantic")


def _stable_fingerprint(parts: Sequence[str]) -> str:
    import hashlib

    joined = "\u241f".join(parts)
    return hashlib.sha256(joined.encode("utf-8", errors="replace")).hexdigest()[:16]


def _normalize_title(title: str) -> str:
    cleaned = title.strip()
    cleaned = cleaned.replace("\n", " ")
    cleaned = " ".join(cleaned.split())
    return cleaned[:120] or "Untitled Dossier"


class DuplicateDossierError(Exception):
    """Raised when an idempotent write is requested but the fingerprint already exists."""


class WikiIntelPipeline:
    """Canonical DoppelGround/LLMwiki intel pipeline.

    Does not delete existing wiki pages. It writes new canonicalized dossiers
    under `wiki_output/dossiers/` with metadata front matter and summary body.
    """

    def __init__(
        self,
        wiki_output_dir: Optional[Path] = None,
        memory_dir: Optional[Path] = None,
    ) -> None:
        base = Path("docs") if Path("docs").exists() else Path(".")
        self.wiki_output_dir = wiki_output_dir or (base / "wiki" / "wiki_output" / "dossiers")
        self.memory_dir = memory_dir or (base / "wiki" / "wiki_output" / "memory")
        self._seen: set[str] = set()
        self._load_memory()

    def _load_memory(self) -> None:
        if not self.memory_dir.exists():
            self.memory_dir.mkdir(parents=True, exist_ok=True)
            return
        mem_file = self.memory_dir / "wiki_intel_memory.json"
        if not mem_file.exists() or mem_file.stat().st_size == 0:
            return
        try:
            data = json.loads(mem_file.read_text(encoding="utf-8", errors="replace"))
            self._seen.update(data.get("seen_fingerprints", []))
        except (json.JSONDecodeError, OSError) as exc:
            logger.debug("wiki intel memory load skipped: %s", exc)

    def _save_memory(self) -> None:
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        mem_file = self.memory_dir / "wiki_intel_memory.json"
        payload = json.dumps(
            {"seen_fingerprints": sorted(self._seen), "updated_at": datetime.now(timezone.utc).isoformat()},
            indent=2,
        )
        mem_file.write_text(payload, encoding="utf-8")

    def ingest_evidence_claims(self, claims: List[dict]) -> List[WikiDossier]:
        """Ingest raw evidence-claim dicts and emit per-topic dossiers."""
        buckets: Dict[str, dict] = {}
        for claim in claims:
            artifact = str(claim.get("artifact") or "").strip()
            topic = _normalize_title(artifact)
            bucket = buckets.setdefault(
                topic,
                {"claims": [], "artifacts": [], "title": topic},
            )
            bucket["claims"].append(claim)
            if artifact and artifact not in bucket["artifacts"]:
                bucket["artifacts"].append(artifact)

        return [
            self._build_dossier_from_topic(title=bucket["title"], claims=bucket["claims"], source_artifacts=bucket["artifacts"])
            for bucket in buckets.values()
        ]

    def ingest_research_synthesis(self, synthesis: dict) -> List[WikiDossier]:
        """Ingest a research synthesis payload and emit domain dossiers."""
        findings = synthesis.get("findings", []) if isinstance(synthesis, dict) else []
        if not findings:
            return []

        by_domain: Dict[str, dict] = {}
        for finding in findings:
            domain = _normalize_title(str(finding.get("domain") or finding.get("title") or "Research"))
            bucket = by_domain.setdefault(domain, {"findings": [], "artifacts": [], "title": domain})
            bucket["findings"].append(finding)
            source = str(finding.get("source") or "").strip()
            if source and source not in bucket["artifacts"]:
                bucket["artifacts"].append(source)

        return [self._build_dossier_from_synthesis(bucket["title"], bucket["findings"], bucket["artifacts"]) for bucket in by_domain.values()]

    def unify(self, evidence_claims: Optional[List[dict]] = None, research_synthesis: Optional[dict] = None) -> List[WikiDossier]:
        out: List[WikiDossier] = []
        if evidence_claims:
            out.extend(self.ingest_evidence_claims(evidence_claims))
        if research_synthesis:
            out.extend(self.ingest_research_synthesis(research_synthesis))
        return out

    def write_dossiers(self, dossiers: Sequence[WikiDossier], overwrite: bool = False) -> List[Path]:
        written: List[Path] = []
        for dossier in dossiers:
            fp = _stable_fingerprint([dossier.dossier_id, dossier.canonical_ref or dossier.title])
            if not overwrite and fp in self._seen:
                logger.debug("skip duplicate dossier %s fp=%s", dossier.dossier_id or dossier.title, fp)
                continue
            target = self.wiki_output_dir / f"{fp}_{dossier.dossier_id or 'dossier'}.md"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(self._render_dossier(dossier), encoding="utf-8")
            written.append(target)
            self._seen.add(fp)
        if written:
            self._save_memory()
        return written

    def lint(self) -> Dict[str, int]:
        counts: Dict[str, int] = {"dossiers": 0, "missing_vap": 0, "missing_canonical_ref": 0, "missing_provenance": 0}
        if not self.wiki_output_dir.exists():
            return counts
        for path in self.wiki_output_dir.glob("*.md"):
            counts["dossiers"] += 1
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if "vap_integrity:" not in text:
                counts["missing_vap"] += 1
            if "canonical_ref:" not in text:
                counts["missing_canonical_ref"] += 1
            if "source_artifacts:" not in text and "source_kind:" not in text:
                counts["missing_provenance"] += 1
        return counts

    def known_dossier_count(self) -> int:
        if not self.wiki_output_dir.exists():
            return 0
        return len(list(self.wiki_output_dir.glob("*.md")))

    def enrich_with_wiki(self, dossiers: Sequence[WikiDossier]) -> List[WikiEnrichmentResult]:
        results: List[WikiEnrichmentResult] = []
        try:
            from nexus_os.nexusclaw.wiki_helpers import safe_wiki_search
        except Exception as exc:  # pragma: no cover — optional helper
            logger.debug("wiki enrichment skipped: %s", exc)
            return results
        for dossier in dossiers:
            topic = dossier.tags[0] if dossier.tags else dossier.title
            try:
                refs = safe_wiki_search(topic, limit=2)
            except Exception:
                refs = []
            results.append(WikiEnrichmentResult(topic=topic, wiki_refs=refs, cross_ref_added=bool(refs)))
        return results

    # ------------------------------------------------------------------
    # Private builders
    # ------------------------------------------------------------------

    def _build_dossier_from_topic(self, title: str, claims: List[dict], source_artifacts: List[str]) -> WikiDossier:
        kind_guess = self._infer_kind_from_artifacts(source_artifacts)
        channel = _channel_for_source_kind(kind_guess)
        verified = sum(1 for c in claims if str(c.get("disposition", "")).lower() == "verified")
        rejected = sum(1 for c in claims if str(c.get("disposition", "")).lower() == "rejected")
        summary_lines = [
            f"# Evidence dossier: {_normalize_title(title)}\n",
            "\n",
            "## TL;DR\n",
            "\n",
            f"- Source kind: {kind_guess}\n",
            f"- Wiki channel: {channel}\n",
            f"- Claims: {len(claims)} (verified={verified}, rejected={rejected})\n",
            f"- Generators: {', '.join(source_artifacts[:5])}\n",
            "\n",
            "## Key findings\n",
            "\n",
        ]
        for claim in claims[:20]:
            disposition = str(claim.get("disposition", "")).lower()
            summary_lines.append(f"- [{disposition}] {claim.get('claim', '')}")
        summary_lines.append("\n")
        if verified < len(claims):
            summary_lines.append("## Caveats\n")
            summary_lines.append(
                "\n- Some claims are unverified, reframed, or deferred. Use this dossier as orientation, not ground truth.\n"
            )
            summary_lines.append("\n")

        return WikiDossier(
            dossier_id=_stable_fingerprint(source_artifacts + [title]),
            title=_normalize_title(title),
            source_kind=kind_guess,
            channel=channel,
            content="".join(summary_lines),
            provenance=DossierProvenance(
                source_artifacts=source_artifacts,
                claim_count=len(claims),
                verified_claim_count=verified,
                rejected_claim_count=rejected,
                source_kind=kind_guess,
                channel=channel,
                stable_fingerprint="",
            ),
            canonical_ref=f"nexus:wiki:{channel}:{_stable_fingerprint(source_artifacts)}",
        )

    def _build_dossier_from_synthesis(self, title: str, findings: List[dict], source_artifacts: List[str]) -> WikiDossier:
        kind_guess = self._infer_kind_from_artifacts(source_artifacts)
        channel = _channel_for_source_kind(kind_guess)
        lines = [
            f"# Research dossier: {_normalize_title(title)}\n",
            "\n",
            "## TL;DR\n",
            "\n",
            f"- Domain: {_normalize_title(title)}\n",
            f"- Source kind: {kind_guess}\n",
            f"- Wiki channel: {channel}\n",
            f"- Finding count: {len(findings)}\n",
            "- Generators: " + ", ".join(source_artifacts[:5]) + "\n",
            "\n",
            "## Findings\n",
            "\n",
        ]
        for f in findings[:20]:
            source = str(f.get("source") or "")
            content = str(f.get("content") or f.get("finding") or f.get("title") or "")
            if source:
                lines.append(f"- [{source}] {content}\n")
            else:
                lines.append(f"- {content}\n")
        lines.append("\n")
        refs = self.enrich_with_wiki([WikiDossier(dossier_id="", title=title, source_kind=kind_guess, channel=channel, content="".join(lines), provenance=DossierProvenance(source_artifacts=source_artifacts, stable_fingerprint=""))])  # type: ignore[arg-type]
        if refs and refs[0].wiki_refs:
            lines.append("## Wiki refs\n")
            for ref in refs[0].wiki_refs:
                lines.append(f"- {ref.get('title', 'Untitled')} ({ref.get('slug', '')})\n")
        lines.append("\n")
        return WikiDossier(
            dossier_id=_stable_fingerprint(source_artifacts + [title]),
            title=_normalize_title(title),
            source_kind=kind_guess,
            channel=channel,
            content="".join(lines),
            provenance=DossierProvenance(
                source_artifacts=source_artifacts,
                claim_count=len(findings),
                verified_claim_count=len(findings),
                source_kind=kind_guess,
                channel=channel,
                stable_fingerprint="",
            ),
            canonical_ref=f"nexus:wiki:{channel}:{_stable_fingerprint(source_artifacts)}",
        )

    def _render_dossier(self, dossier: WikiDossier) -> str:
        header = [
            "---\n",
            "wiki_dossier: true\n",
            f"dossier_id: {dossier.dossier_id}\n",
            f"title: {dossier.title}\n",
            f"source_kind: {dossier.source_kind}\n",
            f"channel: {dossier.channel}\n",
            f"canonical_ref: {dossier.canonical_ref or ''}\n",
            f"vap_integrity: {dossier.vap_integrity or 'pending'}\n",
            f"source_artifacts: {json.dumps(dossier.provenance.source_artifacts, ensure_ascii=False)}\n",
            f"claim_count: {dossier.provenance.claim_count}\n",
            f"verified_claim_count: {dossier.provenance.verified_claim_count}\n",
            f"rejected_claim_count: {dossier.provenance.rejected_claim_count}\n",
            f"trust_score_default: {dossier.provenance.trust_score_default}\n",
            f"stable_fingerprint: {dossier.provenance.stable_fingerprint or dossier.dossier_id}\n",
            f"tags: {json.dumps(dossier.tags, ensure_ascii=False)}\n",
            "generated_at: " + datetime.now(timezone.utc).isoformat() + "\n",
            "---\n",
            "\n",
        ]
        return "".join(header) + dossier.content

    @staticmethod
    def _infer_kind_from_artifacts(artifacts: List[str]) -> str:
        lowered = " ".join(artifacts).lower()
        if any(token in lowered for token in ["model", "llm", "prompt", "inference", "router", "relay"]):
            return "doc"
        if any(token in lowered for token in ["attack", "jailbreak", "redteam", "defense"]):
            return "deep_research"
        if any(token in lowered for token in ["code", "bridge", "server", "mcp"]):
            return "code"
        if any(token in lowered for token in ["paper", "research", "arxiv", "dossier"]):
            return "deep_research"
        return "doc"
