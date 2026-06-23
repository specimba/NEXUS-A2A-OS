"""Evidence matrix primitives for NexusClaw Core V0 intake."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class EvidenceDisposition(str, Enum):
    VERIFIED = "verified"
    REFRAMED = "reframed"
    SUSPECT = "suspect"
    REJECTED = "rejected"
    DEFERRED = "deferred"


@dataclass(frozen=True)
class EvidenceClaim:
    artifact: str
    claim: str
    disposition: EvidenceDisposition
    rationale: str

    def to_dict(self) -> dict[str, str]:
        return {
            "artifact": self.artifact,
            "claim": self.claim,
            "disposition": self.disposition.value,
            "rationale": self.rationale,
        }


def default_nexusclaw_evidence_matrix() -> list[EvidenceClaim]:
    """Return the V0 evidence matrix for the listed Downloads/GROSS inputs.

    The matrix is intentionally secret-free. It names artifacts and claim
    classes only; it does not copy token material or raw Downloads content.
    """

    return [
        EvidenceClaim(
            artifact="NEXUS_GROSS_MASTER_MOVEMENT_PLAN_V7.md",
            claim="NexusClaw should coordinate Tailscale, MCP, A2A, NemoClaw/OpenClaw runtime, and NEXUS governance.",
            disposition=EvidenceDisposition.REFRAMED,
            rationale="Useful architecture direction, but NEXUS must remain the KAIJU/VAP/Vault authority.",
        ),
        EvidenceClaim(
            artifact="NEXUS_GROSS_MASTER_MOVEMENT_PLAN_V7.md",
            claim="Deletion, quantum, livestream, purge, or self-remediation claims are proven.",
            disposition=EvidenceDisposition.REJECTED,
            rationale="Operational claims require independent filesystem/network evidence and operator approval.",
        ),
        EvidenceClaim(
            artifact="GROSSantigravitygeminiopuslogs-05.txt",
            claim="Antigravity logs provide roadmap ideas for browser-source Grok investigation.",
            disposition=EvidenceDisposition.REFRAMED,
            rationale="Strategic ideas can inform tasks, but auto-proceed behavior and created-plan claims are contaminated.",
        ),
        EvidenceClaim(
            artifact="NEXUSubuntuHERMESlog-01.txt",
            claim="Hermes WSL is a useful planner/delegator surface but not a stable default router.",
            disposition=EvidenceDisposition.VERIFIED,
            rationale="Provider failures must fast-fail degraded; Grok success does not make Hermes default-safe.",
        ),
        EvidenceClaim(
            artifact="NEXUSbenchmarkMODELresearchlog-01.txt",
            claim="Broad model relay health checks can load Ollama runners and exceed the 8GB VRAM envelope.",
            disposition=EvidenceDisposition.VERIFIED,
            rationale="ModelRelay discovery must remain lazy, opt-in, and cheap.",
        ),
        EvidenceClaim(
            artifact="NEXUSbackendOPENCODEm3log-01.txt",
            claim="OpenCode/KiloCode adapters are useful if routed through governed task envelopes.",
            disposition=EvidenceDisposition.REFRAMED,
            rationale="Adapters should receive bounded tasks, not raw all-filesystem or remote stdio access.",
        ),
        EvidenceClaim(
            artifact="NEXUSdockerGORDONlog-01.txt",
            claim="Docker Gordon should become a profile manager.",
            disposition=EvidenceDisposition.REFRAMED,
            rationale="Profiles core, mcp-light, observability, and ai-tools reduce background churn.",
        ),
        EvidenceClaim(
            artifact="RESEARCHclawllmhighvaluepapers.txt",
            claim="Research papers may inform hardening gates and model intake policy.",
            disposition=EvidenceDisposition.DEFERRED,
            rationale="Raw research dumps require governed intake before changing canonical policy.",
        ),
        EvidenceClaim(
            artifact="RESEARCHselective Forgetting in Deep Networks.txt",
            claim="Selective-forgetting research can directly change runtime governance.",
            disposition=EvidenceDisposition.DEFERRED,
            rationale="Needs brief, evidence refs, and threat-model mapping before implementation.",
        ),
        EvidenceClaim(
            artifact="megaLinkModelPaperdump-01.txt",
            claim="Bulk model/paper dumps are trusted model supply-chain sources.",
            disposition=EvidenceDisposition.SUSPECT,
            rationale="Model intake requires quarantine; no trust_remote_code, pickle, or unsafe torch load paths.",
        ),
        EvidenceClaim(
            artifact="nexus_os_architecture_upgrades_synthesis.md",
            claim="Architecture synthesis can inform NexusClaw expansion phases.",
            disposition=EvidenceDisposition.REFRAMED,
            rationale="Expansion must follow V0 dry-run validation and governance gates.",
        ),
        EvidenceClaim(
            artifact="NEXUSforks-01.txt",
            claim="Fork inventory is canonical repo state.",
            disposition=EvidenceDisposition.DEFERRED,
            rationale="Fork claims require live git/remote verification before becoming canonical state.",
        ),
        EvidenceClaim(
            artifact="archivist/NEXUS-CLAW-01.txt",
            claim="NemoClaw/OpenClaw can be installed as the default NexusClaw runtime.",
            disposition=EvidenceDisposition.REFRAMED,
            rationale="WSL, port, GPU, egress, VAP, KAIJU, and provenance collisions require native NEXUSCLAW coordination first.",
        ),
        EvidenceClaim(
            artifact="archivist/PLAN.md",
            claim="NexusClaw Core V0 should remain a thin governed coordinator with dry-run dispatch.",
            disposition=EvidenceDisposition.VERIFIED,
            rationale="Matches implemented V0 scope: governed envelopes, no cloud fallback, no broad polling, and no remote stdio.",
        ),
        EvidenceClaim(
            artifact="archivist/nexus-os-v2-dualmode-distribution",
            claim="Strict/frontier mode and evidence-gated promotion are useful trust-kernel inputs.",
            disposition=EvidenceDisposition.REFRAMED,
            rationale="Useful research artifact, but simple scalar thresholds must not replace NEXUS trust and memory formulations.",
        ),
        EvidenceClaim(
            artifact="archivist/deepseek_data-2026-05-06/conversations.json",
            claim="DeepSeek conversation export is safe to index as normal project memory.",
            disposition=EvidenceDisposition.DEFERRED,
            rationale="Private conversation and account metadata require explicit intake, redaction, and provenance handling.",
        ),
        EvidenceClaim(
            artifact="Downloads credential-shaped artifacts",
            claim="Terminal JWTs, API key files, client properties, and SSH keys can be copied into repo evidence docs.",
            disposition=EvidenceDisposition.REJECTED,
            rationale="Secret-bearing artifacts must stay out of commits, docs, cloud sync, and automation summaries.",
        ),
    ]


def wiki_lookup(claim: EvidenceClaim, limit: int = 5) -> list[dict[str, str]]:
    """Search the wiki for pages relevant to an evidence claim.

    Uses the wiki_pipeline's keyword search to find related dossiers
    and wiki pages. Returns a list of dicts with 'slug' and 'title' keys.

    Falls back gracefully if wiki pipeline is unavailable.
    """
    try:
        from nexus_cli_ctl.integrations.wiki_pipeline import get_wiki_pipeline
        pipeline = get_wiki_pipeline()
        # Search using the claim's artifact name and keywords
        query_parts = claim.artifact.split()
        query = " ".join(query_parts[:3])  # Use first 3 terms
        results = pipeline.search(query, limit=limit)
        return [{"slug": r.get("slug", ""), "title": r.get("title", "")} for r in results]
    except Exception:
        return []  # Graceful fallback when wiki is unavailable
