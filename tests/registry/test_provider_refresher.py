"""Tests for the generic provider refresher (registry-driven liveness)."""
from __future__ import annotations

import json
import time
from unittest.mock import MagicMock, patch

import pytest

from nexus_os.relay.provider_refresher import (
    DEPRECATE_AFTER_DAYS,
    SUSPEND_AFTER_DAYS,
    ProviderRefresher,
)


@pytest.fixture
def registry_file(tmp_path):
    registry = {
        "version": 1,
        "providers": {
            "testprov": {
                "keyRef": "testprov",
                "baseUrl": "https://api.test.example/v1",
                "status": "active",
            },
            "discovery-only": {"keyRef": "d", "status": "active"},
            "dead": {"keyRef": None, "baseUrl": "https://x.example", "status": "deprecated"},
        },
        "models": [
            {"id": "model-a", "provider": "testprov", "status": "active"},
            {"id": "model-gone", "provider": "testprov", "status": "active"},
        ],
    }
    p = tmp_path / "registry.json"
    p.write_text(json.dumps(registry), encoding="utf-8")
    return p


@pytest.fixture
def refresher(registry_file, tmp_path, monkeypatch):
    monkeypatch.setenv("TESTPROV_API_KEY", "test-key-value")
    return ProviderRefresher(registry_path=registry_file, sidecar_path=tmp_path / "health.json")


def _listing_response(ids):
    resp = MagicMock()
    resp.ok = True
    resp.json.return_value = {"data": [{"id": i} for i in ids]}
    return resp


class TestProbe:
    def test_listing_match_marks_active(self, refresher):
        with patch("nexus_os.relay.provider_refresher.requests.get",
                   return_value=_listing_response(["model-a", "model-gone"])):
            result = refresher.probe_provider("testprov", chat_probe_absentees=False)
        assert result.reachable
        assert result.missing_from_listing == []
        assert refresher.health["models"]["testprov:model-a"]["status"] == "active"

    def test_absentee_gets_chat_probe_and_survives(self, refresher):
        chat_ok = MagicMock(ok=True)
        with patch("nexus_os.relay.provider_refresher.requests.get",
                   return_value=_listing_response(["model-a"])), \
             patch("nexus_os.relay.provider_refresher.requests.post", return_value=chat_ok):
            result = refresher.probe_provider("testprov")
        assert result.missing_from_listing == ["model-gone"]
        assert result.chat_confirmed == ["model-gone"]
        assert refresher.health["models"]["testprov:model-gone"]["status"] == "active"

    def test_discovery_only_provider_skipped_gracefully(self, refresher):
        result = refresher.probe_provider("discovery-only")
        assert not result.reachable
        assert "discovery-only" in result.error

    def test_deprecated_provider_excluded_from_refresh_all(self, refresher):
        with patch("nexus_os.relay.provider_refresher.requests.get",
                   return_value=_listing_response(["model-a", "model-gone"])):
            results = refresher.refresh_all(chat_probe=False)
        assert {r.provider for r in results} == {"testprov", "discovery-only"}


class TestStateMachine:
    def _age_first_missing(self, refresher, key, days):
        refresher.health["models"][key]["first_missing"] = time.time() - days * 86400

    def test_missing_suspends_after_window(self, refresher):
        chat_fail = MagicMock(ok=False)
        with patch("nexus_os.relay.provider_refresher.requests.get",
                   return_value=_listing_response(["model-a"])), \
             patch("nexus_os.relay.provider_refresher.requests.post", return_value=chat_fail):
            refresher.probe_provider("testprov")
            self._age_first_missing(refresher, "testprov:model-gone", SUSPEND_AFTER_DAYS + 1)
            refresher.probe_provider("testprov")
        assert refresher.health["models"]["testprov:model-gone"]["status"] == "suspended"

    def test_missing_deprecates_after_long_window(self, refresher):
        chat_fail = MagicMock(ok=False)
        with patch("nexus_os.relay.provider_refresher.requests.get",
                   return_value=_listing_response(["model-a"])), \
             patch("nexus_os.relay.provider_refresher.requests.post", return_value=chat_fail):
            refresher.probe_provider("testprov")
            self._age_first_missing(refresher, "testprov:model-gone", DEPRECATE_AFTER_DAYS + 1)
            refresher.probe_provider("testprov")
        assert refresher.health["models"]["testprov:model-gone"]["status"] == "deprecated"

    def test_reappearance_resets_to_active(self, refresher):
        chat_fail = MagicMock(ok=False)
        with patch("nexus_os.relay.provider_refresher.requests.get",
                   return_value=_listing_response(["model-a"])), \
             patch("nexus_os.relay.provider_refresher.requests.post", return_value=chat_fail):
            refresher.probe_provider("testprov")
            self._age_first_missing(refresher, "testprov:model-gone", SUSPEND_AFTER_DAYS + 1)
            refresher.probe_provider("testprov")
        with patch("nexus_os.relay.provider_refresher.requests.get",
                   return_value=_listing_response(["model-a", "model-gone"])):
            refresher.probe_provider("testprov", chat_probe_absentees=False)
        assert refresher.health["models"]["testprov:model-gone"]["status"] == "active"

    def test_sidecar_never_touches_registry(self, refresher, registry_file):
        before = registry_file.read_text(encoding="utf-8")
        with patch("nexus_os.relay.provider_refresher.requests.get",
                   return_value=_listing_response([])), \
             patch("nexus_os.relay.provider_refresher.requests.post", return_value=MagicMock(ok=False)):
            refresher.probe_provider("testprov")
        assert registry_file.read_text(encoding="utf-8") == before


class TestDiffReport:
    def test_report_shape(self, refresher):
        with patch("nexus_os.relay.provider_refresher.requests.get",
                   return_value=_listing_response(["model-a", "model-gone"])):
            results = refresher.refresh_all(chat_probe=False)
        report = refresher.diff_report(results)
        entry = report["providers"]["testprov"]
        assert entry["registered"] == 2
        assert entry["listed"] == 2
        assert entry["missing_from_listing"] == []
