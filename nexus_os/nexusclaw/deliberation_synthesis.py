"""nexusclaw/deliberation_synthesis.py — Structured Deliberation Synthesis

Upgrades the heuristic deliberation_synthesize() from brainstorm.py with:
  1. Pydantic models for structured deliberation output
  2. Schema-based synthesis using ModelRelay (when available)
  3. Heuristic fallback when ModelRelay is unavailable

Usage:
    synth = DeliberationSynthesizer()
    result = synth.synthesize(proposal, trajectories)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from nexus_os.nexusclaw.heavyskill_relay import (
    ModelRelayHeavySkill,
    get_heavy_relay,
    TrajectoryScore,
    SynthesisOutput as RelaySynthesisOutput,
)

logger = logging.getLogger(__name__)


# ── Structured Deliberation Models ─────────────────────────────────────────────


class SynthesisVerdict(str, Enum):
    APPROVE = "approve"
    APPROVE_WITH_CONCERNS = "approve_with_concerns"
    NEEDS_REVISION = "needs_revision"
    REJECT = "reject"
    INCONCLUSIVE = "inconclusive"


@dataclass
class TrajectoryEvaluation:
    trajectory_id: str
    agent_name: str
    reasoning_text: str
    emphasis: str
    score: float
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    verdict: SynthesisVerdict = SynthesisVerdict.INCONCLUSIVE


@dataclass
class StructuredDeliberation:
    proposal_id: str
    proposal_title: str
    verdict: SynthesisVerdict
    final_confidence: float
    synthesized_answer: str
    trajectories_used: int
    consensus_points: List[str] = field(default_factory=list)
    remaining_concerns: List[str] = field(default_factory=list)
    cross_validation_notes: List[str] = field(default_factory=list)
    answer_distribution: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "proposal_title": self.proposal_title,
            "verdict": self.verdict.value,
            "final_confidence": self.final_confidence,
            "synthesized_answer": self.synthesized_answer,
            "trajectories_used": self.trajectories_used,
            "consensus_points": self.consensus_points,
            "remaining_concerns": self.remaining_concerns,
            "cross_validation_notes": self.cross_validation_notes,
            "answer_distribution": self.answer_distribution,
        }


# ── Synthesis Config ───────────────────────────────────────────────────────────


@dataclass
class SynthesisConfig:
    approve_confidence_threshold: float = 0.7
    approval_ratio_threshold: float = 0.55
    high_confidence_majority_pct: float = 0.5
    critical_confidence_requirement: float = 0.75
    min_consensus_points: int = 2
    use_model_relay: bool = True
    max_synthesis_length: int = 2000


# ── Synthesizer ────────────────────────────────────────────────────────────────


class DeliberationSynthesizer:
    """Upgraded deliberation synthesis with structured schemas and ModelRelay support.

    Two modes:
    1. ModelRelay mode: Uses LLM to synthesize trajectories (rich output)
    2. Heuristic mode: Falls back to confidence-based synthesis (always available)
    """

    def __init__(
        self,
        config: Optional[SynthesisConfig] = None,
        relay: Optional[ModelRelayHeavySkill] = None,
    ) -> None:
        self.config = config or SynthesisConfig()
        self._relay = relay

    # ── Relay access ───────────────────────────────────────────────

    def _get_relay(self) -> Optional[ModelRelayHeavySkill]:
        if self._relay is None and self.config.use_model_relay:
            self._relay = get_heavy_relay()
        return self._relay

    # ── Public API ─────────────────────────────────────────────────

    def synthesize(
        self,
        proposal_id: str,
        proposal_title: str,
        proposal_desc: str,
        trajectories: List[Any],
        risk_level: Any = None,
    ) -> StructuredDeliberation:
        """Synthesize trajectories into a structured deliberation result.

        Args:
            proposal_id: Unique proposal identifier.
            proposal_title: Human-readable title.
            proposal_desc: Full description.
            trajectories: List of ParallelTrajectory objects (from brainstorm.py).
            risk_level: Optional RiskLevel enum for severity-aware synthesis.

        Returns:
            StructuredDeliberation with verdict, confidence, and structured fields.
        """
        if not trajectories:
            return StructuredDeliberation(
                proposal_id=proposal_id,
                proposal_title=proposal_title,
                verdict=SynthesisVerdict.INCONCLUSIVE,
                final_confidence=0.0,
                synthesized_answer="No trajectories available for synthesis.",
                trajectories_used=0,
                cross_validation_notes=["Insufficient reasoning trajectories."],
                remaining_concerns=["No trajectories to evaluate."],
            )

        # Convert trajectory objects to evaluation format
        evaluations = self._evaluate_trajectories(trajectories)

        # Try ModelRelay synthesis first
        relay = self._get_relay()
        if relay and relay.check_availability():
            result = self._synthesize_via_relay(relay, proposal_title, proposal_desc, evaluations)
            if result is not None:
                return result

        # Fallback: heuristic synthesis
        return self._synthesize_heuristic(proposal_id, proposal_title, evaluations, risk_level)

    # ── Trajectory Evaluation ──────────────────────────────────────

    def _evaluate_trajectories(
        self,
        trajectories: List[Any],
    ) -> List[TrajectoryEvaluation]:
        """Convert raw trajectory objects to evaluated format."""
        evaluations: List[TrajectoryEvaluation] = []
        for i, traj in enumerate(trajectories):
            emphasis = traj.metadata.get("emphasis", "general") if hasattr(traj, "metadata") and traj.metadata else "general"
            score = getattr(traj, "confidence", 0.5)
            text = getattr(traj, "reasoning_text", "")

            # Determine verdict per trajectory
            if score >= self.config.approve_confidence_threshold:
                verdict = SynthesisVerdict.APPROVE
            elif score >= self.config.approve_confidence_threshold * 0.7:
                verdict = SynthesisVerdict.APPROVE_WITH_CONCERNS
            elif score >= 0.3:
                verdict = SynthesisVerdict.NEEDS_REVISION
            else:
                verdict = SynthesisVerdict.REJECT

            evaluations.append(TrajectoryEvaluation(
                trajectory_id=getattr(traj, "trajectory_id", f"traj-{i}"),
                agent_name=getattr(traj, "agent_name", "unknown"),
                reasoning_text=text,
                emphasis=emphasis,
                score=score,
                verdict=verdict,
            ))
        return evaluations

    # ── ModelRelay Synthesis ───────────────────────────────────────

    def _synthesize_via_relay(
        self,
        relay: ModelRelayHeavySkill,
        proposal_title: str,
        proposal_desc: str,
        evaluations: List[TrajectoryEvaluation],
    ) -> Optional[StructuredDeliberation]:
        """Use ModelRelay to generate a structured synthesis."""
        traj_texts = [
            f"[{e.agent_name}] (score={e.score:.2f}, verdict={e.verdict.value})\n{e.reasoning_text[:500]}"
            for e in evaluations
        ]
        traj_scores = [
            TrajectoryScore(trajectory_id=e.trajectory_id, score=e.score)
            for e in evaluations
        ]

        output = relay.synthesize(proposal_title, proposal_desc, traj_texts, traj_scores)
        if output is None:
            return None

        # Map relay output to structured deliberation
        verdict = self._compute_verdict(output.final_confidence, output.remaining_concerns)
        answer_dist = self._compute_answer_distribution(evaluations)

        return StructuredDeliberation(
            proposal_id="relay-synthesis",
            proposal_title=proposal_title,
            verdict=verdict,
            final_confidence=output.final_confidence,
            synthesized_answer=output.synthesized_answer,
            trajectories_used=len(evaluations),
            consensus_points=output.consensus_points,
            remaining_concerns=output.remaining_concerns,
            cross_validation_notes=output.cross_validation_notes,
            answer_distribution=answer_dist,
        )

    # ── Heuristic Synthesis (Fallback) ─────────────────────────────

    def _synthesize_heuristic(
        self,
        proposal_id: str,
        proposal_title: str,
        evaluations: List[TrajectoryEvaluation],
        risk_level: Any = None,
    ) -> StructuredDeliberation:
        """Heuristic fallback synthesis using trajectory scores and metadata."""
        n = len(evaluations)
        scores = [e.score for e in evaluations]
        high_conf_count = sum(1 for s in scores if s > self.config.approve_confidence_threshold)

        # Answer distribution
        answer_dist: Dict[str, int] = {}
        verdict_counts: Dict[str, int] = {}
        for e in evaluations:
            verdict_counts[e.verdict.value] = verdict_counts.get(e.verdict.value, 0) + 1
        answer_dist = verdict_counts

        # Cross-validation
        cross_notes: List[str] = []
        if high_conf_count >= n * self.config.high_confidence_majority_pct:
            cross_notes.append(f"Majority ({high_conf_count}/{n}) show high confidence (>={self.config.approve_confidence_threshold}).")
        else:
            cross_notes.append(f"Only {high_conf_count}/{n} show high confidence.")

        emphases = {e.emphasis for e in evaluations}
        if len(emphases) >= 3:
            cross_notes.append(f"Diverse emphasis ({len(emphases)} angles).")

        # Identify concerns
        concerns: List[str] = []
        if high_conf_count < n * 0.75:
            concerns.append("Insufficient high-confidence trajectories for decisive synthesis.")

        # Risk escalation
        if risk_level is not None:
            risk_name = getattr(risk_level, "value", str(risk_level)).upper()
            if risk_name in ("CRITICAL", "HIGH") and high_conf_count < n * self.config.critical_confidence_requirement:
                concerns.append(f"{risk_name} proposal lacks sufficient high-confidence approval.")

        # Weighted final score
        total_weight = sum(scores)
        approve_weight = sum(s for s in scores if s > self.config.approve_confidence_threshold)
        approval_ratio = approve_weight / total_weight if total_weight > 0 else 0.0

        # Verdict and answer
        verdict = self._compute_verdict(approval_ratio, concerns)
        if verdict in (SynthesisVerdict.APPROVE, SynthesisVerdict.APPROVE_WITH_CONCERNS):
            answer = (
                f"Synthesis {verdict.value.upper()} proposal '{proposal_title}'. "
                f"Approval ratio: {approval_ratio:.2f} (threshold: {self.config.approval_ratio_threshold}). "
                f"{len(cross_notes)} validation notes, {len(concerns)} concerns."
            )
            final_conf = approval_ratio
        else:
            answer = (
                f"Synthesis {verdict.value.upper()} proposal '{proposal_title}'. "
                f"Approval ratio: {approval_ratio:.2f} (threshold: {self.config.approval_ratio_threshold}). "
                f"{len(cross_notes)} validation notes, {len(concerns)} concerns."
            )
            final_conf = 1.0 - approval_ratio

        return StructuredDeliberation(
            proposal_id=proposal_id,
            proposal_title=proposal_title,
            verdict=verdict,
            final_confidence=max(0.0, min(1.0, final_conf)),
            synthesized_answer=answer,
            trajectories_used=n,
            consensus_points=[],  # Not available in heuristic mode
            remaining_concerns=concerns,
            cross_validation_notes=cross_notes,
            answer_distribution=answer_dist,
        )

    # ── Helpers ────────────────────────────────────────────────────

    def _compute_verdict(
        self,
        confidence: float,
        concerns: List[str],
    ) -> SynthesisVerdict:
        if confidence >= self.config.approve_confidence_threshold and not concerns:
            return SynthesisVerdict.APPROVE
        elif confidence >= self.config.approve_confidence_threshold:
            return SynthesisVerdict.APPROVE_WITH_CONCERNS
        elif confidence >= self.config.approval_ratio_threshold:
            return SynthesisVerdict.NEEDS_REVISION
        elif confidence > 0.2:
            return SynthesisVerdict.REJECT
        return SynthesisVerdict.INCONCLUSIVE

    def _compute_answer_distribution(
        self,
        evaluations: List[TrajectoryEvaluation],
    ) -> Dict[str, int]:
        dist: Dict[str, int] = {}
        for e in evaluations:
            dist[e.verdict.value] = dist.get(e.verdict.value, 0) + 1
        return dist
