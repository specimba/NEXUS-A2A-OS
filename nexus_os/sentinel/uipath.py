"""Optional UiPath enterprise integration boundary."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx


class UiPathIntegrationError(RuntimeError):
    pass


@dataclass(frozen=True)
class UiPathConfig:
    enabled: bool
    base_url: str
    token_url: str
    client_id: str
    client_secret: str
    folder_key: str
    process_key: str
    deployment_id: str
    process_version: str
    mcp_url: str = ""

    @classmethod
    def from_env(cls) -> "UiPathConfig":
        return cls(
            enabled=os.getenv("NEXUS_UIPATH_ENABLED", "false").lower() == "true",
            base_url=os.getenv("NEXUS_UIPATH_BASE_URL", ""),
            token_url=os.getenv(
                "NEXUS_UIPATH_TOKEN_URL",
                "https://cloud.uipath.com/identity_/connect/token",
            ),
            client_id=os.getenv("NEXUS_UIPATH_CLIENT_ID", ""),
            client_secret=os.getenv("NEXUS_UIPATH_CLIENT_SECRET", ""),
            folder_key=os.getenv("NEXUS_UIPATH_FOLDER_KEY", ""),
            process_key=os.getenv("NEXUS_UIPATH_PROCESS_KEY", ""),
            deployment_id=os.getenv("NEXUS_UIPATH_DEPLOYMENT_ID", ""),
            process_version=os.getenv("NEXUS_UIPATH_PROCESS_VERSION", ""),
            mcp_url=os.getenv("NEXUS_UIPATH_MCP_URL", ""),
        )

    def validate(self) -> None:
        if not self.enabled:
            raise UiPathIntegrationError("UiPath integration is disabled")
        missing = [
            name
            for name in (
                "base_url",
                "client_id",
                "client_secret",
                "folder_key",
                "process_key",
                "deployment_id",
                "process_version",
            )
            if not getattr(self, name)
        ]
        if missing:
            raise UiPathIntegrationError(
                "missing UiPath configuration: " + ", ".join(missing)
            )


class UiPathClient:
    def __init__(self, config: UiPathConfig, transport: httpx.BaseTransport | None = None):
        self.config = config
        self._client = httpx.Client(timeout=20.0, transport=transport)
        self._token: str | None = None

    def deployment_status(self, last_successful_job_id: str | None = None) -> dict[str, Any]:
        configured = bool(
            self.config.enabled
            and self.config.deployment_id
            and self.config.folder_key
            and self.config.process_version
        )
        return {
            "enabled": self.config.enabled,
            "configured": configured,
            "operational": configured and bool(last_successful_job_id),
            "deployment_id": self.config.deployment_id or None,
            "process_version": self.config.process_version or None,
            "last_successful_job_id": last_successful_job_id,
        }

    def _access_token(self) -> str:
        self.config.validate()
        if self._token:
            return self._token
        response = self._client.post(
            self.config.token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
                "scope": "OR.Default OR.Execution OR.Jobs",
            },
        )
        if response.status_code != 200:
            raise UiPathIntegrationError(
                f"UiPath token request failed: {response.status_code}"
            )
        token = response.json().get("access_token")
        if not token:
            raise UiPathIntegrationError("UiPath token response omitted access_token")
        self._token = token
        return token

    def _start_request(self, arguments: dict[str, Any], token: str) -> httpx.Response:
        url = (
            f"{self.config.base_url.rstrip('/')}/orchestrator_/odata/Jobs/"
            "UiPath.Server.Configuration.OData.StartJobs"
        )
        return self._client.post(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "X-UIPATH-FolderKey": self.config.folder_key,
            },
            json={
                "startInfo": {
                    "ReleaseKey": self.config.process_key,
                    "Strategy": "Specific",
                    "RobotIds": [],
                    "JobsCount": 1,
                    "InputArguments": arguments,
                }
            },
        )

    def start_process(self, arguments: dict[str, Any]) -> dict[str, Any]:
        token = self._access_token()
        response = self._start_request(arguments, token)
        if response.status_code == 401:
            self._token = None
            response = self._start_request(arguments, self._access_token())
        if response.status_code not in {200, 201}:
            raise UiPathIntegrationError(
                f"UiPath process start failed: {response.status_code}"
            )
        return response.json()

    @staticmethod
    def job_evidence(job: dict[str, Any]) -> dict[str, Any]:
        job_id = job.get("Id") or job.get("id")
        state = str(job.get("State") or job.get("state") or "UNKNOWN").upper()
        successful = bool(job_id and state == "SUCCESSFUL")
        return {
            "job_id": job_id,
            "state": state,
            "live_verified": successful,
            "reason": None if successful else "successful UiPath job evidence is absent",
        }