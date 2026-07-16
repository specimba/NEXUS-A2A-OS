from types import SimpleNamespace

from nexusctl.model_team_cli import run_model_team


def _args(command, **kwargs):
    base = {
        "model_team_command": command,
        "role": "Planner",
        "provider": "longcat",
        "model": "LongCat-2.0",
        "live": False,
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_model_team_lists_current_longcat_and_intern_aliases(monkeypatch, tmp_path):
    monkeypatch.setenv("NEXUS_PROVIDER_BUDGET_DB", str(tmp_path / "quota.sqlite3"))

    code, payload = run_model_team(_args("list"))

    assert code == 0
    assert payload["active_models"]["LongCat-2.0"] is True
    assert payload["active_models"]["LongCat-2.0-Preview"] is False
    assert payload["active_models"]["intern-s2-preview"] is True
    assert payload["active_models"]["intern-latest"] is True
    assert payload["active_models"]["internvl3.5-latest"] is True


def test_model_team_plan_is_quota_aware_and_serialized(monkeypatch, tmp_path):
    monkeypatch.setenv("NEXUS_PROVIDER_BUDGET_DB", str(tmp_path / "quota.sqlite3"))

    code, payload = run_model_team(_args("plan", role="Planner"))

    assert code == 0
    assert payload["plan"]["preferred_provider"] == "longcat"
    assert payload["plan"]["preferred_model"] == "LongCat-2.0"
    assert payload["plan"]["rpm_limit"] <= 6
    assert payload["quota"]["concurrency_limit"] == 1


def test_model_team_probe_rejects_retired_longcat_preview(monkeypatch, tmp_path):
    monkeypatch.setenv("NEXUS_PROVIDER_BUDGET_DB", str(tmp_path / "quota.sqlite3"))

    ok_code, ok_payload = run_model_team(_args("probe", provider="longcat", model="LongCat-2.0"))
    blocked_code, blocked_payload = run_model_team(_args("probe", provider="longcat", model="LongCat-2.0-Preview"))

    assert ok_code == 0
    assert ok_payload["status"] == "ok"
    assert blocked_code == 2
    assert blocked_payload["status"] == "blocked"
    assert blocked_payload["provider_known"] is True
    assert blocked_payload["model_known"] is False
