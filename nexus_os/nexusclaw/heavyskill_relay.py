"""nexusclaw/heavyskill_relay.py — HeavySkill real API adapter via ModelRelay

Replaces mock trajectory generation in brainstorm.py with real model inference
through ModelRelay. Falls back gracefully to simulation when ModelRelay is
unavailable or when no suitable model is healthy.

API:
    relay = ModelRelayHeavySkill()
    trajs = relay.generate_trajectories(proposal, agents, k=8)
    scores = relay.score_trajectories(trajs)
"""

from __future__ import annotations

import json
import logging
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

def _default_relay_url() -> str:
    import os
    port = int(os.environ.get("NODERELAY_PORT", "7350"))
    return f"http://127.0.0.1:{port}"

DEFAULT_RELAY_URL = _default_relay_url()
DEFAULT_TIMEOUT = 30.0

TRAJECTORY_EMPHASES = [
    "focus on correctness and edge cases",
    "focus on simplicity and maintainability",
    "focus on security implications",
    "focus on performance and scalability",
    "focus on compatibility with existing systems",
    "focus on cost and resource efficiency",
    "focus on testability and observability",
    "focus on governance and compliance",
]

SCORING_SYSTEM_PROMPT = (
    "You are a rigorous reasoning evaluator. Rate the following reasoning trajectory "
    "on a scale of 0.0 to 1.0 based on: logical coherence, evidence grounding, "
    "thoroughness, and novelty. Return ONLY a JSON object with keys: "
    "\"score\" (float 0-1), \"strengths\" (list of strings), "
    "\"weaknesses\" (list of strings), \"cross_validate\" (bool)."
)

SYNTHESIS_SYSTEM_PROMPT = (
    "You are a deliberation synthesis expert. Given multiple reasoning trajectories "
    "about a proposal, synthesize the best final answer. Identify consensus points, "
    "conflicts, and gaps. Return ONLY a JSON object with keys: "
    "\"synthesized_answer\" (string), \"final_confidence\" (float 0-1), "
    "\"consensus_points\" (list of strings), \"remaining_concerns\" (list of strings), "
    "\"cross_validation_notes\" (list of strings)."
)


@dataclass
class TrajectoryScore:
    trajectory_id: str
    score: float
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    cross_validate: bool = True


@dataclass
class SynthesisOutput:
    synthesized_answer: str
    final_confidence: float
    consensus_points: List[str] = field(default_factory=list)
    remaining_concerns: List[str] = field(default_factory=list)
    cross_validation_notes: List[str] = field(default_factory=list)


# ── Relay adapter ──────────────────────────────────────────────────────────────


