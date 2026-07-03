from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from nexus_os.model_relay.provider_budget import BudgetDenied, ProviderBudgetLedger


def _future_iso(days: int = 30) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def test_default_allocations_preserve_ten_percent_reserve(tmp_path):
    ledger = ProviderBudgetLedger(tmp_path / "quota.sqlite3")
    longcat = ledger.status("longcat")
    intern = ledger.status("internai")

    assert (longcat["allocation_tokens"], longcat["target_tokens"], longcat["reserve_tokens"]) == (
        65_000_000,
        58_500_000,
        6_500_000,
    )
    assert (intern["allocation_tokens"], intern["target_tokens"], intern["reserve_tokens"]) == (
        90_000_000,
        81_000_000,
        9_000_000,
    )


def test_unverified_provider_allows_only_two_bounded_probes(tmp_path):
    ledger = ProviderBudgetLedger(tmp_path / "quota.sqlite3")
    ledger.reserve("probe-1", "longcat", 8_000, probe=True)
    ledger.complete("probe-1", input_tokens=4_000, output_tokens=4_000)
    ledger.reserve("probe-2", "longcat", 8_000, probe=True)
    ledger.complete("probe-2", input_tokens=4_000, output_tokens=4_000)

    with pytest.raises(BudgetDenied, match="probe limit"):
        ledger.reserve("probe-3", "longcat", 1, probe=True)
    with pytest.raises(BudgetDenied, match="not verified"):
        ledger.reserve("normal-1", "longcat", 100)


def test_verification_requires_reset_or_expiry(tmp_path):
    ledger = ProviderBudgetLedger(tmp_path / "quota.sqlite3")
    with pytest.raises(ValueError, match="reset_at or expires_at"):
        ledger.verify_balance("longcat", 65_000_000, source="account")


def test_verified_budget_reserves_atomically_and_survives_restart(tmp_path):
    path = tmp_path / "quota.sqlite3"
    first = ProviderBudgetLedger(path)
    first.verify_balance("longcat", 65_000_000, expires_at=_future_iso(), source="account-dashboard")
    first.reserve("job-1", "longcat", 10_000)

    second = ProviderBudgetLedger(path)
    assert second.status("longcat")["active_reserved_tokens"] == 10_000
    with pytest.raises(BudgetDenied, match="concurrency"):
        second.reserve("job-2", "longcat", 10_000)


def test_corpus_work_is_globally_serialized(tmp_path):
    ledger = ProviderBudgetLedger(tmp_path / "quota.sqlite3")
    ledger.verify_balance("longcat", 65_000_000, expires_at=_future_iso(), source="account")
    ledger.verify_balance("internai", 90_000_000, reset_at=_future_iso(), source="account")

    ledger.reserve("longcat-corpus", "longcat", 10_000, corpus=True)
    with pytest.raises(BudgetDenied, match="corpus"):
        ledger.reserve("intern-corpus", "internai", 10_000, corpus=True)


def test_completed_usage_is_reconciled_and_reserve_is_protected(tmp_path):
    ledger = ProviderBudgetLedger(tmp_path / "quota.sqlite3")
    ledger.verify_balance("longcat", 6_500_100, expires_at=_future_iso(), source="account")
    ledger.reserve("last-allowed", "longcat", 100)
    ledger.complete("last-allowed", input_tokens=60, output_tokens=40)

    status = ledger.status("longcat")
    assert status["local_consumed_tokens"] == 100
    assert status["consumed_tokens"] == 58_500_000
    assert status["target_remaining_tokens"] == 0
    with pytest.raises(BudgetDenied, match="reserve"):
        ledger.reserve("reserve-break", "longcat", 1)


def test_missing_usage_fails_closed_for_budgeted_provider(tmp_path):
    ledger = ProviderBudgetLedger(tmp_path / "quota.sqlite3")
    ledger.verify_balance("internai", 90_000_000, reset_at=_future_iso(), source="account")
    ledger.reserve("job-1", "internai", 100)

    with pytest.raises(BudgetDenied, match="usage metadata"):
        ledger.complete("job-1", input_tokens=None, output_tokens=None)
    assert ledger.status("internai")["active_reservations"] == 0


def test_rate_limit_applies_provider_specific_cooldown(tmp_path):
    ledger = ProviderBudgetLedger(tmp_path / "quota.sqlite3")
    ledger.verify_balance("internai", 90_000_000, reset_at=_future_iso(), source="account")
    ledger.reserve("job-1", "internai", 100)
    ledger.fail("job-1", status_code=429, retry_after_seconds=1)

    status = ledger.status("internai")
    assert status["current_rpm"] == 10
    assert status["cooldown_remaining_seconds"] >= 1_190
    with pytest.raises(BudgetDenied, match="cooldown"):
        ledger.reserve("job-2", "internai", 100)


