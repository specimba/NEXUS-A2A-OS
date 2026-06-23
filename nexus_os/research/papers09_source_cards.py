"""Source-card helpers for ARCHIVIST PAPERS/papers09 intake.

This module intentionally separates draft filename inventory from promotable
paper evidence. A paper is not promotable until it has a body-derived claim,
hash, target NEXUS lane, and adoption gate.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
from pathlib import Path
from typing import Iterable


PRIORITY_TITLES = (
    "VibeThinker-3B",
    "FastContext",
    "Nanbeige4.1-3B",
    "TFPI",
    "LongCat-Flash-Thinking",
    "SWE-LEGO",
    "GUARD-SLM",
    "SafeDecoding",
    "Reasoned Safety Alignment",
    "Context Compression",
    "AllMem",
    "Hybrid Associative Memories",
)


LANE_HINTS = {
    "VibeThinker-3B": "smart_math_coding",
    "FastContext": "repo_explorer",
    "Nanbeige4.1-3B": "small_model_probe",
    "TFPI": "reasoning_policy",
    "LongCat-Flash-Thinking": "teacher_probe",
    "SWE-LEGO": "heavyskill_reviewer",
    "GUARD-SLM": "guard_bouncer",
    "SafeDecoding": "guard_bouncer",
    "Reasoned Safety Alignment": "behavior_control_lab",
    "Context Compression": "vault_memory",
    "AllMem": "vault_memory",
    "Hybrid Associative Memories": "vault_memory",
}


@dataclass(frozen=True)
class PaperSourceCard:
    """Evidence card for one papers09 file."""

    title: str
    source_path: str
    sha256: str
    target_lane: str
    evidence_grade: str
    body_claim: str
    adoption_gate: str

    @property
    def promotable(self) -> bool:
        return bool(self.body_claim.strip()) and self.evidence_grade not in {"E0", "draft"}

    def to_dict(self) -> dict[str, str | bool]:
        data = asdict(self)
        data["promotable"] = self.promotable
        return data


def hash_file(path: Path) -> str:
    """Return SHA256 for a source file."""

    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def lane_for_title(title: str) -> str:
    """Map a known priority title to a NEXUS lane."""

    for key, lane in LANE_HINTS.items():
        if key.lower() in title.lower():
            return lane
    return "research_intake"


def create_draft_card(path: Path) -> PaperSourceCard:
    """Create a non-promotable draft source card from a file path."""

    return PaperSourceCard(
        title=path.stem,
        source_path=str(path),
        sha256=hash_file(path),
        target_lane=lane_for_title(path.stem),
        evidence_grade="E0",
        body_claim="",
        adoption_gate="body_read_required_before_architecture_promotion",
    )


def promote_card(card: PaperSourceCard, *, body_claim: str, evidence_grade: str = "E1") -> PaperSourceCard:
    """Return a promotable card after a body-read claim is supplied."""

    if not body_claim.strip():
        raise ValueError("body_claim is required before promotion")
    if evidence_grade == "E0":
        raise ValueError("E0 filename-only evidence cannot be promoted")
    return PaperSourceCard(
        title=card.title,
        source_path=card.source_path,
        sha256=card.sha256,
        target_lane=card.target_lane,
        evidence_grade=evidence_grade,
        body_claim=body_claim.strip(),
        adoption_gate=card.adoption_gate,
    )


def iter_priority_paths(root: Path) -> Iterable[Path]:
    """Yield priority papers from a papers09 folder in deterministic order."""

    files = sorted(path for path in root.iterdir() if path.is_file())
    for title in PRIORITY_TITLES:
        lowered = title.lower()
        for path in files:
            if lowered in path.stem.lower():
                yield path
                break
