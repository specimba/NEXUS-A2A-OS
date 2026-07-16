"""Safety contracts for the partner ModelRelay reconciler.

The helper deliberately works with an isolated JSON fixture.  It must never
need a live provider request to establish or test the configuration contract.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT_PATH = Path("scripts/reconcile_partner_modelrelay.py")
SPEC = importlib.util.spec_from_file_location("reconcile_partner_modelrelay", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
reconciler = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(reconciler)


def _config() -> dict:
    return {
        "apiKeys": {"nvidia": "existing-nvidia-secret"},
        "providers": {
            "nvidia": {"enabled": True},
            # These are historical custom records.  The live Node relay only
            # loads canonical openai-compatible instances.
            "longcat": {"baseUrl": "https://api.longcat.chat/openai", "models": ["LongCat-2.0-Preview"]},
            "internai": {"baseUrl": "https://chat.intern-ai.org.cn/api/v1", "models": ["intern-latest"]},
        },
        "unrelated": {"preserve": ["this", "exactly"]},
    }


def _write_config(tmp_path: Path, payload: dict | None = None) -> Path:
    path = tmp_path / ".modelrelay.json"
    path.write_text(json.dumps(payload if payload is not None else _config(), indent=2), encoding="utf-8")
    return path


def _env() -> dict[str, str]:
    return {
        "LONGCAT_MODELRELAY_API_KEY": "longcat-test-secret",
        "INTERN_MODELRELAY_API_KEY": "intern-test-secret",
    }


def test_report_mode_never_mutates_or_leaks_env_secret(tmp_path):
    path = _write_config(tmp_path)
    original = path.read_bytes()

    report = reconciler.reconcile_file(
        path,
        providers=("longcat", "internai"),
        apply=False,
        activate=False,
        environ=_env(),
    )

    assert path.read_bytes() == original
    assert report["mode"] == "report"
    assert report["providers"]["longcat"]["legacy_record_present"] is True
    assert report["providers"]["longcat"]["endpoint_state"] == "missing"
    assert report["providers"]["longcat"]["selected_key_env"] == "LONGCAT_MODELRELAY_API_KEY"
    assert report["inference_performed"] is False
    rendered = json.dumps(report)
    assert "longcat-test-secret" not in rendered
    assert "intern-test-secret" not in rendered


def test_apply_requires_each_selected_env_key_and_leaves_file_unchanged(tmp_path):
    path = _write_config(tmp_path)
    original = path.read_bytes()

    report = reconciler.reconcile_file(
        path,
        providers=("longcat", "internai"),
        apply=True,
        activate=False,
        environ={"LONGCAT_MODELRELAY_API_KEY": "longcat-test-secret"},
    )

    assert report["apply"]["ok"] is False
    assert report["apply"]["reason"] == "required_environment_key_missing"
    assert path.read_bytes() == original


def test_apply_stages_exact_endpoint_records_preserves_unrelated_data_and_backups(tmp_path):
    path = _write_config(tmp_path)
    original = path.read_bytes()

    report = reconciler.reconcile_file(
        path,
        providers=("longcat", "internai"),
        apply=True,
        activate=False,
        environ=_env(),
    )

    assert report["apply"]["ok"] is True
    assert report["mode"] == "applied_staged"
    written = json.loads(path.read_text(encoding="utf-8"))
    assert written["unrelated"] == _config()["unrelated"]
    assert written["apiKeys"]["openai-compatible:longcat"] == "longcat-test-secret"
    assert written["apiKeys"]["openai-compatible:internai"] == "intern-test-secret"
    assert written["providers"]["openai-compatible:longcat"] == {
        "name": "LongCat (governed partner)",
        "baseUrl": "https://api.longcat.chat/openai/v1",
        "modelId": "LongCat-2.0",
        "enabled": False,
        "discoverModels": False,
        "nexusManaged": "partner-provider-reconcile-v1",
    }
    assert written["providers"]["openai-compatible:internai"] == {
        "name": "InternAI (governed partner)",
        "baseUrl": "https://chat.intern-ai.org.cn/api/v1",
        "modelId": "intern-latest",
        "enabled": False,
        "discoverModels": True,
        "nexusManaged": "partner-provider-reconcile-v1",
    }
    assert path.with_name(".modelrelay.json.partner-reconcile.bak").read_bytes() == original
    rendered = json.dumps(report)
    assert "longcat-test-secret" not in rendered
    assert "intern-test-secret" not in rendered


def test_activate_is_separate_explicit_opt_in(tmp_path):
    path = _write_config(tmp_path)

    report = reconciler.reconcile_file(
        path,
        providers=("longcat",),
        apply=True,
        activate=True,
        environ=_env(),
    )

    assert report["mode"] == "applied_active"
    written = json.loads(path.read_text(encoding="utf-8"))
    assert written["providers"]["openai-compatible:longcat"]["enabled"] is True
    assert report["routing_eligibility_after_refresh"] == "may_become_eligible"


def test_conflicting_unmanaged_endpoint_refuses_to_overwrite(tmp_path):
    payload = _config()
    payload["providers"]["openai-compatible:longcat"] = {
        "name": "User owned endpoint",
        "baseUrl": "https://different.example/v1",
        "modelId": "different-model",
    }
    path = _write_config(tmp_path, payload)
    original = path.read_bytes()

    report = reconciler.reconcile_file(
        path,
        providers=("longcat",),
        apply=True,
        activate=False,
        environ=_env(),
    )

    assert report["providers"]["longcat"]["endpoint_state"] == "conflict_unmanaged"
    assert report["apply"]["ok"] is False
    assert report["apply"]["reason"] == "unmanaged_endpoint_conflict"
    assert path.read_bytes() == original


def test_runtime_probe_only_reports_sanitized_representation_state():
    def fake_fetch(url: str, timeout: float):
        del timeout
        if url.endswith("/api/config"):
            return [
                {"key": "openai-compatible:longcat", "enabled": False},
                {"key": "openai-compatible:internai", "enabled": True},
            ]
        if url.endswith("/api/models"):
            return {
                "models": [
                    {"providerKey": "openai-compatible:internai", "modelId": "intern-latest", "status": "pending"},
                ]
            }
        raise AssertionError(url)

    report = reconciler.probe_runtime("http://127.0.0.1:7350", fetch_json=fake_fetch)

    assert report["checked"] is True
    assert report["providers"]["longcat"]["endpoint_configured"] is True
    assert report["providers"]["longcat"]["model_rows"] == []
    assert report["providers"]["internai"]["model_rows"] == [
        {"model_id": "intern-latest", "status": "pending"}
    ]
