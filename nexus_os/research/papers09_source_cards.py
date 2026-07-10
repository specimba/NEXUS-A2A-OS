"""Source-card helpers for ARCHIVIST PAPERS intake.

This module intentionally separates draft filename inventory from promotable
paper evidence. A paper is not promotable until it has a body-derived claim,
hash, target NEXUS lane, and adoption gate.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
from pathlib import Path
from typing import Iterable


PAPERS09_PRIORITY_TITLES = (
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


PAPERS10_PRIORITY_TITLES = (
    "Fugu_technical_report",
    "FastContext",
    "GLM-5 from Vibe Coding to Agentic Engineering",
    "Agent Security Bench",
    "A Survey of LLM-based Deep Search Agents",
    "Deep Research Agents",
    "Context Compression",
    "AllMem",
    "GUARD-SLM",
    "SafeDecoding",
    "Reasoned Safety Alignment",
    "Claw-Eval",
    "Progent",
    "CommandSans",
    "TRINITY",
    "VERGE",
    "VERIWEB",
    "Learning to Route Among Specialized Experts",
    "Training Long-Context, Multi-Turn Software",
    "SWE-LEGO",
    "VibeThinker-3B",
    "Nanbeige4.1-3B",
)
PAPERS12_13_PRIORITY_TITLES = (
    "Antislop",
    "Can Editing 1 Neuron Fix Repetition Loops",
    "Efficient Memory Management",
    "Benchmarking and Intervention-Based Auditing",
    "Anomaly Detection with Multimodal",
    "GUARD Glocal Uncertainty-Aware Robust Decoding",
    "p-LESS SAMPLING",
    "Min-k Sampling",
    "A Survey on Evaluation of LLM-based Agents",
    "Beyond Quantity Trajectory Diversity Scaling for Code Agents",
    "BOOSTER TACKLING HARMFUL FINE-TUNING",
    "Breaking Entropy Bounds",
    "CAR-bench",
    "CIRRUSBENCH",
    "DeepSeek-V4",
    "EAGLE Speculative Sampling",
)
PRIORITY_TITLES = PAPERS09_PRIORITY_TITLES + tuple(
    title for title in PAPERS10_PRIORITY_TITLES + PAPERS12_13_PRIORITY_TITLES if title not in PAPERS09_PRIORITY_TITLES
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

    "Fugu": "free_cloud_model_relay",
    "GLM-5": "modal_teacher_probe",
    "Agent Security Bench": "internal_ai_stress_lab",
    "Deep Research": "research_systems",
    "Progent": "guard_bouncer",
    "CommandSans": "guard_bouncer",
    "TRINITY": "nexusclaw_coordinator",
    "VERGE": "verification",
    "VERIWEB": "browser_ai_eval",
    "Learning to Route": "modelrelay_router",
    "Training Long-Context": "heavyskill_reviewer",
    "Antislop": "model_quality_anti_slop",
    "Repetition Loops": "decoding_repetition_control",
    "Efficient Memory Management": "vault_memory",
    "Intervention-Based Auditing": "vap_audit",
    "Anomaly Detection": "monitoring_anomaly_detection",
    "Glocal Uncertainty-Aware Robust Decoding": "robust_decoding",
    "p-LESS": "robust_decoding",
    "Min-k Sampling": "robust_decoding",
    "Evaluation of LLM-based Agents": "agent_eval",
    "Trajectory Diversity": "code_agent_training",
    "BOOSTER": "safety_finetune",
    "Breaking Entropy Bounds": "inference_acceleration",
    "CAR-bench": "agent_eval",
    "CIRRUSBENCH": "agent_eval",
    "DeepSeek-V4": "modelrelay_provider",
    "EAGLE": "inference_acceleration",
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



def create_promoted_card_from_body(
    path: Path,
    *,
    body_text: str,
    evidence_grade: str = "E1",
) -> PaperSourceCard:
    """Create a promotable source card from a bounded body-read excerpt.

    The body text must come from extracted PDF text, a trusted sidecar, or a
    manually reviewed excerpt. Filename-only evidence must use
    ``create_draft_card`` instead.
    """

    excerpt = " ".join(body_text.strip().split())
    if len(excerpt) < 80:
        raise ValueError("body_text excerpt is too short for E1 promotion")
    claim = excerpt[:360]
    if len(excerpt) > 360:
        claim += "..."
    return promote_card(create_draft_card(path), body_claim=claim, evidence_grade=evidence_grade)


def create_backlog_cards(root: Path, *, priority_titles: Iterable[str] = PRIORITY_TITLES) -> list[PaperSourceCard]:
    """Create deterministic non-promoted cards for a papers folder."""

    return [create_draft_card(path) for path in iter_priority_paths(root, priority_titles=priority_titles)]


def _match_key(value: str) -> str:
    """Normalize paper titles for filename matching across spaces/underscores."""

    return " ".join(value.replace("_", " ").replace("-", " ").lower().split())


def iter_priority_paths(root: Path, *, priority_titles: Iterable[str] = PRIORITY_TITLES) -> Iterable[Path]:
    """Yield priority papers from a papers folder in deterministic order."""

    files = sorted(path for path in root.iterdir() if path.is_file())
    matched: set[Path] = set()
    for title in priority_titles:
        lowered = _match_key(title)
        for path in files:
            if path in matched:
                continue
            if lowered in _match_key(path.stem):
                matched.add(path)
                yield path
                break