def test_nvidia_rate_limit_quarantines_for_one_hour(tmp_path):
    ledger = ProviderBudgetLedger(tmp_path / "quota.sqlite3")
    ledger.reserve("nim-1", "nvidia", 100)
    ledger.fail("nim-1", status_code=429)

    status = ledger.status("nvidia")
    assert status["current_rpm"] == 8
    assert status["cooldown_remaining_seconds"] >= 3_590


def test_three_rate_limits_disable_provider(tmp_path, monkeypatch):
    now = [datetime.now(timezone.utc).timestamp()]
    monkeypatch.setattr("nexus_os.model_relay.provider_budget.time.time", lambda: now[0])
    ledger = ProviderBudgetLedger(tmp_path / "quota.sqlite3")
    ledger.verify_balance("longcat", 65_000_000, expires_at=now[0] + 100_000, source="account")

    for index in range(3):
        request_id = f"rate-{index}"
        ledger.clear_cooldown("longcat")
        now[0] += 1_201
        ledger.reserve(request_id, "longcat", 100)
        ledger.fail(request_id, status_code=429)

    status = ledger.status("longcat")
    assert status["enabled"] is False
    assert status["disabled_reason"] == "rate_limit_quarantine"


def test_gateway_blocks_unverified_budget_without_provider_call(tmp_path, monkeypatch):
    from upload.gateway import ModelRelayGateway

    ledger = ProviderBudgetLedger(tmp_path / "quota.sqlite3")
    gateway = ModelRelayGateway(budget_ledger=ledger)
    called = []
    monkeypatch.setattr(gateway, "_call_provider", lambda *args, **kwargs: called.append(True))
    plan = {
        "request_id": "blocked-1",
        "primary_model": "longcat/LongCat-2.0",
        "fallback_chain": [],
        "provider": "longcat",
        "max_tokens": 100,
        "metadata": {},
    }

    result = gateway.execute_request(plan, [{"role": "user", "content": "hello"}])

    assert called == []
    assert result["quota_status"] == "denied"
    assert "not verified" in result["error"]


def test_gateway_reconciles_usage_and_model_echo(tmp_path, monkeypatch):
    from upload.gateway import ModelRelayGateway

    ledger = ProviderBudgetLedger(tmp_path / "quota.sqlite3")
    ledger.verify_balance("internai", 90_000_000, reset_at=_future_iso(), source="account")
    gateway = ModelRelayGateway(budget_ledger=ledger)
    monkeypatch.setattr(
        gateway,
        "_call_provider",
        lambda *args, **kwargs: {
            "success": True,
            "output": "ok",
            "usage": {"prompt_tokens": 12, "completion_tokens": 8, "total_tokens": 20},
            "tokens_used": 20,
            "latency_ms": 15,
            "provider_echo": "Intern-S2-Preview",
            "resolved_model": "intern-s2-preview",
        },
    )
    plan = {
        "request_id": "intern-1",
        "primary_model": "internai/intern-s2-preview",
        "fallback_chain": [],
        "provider": "internai",
        "max_tokens": 100,
        "metadata": {},
    }

    result = gateway.execute_request(plan, [{"role": "user", "content": "hello"}])

    assert result["requested_model"] == "internai/intern-s2-preview"
    assert result["resolved_model"] == "intern-s2-preview"
    assert result["provider_echo"] == "Intern-S2-Preview"
    assert ledger.status("internai")["local_consumed_tokens"] == 20


def test_expired_quota_window_fails_closed(tmp_path):
    ledger = ProviderBudgetLedger(tmp_path / "quota.sqlite3")
    expired = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    ledger.verify_balance("longcat", 65_000_000, expires_at=expired, source="account")

    with pytest.raises(BudgetDenied, match="expired"):
        ledger.reserve("expired-1", "longcat", 100)


def test_longcat_ramps_only_after_six_clean_hours(tmp_path, monkeypatch):
    now = [1_800_000_000.0]
    monkeypatch.setattr("nexus_os.model_relay.provider_budget.time.time", lambda: now[0])
    ledger = ProviderBudgetLedger(tmp_path / "quota.sqlite3")
    ledger.verify_balance("longcat", 65_000_000, expires_at=now[0] + 86_400, source="account")
    assert ledger.status("longcat")["current_rpm"] == 6

    now[0] += 6 * 3_600 + 1
    ledger.reserve("ramped-1", "longcat", 100)
    assert ledger.status("longcat")["current_rpm"] == 12


def test_server_error_uses_bounded_persistent_backoff(tmp_path):
    ledger = ProviderBudgetLedger(tmp_path / "quota.sqlite3")
    ledger.verify_balance("internai", 90_000_000, reset_at=_future_iso(), source="account")
    ledger.reserve("server-1", "internai", 100)
    ledger.fail("server-1", status_code=503, reason="upstream unavailable")

    status = ledger.status("internai")
    assert 50 <= status["cooldown_remaining_seconds"] <= 60
    with pytest.raises(BudgetDenied, match="cooldown"):
        ledger.reserve("server-2", "internai", 100)
