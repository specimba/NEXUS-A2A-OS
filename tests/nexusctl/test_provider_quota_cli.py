from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone

from nexusctl.cli import main


def test_quota_status_is_json(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("NEXUS_PROVIDER_BUDGET_DB", str(tmp_path / "quota.sqlite3"))
    monkeypatch.setattr(sys, "argv", ["nexusctl", "quota", "status", "--json"])

    assert main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert {"longcat", "internai", "nvidia"} <= payload["providers"].keys()


def test_quota_verify_records_operator_telemetry(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("NEXUS_PROVIDER_BUDGET_DB", str(tmp_path / "quota.sqlite3"))
    expiry = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "nexusctl",
            "quota",
            "verify",
            "--provider",
            "longcat",
            "--remaining-tokens",
            "65000000",
            "--expires-at",
            expiry,
            "--source",
            "account-dashboard",
            "--json",
        ],
    )

    assert main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["provider"] == "longcat"
    assert payload["balance_verified"] is True


def test_quota_plan_refuses_unverified_schedule(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("NEXUS_PROVIDER_BUDGET_DB", str(tmp_path / "quota.sqlite3"))
    monkeypatch.setattr(
        sys,
        "argv",
        ["nexusctl", "quota", "plan", "--provider", "internai", "--json"],
    )

    assert main() == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["balance_verified"] is False
    assert payload["daily_budget_tokens"] is None
