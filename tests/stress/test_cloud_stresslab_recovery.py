from __future__ import annotations

from nexus_os.stresslab import CloudAttackBeeV2, CloudReportBee
from nexus_os.stresslab.cloud_swarm_orchestrator import TokenBudgetGuard


def test_cloud_attack_bee_generates_adversarial_and_benign_queries() -> None:
    bee = CloudAttackBeeV2()

    adversarial = bee.generate_adversarial_queries()
    benign = bee.generate_benign_queries()

    assert adversarial
    assert benign
    assert all(item["is_adversarial"] is True for item in adversarial)
    assert all(item["expected_verdict"] == "safe" for item in benign)


def test_cloud_report_hash_ignores_existing_chain_hash() -> None:
    payload = {"phase": "attack", "payload": {"x": 1}, "chain_hash": "stale"}

    first = CloudReportBee._compute_hash(payload)
    payload["chain_hash"] = "different"

    assert CloudReportBee._compute_hash(payload) == first


def test_token_budget_guard_halts_at_limit() -> None:
    guard = TokenBudgetGuard(max_queries=10, max_tokens=100)

    guard.record(40)
    assert guard.can_run() is True

    guard.record(60)
    assert guard.halted is True
    assert guard.can_run() is False
