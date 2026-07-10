"""B2 relay cloud-health fix: provider-aware _check_health.

Before this fix _check_health POSTed EVERY model to the local Ollama chat
URL, so cloud-provider models (nvidia/..., siliconflow/..., baseten ids)
were permanently marked unhealthy. Now only Ollama-lane models get the
live probe; cloud models take their health from the provider_refresher
sidecar (~/.nexus/registry_health.json, read-only) or default to
available, with _health_source provenance so nothing pretends a live
probe happened.
"""
from __future__ import annotations

import sys
import json
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from nexus_os.relay import model_relay
from nexus_os.relay.model_relay import ModelRelay


CLOUD_MODEL = "nvidia/nemotron-3-super"  # in ALL_ACTIVE_CLOUD_MODELS, not Ollama lane


@pytest.fixture
def relay(monkeypatch):
    """A relay that never touches the network during construction."""
    monkeypatch.setattr(ModelRelay, "_discover_ollama_models", lambda self: None)
    monkeypatch.setattr(ModelRelay, "_start_health_loop", lambda self: None)
    return ModelRelay()


@pytest.fixture
def no_sidecar(monkeypatch, tmp_path):
    """Point the sidecar at a path that does not exist."""
    monkeypatch.setattr(model_relay, "REGISTRY_HEALTH_SIDECAR", tmp_path / "registry_health.json")
    return tmp_path / "registry_health.json"


def _write_sidecar(path, models):
    path.write_text(json.dumps({"models": models, "providers": {}}), encoding="utf-8")


# -- (a) local / Ollama-lane models still get the live probe --------------


class TestLocalLaneProbed:
    def test_local_model_probes_ollama_url(self, relay, monkeypatch):
        posts = []

        class _Resp:
            ok = True

        def _capture(url, **kw):
            posts.append(url)
            return _Resp()

        monkeypatch.setattr(model_relay.requests, "post", _capture)
        assert relay._check_health("llama-guard3:1b") is True
        assert posts == [model_relay.OLLAMA_CHAT_URL]
        assert relay._health_source["llama-guard3:1b"] == "ollama_probe"

    def test_discovered_ollama_model_probed(self, relay, monkeypatch):
        relay._available_ollama_models = ["some-custom/finetune:latest"]
        posts = []

        class _Resp:
            ok = True

        monkeypatch.setattr(
            model_relay.requests, "post", lambda url, **kw: posts.append(url) or _Resp()
        )
        assert relay._check_health("some-custom/finetune:latest") is True
        assert posts == [model_relay.OLLAMA_CHAT_URL]

    def test_ollama_cloud_alias_stays_on_probe_lane(self, relay, monkeypatch):
        """minimax-m3:cloud is served THROUGH the local daemon: probe it."""
        posts = []

        class _Resp:
            ok = True

        monkeypatch.setattr(
            model_relay.requests, "post", lambda url, **kw: posts.append(url) or _Resp()
        )
        assert relay._check_health("minimax-m3:cloud") is True
        assert posts == [model_relay.OLLAMA_CHAT_URL]
        assert relay._health_source["minimax-m3:cloud"] == "ollama_probe"

    def test_probe_failure_still_marks_unhealthy_with_timestamp(self, relay, monkeypatch):
        monkeypatch.setattr(
            model_relay.requests, "post",
            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("down")),
        )
        assert relay._check_health("gone-model") is False
        assert relay._health_checked_at["gone-model"] == pytest.approx(time.time(), abs=5)
        assert relay._health_source["gone-model"] == "ollama_probe"


# -- (b) cloud models: no Ollama probe, fail-open default -----------------


class TestCloudLaneNotProbed:
    def test_cloud_model_never_hits_ollama(self, relay, monkeypatch, no_sidecar):
        monkeypatch.setattr(
            model_relay.requests, "post",
            lambda *a, **k: pytest.fail("cloud model must not be probed against Ollama"),
        )
        assert relay._check_health(CLOUD_MODEL) is True

    def test_cloud_default_is_unprobed_with_provenance(self, relay, monkeypatch, no_sidecar):
        monkeypatch.setattr(
            model_relay.requests, "post",
            lambda *a, **k: pytest.fail("no HTTP call expected"),
        )
        relay._check_health(CLOUD_MODEL)
        assert relay._model_health[CLOUD_MODEL] is True
        assert relay._health_source[CLOUD_MODEL] == "unprobed_default"
        assert relay._health_checked_at[CLOUD_MODEL] == pytest.approx(time.time(), abs=5)

    def test_corrupt_sidecar_fails_open(self, relay, monkeypatch, no_sidecar):
        no_sidecar.write_text("{not json", encoding="utf-8")
        monkeypatch.setattr(
            model_relay.requests, "post",
            lambda *a, **k: pytest.fail("no HTTP call expected"),
        )
        assert relay._check_health(CLOUD_MODEL) is True
        assert relay._health_source[CLOUD_MODEL] == "unprobed_default"

    def test_health_check_ttl_applies_to_cloud_models(self, relay, monkeypatch, no_sidecar):
        """Cached cloud verdict is honored within TTL (no re-check)."""
        checks = []
        monkeypatch.setattr(
            ModelRelay, "_check_health", lambda self, m: checks.append(m) or True
        )
        relay._model_health[CLOUD_MODEL] = True
        relay._health_checked_at[CLOUD_MODEL] = time.time()
        assert relay.health_check(CLOUD_MODEL) is True
        assert checks == []
        relay._health_checked_at[CLOUD_MODEL] = time.time() - (model_relay.HEALTH_TTL_S + 1)
        relay.health_check(CLOUD_MODEL)
        assert checks == [CLOUD_MODEL]


