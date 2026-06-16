"""Token Policy Plane v2 tests."""

from pathlib import Path

from nexus_os.monitoring.token_guard import TokenGuard
from nexus_os.monitoring.token_policy import (
    BudgetScope,
    TokenEstimate,
    TokenLedger,
    TokenPolicy,
    TokenPolicyDecision,
    TokenReservation,
    TokenUsageActual,
    redact_token_context,
)


def test_token_policy_denies_projected_hard_stop():
    policy = TokenPolicy(scope=BudgetScope.AGENT, total=1000, used=900)

    result = policy.evaluate(TokenEstimate(input_tokens=100))

    assert result.allowed is False
    assert result.decision == TokenPolicyDecision.DENY
    assert result.reason == "projected_hard_stop"


def test_token_context_redaction_masks_secret_keys_and_values():
    redacted = redact_token_context(
        {
            "api_key": "sk-test-secret",
            "headers": {"Authorization": "Bearer secret"},
            "safe": "normal text",
        }
    )

    assert redacted["api_key"] == "[REDACTED]"
    assert redacted["headers"]["Authorization"] == "[REDACTED]"
    assert redacted["safe"] == "normal text"


def test_token_ledger_hash_chain_round_trip(tmp_path: Path):
    ledger_path = tmp_path / "tokens.jsonl"
    ledger = TokenLedger(ledger_path)
    first = TokenReservation.create(
        scope=BudgetScope.AGENT,
        actor="agent-a",
        estimate=TokenEstimate(input_tokens=100),
    )
    second = first.commit(TokenUsageActual(input_tokens=80, output_tokens=10))

    first_event = ledger.record(first)
    second_event = ledger.record(second)

    assert second_event.parent_hash == first_event.event_hash
    assert ledger.verify() is True
    assert TokenLedger(ledger_path).verify() is True


def test_token_guard_reservation_lifecycle_with_ledger(tmp_path: Path):
    guard = TokenGuard(budgets={"agent": 1000}, token_ledger_path=tmp_path / "ledger.jsonl")

    reserved = guard.reserve("agent-a", 100, operation="model_call")
    committed = guard.commit_reservation(
        reserved["reservation_id"],
        actual_input_tokens=70,
        actual_output_tokens=20,
    )
    refunded = guard.refund_reservation(reserved["reservation_id"], reason="retry_cancelled")

    assert reserved["allowed"] is True
    assert reserved["status"] == "reserved"
    assert committed["status"] == "committed"
    assert refunded["status"] == "refunded"
    assert guard.get_token_ledger(limit=10)
