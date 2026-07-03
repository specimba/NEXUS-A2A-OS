from __future__ import annotations

from datetime import datetime, timedelta, timezone
import sqlite3

from nexus_os.model_relay.persistent_router import TIER_PRIMARY
from nexus_os.model_relay.provider_budget import ProviderBudgetLedger
from nexus_os.model_relay.quota_tracker import QuotaTracker


def _future_iso() -> str:
    return (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()


def test_governed_provider_selection_uses_durable_budget(tmp_path):
    ledger = ProviderBudgetLedger(tmp_path / "budget.sqlite3")
    tracker = QuotaTracker(tmp_path / "legacy.json", budget_ledger=ledger)

    assert tracker.is_quota_exhausted("longcat") is True
    assert tracker.is_quota_exhausted("internai") is True
    assert tracker.get_status("nim")["durable_provider"] == "nvidia"

    ledger.verify_balance(
        "longcat",
        65_000_000,
        expires_at=_future_iso(),
        source="test",
    )
    assert tracker.is_quota_exhausted("longcat") is False
    assert tracker.get_remaining_for_today("longcat") == 58_500_000


def test_selection_does_not_create_governed_dispatch_usage(tmp_path):
    database = tmp_path / "budget.sqlite3"
    ledger = ProviderBudgetLedger(database)
    tracker = QuotaTracker(tmp_path / "legacy.json", budget_ledger=ledger)

    tracker.record_call("longcat", "LongCat-2.0", tokens=10_000)
    tracker.record_call("nim", "nvidia/nemotron-3-ultra-550b-a55b", tokens=10_000)

    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM provider_requests").fetchone()[0] == 0


def test_primary_rotation_excludes_permanently_suspended_nim_models():
    primary = {(provider, model) for provider, model, _ in TIER_PRIMARY["models"]}

    assert ("nim", "z-ai/glm-5.1") not in primary
    assert ("nim", "moonshotai/kimi-k2-thinking") not in primary
    assert ("nim", "nvidia/devstral-2-123b") not in primary
    assert ("nim", "nvidia/nemotron-3-ultra-550b-a55b") in primary
    assert ("nim", "minimaxai/minimax-m3") in primary