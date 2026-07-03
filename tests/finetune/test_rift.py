"""RIFT rebalance + stabilized loss (nexus_os/finetune/rift.py, papers09)."""
from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

import pytest

from nexus_os.finetune.rift import (
    RIFTConfig,
    compute_class_weights,
    naive_signed_loss,
    rebalance_pairs,
    rift_loss,
)

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "finetune" / "rift_rebalance_guard_pairs.py"


def _pair(i: int, label: str) -> dict:
    return {
        "prompt": f"Classify request {i} as SAFE or UNSAFE.",
        "chosen": f"VERDICT: {label} - routine engineering rationale {i}.",
        "rejected": f"VERDICT: {'UNSAFE' if label == 'SAFE' else 'SAFE'} - wrong rationale {i}.",
        "meta": {"label": label, "pair_index": i, "judge": "offline-template"},
    }


def _mixed_pairs(n_safe: int = 6, n_unsafe: int = 2) -> list[dict]:
    pairs = [_pair(i, "SAFE") for i in range(n_safe)]
    pairs += [_pair(100 + i, "UNSAFE") for i in range(n_unsafe)]
    return pairs


# ---------------------------------------------------------------- weights


def test_class_weights_equalize_mass():
    weights = compute_class_weights(["SAFE"] * 247 + ["UNSAFE"] * 128)
    assert weights["UNSAFE"] > 1.0 > weights["SAFE"]
    assert 247 * weights["SAFE"] == pytest.approx(128 * weights["UNSAFE"])
    # centered: weighted total mass == raw total
    assert 247 * weights["SAFE"] + 128 * weights["UNSAFE"] == pytest.approx(375)


def test_class_weights_empty_and_single():
    assert compute_class_weights([]) == {}
    assert compute_class_weights(["SAFE", "SAFE"]) == {"SAFE": 1.0}


# ------------------------------------------------------------- rebalance


def test_rebalance_repurposes_negatives_not_discards():
    pairs = _mixed_pairs()
    records = list(rebalance_pairs(pairs))
    assert len(records) == 2 * len(pairs)
    roles = {r["meta"]["role"] for r in records}
    assert roles == {"chosen", "rejected"}
    for r in records:
        if r["meta"]["role"] == "chosen":
            assert r["reward"] > 0
        else:
            assert r["reward"] < 0


def test_rebalance_equalizes_class_mass():
    records = list(rebalance_pairs(_mixed_pairs(n_safe=6, n_unsafe=2)))
    mass = {"SAFE": 0.0, "UNSAFE": 0.0}
    for r in records:
        mass[r["meta"]["label"]] += abs(r["reward"])
    assert mass["SAFE"] == pytest.approx(mass["UNSAFE"])


def test_rebalance_deterministic():
    pairs = _mixed_pairs()
    a = list(rebalance_pairs(pairs))
    b = list(rebalance_pairs(pairs))
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_rebalance_preserves_source_meta_and_stamps_config():
    record = next(iter(rebalance_pairs([_pair(7, "UNSAFE")])))
    assert record["meta"]["pair_index"] == 7
    assert record["meta"]["judge"] == "offline-template"
    assert record["meta"]["rift"]["neg_reward"] == -0.2


def test_config_validation():
    with pytest.raises(ValueError):
        RIFTConfig(pos_reward=0.0)
    with pytest.raises(ValueError):
        RIFTConfig(neg_reward=0.5)


# ------------------------------------------------------------------ loss


torch = pytest.importorskip("torch")


def _batch(logp_per_token: list[float], rewards: list[float]):
    t = torch.tensor([[lp] * 4 for lp in logp_per_token], requires_grad=True)
    return t, torch.tensor(rewards)


def test_positive_only_reduces_to_weighted_nll():
    logps, rewards = _batch([-0.5, -1.0], [1.0, 2.0])
    loss = rift_loss(logps, rewards)
    # -(1.0 * 4*-0.5) + -(2.0 * 4*-1.0) = 2 + 8, mean over batch = 5
    assert loss.item() == pytest.approx(5.0)