class ModelRelayHeavySkill:
    """HeavySkill adapter that calls ModelRelay for real trajectory generation
    and scoring. Falls back to simulation when ModelRelay is unreachable.

    Uses synchronous HTTP calls to the ModelRelay API endpoint
    (POST /v1/chat/completions) to avoid asyncio complexity.
    """

    def __init__(
        self,
        relay_url: str = DEFAULT_RELAY_URL,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self._relay_url = relay_url.rstrip("/")
        self._timeout = timeout
        self._available: Optional[bool] = None  # None = unchecked

    # ── Availability ───────────────────────────────────────────────

    def check_availability(self) -> bool:
        """Check if ModelRelay is reachable."""
        if self._available is not None:
            return self._available
        try:
            req = urllib.request.Request(f"{self._relay_url}/health", method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                self._available = resp.status == 200
        except (urllib.error.URLError, OSError, ValueError):
            self._available = False
            logger.info("ModelRelay unavailable at %s — using simulation fallback", self._relay_url)
        return self._available

    def reset_availability(self) -> None:
        self._available = None

    # ── API calls ──────────────────────────────────────────────────

    def _chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "auto",
        temperature: float = 0.7,
        max_tokens: int = 512,
    ) -> Optional[str]:
        """Call proxy_completion via HTTP. Returns the content string or None."""
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                f"{self._relay_url}/v1/chat/completions",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            choices = result.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "")
        except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError) as e:
            logger.debug("ModelRelay chat completion failed: %s", e)
        return None

    def _json_completion(
        self,
        system_prompt: str,
        user_content: str,
        temperature: float = 0.3,
    ) -> Optional[Dict[str, Any]]:
        """Call ModelRelay with a JSON-format response request."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
        result = self._chat_completion(messages, temperature=temperature, max_tokens=1024)
        if not result:
            return None
        try:
            # Try to extract JSON from the response (may be wrapped in ```json ... ```)
            cleaned = result.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                cleaned = "\n".join(l for l in lines if not l.startswith("```"))
            return json.loads(cleaned)
        except (json.JSONDecodeError, TypeError) as e:
            logger.debug("JSON completion parse failed: %s", e)
            return None

    # ── Trajectory Generation ──────────────────────────────────────

    def generate_trajectory(
        self,
        proposal_title: str,
        proposal_desc: str,
        evidence_refs: List[str],
        emphasis: str,
        temperature: float = 0.7,
        model: str = "auto",
    ) -> Optional[str]:
        """Generate a single reasoning trajectory for a proposal."""
        if not self.check_availability():
            return None

        prompt = (
            f"Proposal: {proposal_title}\n\n"
            f"Description: {proposal_desc}\n\n"
            f"Evidence references: {evidence_refs}\n\n"
            f"Please analyze this proposal with the following emphasis: {emphasis}.\n\n"
            "Provide a detailed reasoning trajectory evaluating the proposal. "
            "Include: key considerations, potential issues, and your assessment."
        )
        messages = [
            {"role": "system", "content": "You are a thorough reasoning assistant performing independent trajectory analysis."},
            {"role": "user", "content": prompt},
        ]
        return self._chat_completion(messages, model=model, temperature=temperature)

    def generate_trajectories(
        self,
        proposal_title: str,
        proposal_desc: str,
        evidence_refs: List[str],
        k: int = 8,
        models: Optional[List[str]] = None,
        temperatures: Optional[List[float]] = None,
    ) -> List[Optional[str]]:
        """Generate K independent trajectories with varied parameters.

        Args:
            proposal_title: Title of the proposal.
            proposal_desc: Description.
            evidence_refs: List of evidence reference strings.
            k: Number of trajectories.
            models: List of model names to cycle through (default: ["auto"]).
            temperatures: List of temperatures to cycle through.

        Returns:
            List of trajectory text strings (None for failed generations).
        """
        models = models or ["auto"]
        temperatures = temperatures or [0.3, 0.5, 0.7, 0.9, 1.1]

        trajectories: List[Optional[str]] = []
        for i in range(k):
            emphasis = TRAJECTORY_EMPHASES[i % len(TRAJECTORY_EMPHASES)]
            model = models[i % len(models)]
            temp = temperatures[i % len(temperatures)]
            text = self.generate_trajectory(
                proposal_title, proposal_desc, evidence_refs,
                emphasis=emphasis, temperature=temp, model=model,
            )
            trajectories.append(text)
        return trajectories

    # ── Trajectory Scoring ─────────────────────────────────────────

    def score_trajectory(
        self,
        trajectory_text: str,
        trajectory_id: str = "",
    ) -> Optional[TrajectoryScore]:
        """Score a single trajectory using ModelRelay.

        Falls back to heuristic scoring if ModelRelay unavailable.
        """
        if not self.check_availability():
            return None

        data = self._json_completion(SCORING_SYSTEM_PROMPT, trajectory_text)
        if data is None:
            return None

        return TrajectoryScore(
            trajectory_id=trajectory_id,
            score=max(0.0, min(1.0, float(data.get("score", 0.5)))),
            strengths=data.get("strengths", []),
            weaknesses=data.get("weaknesses", []),
            cross_validate=bool(data.get("cross_validate", True)),
        )

    def score_trajectories(
        self,
        trajectory_texts: List[str],
        trajectory_ids: List[str],
    ) -> List[TrajectoryScore]:
        """Score multiple trajectories."""
        scores: List[TrajectoryScore] = []
        for i, text in enumerate(trajectory_texts):
            tid = trajectory_ids[i] if i < len(trajectory_ids) else f"traj-{i}"
            score = self.score_trajectory(text, tid)
            if score is None:
                # Fallback heuristic
                scores.append(TrajectoryScore(
                    trajectory_id=tid,
                    score=0.5 + (0.05 * ((-1) ** i)),
                ))
            else:
                scores.append(score)
        return scores

    # ── Deliberation Synthesis ─────────────────────────────────────

    def synthesize(
        self,
        proposal_title: str,
        proposal_desc: str,
        trajectories: List[str],
        trajectory_scores: List[TrajectoryScore],
    ) -> Optional[SynthesisOutput]:
        """Synthesize multiple trajectories into a final answer using ModelRelay.

        Returns None if ModelRelay is unavailable.
        """
        if not self.check_availability():
            return None

        traj_summary = "\n\n".join(
            f"Trajectory {i+1} (score={s.score:.2f}):\n{t[:500]}"
            for i, (t, s) in enumerate(zip(trajectories, trajectory_scores))
        )
        user_content = (
            f"Proposal: {proposal_title}\n\n"
            f"Description: {proposal_desc}\n\n"
            f"Reasoning trajectories:\n\n{traj_summary}\n\n"
            "Synthesize the best final answer from these trajectories."
        )

        data = self._json_completion(SYNTHESIS_SYSTEM_PROMPT, user_content, temperature=0.3)
        if data is None:
            return None

        return SynthesisOutput(
            synthesized_answer=data.get("synthesized_answer", ""),
            final_confidence=max(0.0, min(1.0, float(data.get("final_confidence", 0.5)))),
            consensus_points=data.get("consensus_points", []),
            remaining_concerns=data.get("remaining_concerns", []),
            cross_validation_notes=data.get("cross_validation_notes", []),
        )

    # ── Mock Fallback ──────────────────────────────────────────────

    def generate_mock_trajectory(
        self,
        agent_name: str,
        proposal_title: str,
        proposal_desc: str,
        evidence_refs: List[str],
        trust_score: float,
        index: int,
        k: int,
    ) -> str:
        """Fallback: generate a simulated trajectory without ModelRelay."""
        emphasis = TRAJECTORY_EMPHASES[index % len(TRAJECTORY_EMPHASES)]
        return (
            f"[Trajectory {index+1}/{k} by {agent_name}] "
            f"Analyzing proposal '{proposal_title}' with emphasis: {emphasis}.\n\n"
            f"Proposal: {proposal_desc[:500]}\n\n"
            f"Reasoning: Starting from the evidence references {evidence_refs}, "
            f"this trajectory evaluates the proposal through the lens of {emphasis}. "
            f"Initial assessment: the proposal has merit but requires verification."
        )

    def score_mock(
        self,
        trust_score: float,
        trajectory_index: int,
    ) -> float:
        """Fallback: compute a simulated confidence score."""
        base = min(0.95, trust_score / 100.0)
        variation = 0.05 * ((-1) ** trajectory_index)
        return max(0.1, min(0.99, base + variation))

    def synthesize_mock(
        self,
        proposal_title: str,
        trajectory_count: int,
        scores: List[float],
        k: int,
        emphases: List[str],
    ) -> SynthesisOutput:
        """Fallback: heuristic deliberation synthesis."""
        high_conf_count = sum(1 for s in scores if s > 0.7)
        total_weight = sum(scores)
        approve_weight = sum(s for s in scores if s > 0.7)
        approval_ratio = approve_weight / total_weight if total_weight > 0 else 0.0

        cross_notes = []
        if high_conf_count >= trajectory_count / 2:
            cross_notes.append(f"Majority ({high_conf_count}/{trajectory_count}) show high confidence.")
        else:
            cross_notes.append(f"Only {high_conf_count}/{trajectory_count} show high confidence.")

        unique_emphases = set(emphases)
        if len(unique_emphases) >= 3:
            cross_notes.append(f"Diverse emphasis ({len(unique_emphases)} angles).")

        concerns = []
        if trajectory_count < k:
            concerns.append(f"Only {trajectory_count}/{k} trajectories generated.")

        if approval_ratio >= 0.6:
            answer = f"Synthesis APPROVES '{proposal_title}'. Ratio: {approval_ratio:.2f}."
            final_conf = approval_ratio
        else:
            answer = f"Synthesis REJECTS '{proposal_title}'. Ratio: {approval_ratio:.2f}."
            final_conf = 1.0 - approval_ratio

        return SynthesisOutput(
            synthesized_answer=answer,
            final_confidence=final_conf,
            cross_validation_notes=cross_notes,
            remaining_concerns=concerns,
        )


# Singleton
_relay_instance: Optional[ModelRelayHeavySkill] = None


def get_heavy_relay(relay_url: str = DEFAULT_RELAY_URL) -> ModelRelayHeavySkill:
    global _relay_instance
    if _relay_instance is None:
        _relay_instance = ModelRelayHeavySkill(relay_url=relay_url)
    return _relay_instance