# -- (c) sidecar-present path ---------------------------------------------


class TestSidecarPath:
    def test_active_sidecar_entry_marks_healthy(self, relay, monkeypatch, no_sidecar):
        _write_sidecar(no_sidecar, {
            "nvidia:nemotron-3-super": {
                "status": "active", "first_missing": None, "last_seen": time.time(),
            },
        })
        monkeypatch.setattr(
            model_relay.requests, "post",
            lambda *a, **k: pytest.fail("sidecar path must not probe Ollama"),
        )
        assert relay._check_health(CLOUD_MODEL) is True
        assert relay._health_source[CLOUD_MODEL] == "sidecar:active"

    def test_suspended_sidecar_entry_marks_unhealthy(self, relay, monkeypatch, no_sidecar):
        # first_missing 8 days ago -> effective_status() says suspended
        _write_sidecar(no_sidecar, {
            "nvidia:nemotron-3-super": {
                "status": "active",
                "first_missing": time.time() - 8 * 86400,
                "last_seen": None,
            },
        })
        monkeypatch.setattr(
            model_relay.requests, "post",
            lambda *a, **k: pytest.fail("sidecar path must not probe Ollama"),
        )
        assert relay._check_health(CLOUD_MODEL) is False
        assert relay._health_source[CLOUD_MODEL] == "sidecar:suspended"

    def test_deprecated_sidecar_entry_marks_unhealthy(self, relay, monkeypatch, no_sidecar):
        _write_sidecar(no_sidecar, {
            "nvidia:nemotron-3-super": {
                "status": "deprecated",
                "first_missing": time.time() - 40 * 86400,
                "last_seen": None,
            },
        })
        assert relay._check_health(CLOUD_MODEL) is False
        assert relay._health_source[CLOUD_MODEL] == "sidecar:deprecated"

    def test_bare_model_id_matches_sidecar_key(self, relay, monkeypatch, no_sidecar):
        """Sidecar keys are provider:id; the bare id form matches too."""
        _write_sidecar(no_sidecar, {
            "siliconflow:kimi-k2-thinking": {
                "status": "active", "first_missing": None, "last_seen": time.time(),
            },
        })
        assert relay._check_health("kimi-k2-thinking") is True
        assert relay._health_source["kimi-k2-thinking"] == "sidecar:active"

    def test_unrelated_sidecar_entries_ignored(self, relay, monkeypatch, no_sidecar):
        _write_sidecar(no_sidecar, {
            "baseten:zai-org/GLM-5.2": {
                "status": "deprecated",
                "first_missing": time.time() - 40 * 86400,
            },
        })
        assert relay._check_health(CLOUD_MODEL) is True
        assert relay._health_source[CLOUD_MODEL] == "unprobed_default"


# -- lane classification ---------------------------------------------------


class TestLaneClassification:
    def test_lane_membership(self, relay):
        assert relay._is_ollama_lane("functiongemma:latest") is True      # registry local map
        assert relay._is_ollama_lane("minimax-m3:cloud") is True          # ollama-cloud alias
        assert relay._is_ollama_lane("llama-guard3:1b") is True           # bare local name
        assert relay._is_ollama_lane("nvidia/nemotron-3-super") is False  # cloud provider
        assert relay._is_ollama_lane("siliconflow/zai-org/GLM-5.2") is False
        assert relay._is_ollama_lane("kimi-k2-thinking") is False         # bare cloud-only id
        assert relay._is_ollama_lane("some-org/unknown-model") is False   # prefixed unknown

    def test_discovered_model_beats_cloud_heuristic(self, relay):
        """A slash-named model actually pulled locally is still lane-local."""
        relay._available_ollama_models = ["some-org/unknown-model"]
        assert relay._is_ollama_lane("some-org/unknown-model") is True
