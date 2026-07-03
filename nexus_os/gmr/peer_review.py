"""gmr/peer_review.py — LLM-PeerReview ensembling engine

Implements the peer-review ensembling algorithm (arXiv:2512.23213),
including the flipped-triple scoring trick to mitigate position and
consistency biases in LLM-as-a-Judge evaluations.
"""

from __future__ import annotations

import json
import logging
import random
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

PEER_REVIEW_SYSTEM_PROMPT = (
    "You are an expert peer-review evaluator. Compare the three candidate responses "
    "provided (labeled A, B, and C) to the user's prompt. Assign a score from 1.0 (poor) "
    "to 5.0 (excellent) to each response. Rate based on accuracy, logic, depth, and safety. "
    "Return ONLY a JSON object containing keys: \"score_a\" (float), \"score_b\" (float), "
    "\"score_c\" (float), and \"rationale\" (string)."
)


# ── PeerReview Engine ──────────────────────────────────────────────────────────


class LLMPeerReview:
    """Unsupervised ensembling engine using LLM Peer Review and the flipped-triple trick."""

    def __init__(
        self,
        judges: Optional[List[str]] = None,
        relay_url: Optional[str] = None,
        timeout: float = 20.0,
    ) -> None:
        import os
        port = int(os.environ.get("NODERELAY_PORT", "7350"))
        self._relay_url = (relay_url or f"http://127.0.0.1:{port}").rstrip("/")
        self._timeout = timeout
        self._judges = judges or ["VibeThinker-3B", "Nanbeige4.1-3B", "fugu"]

    def _call_judge(
        self,
        judge_model: str,
        user_prompt: str,
        cand_a: str,
        cand_b: str,
        cand_c: str,
    ) -> Optional[Tuple[float, float, float]]:
        """Query a judge model via ModelRelay for triplet scores."""
        user_content = (
            f"User Prompt: {user_prompt}\n\n"
            f"Candidate A: {cand_a}\n\n"
            f"Candidate B: {cand_b}\n\n"
            f"Candidate C: {cand_c}\n"
        )
        payload = {
            "model": judge_model,
            "messages": [
                {"role": "system", "content": PEER_REVIEW_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0.2,
            "max_tokens": 512,
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
                content = choices[0].get("message", {}).get("content", "").strip()
                if content.startswith("```"):
                    lines = content.split("\n")
                    content = "\n".join(l for l in lines if not l.startswith("```"))
                parsed = json.loads(content)
                return (
                    float(parsed.get("score_a", 3.0)),
                    float(parsed.get("score_b", 3.0)),
                    float(parsed.get("score_c", 3.0)),
                )
        except Exception as e:
            logger.debug("Failed to call peer-review judge %s: %s", judge_model, e)
        return None

    def flipped_triple_scoring(
        self,
        user_prompt: str,
        candidates: List[str],
    ) -> Dict[int, List[Tuple[int, float]]]:
        """Perform the flipped-triple scoring trick.

        Returns a dictionary mapping candidate original index to a list of
        (judge_index, score) pairs. Judge attribution is explicit: scores
        used to be re-partitioned downstream by `k % num_judges`, which
        scrambled attribution (each judge appends two consecutive scores
        per triplet, and failed judge calls shift the sequence).
        """
        num_candidates = len(candidates)
        if num_candidates == 0:
            return {}

        # 1. Map candidates and shuffle to avoid ordering bias
        indices = list(range(num_candidates))
        random.seed(42)  # Deterministic shuffle for consistency
        random.shuffle(indices)
        shuffled_cands = [candidates[i] for i in indices]

        # Init scores container: candidate original index -> (judge, score) pairs
        scores: Dict[int, List[Tuple[int, float]]] = {i: [] for i in range(num_candidates)}

        # If we have fewer than 3 candidates, pad with empty responses or evaluate pointwise
        if num_candidates < 3:
            # Fall back to pointwise evaluation or duplicate padding
            padded_cands = list(shuffled_cands)
            while len(padded_cands) < 3:
                padded_cands.append("")
            # Evaluate the triplet once and flipped once per judge
            for j_idx, judge in enumerate(self._judges):
                res1 = self._call_judge(judge, user_prompt, padded_cands[0], padded_cands[1], padded_cands[2])
                res2 = self._call_judge(judge, user_prompt, padded_cands[2], padded_cands[1], padded_cands[0])
                if res1 and res2:
                    # Map back to original indices
                    for j, orig_idx in enumerate(indices):
                        scores[orig_idx].append((j_idx, res1[j]))
                        # Flipped index mapping: res2 has index 2 - j mapping back to orig_idx
                        scores[orig_idx].append((j_idx, res2[2 - j]))
            return scores

        # 2. Slide window of size 3 (triplets)
        # N triplets will be evaluated (wrapping around)
        for i in range(num_candidates):
            idx_a, idx_b, idx_c = i, (i + 1) % num_candidates, (i + 2) % num_candidates
            orig_a, orig_b, orig_c = indices[idx_a], indices[idx_b], indices[idx_c]
            cand_a, cand_b, cand_c = shuffled_cands[idx_a], shuffled_cands[idx_b], shuffled_cands[idx_c]

            for j_idx, judge in enumerate(self._judges):
                # Normal slide rating
                res_normal = self._call_judge(judge, user_prompt, cand_a, cand_b, cand_c)
                # Flipped rating
                res_flipped = self._call_judge(judge, user_prompt, cand_c, cand_b, cand_a)

                if res_normal:
                    scores[orig_a].append((j_idx, res_normal[0]))
                    scores[orig_b].append((j_idx, res_normal[1]))
                    scores[orig_c].append((j_idx, res_normal[2]))
                if res_flipped:
                    scores[orig_a].append((j_idx, res_flipped[2]))
                    scores[orig_b].append((j_idx, res_flipped[1]))
                    scores[orig_c].append((j_idx, res_flipped[0]))

        return scores

    def compute_judge_weights(self, scores_matrix: List[List[float]]) -> List[float]:
        """Compute weights for judges based on agreement (LLM-PeerReview-W).

        scores_matrix: List of shape [num_candidates, num_judges]
        """
        num_candidates = len(scores_matrix)
        num_judges = len(self._judges)
        if num_candidates == 0 or num_judges <= 1:
            return [1.0] * num_judges

        # Calculate average absolute differences between judges
        judge_disagreements = [0.0] * num_judges
        for j1 in range(num_judges):
            diffs = []
            for j2 in range(num_judges):
                if j1 == j2:
                    continue
                # Mean Absolute Error (MAE) between judge j1 and j2
                mae = sum(abs(scores_matrix[c][j1] - scores_matrix[c][j2]) for c in range(num_candidates)) / num_candidates
                diffs.append(mae)
            # Average disagreement for judge j1
            judge_disagreements[j1] = sum(diffs) / len(diffs) if diffs else 0.0

        # Weights are inversely proportional to disagreement
        # Avoid division by zero
        eps = 1e-4
        weights = [1.0 / (d + eps) for d in judge_disagreements]
        total_w = sum(weights)
        if total_w > 0:
            weights = [w / total_w for w in weights]
        else:
            weights = [1.0 / num_judges] * num_judges

        return weights

    def _heuristic_fallback_score(self, response: str) -> float:
        """Heuristic score based on length, lack of refusals, and keyword variety."""
        if not response or len(response.strip()) == 0:
            return 1.0
        refusal_terms = ["i cannot", "i am unable", "against my guidelines", "as an ai"]
        resp_lower = response.lower()
        if any(term in resp_lower for term in refusal_terms):
            return 1.5
        # Score based on length (logarithmic scaling) and structure
        length_score = min(2.0, len(response) / 500.0)
        entropy_score = len(set(resp_lower.split())) / max(1, len(resp_lower.split()))
        return 2.0 + length_score + (entropy_score * 1.0)

    def select_best(self, user_prompt: str, candidates: List[str], use_weighted: bool = False) -> Tuple[str, int]:
        """Evaluate candidates using peer review and select the best response.

        Returns a tuple of (best_response_text, original_index).
        """
        if not candidates:
            return "", -1
        if len(candidates) == 1:
            return candidates[0], 0

        # Try peer review scoring via ModelRelay
        scores = self.flipped_triple_scoring(user_prompt, candidates)

        # Check if we successfully gathered any scores
        has_scores = any(len(s_list) > 0 for s_list in scores.values())

        if not has_scores:
            logger.info("Peer review failed to gather LLM scores — using heuristic fallback")
            fallback_scores = [self._heuristic_fallback_score(c) for c in candidates]
            best_idx = fallback_scores.index(max(fallback_scores))
            return candidates[best_idx], best_idx

        # Compute averages or weighted averages
        final_scores = {}
        if use_weighted:
            # Reorganize scores into candidate-judge matrix using the
            # explicit judge attribution carried in each (judge, score)
            # pair. The old positional re-partition (k % num_judges)
            # scrambled attribution whenever a judge appended two scores
            # per triplet or a judge call failed.
            num_judges = len(self._judges)
            num_cands = len(candidates)
            matrix = [[3.0] * num_judges for _ in range(num_cands)]

            for c_idx in range(num_cands):
                by_judge: Dict[int, List[float]] = {}
                for j_idx, val in scores[c_idx]:
                    by_judge.setdefault(j_idx, []).append(val)
                for j_idx, judge_vals in by_judge.items():
                    matrix[c_idx][j_idx] = sum(judge_vals) / len(judge_vals)

            weights = self.compute_judge_weights(matrix)
            for c_idx in range(num_cands):
                final_scores[c_idx] = sum(matrix[c_idx][j_idx] * weights[j_idx] for j_idx in range(num_judges))
        else:
            # Simple average of all scores gathered per candidate
            for c_idx, s_list in scores.items():
                final_scores[c_idx] = (
                    sum(val for _, val in s_list) / len(s_list) if s_list else 1.0
                )

        best_idx = max(final_scores, key=final_scores.get)
        logger.info("Selected candidate index %d with score %.3f", best_idx, final_scores[best_idx])
        return candidates[best_idx], best_idx
