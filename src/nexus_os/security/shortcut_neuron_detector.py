"""nexus_os.security.shortcut_neuron_detector — Shortcut Neuron Analysis

Implements the Zhu et al. (2025) method for identifying and patching
shortcut neurons in contaminated LLMs.

Key insight: contaminated models acquire a sparse set of ~5000 shortcut
neurons that encode benchmark-specific solutions (input-format shortcuts
and reasoning shortcuts). These can be identified by comparing contaminated
vs clean models of the same architecture, then patched using base-model
activations without harming general abilities.

Reference:
  Zhu et al. "Establishing Trustworthy LLM Evaluation via Shortcut Neuron
  Analysis" (viXra 2025). Spearman correlation >0.95 with MixEval.

Usage (blueprint mode — no torch required):
    from nexus_os.security.shortcut_neuron_detector import ShortcutNeuronDetector
    detector = ShortcutNeuronDetector()
    report = detector.detect_from_simulation(
        model_seed="contaminated-qwen-1.5b",
        benchmark="GSM8K",
    )
    print(report.contaminated, report.confidence, report.details["shortcut_neuron_count"])

When torch is available, use the real activation hooks:
    detector.detect(contaminated_activations, clean_activations, base_activations)
"""
from __future__ import annotations

import math
import hashlib
from dataclasses import dataclass, field
from typing import Optional, Sequence, List, Dict

# ── Optional heavy dependencies ─────────────────────────────────────
try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:  # pragma: no cover
    _HAS_NUMPY = False

try:
    import torch
    _HAS_TORCH = True
except ImportError:  # pragma: no cover
    _HAS_TORCH = False


# ── Shared result type (same as contamination_detector) ─────────────
@dataclass
class ShortcutNeuronReport:
    contaminated: bool
    confidence: float  # 0.0–1.0
    method_used: str = "shortcut_neuron_analysis"
    details: dict = field(default_factory=dict)
    recommendation: str = ""


@dataclass
class NeuronProfile:
    """Metadata for a single shortcut neuron candidate."""
    layer_idx: int
    neuron_idx: int
    shortcut_score: float  # contamination indicator score
    activation_pattern: str  # e.g. 'contaminated_spike', 'format_gaming', 'reasoning_shortcut'
    mean_activation_clean: float = 0.0
    mean_activation_contaminated: float = 0.0
    mean_activation_base: float = 0.0


# ── Deterministic activation simulator (blueprint mode) ───────────────
class _ActivationSimulator:
    """Deterministic LCG-based activation generator for blueprint mode.

    Produces reproducible hidden-state activations given a seed string,
    allowing the detector to run without PyTorch or actual model weights.
    Same principle as DICEHiddenStateDetector in contamination_detector.py.
    """

    def __init__(self, seed: str, dim: int = 4096):
        self.dim = dim
        self._state = int(hashlib.sha256(seed.encode()).hexdigest(), 16) & 0xFFFFFFFF

    def _lcg(self) -> float:
        """Return next float in [0, 1)."""
        self._state = (self._state * 1664525 + 1013904223) & 0xFFFFFFFF
        return self._state / 0xFFFFFFFF

    def generate(self, n_samples: int) -> List[float]:
        """Generate n_samples deterministic activations."""
        return [self._lcg() for _ in range(n_samples)]

    def layer_activations(self, layer_idx: int, n_neurons: int) -> List[float]:
        """Generate activations for a specific layer."""
        # Re-seed per layer so layer order matters
        layer_seed = f"{self._state}_layer_{layer_idx}"
        sim = _ActivationSimulator(layer_seed, self.dim)
        return sim.generate(n_neurons)


