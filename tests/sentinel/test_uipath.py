import httpx
import pytest

from nexus_os.sentinel.uipath import (
    UiPathClient,
    UiPathConfig,
    UiPathIntegrationError,
)


def _config(**overrides):
    values = {
        "enabled": True,
        "base_url": "https://cloud.uipath.example/org/tenant",
        "token_url": "https://cloud.uipath.example/identity_/connect/token",
        "client_id": "client",
        "client_secret": "secret",
        "folder_key": "folder",
        "process_key": "process",
        "deployment_id": "deployment",
        "process_version": "1.0.0",
    }
    values.update(overrides)
    return UiPathConfig(**values)


def test_uipath_disabled_by_default(monkeypatch):
    monkeypatch.delenv("NEXUS_UIPATH_ENABLED", raising=False)
    config = UiPathConfig.from_env()
    assert config.enabled is False
    with pytest.raises(UiPathIntegrationError, match="disabled"):
        config.validate()


def test_deployment_is_not_operational_without_successful_job():
    client = UiPathClient(_config())
    assert client.deployment_status()["operational"] is False
    assert client.deployment_status("job-1")["operational"] is True


def test_token_failure_is_closed_without_leaking_secret():
    def handler(request):
        return httpx.Response(401, json={"error": "invalid_client"})

    client = UiPathClient(_config(), httpx.MockTransport(handler))
    with pytest.raises(UiPathIntegrationError) as exc:
        client.start_process({})
    assert "secret" not in str(exc.value)


def test_process_start_uses_required_scopes_and_folder_header():
    seen = []

    def handler(request):
        seen.append(request)
        if request.url.path.endswith("/connect/token"):
            return httpx.Response(200, json={"access_token": "token-value"})
        return httpx.Response(201, json={"value": [{"Id": "job-1"}]})

    client = UiPathClient(_config(), httpx.MockTransport(handler))
    response = client.start_process({"case_id": "CASE-1"})
    assert response["value"][0]["Id"] == "job-1"
    assert seen[1].headers["x-uipath-folderkey"] == "folder"
    assert seen[1].headers["authorization"] == "Bearer token-value"
    assert b"OR.Default+OR.Execution+OR.Jobs" in seen[0].content



def test_unpublished_process_configuration_fails_closed():
    client = UiPathClient(_config(process_key=""))
    with pytest.raises(UiPathIntegrationError, match="process_key"):
        client.start_process({})


def test_missing_execution_scopes_fail_closed():
    def handler(request):
        return httpx.Response(403, json={"error": "insufficient_scope"})

    client = UiPathClient(_config(), httpx.MockTransport(handler))
    with pytest.raises(UiPathIntegrationError, match="403"):
        client.start_process({})


def test_expired_token_is_refreshed_once():
    tokens = 0
    starts = 0

    def handler(request):
        nonlocal tokens, starts
        if request.url.path.endswith("/connect/token"):
            tokens += 1
            return httpx.Response(200, json={"access_token": f"token-{tokens}"})
        starts += 1
        if starts == 1:
            return httpx.Response(401, json={"error": "expired"})
        return httpx.Response(201, json={"value": [{"Id": "job-2"}]})

    client = UiPathClient(_config(), httpx.MockTransport(handler))
    assert client.start_process({})["value"][0]["Id"] == "job-2"
    assert tokens == starts == 2


def test_job_evidence_requires_successful_job():
    failed = UiPathClient.job_evidence({"Id": "job-failed", "State": "Failed"})
    assert failed["live_verified"] is False
    successful = UiPathClient.job_evidence({"Id": "job-ok", "State": "Successful"})
    assert successful == {
        "job_id": "job-ok",
        "state": "SUCCESSFUL",
        "live_verified": True,
        "reason": None,
    }