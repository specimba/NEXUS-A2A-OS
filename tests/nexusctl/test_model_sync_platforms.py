"""Platform, authentication, and preservation contracts for Hermes model sync.

These tests deliberately keep the live WSL config out of scope.  The apply
path is only allowed after ModelRelay proves that anonymous callers are
rejected and an environment-backed bearer credential can list models.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from nexusctl import model_sync


def _target(path: Path, **overrides):
    target = {
        "id": "hermes-wsl",
        "instance": "wsl",
        "distro": "Ubuntu",
        "config_path": str(path),
        "relay_base_url": "http://172.26.240.1:7350/v1",
        "key_env": "NEXUS_MODELRELAY_API_KEY",
    }
    target.update(overrides)
    return target


def _probe(*, ok=True, auth_enforced=True, models=None, reason="ready"):
    model_ids = models if models is not None else [
        model_sync.HERMES_PRIMARY_MODEL,
        "nexus-resilient",
        "deepseek-v4-pro",
    ]
    return {
        "ok": ok,
        "reason": reason,
        "auth_enforced": auth_enforced,
        "anonymous_status": 401 if auth_enforced else 200,
        "authenticated_status": 200 if ok else None,
        "models": model_ids,
        "model_count": len(model_ids),
        "missing_required_models": [],
    }

@pytest.fixture(autouse=True)
def _target_key_is_ready_by_default(monkeypatch):
    monkeypatch.setattr(
        model_sync,
        "probe_hermes_target_key_env",
        lambda *args, **kwargs: {
            "ok": True,
            "reason": "ready",
            "source": "hermes_env_file",
            "secure_permissions": True,
        },
    )


@pytest.mark.parametrize(
    ("path", "kind"),
    [
        (r"C:\\Tools\\hermes.exe", "windows-exe"),
        (r"C:\\Tools\\hermes.cmd", "windows-cmd"),
        (r"C:\\Tools\\hermes.bat", "windows-bat"),
        (r"C:\\Tools\\hermes.ps1", "powershell-script"),
        ("/home/speci/.local/bin/hermes", "linux-native"),
    ],
)
def test_binary_classification_distinguishes_windows_shims_and_linux(path, kind):
    assert model_sync.classify_cli_binary(path) == kind


def test_wsl_gateway_uses_dynamic_default_route_before_nameserver():
    calls = []

    def runner(cmd, **kwargs):
        calls.append(cmd)
        return SimpleNamespace(returncode=0, stdout="default via 172.26.240.1 dev eth0\n", stderr="")

    assert model_sync.resolve_wsl_windows_gateway("Ubuntu", runner=runner) == "172.26.240.1"
    assert calls[0][-4:] == ["ip", "route", "show", "default"]


def test_wsl_gateway_falls_back_to_resolv_nameserver_and_rejects_junk():
    responses = iter(
        [
            SimpleNamespace(returncode=1, stdout="", stderr="no route"),
            SimpleNamespace(returncode=0, stdout="nameserver 172.20.0.1\n", stderr=""),
        ]
    )
    assert model_sync.resolve_wsl_windows_gateway(
        "Ubuntu", runner=lambda *args, **kwargs: next(responses)
    ) == "172.20.0.1"

    bad = iter(
        [
            SimpleNamespace(returncode=0, stdout="default via not-an-ip dev eth0\n", stderr=""),
            SimpleNamespace(returncode=0, stdout="nameserver also-bad\n", stderr=""),
        ]
    )
    assert model_sync.resolve_wsl_windows_gateway(
        "Ubuntu", runner=lambda *args, **kwargs: next(bad)
    ) is None


def test_hermes_target_discovery_distinguishes_windows_and_wsl(tmp_path):
    win_home = tmp_path / "windows-home"
    (win_home / ".hermes").mkdir(parents=True)
    (win_home / ".hermes" / "config.yaml").write_text("model: keep\n", encoding="utf-8")

    def runner(cmd, **kwargs):
        if cmd[-2:] == ["printenv", "HOME"]:
            return SimpleNamespace(returncode=0, stdout="/home/speci\n", stderr="")
        if cmd[-2:] == ["which", "hermes"]:
            return SimpleNamespace(returncode=1, stdout="", stderr="")
        return SimpleNamespace(returncode=1, stdout="", stderr="")

    targets = model_sync.discover_hermes_targets(
        home=win_home,
        distro="Ubuntu",
        runner=runner,
        which=lambda _name: r"C:\\Tools\\hermes.cmd",
    )
    by_id = {target["id"]: target for target in targets}

    assert set(by_id) == {"hermes", "hermes-wsl"}
    assert by_id["hermes"]["instance"] == "windows"
    assert by_id["hermes"]["binary_kind"] == "windows-cmd"
    assert by_id["hermes-wsl"]["instance"] == "wsl"
    assert by_id["hermes-wsl"]["config_path_posix"] == "/home/speci/.hermes/config.yaml"
    assert by_id["hermes-wsl"]["binary_kind"] == "linux-native"


def test_resolved_targets_replace_legacy_hermes_with_both_instances(monkeypatch):
    discovered = [
        {"id": "hermes", "name": "Windows", "config_path": "win", "config_format": "yaml"},
        {"id": "hermes-wsl", "name": "WSL", "config_path": "wsl", "config_format": "yaml"},
    ]
    monkeypatch.setattr(model_sync, "discover_hermes_targets", lambda: discovered)

    ids = [target["id"] for target in model_sync.resolved_cli_targets()]

    assert ids.count("hermes") == 1
    assert ids.count("hermes-wsl") == 1


@pytest.mark.parametrize(
    ("only", "expected"),
    [
        ("hermes", ["hermes", "hermes-wsl"]),
        ("hermes-wsl", ["hermes-wsl"]),
    ],
)
def test_main_routes_legacy_hermes_alias_to_both_instances(
    only,
    expected,
    monkeypatch,
    capsys,
):
    state = {
        "timestamp": "2026-07-11T00:00:00Z",
        "lanes": [],
        "models": [],
        "god_proxy_alive": True,
        "node_relay_alive": True,
    }
    targets = [
        {"id": "hermes", "name": "Windows", "config_path": "win", "config_format": "yaml"},
        {"id": "hermes-wsl", "name": "WSL", "config_path": "wsl", "config_format": "yaml"},
    ]
    calls = []

    def handler(_state, target, dry_run):
        calls.append((target["id"], dry_run))
        return {"target": target["id"], "ok": True, "dry_run": dry_run}

    monkeypatch.setattr(model_sync, "fetch_live_state", lambda refresh=False: state)
    monkeypatch.setattr(model_sync, "resolved_cli_targets", lambda: targets)
    monkeypatch.setitem(model_sync.SYNC_HANDLERS, "hermes", handler)
    monkeypatch.setitem(model_sync.SYNC_HANDLERS, "hermes-wsl", handler)

    assert model_sync.main(["--dry-run", "--only", only]) == 0
    assert [target_id for target_id, _ in calls] == expected
    assert all(dry_run for _, dry_run in calls)
    assert json.loads(capsys.readouterr().out)["dry_run"] is True


def test_main_dry_run_never_revives_dead_relays(monkeypatch, capsys):
    dead_state = {
        "timestamp": "2026-07-14T00:00:00Z",
        "lanes": [],
        "models": [],
        "god_proxy_alive": False,
        "node_relay_alive": False,
    }
    revive_calls = []
    monkeypatch.setattr(model_sync, "fetch_live_state", lambda refresh=False: dead_state)
    monkeypatch.setattr(
        model_sync,
        "_auto_revive_relays",
        lambda: revive_calls.append("called") or True,
    )

    assert model_sync.main(["--dry-run", "--only", "hermes-wsl"]) == 2
    payload = json.loads(capsys.readouterr().out)
    assert revive_calls == []
    assert payload["dry_run"] is True
    assert payload["auto_revive_attempted"] is False


def test_package_cli_can_target_wsl_hermes_instance(monkeypatch):
    from nexusctl import cli

    observed: dict[str, list[str]] = {}

    def fake_main(argv):
        observed["argv"] = list(argv)
        return 0

    monkeypatch.setattr(model_sync, "main", fake_main)
    monkeypatch.setattr(sys, "argv", ["nexusctl", "model-sync", "--dry-run", "--only", "hermes-wsl"])



def test_hermes_target_discovery_has_auditable_wsl_home_fallback(tmp_path):
    win_home = tmp_path / "speci.000"
    win_home.mkdir()

    def unavailable(*args, **kwargs):
        return SimpleNamespace(returncode=1, stdout="", stderr="blocked")

    targets = model_sync.discover_hermes_targets(
        home=win_home,
        distro="Ubuntu",
        runner=unavailable,
        which=lambda _name: None,
    )
    wsl = next(target for target in targets if target["id"] == "hermes-wsl")

    assert wsl["config_path_posix"] == "/home/speci/.hermes/config.yaml"
    assert wsl["discovery_source"] == "configured_fallback"


def test_wsl_cli_inventory_reports_installed_and_not_installed_without_config_probe():
    observed = {}

    def runner(cmd, **kwargs):
        observed["cmd"] = cmd
        observed["kwargs"] = kwargs
        return SimpleNamespace(
            returncode=0,
            stdout=(
                "opencode\tinstalled\t/home/speci/.local/bin/opencode\n"
                "mimo\tnot_installed\t\n"
                "kilo\tinstalled\t/usr/local/bin/kilo\n"
                "pi\tnot_installed\t\n"
            ),
            stderr="",
        )

    rows = model_sync.discover_wsl_cli_inventory(distro="Ubuntu", runner=runner)
    by_id = {row["id"]: row for row in rows}

    assert observed["cmd"][:6] == ["wsl.exe", "-d", "Ubuntu", "--exec", "sh", "-c"]
    assert "input" not in observed["kwargs"]
    assert by_id["opencode-wsl"]["binary_installed"] is True
    assert by_id["opencode-wsl"]["binary_path"] == "/home/speci/.local/bin/opencode"
    assert by_id["mimo-wsl"]["binary_installed"] is False
    assert by_id["mimo-wsl"]["binary_status"] == "not_installed"
    assert by_id["kilo-wsl"]["binary_kind"] == "linux-native"
    assert all(row["discovery_status"] == "available" for row in rows)
    assert all(row["config_discovery_status"] == "not_attempted" for row in rows)
    assert all(row["config_path"] is None for row in rows)
    assert all(row["sync_supported"] is False for row in rows)


def test_wsl_cli_inventory_marks_access_denied_as_blocked_not_not_installed():
    rows = model_sync.discover_wsl_cli_inventory(
        distro="Ubuntu",
        runner=lambda *args, **kwargs: SimpleNamespace(
            returncode=1,
            stdout="",
            stderr="Wsl/Service/E_ACCESSDENIED",
        ),
    )

    assert {row["binary_status"] for row in rows} == {"unknown"}
    assert {row["binary_installed"] for row in rows} == {None}
    assert {row["discovery_status"] for row in rows} == {"blocked"}
    assert {row["discovery_reason"] for row in rows} == {"wsl_service_access_denied"}
    assert all(row["config_discovery_status"] == "not_attempted" for row in rows)


def test_cli_inventory_includes_read_only_wsl_observations(tmp_path, monkeypatch):
    windows_target = {
        "id": "opencode",
        "name": "OpenCode",
        "version_cmd": ["opencode", "--version"],
        "config_path": tmp_path / "opencode.json",
        "config_format": "json",
    }
    blocked_wsl_row = {
        "id": "opencode-wsl",
        "source_id": "opencode",
        "name": "OpenCode (WSL)",
        "instance": "wsl",
        "distro": "Ubuntu",
        "binary_name": "opencode",
        "binary_path": None,
        "binary_kind": "unknown",
        "binary_installed": None,
        "binary_status": "unknown",
        "discovery_status": "blocked",
        "discovery_reason": "wsl_service_access_denied",
        "config_discovery_status": "not_attempted",
        "config_path": None,
        "config_format": "json",
    }
    monkeypatch.setattr(
        model_sync,
        "discover_wsl_cli_inventory",
        lambda: [blocked_wsl_row],
    )
    monkeypatch.setattr(
        model_sync.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )

    payload = model_sync.list_cli_inventory({"lanes": [], "models": []}, targets=[windows_target])
    by_id = {row["id"]: row for row in payload["clis"]}

    assert by_id["opencode"]["binary_installed"] is True
    assert by_id["opencode-wsl"]["discovery_status"] == "blocked"
    assert by_id["opencode-wsl"]["binary_installed"] is None


def test_authenticated_probe_requires_anonymous_rejection_and_projects_glm(monkeypatch):
    calls = []

    def requester(url, token, timeout):
        calls.append((url, token, timeout))
        if token is None:
            return 401, None
        return 200, {
            "data": [
                {"id": model_sync.HERMES_PRIMARY_MODEL},
                {"id": "nexus-resilient"},
                {"id": "deepseek-v4-pro"},
            ]
        }

    result = model_sync.probe_modelrelay_v1(
        "http://172.26.240.1:7350/v1",
        token_env="NEXUS_MODELRELAY_API_KEY",
        environ={"NEXUS_MODELRELAY_API_KEY": "test-secret"},
        requester=requester,
    )

    assert result["ok"] is True
    assert result["auth_enforced"] is True
    assert result["models"] == [
        model_sync.HERMES_PRIMARY_MODEL,
        "nexus-resilient",
        "deepseek-v4-pro",
    ]
    assert calls[0][0].endswith("/v1/models") and calls[0][1] is None
    assert calls[1][1] == "test-secret"
    assert "test-secret" not in json.dumps(result)


def test_authenticated_probe_requires_the_exact_locked_glm_route():
    def requester(_url, token, _timeout):
        if token is None:
            return 401, None
        return 200, {"data": [{"id": "z-ai/glm-5.2"}]}

    result = model_sync.probe_modelrelay_v1(
        "http://172.26.240.1:7350/v1",
        environ={"NEXUS_MODELRELAY_API_KEY": "test-secret"},
        requester=requester,
    )

    assert result["ok"] is False
    assert result["reason"] == "required_models_missing"
    assert result["missing_required_models"] == [
        model_sync.HERMES_PRIMARY_MODEL,
        "nexus-resilient",
    ]
    assert result["models"] == ["z-ai/glm-5.2"]


def test_probe_rejects_public_catalog_even_when_models_are_present():
    def requester(_url, token, _timeout):
        assert token is None
        return 200, {"data": [{"id": "glm-5.2"}]}

    result = model_sync.probe_modelrelay_v1(
        "http://172.26.240.1:7350/v1",
        token_env="NEXUS_MODELRELAY_API_KEY",
        environ={},
        requester=requester,
    )

    assert result["ok"] is False
    assert result["auth_enforced"] is False
    assert result["models"] == ["glm-5.2"]
    assert result["reason"] == "anonymous_catalog_accessible"


def test_wsl_probe_passes_secret_over_stdin_not_process_arguments():
    observed = {}

    def runner(cmd, **kwargs):
        observed["cmd"] = cmd
        observed["input"] = kwargs["input"]
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps({"status": 200, "payload": {"data": [{"id": "glm-5.2"}]}}),
            stderr="",
        )

    status, payload = model_sync._wsl_http_json_request(
        "Ubuntu",
        "http://172.26.240.1:7350/v1/models",
        token="test-secret",
        runner=runner,
    )

    assert status == 200 and payload["data"][0]["id"] == "glm-5.2"
    assert "--exec" in observed["cmd"]
    assert "test-secret" not in " ".join(observed["cmd"])
    assert json.loads(observed["input"])["token"] == "test-secret"


def test_relay_bearer_loader_prefers_environment_then_private_file(tmp_path):
    token_file = tmp_path / "relay.token"
    token_file.write_text("file-secret-value", encoding="utf-8")

    assert model_sync.load_modelrelay_bearer(
        environ={"NEXUS_MODELRELAY_API_KEY": "env-secret-value"},
        token_path=token_file,
    ) == "env-secret-value"
    assert model_sync.load_modelrelay_bearer(
        environ={},
        token_path=token_file,
    ) == "file-secret-value"


def test_wsl_config_io_keeps_path_and_content_out_of_process_arguments():
    observed = {}

    def runner(cmd, **kwargs):
        observed["cmd"] = cmd
        observed["request"] = json.loads(kwargs["input"])
        return SimpleNamespace(returncode=0, stdout=json.dumps({"ok": True}), stderr="")

    result = model_sync._wsl_config_request(
        "Ubuntu",
        "/home/speci/.hermes/config.yaml",
        operation="write",
        content="key_env: PRIVATE_NAME\nsecret_marker: never-in-argv\n",
        runner=runner,
    )

    argv = " ".join(observed["cmd"])
    assert result["ok"] is True
    assert "--exec" in observed["cmd"]
    assert "/home/speci/.hermes/config.yaml" not in argv
    assert "never-in-argv" not in argv
    assert observed["request"]["operation"] == "write"
    assert observed["request"]["path"] == "/home/speci/.hermes/config.yaml"
    assert "never-in-argv" in observed["request"]["content"]


def test_wsl_config_io_reports_access_denied_without_exposing_stderr():
    def runner(_cmd, **_kwargs):
        return SimpleNamespace(
            returncode=-1,
            stdout="Access is denied.\x00 WSL/Service/CreateInstance/E_ACCESS_DENIED",
            stderr="",
        )

    result = model_sync._wsl_config_request(
        "Ubuntu",
        "/home/speci/.hermes/config.yaml",
        operation="read",
        runner=runner,
    )

    assert result == {"ok": False, "error": "wsl_access_denied"}


def test_hermes_wsl_sync_uses_stdin_io_and_preserves_nonprovider_settings(monkeypatch):
    original = "default_model: grok-build-0.1\ntheme: dark\nproviders: {}\n"
    requests = []

    def config_io(_distro, _path, *, operation, content=None, runner=None):
        requests.append((operation, content))
        if operation == "read":
            return {"ok": True, "content": original}
        return {"ok": True}

    target = _target(
        Path(r"\\wsl.localhost\Ubuntu\home\speci\.hermes\config.yaml"),
        config_path_posix="/home/speci/.hermes/config.yaml",
    )
    monkeypatch.setattr(model_sync, "_wsl_config_request", config_io)
    monkeypatch.setattr(model_sync, "probe_modelrelay_for_target", lambda *a, **k: _probe())

    result = model_sync.sync_hermes({}, target, dry_run=False)

    assert result["ok"] is True and result["written"] is True
    assert [operation for operation, _ in requests] == ["read", "write"]
    written = yaml.safe_load(requests[-1][1])
    assert written["default_model"] == "grok-build-0.1"
    assert written["theme"] == "dark"
    assert written["providers"]["modelrelay"]["key_env"] == "NEXUS_MODELRELAY_API_KEY"
    assert "api_key" not in written["providers"]["modelrelay"]


def test_hermes_dry_run_is_modelrelay_only_and_never_changes_file(tmp_path, monkeypatch):
    path = tmp_path / "config.yaml"
    original = "default_model: grok-build-0.1\ndefault_provider: xai-oauth\nproviders: {}\n"
    path.write_text(original, encoding="utf-8")
    monkeypatch.setattr(
        model_sync,
        "probe_modelrelay_for_target",
        lambda *args, **kwargs: _probe(ok=False, auth_enforced=False, reason="anonymous_catalog_accessible"),
    )

    result = model_sync.sync_hermes({}, _target(path), dry_run=True)

    assert result["ok"] is True
    assert result["apply_ready"] is False
    assert result["providers_added"] == ["modelrelay"]
    assert result["models_projected"] == 3
    assert result["required_models_present"] is True
    assert result["provider_preview"]["key_env"] == "NEXUS_MODELRELAY_API_KEY"
    assert "api_key" not in result["provider_preview"]
    assert path.read_text(encoding="utf-8") == original


def test_hermes_apply_is_blocked_until_bearer_auth_is_enforced(tmp_path, monkeypatch):
    path = tmp_path / "config.yaml"
    original = "model: grok-build-0.1\nprovider: xai-oauth\nproviders: {}\n"
    path.write_text(original, encoding="utf-8")
    monkeypatch.setattr(
        model_sync,
        "probe_modelrelay_for_target",
        lambda *args, **kwargs: _probe(ok=False, auth_enforced=False, reason="anonymous_catalog_accessible"),
    )

    result = model_sync.sync_hermes({}, _target(path), dry_run=False)

    assert result["ok"] is False
    assert result["reason"] == "anonymous_catalog_accessible"
    assert result["written"] is False
    assert path.read_text(encoding="utf-8") == original
    assert not path.with_name("config.yaml.nexus-sync.bak").exists()


def test_hermes_apply_requires_glm52_in_authenticated_projection(tmp_path, monkeypatch):
    path = tmp_path / "config.yaml"
    original = "model: keep\nproviders: {}\n"
    path.write_text(original, encoding="utf-8")
    monkeypatch.setattr(
        model_sync,
        "probe_modelrelay_for_target",
        lambda *args, **kwargs: _probe(models=["deepseek-v4-pro"]),
    )

    result = model_sync.sync_hermes({}, _target(path), dry_run=False)

    assert result["ok"] is False
    assert result["reason"] == "required_models_missing"
    assert result["missing_required_models"] == [
        model_sync.HERMES_PRIMARY_MODEL,
        "nexus-resilient",
    ]
    assert path.read_text(encoding="utf-8") == original


def test_hermes_apply_preserves_defaults_and_writes_only_managed_modelrelay(tmp_path, monkeypatch):
    path = tmp_path / "config.yaml"
    original = (
        "default_model: grok-build-0.1\n"
        "default_provider: xai-oauth\n"
        "theme: dark\n"
        "providers:\n"
        "  user_private:\n"
        "    base_url: https://example.invalid/v1\n"
        "    key_env: USER_PRIVATE_KEY\n"
        "  modelrelay:\n"
        "    base_url: http://127.0.0.1:7350/v1\n"
        "# === nexusctl model-sync providers (managed) ===\n"
        "nvidia_nim:\n"
        "  api_key: should-disappear\n"
        "# === end nexusctl managed ===\n"
    )
    path.write_text(original, encoding="utf-8")
    monkeypatch.setattr(
        model_sync,
        "probe_modelrelay_for_target",
        lambda *args, **kwargs: _probe(),
    )

    result = model_sync.sync_hermes({}, _target(path), dry_run=False)

    assert result["ok"] is True and result["written"] is True
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert cfg["default_model"] == "grok-build-0.1"
    assert cfg["default_provider"] == "xai-oauth"
    assert cfg["theme"] == "dark"
    assert cfg["providers"]["user_private"]["key_env"] == "USER_PRIVATE_KEY"
    managed = cfg["providers"]["modelrelay"]
    assert managed["base_url"] == "http://172.26.240.1:7350/v1"
    assert managed["key_env"] == "NEXUS_MODELRELAY_API_KEY"
    assert managed["discover_models"] is False
    assert set(managed["models"]) == {
        model_sync.HERMES_PRIMARY_MODEL,
        "nexus-resilient",
        "deepseek-v4-pro",
    }
    text = path.read_text(encoding="utf-8")
    assert "nvidia_nim" not in text
    assert "should-disappear" not in text
    assert "api_key:" not in text
    assert text.count("  modelrelay:") == 1


def test_hermes_atomic_write_failure_keeps_original(tmp_path, monkeypatch):
    path = tmp_path / "config.yaml"
    original = "model: keep\nproviders: {}\n"
    path.write_text(original, encoding="utf-8")
    monkeypatch.setattr(model_sync, "probe_modelrelay_for_target", lambda *a, **k: _probe())

    def fail_replace(_source, _target):
        raise PermissionError("synthetic replace failure")

    monkeypatch.setattr(model_sync.os, "replace", fail_replace)
    result = model_sync.sync_hermes({}, _target(path), dry_run=False)

    assert result["ok"] is False
    assert result["reason"] == "write_failed"
    assert result["written"] is False
    assert path.read_text(encoding="utf-8") == original


def test_hermes_write_validation_failure_keeps_original(tmp_path, monkeypatch):
    path = tmp_path / "config.yaml"
    original = "model: keep\nproviders: {}\n"
    path.write_text(original, encoding="utf-8")
    monkeypatch.setattr(model_sync, "probe_modelrelay_for_target", lambda *a, **k: _probe())
    monkeypatch.setattr(model_sync, "_validate_hermes_candidate", lambda *a, **k: "synthetic failure")

    result = model_sync.sync_hermes({}, _target(path), dry_run=False)

    assert result["ok"] is False
    assert result["reason"] == "candidate_validation_failed"
    assert path.read_text(encoding="utf-8") == original



def test_hermes_apply_blocks_when_target_key_env_is_unresolved(tmp_path, monkeypatch):
    path = tmp_path / "config.yaml"
    original = "model: keep\nproviders: {}\n"
    path.write_text(original, encoding="utf-8")
    monkeypatch.setattr(model_sync, "probe_modelrelay_for_target", lambda *a, **k: _probe())
    monkeypatch.setattr(
        model_sync,
        "probe_hermes_target_key_env",
        lambda *args, **kwargs: {
            "ok": False,
            "reason": "target_key_env_unresolved",
            "source": None,
            "secure_permissions": None,
        },
    )

    result = model_sync.sync_hermes({}, _target(path), dry_run=False)

    assert result["ok"] is False
    assert result["apply_ready"] is False
    assert result["reason"] == "target_key_env_unresolved"
    assert result["target_key_resolved"] is False
    assert result["target_key_source"] is None
    assert path.read_text(encoding="utf-8") == original
    assert not path.with_name("config.yaml.nexus-sync.bak").exists()


def test_hermes_active_modelrelay_runtime_migrates_to_resilient_fallback(
    tmp_path,
    monkeypatch,
):
    path = tmp_path / "config.yaml"
    original = (
        "_config_version: 1\n"
        "model:\n"
        "  default: glm-5.2\n"
        "  provider: modelrelay\n"
        "  base_url: http://127.0.0.1:7350/v1\n"
        "  reasoning_effort: medium\n"
        "agent:\n"
        "  api_max_retries: 3\n"
        "  max_tool_iterations: 60\n"
        "fallback_providers:\n"
        "  - provider: modelrelay\n"
        "    model: labs-leanstral-1-5-1\n"
        "    base_url: http://127.0.0.1:7350/v1\n"
        "auxiliary:\n"
        "  summarization:\n"
        "    provider: auto\n"
        "  title_generation:\n"
        "    provider: auto\n"
        "    max_tokens: 32\n"
        "    key_env: LEGACY_TITLE_KEY\n"
        "theme: dark\n"
        "providers: {}\n"
    )
    path.write_text(original, encoding="utf-8")
    monkeypatch.setattr(model_sync, "probe_modelrelay_for_target", lambda *a, **k: _probe())

    result = model_sync.sync_hermes({}, _target(path), dry_run=False)

    assert result["ok"] is True
    assert result["runtime_settings_managed"] is True
    assert result["api_max_retries"] == 1
    assert result["fallback_model"] == "nexus-resilient"
    assert result["auxiliary_title_model"] == "nexus-resilient"
    written = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert written["model"]["base_url"] == "http://172.26.240.1:7350/v1"
    assert written["model"]["default"] == model_sync.HERMES_PRIMARY_MODEL
    assert written["model"]["reasoning_effort"] == "medium"
    assert written["agent"]["api_max_retries"] == 1
    assert written["agent"]["max_tool_iterations"] == 60
    assert written["theme"] == "dark"
    assert written["auxiliary"]["summarization"] == {"provider": "auto"}
    assert written["auxiliary"]["title_generation"] == {
        "provider": "modelrelay",
        "model": "nexus-resilient",
        "max_tokens": 32,
    }
    assert written["fallback_providers"][0] == {
        "provider": "modelrelay",
        "model": "nexus-resilient",
        "base_url": "http://172.26.240.1:7350/v1",
    }
    assert "key_env" not in written["fallback_providers"][0]
    assert "key_env" not in written["auxiliary"]["title_generation"]
    assert written["providers"]["modelrelay"]["key_env"] == "NEXUS_MODELRELAY_API_KEY"
    assert all(
        fallback.get("model") != "labs-leanstral-1-5-1"
        for fallback in written["fallback_providers"]
    )

    first = path.read_text(encoding="utf-8")
    result = model_sync.sync_hermes({}, _target(path), dry_run=False)
    assert result["ok"] is True
    assert path.read_text(encoding="utf-8") == first


def test_hermes_active_modelrelay_preserves_an_explicit_non_glm_choice(
    tmp_path,
    monkeypatch,
):
    path = tmp_path / "config.yaml"
    path.write_text(
        "model:\n"
        "  default: deepseek-v4-pro\n"
        "  provider: modelrelay\n"
        "  base_url: http://127.0.0.1:7350/v1\n"
        "providers: {}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(model_sync, "probe_modelrelay_for_target", lambda *a, **k: _probe())

    result = model_sync.sync_hermes({}, _target(path), dry_run=False)

    assert result["ok"] is True
    written = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert written["model"]["default"] == "deepseek-v4-pro"


def test_hermes_validation_rejects_a_managed_bare_glm_primary():
    original = (
        "model:\n"
        "  default: glm-5.2\n"
        "  provider: modelrelay\n"
        "  base_url: http://127.0.0.1:7350/v1\n"
        "providers: {}\n"
    )
    provider = model_sync._hermes_modelrelay_provider(
        "http://127.0.0.1:7350/v1",
        "NEXUS_MODELRELAY_API_KEY",
        [model_sync.HERMES_PRIMARY_MODEL, "nexus-resilient"],
    )
    runtime, _ = model_sync._reconcile_hermes_runtime_settings(
        original,
        "http://127.0.0.1:7350/v1",
        "NEXUS_MODELRELAY_API_KEY",
    )
    candidate = model_sync._replace_hermes_managed_block(
        runtime,
        model_sync._render_hermes_managed_block(provider),
    )
    parsed = yaml.safe_load(candidate)
    parsed["model"]["default"] = "glm-5.2"

    error = model_sync._validate_hermes_candidate(
        original,
        yaml.safe_dump(parsed, sort_keys=False),
        expected_base_url="http://127.0.0.1:7350/v1",
    )

    assert error == "active modelrelay primary model mismatch"


def test_hermes_managed_fallback_uses_supported_entry_fields():
    fallback = model_sync._managed_hermes_fallback("http://172.26.240.1:7350/v1")

    assert fallback == {
        "provider": "modelrelay",
        "model": "nexus-resilient",
        "base_url": "http://172.26.240.1:7350/v1",
    }


def test_hermes_inactive_provider_does_not_manage_auxiliary():
    original = (
        "model: grok-build-0.1\n"
        "provider: xai-oauth\n"
        "auxiliary:\n"
        "  title_generation:\n"
        "    provider: auto\n"
    )

    candidate, managed = model_sync._reconcile_hermes_runtime_settings(
        original,
        "http://127.0.0.1:7350/v1",
        "NEXUS_MODELRELAY_API_KEY",
    )

    assert managed is False
    assert candidate == original


def test_hermes_validation_rejects_missing_auxiliary_title_route():
    original = (
        "model:\n"
        "  default: glm-5.2\n"
        "  provider: modelrelay\n"
        "providers: {}\n"
    )
    provider = model_sync._hermes_modelrelay_provider(
        "http://127.0.0.1:7350/v1",
        "NEXUS_MODELRELAY_API_KEY",
        [model_sync.HERMES_PRIMARY_MODEL, "nexus-resilient"],
    )
    runtime, _ = model_sync._reconcile_hermes_runtime_settings(
        original,
        "http://127.0.0.1:7350/v1",
        "NEXUS_MODELRELAY_API_KEY",
    )
    candidate = model_sync._replace_hermes_managed_block(
        runtime,
        model_sync._render_hermes_managed_block(provider),
    )
    parsed = yaml.safe_load(candidate)
    parsed["auxiliary"].pop("title_generation")
    candidate = yaml.safe_dump(parsed, sort_keys=False)

    error = model_sync._validate_hermes_candidate(
        original,
        candidate,
        expected_base_url="http://127.0.0.1:7350/v1",
    )

    assert error == "active modelrelay auxiliary title route missing"



def test_hermes_key_provisioning_uses_stdin_and_returns_no_secret():
    observed = {}

    def runner(cmd, **kwargs):
        observed["cmd"] = cmd
        observed["request"] = json.loads(kwargs["input"])
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps({
                "ok": True,
                "reason": "ready",
                "source": "hermes_env_file",
                "secure_permissions": True,
                "changed": True,
            }),
            stderr="",
        )

    target = _target(
        Path(r"\\wsl.localhost\Ubuntu\home\speci\.hermes\config.yaml"),
        config_path_posix="/home/speci/.hermes/config.yaml",
        env_path_posix="/home/speci/.hermes/.env",
    )
    result = model_sync.provision_hermes_target_key_env(
        target,
        token="test-secret-value",
        runner=runner,
    )

    assert result == {
        "ok": True,
        "reason": "ready",
        "source": "hermes_env_file",
        "secure_permissions": True,
        "changed": True,
    }
    assert "test-secret-value" not in " ".join(observed["cmd"])
    assert "test-secret-value" not in json.dumps(result)
    assert observed["request"] == {
        "name": "NEXUS_MODELRELAY_API_KEY",
        "value": "test-secret-value",
        "env_path": "/home/speci/.hermes/.env",
    }