# ── Main detector ────────────────────────────────────────────────────
class ShortcutNeuronDetector:
    """Identify and patch shortcut neurons in contaminated models.

    Two modes of operation:
      1. **Blueprint mode** (no torch): uses deterministic simulation to
         demonstrate the detection logic and produce analyzable reports.
      2. **Real mode** (torch available): accepts actual activation tensors
         from contaminated, clean, and base models.
    """

    DEFAULT_TOP_K: int = 5000
    DEFAULT_THRESHOLD: float = 0.80
    N_LAYERS: int = 24  # Typical for 1.5B-param models (Qwen2.5, etc.)
    N_NEURONS_PER_LAYER: int = 4096  # Hidden dim

    def __init__(
        self,
        threshold: float = DEFAULT_THRESHOLD,
        top_k: int = DEFAULT_TOP_K,
        n_layers: int = N_LAYERS,
        n_neurons: int = N_NEURONS_PER_LAYER,
    ):
        self.threshold = threshold
        self.top_k = top_k
        self.n_layers = n_layers
        self.n_neurons = n_neurons

    # ── Blueprint: deterministic simulation ─────────────────────────
    def detect_from_simulation(
        self,
        model_seed: str,
        benchmark: str = "GSM8K",
        contamination_level: float = 0.3,
    ) -> ShortcutNeuronReport:
        """Run shortcut-neuron detection on simulated activations.

        Args:
            model_seed: arbitrary string identifying the model variant.
            benchmark: benchmark name affecting shortcut pattern generation.
            contamination_level: 0.0–1.0 scale of contamination intensity.
        """
        # Simulate three model variants
        contaminated_sim = _ActivationSimulator(f"{model_seed}_contaminated_{benchmark}")
        clean_sim = _ActivationSimulator(f"{model_seed}_clean_{benchmark}")
        base_sim = _ActivationSimulator(f"{model_seed}_base_{benchmark}")

        shortcut_neurons: List[NeuronProfile] = []
        total_score = 0.0

        for layer_idx in range(self.n_layers):
            cont_acts = contaminated_sim.layer_activations(layer_idx, self.n_neurons)
            clean_acts = clean_sim.layer_activations(layer_idx, self.n_neurons)
            base_acts = base_sim.layer_activations(layer_idx, self.n_neurons)

            for neuron_idx in range(self.n_neurons):
                ca, cl, ba = cont_acts[neuron_idx], clean_acts[neuron_idx], base_acts[neuron_idx]

                # Zhu et al. heuristic: shortcut neurons show
                # (1) abnormally HIGH activation on contaminated data
                # (2) divergence from both clean and base patterns
                spike = max(0.0, ca - max(cl, ba))
                divergence = abs(ca - cl) + abs(ca - ba)
                shortcut_score = min(1.0, (spike * 2.0 + divergence) * contamination_level)

                if shortcut_score >= self.threshold:
                    pattern = self._classify_pattern(ca, cl, ba)
                    shortcut_neurons.append(
                        NeuronProfile(
                            layer_idx=layer_idx,
                            neuron_idx=neuron_idx,
                            shortcut_score=shortcut_score,
                            activation_pattern=pattern,
                            mean_activation_clean=cl,
                            mean_activation_contaminated=ca,
                            mean_activation_base=ba,
                        )
                    )
                    total_score += shortcut_score

        # Sort by score descending, keep top_k
        shortcut_neurons.sort(key=lambda n: n.shortcut_score, reverse=True)
        shortcut_neurons = shortcut_neurons[: self.top_k]

        confidence = min(1.0, len(shortcut_neurons) / self.top_k)
        contaminated = len(shortcut_neurons) > (self.top_k * 0.05)

        # Layer distribution analysis
        layer_counts: Dict[int, int] = {}
        for n in shortcut_neurons:
            layer_counts[n.layer_idx] = layer_counts.get(n.layer_idx, 0) + 1

        pattern_counts: Dict[str, int] = {}
        for n in shortcut_neurons:
            pattern_counts[n.activation_pattern] = pattern_counts.get(n.activation_pattern, 0) + 1

        recommendation = (
            f"Identified {len(shortcut_neurons)} shortcut neurons (top-{self.top_k}). "
            f"Apply patching: replace contaminated neuron activations with base-model activations "
            f"for layers {sorted(layer_counts.keys())[:5]}. "
            f"Expected Spearman correlation with trustworthy benchmarks: >0.95."
        )

        return ShortcutNeuronReport(
            contaminated=contaminated,
            confidence=round(confidence, 3),
            method_used="shortcut_neuron_analysis_simulated",
            details={
                "shortcut_neuron_count": len(shortcut_neurons),
                "total_score": round(total_score, 2),
                "layer_distribution": {k: v for k, v in sorted(layer_counts.items(), key=lambda x: -x[1])[:10]},
                "pattern_distribution": pattern_counts,
                "benchmark": benchmark,
                "contamination_level": contamination_level,
            },
            recommendation=recommendation,
        )

    # ── Real mode: torch tensors ────────────────────────────────────
    def detect(
        self,
        contaminated_activations: "torch.Tensor",
        clean_activations: "torch.Tensor",
        base_activations: "torch.Tensor",
    ) -> ShortcutNeuronReport:
        """Real shortcut-neuron detection on torch tensors.

        Args:
            contaminated_activations: shape [n_layers, n_neurons]
            clean_activations: shape [n_layers, n_neurons]
            base_activations: shape [n_layers, n_neurons]
        """
        if not _HAS_TORCH:
            raise RuntimeError(
                "ShortcutNeuronDetector.detect() requires torch. "
                "Use detect_from_simulation() for blueprint mode."
            )

        import torch

        # Validate shapes
        assert contaminated_activations.shape == clean_activations.shape == base_activations.shape
        n_layers, n_neurons = contaminated_activations.shape

        shortcut_neurons: List[NeuronProfile] = []

        for layer_idx in range(n_layers):
            ca = contaminated_activations[layer_idx]
            cl = clean_activations[layer_idx]
            ba = base_activations[layer_idx]

            # Heuristic: spike = max(0, contaminated - max(clean, base))
            spike = torch.clamp(ca - torch.max(cl, ba), min=0.0)
            divergence = torch.abs(ca - cl) + torch.abs(ca - ba)
            shortcut_scores = torch.clamp((spike * 2.0 + divergence), max=1.0)

            # Find neurons above threshold
            mask = shortcut_scores >= self.threshold
            indices = torch.where(mask)[0]

            for idx in indices.tolist():
                shortcut_neurons.append(
                    NeuronProfile(
                        layer_idx=layer_idx,
                        neuron_idx=idx,
                        shortcut_score=float(shortcut_scores[idx]),
                        activation_pattern=self._classify_pattern(
                            float(ca[idx]), float(cl[idx]), float(ba[idx])
                        ),
                        mean_activation_clean=float(cl[idx]),
                        mean_activation_contaminated=float(ca[idx]),
                        mean_activation_base=float(ba[idx]),
                    )
                )

        # Sort and truncate
        shortcut_neurons.sort(key=lambda n: n.shortcut_score, reverse=True)
        shortcut_neurons = shortcut_neurons[: self.top_k]

        confidence = min(1.0, len(shortcut_neurons) / self.top_k)
        contaminated = len(shortcut_neurons) > (self.top_k * 0.05)

        layer_counts = {}
        for n in shortcut_neurons:
            layer_counts[n.layer_idx] = layer_counts.get(n.layer_idx, 0) + 1

        pattern_counts = {}
        for n in shortcut_neurons:
            pattern_counts[n.activation_pattern] = pattern_counts.get(n.activation_pattern, 0) + 1

        return ShortcutNeuronReport(
            contaminated=contaminated,
            confidence=round(confidence, 3),
            method_used="shortcut_neuron_analysis_torch",
            details={
                "shortcut_neuron_count": len(shortcut_neurons),
                "layer_distribution": {k: v for k, v in sorted(layer_counts.items(), key=lambda x: -x[1])[:10]},
                "pattern_distribution": pattern_counts,
            },
            recommendation=f"Patch {len(shortcut_neurons)} shortcut neurons using base-model activations.",
        )

    def patch(
        self,
        contaminated_activations: "torch.Tensor",
        base_activations: "torch.Tensor",
        shortcut_neurons: Sequence[NeuronProfile],
    ) -> "torch.Tensor":
        """Patch contaminated activations by replacing shortcut neurons with base activations.

        Returns a new tensor with patched values.
        """
        if not _HAS_TORCH:
            raise RuntimeError("patch() requires torch.")
        import torch

        patched = contaminated_activations.clone()
        for neuron in shortcut_neurons:
            patched[neuron.layer_idx, neuron.neuron_idx] = base_activations[
                neuron.layer_idx, neuron.neuron_idx
            ]
        return patched

    # ── Helpers ─────────────────────────────────────────────────────
    @staticmethod
    def _classify_pattern(ca: float, cl: float, ba: float) -> str:
        """Classify the shortcut pattern type based on activation relationships."""
        if ca > 0.85 and cl < 0.3 and ba < 0.3:
            return "contaminated_spike"
        elif ca > cl > ba:
            return "format_gaming"
        elif abs(ca - ba) < 0.1 and cl < 0.2:
            return "base_aligned"
        elif ca > 0.7 and cl > 0.5 and abs(ca - cl) < 0.1:
            return "reasoning_shortcut"
        else:
            return "mixed_pattern"


# ── Standalone test / demo ──────────────────────────────────────────
def _demo():
    print("=" * 60)
    print("Shortcut Neuron Detector — Zhu et al. (2025) Blueprint Demo")
    print("=" * 60)

    detector = ShortcutNeuronDetector(threshold=0.75, top_k=100)

    scenarios = [
        ("lightly-contaminated-qwen", "GSM8K", 0.15),
        ("heavily-contaminated-qwen", "GSM8K", 0.60),
        ("clean-qwen", "GSM8K", 0.0),
    ]

    for seed, benchmark, level in scenarios:
        report = detector.detect_from_simulation(seed, benchmark, level)
        print(f"\nModel: {seed}")
        print(f"  Contaminated: {report.contaminated} (confidence={report.confidence})")
        print(f"  Shortcut neurons: {report.details['shortcut_neuron_count']}")
        print(f"  Top layers: {list(report.details['layer_distribution'].keys())[:5]}")
        print(f"  Patterns: {report.details['pattern_distribution']}")
        print(f"  Recommendation: {report.recommendation[:120]}...")

    print("\n" + "=" * 60)
    print("Demo complete. Use detect() with real torch tensors for live models.")


if __name__ == "__main__":
    _demo()
