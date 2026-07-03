"""RIFT — Reward-Informed Fine-Tuning (arXiv 2601.09253, papers09).

Repurposes negative samples instead of discarding them (RFT) by weighting
the SFT loss with scalar rewards, and replaces the logarithmic objective on
negative samples with the paper's *linear probability surrogate* so the loss
stays bounded and gradients cannot explode as pi(y|x) -> 0 (Theorem 3.2/3.4):

    L_RIFT = -E_{D+}[ r * log pi(y|x) ]  -  E_{D-}[ r * pi(y|x) ]

Two consumers:

1. ``rebalance_pairs`` / ``compute_class_weights`` — pure-Python dataset
   shaping: flattens guard DPO chosen/rejected pairs into reward-weighted
   SFT records, with inverse-frequency class weights that equalize the
   effective SAFE/UNSAFE mass (the guard_dpo_v1 dedup set is 247/128).
   Rejected completions become graded NEGATIVE-reward records rather than
   being thrown away — this is the rebalance itself: no new labels needed.

2. ``rift_loss`` — the stabilized loss for a torch training loop (TRL/
   MS-Swift style), consuming per-token logprobs. torch is imported lazily
   so dataset shaping works on hosts without an ML runtime.

Reward magnitudes default to the paper's +1.0 / -0.2 asymmetry (MGPO
finding: emphasize successful traces; sensitivity analyzed in paper §5.1,
where fixed asymmetric rewards beat group-normalization variants).
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Iterable, Iterator

__all__ = [
    "RIFTConfig",
    "compute_class_weights",
    "rebalance_pairs",
    "rift_loss",
    "naive_signed_loss",
]


@dataclass(frozen=True)
class RIFTConfig:
    """Knobs for RIFT dataset shaping and loss.

    pos_reward / neg_reward follow the paper's +1.0 / -0.2 default. The
    negative magnitude is deliberately small: negatives suppress, they do
    not dominate. ``balance_classes`` multiplies each pair's rewards by an
    inverse-frequency class weight so minority-class (UNSAFE) pairs carry
    the same total training mass as majority-class ones.
    """

    pos_reward: float = 1.0
    neg_reward: float = -0.2
    balance_classes: bool = True
    label_key: str = "label"

    def __post_init__(self) -> None:
        if self.pos_reward <= 0:
            raise ValueError("pos_reward must be > 0")
        if self.neg_reward >= 0:
            raise ValueError("neg_reward must be < 0 (negatives suppress)")


def compute_class_weights(labels: Iterable[str]) -> dict[str, float]:
    """Inverse-frequency weights: w_c = N_total / (K * N_c).

    The weighted mass of every class is then identical (N_c * w_c ==
    N_total / K), which is exactly the rebalance the 247/128 guard set
    needs, and the weights stay centered around 1.0 so they compose with
    the reward magnitudes without rescaling the learning rate.
    """
    counts = Counter(labels)
    if not counts:
        return {}
    total = sum(counts.values())
    k = len(counts)
    return {label: total / (k * n) for label, n in counts.items()}


def rebalance_pairs(
    pairs: Iterable[dict[str, Any]],
    config: RIFTConfig | None = None,
) -> Iterator[dict[str, Any]]:
    """Flatten DPO pairs into reward-weighted RIFT SFT records.

    Each input pair ``{prompt, chosen, rejected, meta:{label,...}}`` yields
    two records: the chosen completion with reward ``+pos_reward * w_c``
    and the rejected completion with reward ``neg_reward * w_c`` — the
    negative is repurposed as graded suppression signal, not discarded.

    Deterministic and single-pass-stable: records are emitted in input
    order, chosen before rejected, so reruns produce byte-identical output.
    """
    cfg = config or RIFTConfig()
    pairs = list(pairs)
    if cfg.balance_classes:
        weights = compute_class_weights(
            str((p.get("meta") or {}).get(cfg.label_key, "")) for p in pairs
        )
    else:
        weights = {}

    for pair in pairs:
        meta = dict(pair.get("meta") or {})
        label = str(meta.get(cfg.label_key, ""))
        class_weight = weights.get(label, 1.0)
        base = {
            k: v for k, v in meta.items() if k not in ("role", "reward", "class_weight")
        }
        for role, completion, reward in (
            ("chosen", pair["chosen"], cfg.pos_reward * class_weight),
            ("rejected", pair["rejected"], cfg.neg_reward * class_weight),
        ):
            yield {
                "prompt": pair["prompt"],
                "completion": completion,
                "reward": round(reward, 6),
                "meta": {
                    **base,
                    "role": role,
                    "class_weight": round(class_weight, 6),
                    "rift": {
                        "pos_reward": cfg.pos_reward,
                        "neg_reward": cfg.neg_reward,
                        "balanced": cfg.balance_classes,
                    },
                },
            }


def rift_loss(token_logps, rewards, mask=None):
    """Stabilized RIFT loss over a batch of sequences (torch).

    Args:
        token_logps: FloatTensor [B, T] — per-token log pi_theta(y_t | ...).
        rewards: FloatTensor [B] — signed scalar rewards (class weights
            already folded in by ``rebalance_pairs``).
        mask: optional FloatTensor [B, T] — 1.0 on completion tokens.

    Positives keep the MLE term ``-r * log pi(y|x)``; negatives use the
    bounded linear surrogate ``-r * pi(y|x)`` whose contribution lies in
    ``[0, -r]`` and whose gradient w.r.t. pi is the constant ``-r`` — no
    explosion as suppression succeeds (paper Theorem 3.4).
    """
    import torch

    if mask is None:
        mask = torch.ones_like(token_logps)
    seq_logp = (token_logps * mask).sum(dim=-1)
    positive = rewards > 0

    loss = torch.zeros((), dtype=token_logps.dtype, device=token_logps.device)
    if positive.any():
        loss = loss + (-(rewards[positive] * seq_logp[positive])).sum()
    if (~positive).any():
        pi = torch.exp(seq_logp[~positive])
        loss = loss + (-(rewards[~positive] * pi)).sum()
    return loss / max(int(rewards.shape[0]), 1)


def naive_signed_loss(token_logps, rewards, mask=None):
    """The unstable Definition-3.1 baseline: ``-E[r * log pi]`` for ALL signs.

    Kept only so tests can demonstrate the pathology RIFT removes
    (unbounded loss / exploding gradient on suppressed negatives). Never
    use this for training.
    """
    import torch

    if mask is None:
        mask = torch.ones_like(token_logps)
    seq_logp = (token_logps * mask).sum(dim=-1)
    return (-(rewards * seq_logp)).sum() / max(int(rewards.shape[0]), 1)