def test_negative_contribution_bounded():
    """Theorem 3.4(i): each negative sample contributes within [0, -r]."""
    for lp in (-0.01, -1.0, -50.0, -500.0):
        logps, rewards = _batch([lp], [-0.2])
        loss = rift_loss(logps, rewards)
        assert 0.0 <= loss.item() <= 0.2 + 1e-9
    # naive loss on the same suppressed sample is unbounded
    logps, rewards = _batch([-500.0], [-0.2])
    assert naive_signed_loss(logps, rewards).item() == pytest.approx(-400.0)


def test_negative_gradient_stays_stable_where_naive_explodes():
    """Theorem 3.2 vs 3.4: grad wrt token logp vanishes for RIFT as the
    negative is suppressed, while the naive loss keeps a constant push
    toward -inf (unbounded objective)."""
    suppressed, rewards = _batch([-50.0], [-0.2])
    rift_loss(suppressed, rewards).backward()
    rift_grad = suppressed.grad.abs().max().item()
    assert rift_grad < 1e-6  # bounded surrogate: no further push

    naive_in, rewards2 = _batch([-50.0], [-0.2])
    naive_signed_loss(naive_in, rewards2).backward()
    naive_grad = naive_in.grad.abs().max().item()
    assert naive_grad == pytest.approx(0.2)  # constant drive to -inf forever


def test_mask_excludes_prompt_tokens():
    logps = torch.tensor([[-1.0, -1.0, -2.0, -2.0]], requires_grad=True)
    rewards = torch.tensor([1.0])
    mask = torch.tensor([[0.0, 0.0, 1.0, 1.0]])
    assert rift_loss(logps, rewards, mask).item() == pytest.approx(4.0)


def test_mixed_batch_finite_and_signed_correctly():
    logps, rewards = _batch([-0.5, -3.0, -1.0], [1.0, -0.2, -0.29])
    loss = rift_loss(logps, rewards)
    assert math.isfinite(loss.item())
    # positive term alone would be 2.0/3; negatives can only ADD >= 0
    assert loss.item() >= 2.0 / 3 - 1e-9


# ---------------------------------------------------------------- script


def test_rebalance_script_end_to_end(tmp_path):
    src = tmp_path / "pairs.jsonl"
    with src.open("w", encoding="utf-8") as f:
        for p in _mixed_pairs(n_safe=3, n_unsafe=1):
            f.write(json.dumps(p) + "\n")
    out = tmp_path / "rift.jsonl"

    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--in", str(src), "--out", str(out)],
        capture_output=True, text=True, cwd=str(REPO),
    )
    assert proc.returncode == 0, proc.stderr
    records = [json.loads(x) for x in out.read_text(encoding="utf-8").splitlines()]
    assert len(records) == 8
    mass = {"SAFE": 0.0, "UNSAFE": 0.0}
    for r in records:
        mass[r["meta"]["label"]] += abs(r["reward"])
    assert mass["SAFE"] == pytest.approx(mass["UNSAFE"])
    # idempotent rerun -> byte-identical output
    first = out.read_bytes()
    proc2 = subprocess.run(
        [sys.executable, str(SCRIPT), "--in", str(src), "--out", str(out)],
        capture_output=True, text=True, cwd=str(REPO),
    )
    assert proc2.returncode == 0, proc2.stderr
    assert out.read_bytes() == first


def test_rebalance_script_check_mode_writes_nothing(tmp_path):
    src = tmp_path / "pairs.jsonl"
    src.write_text(json.dumps(_pair(0, "SAFE")) + "\n", encoding="utf-8")
    out = tmp_path / "rift.jsonl"
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--in", str(src), "--out", str(out), "--check"],
        capture_output=True, text=True, cwd=str(REPO),
    )
    assert proc.returncode == 0, proc.stderr
    assert not out.exists()
