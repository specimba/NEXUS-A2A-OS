"""Deterministic PDF source-card creation."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any


LANE_RULES = (
    (("memlineage", "memory injection", "murmur", "ghost in the agent"), "vault_memory_security"),
    (("sponge tool", "agentpoison", "unic-rag", "stealth lens"), "internal_ai_stress_lab"),
    (("vulnagent", "bountybench", "agentcyberrange", "autobax", "sec-bench", "securevibe", "exploitgym"), "cyber_evaluation"),
    (("vibethinker", "entropy bounds", "indexcache", "variable-width"), "model_efficiency"),
    (("gpt-5-6", "fable", "mythos", "metr"), "frontier_claim_audit"),
)


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def lane_for_paper(path: Path) -> str:
    name = path.stem.casefold()
    for terms, lane in LANE_RULES:
        if any(term in name for term in terms):
            return lane
    return "research_intake"


def _extract_body(path: Path, max_pages: int = 2) -> tuple[str, str | None]:
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        if reader.is_encrypted:
            return "", "encrypted_pdf"
        text = " ".join((page.extract_text() or "") for page in reader.pages[:max_pages])
        return " ".join(text.split()), None
    except Exception as exc:
        return "", f"{type(exc).__name__}: {exc}"


def build_paper_card(path: Path, *, event_id: str) -> dict[str, Any]:
    body, error = _extract_body(path)
    evidence_grade = "E1" if len(body) >= 80 else "E0"
    title = path.stem
    frontier = any(term in title.casefold() for term in ("gpt-5-6", "fable", "mythos", "metr"))
    return {
        "event_id": event_id,
        "title": title,
        "source_path": str(path),
        "source_hash": file_sha256(path),
        "source_type": "official_system_card" if title.casefold() == "gpt-5-6-preview" else "academic_or_preprint",
        "target_lane": lane_for_paper(path),
        "evidence_grade": evidence_grade,
        "body_claim": body[:500] if evidence_grade == "E1" else "",
        "contradiction_status": "requires_primary_source_reconciliation" if frontier else "unreviewed",
        "adoption_gate": "operator_review_before_canonical_promotion",
        "extraction_error": error,
        "promotable": evidence_grade != "E0",
    }
