"""Tests for NEXUS Frontier Scanner — pure unit tests, no network.

Test the parsing logic, delta detection, watchlist bookkeeping. Live probing
is exercised by integration tests separately.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import pytest

from tools.frontier_scanner.signals.catalog_puller import (
    ProviderCatalog,
    _extract_ids,
    pull_provider_catalog,
)
from tools.frontier_scanner.delta.detect_new import (
    DeltaReport,
    diff_catalogs,
)
from tools.frontier_scanner.watchlist.maintain import (
    WatchEntry,
    add_to_watchlist,
    probe_watchlist,
    _load_entries,
    _persist,
    _key,
)


# Catalog parsing tests

def test_extract_ids_wrapped_in_data():
    payload = {"data": [{"id": "a"}, {"id": "b"}, {"id": "c"}]}
    profile = {"data_path": "data.id"}
    assert _extract_ids(payload, profile) == ["a", "b", "c"]


def test_extract_ids_top_level_array():
    payload = [{"id": "x"}, {"id": "y"}, {"name": "z"}]  # z has no id
    profile = {"data_path": "data.id", "raw_root_path": ""}
    assert _extract_ids(payload, profile) == ["x", "y"]


def test_extract_ids_top_level_strings():
    payload = ["q", "r", "s"]
    profile = {"data_path": "data.id", "raw_root_path": ""}
    assert _extract_ids(payload, profile) == ["q", "r", "s"]


def test_extract_ids_empty_payload():
    assert _extract_ids({}, {"data_path": "data.id"}) == []
    assert _extract_ids(None, {"data_path": "data.id"}) == []


def test_catalog_pull_uses_secret_resolver_and_keeps_bounded_metadata(monkeypatch):
    from tools.frontier_scanner.signals import catalog_puller

    class FakeResponse:
        def read(self):
            return json.dumps({
                "data": [{
                    "id": "z-ai/glm-5.2",
                    "name": "GLM 5.2",
                    "context_length": 1_048_576,
                    "supported_parameters": ["tools", "reasoning"],
                    "architecture": {"never": "persisted"},
                    "pricing": {"prompt": "0", "completion": "0"},
                }]
            }).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    seen = {}

    def fake_secret(name, *, provider=None, default=""):
        seen["secret"] = (name, provider, default)
        return "vault-only-token"

    def fake_open(request, timeout):
        seen["url"] = request.full_url
        seen["auth"] = request.get_header("Authorization")
        seen["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(catalog_puller, "get_secret", fake_secret)
    monkeypatch.setattr(catalog_puller.urllib.request, "urlopen", fake_open)
    profile = {
        "models_url": "https://catalog.example/v1/models",
        "auth_env": "NVIDIA_API_KEY",
        "key_ref": "nvidia",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "timeout_seconds": 12,
        "data_path": "data.id",
    }

    catalog = pull_provider_catalog("nvidia", profile)

    assert catalog.status == "ok"
    assert catalog.model_ids == ["z-ai/glm-5.2"]
    assert seen["secret"] == ("NVIDIA_API_KEY", "nvidia", "")
    assert seen["auth"] == "Bearer vault-only-token"
    metadata = catalog.model_metadata["z-ai/glm-5.2"]
    assert metadata["context_tokens"] == 1_048_576
    assert metadata["supported_parameters"] == ["tools", "reasoning"]
    assert metadata["free_hint"] == "zero_catalog_pricing"
    assert "architecture" not in metadata


def test_openrouter_catalog_is_explicitly_public_but_other_profiles_fail_closed_without_key(monkeypatch):
    from tools.frontier_scanner.signals import catalog_puller

    calls = []

    class FakeResponse:
        def read(self):
            return b'{"data": []}'

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    monkeypatch.setattr(catalog_puller, "get_secret", lambda *_args, **_kwargs: "")
    monkeypatch.setattr(
        catalog_puller.urllib.request,
        "urlopen",
        lambda request, timeout: calls.append((request.full_url, timeout)) or FakeResponse(),
    )
    public = pull_provider_catalog("openrouter", {
        "models_url": "https://openrouter.example/models",
        "auth_env": "OPENROUTER_API_KEY",
        "requires_auth": False,
        "timeout_seconds": 10,
        "data_path": "data.id",
    })
    protected = pull_provider_catalog("nvidia", {
        "models_url": "https://nvidia.example/models",
        "auth_env": "NVIDIA_API_KEY",
        "timeout_seconds": 10,
        "data_path": "data.id",
    })

    assert public.status == "ok"
    assert protected.status == "no_key"
    assert calls == [("https://openrouter.example/models", 10)]


# Delta detection tests

def _cat(model_ids, fetched_at=0.0):
    return ProviderCatalog(
        provider="nvidia",
        fetched_at=fetched_at,
        source_url="https://example.com",
        model_ids=list(model_ids),
        status="ok",
        raw_count=len(model_ids),
    )


def test_diff_no_changes():
    prev = _cat(["a", "b", "c"], fetched_at=10.0)
    cur = _cat(["a", "b", "c"], fetched_at=20.0)
    delta = diff_catalogs(prev, cur)
    assert delta.new_ids == []
    assert delta.disappeared_ids == []
    assert delta.stable_ids == ["a", "b", "c"]


def test_diff_one_new():
    prev = _cat(["a", "b"], fetched_at=10.0)
    cur = _cat(["a", "b", "c-new"], fetched_at=20.0)
    delta = diff_catalogs(prev, cur)
    assert delta.new_ids == ["c-new"]
    assert delta.disappeared_ids == []
    assert delta.stable_ids == ["a", "b"]


def test_diff_carries_metadata_only_for_new_ids():
    previous = _cat(["a"], fetched_at=10.0)
    current = _cat(["a", "new"], fetched_at=20.0)
    current.model_metadata = {"a": {"ignored": True}, "new": {"context_tokens": 128_000}}
    delta = diff_catalogs(previous, current)
    assert delta.new_metadata == {"new": {"context_tokens": 128_000}}


def test_diff_one_disappeared():
    prev = _cat(["a", "b", "c-eol"], fetched_at=10.0)
    cur = _cat(["a", "b"], fetched_at=20.0)
    delta = diff_catalogs(prev, cur)
    assert delta.new_ids == []
    assert delta.disappeared_ids == ["c-eol"]


def test_diff_mixed():
    prev = _cat(["a", "b", "c-eol"], fetched_at=10.0)
    cur = _cat(["a", "b", "c-new"], fetched_at=20.0)
    delta = diff_catalogs(prev, cur)
    assert delta.new_ids == ["c-new"]
    assert delta.disappeared_ids == ["c-eol"]
    assert delta.stable_ids == ["a", "b"]


# Watchlist tests

def test_add_to_watchlist_creates_entry(tmp_path: Path):
    state = tmp_path / "state"
    state.mkdir()
    entry = add_to_watchlist(state, "nvidia", "z-ai/glm-5.2")
    assert entry.provider == "nvidia"
    assert entry.model_id == "z-ai/glm-5.2"
    assert entry.first_seen > 0.0
    assert entry.passes == 0
    second = add_to_watchlist(state, "nvidia", "z-ai/glm-5.2")
    assert second.provider == entry.provider
    assert second.model_id == entry.model_id
    assert second.first_seen == entry.first_seen


def test_add_with_initial_pass_validation(tmp_path: Path):
    state = tmp_path / "state"
    state.mkdir()

    class FakeVal:
        finished_at = 100.0
        decision = "pass"

    entry = add_to_watchlist(state, "nvidia", "z-ai/glm-5.2", initial_validation=FakeVal())
    assert entry.passes == 1
    assert entry.probes == 1


def test_watchlist_persistence(tmp_path: Path):
    state = tmp_path / "state"
    state.mkdir()
    add_to_watchlist(state, "nvidia", "z-ai/glm-5.2")
    add_to_watchlist(state, "longcat", "LongCat-2.0")

    entries = _load_entries(state / "watchlist.json")
    assert len(entries) == 2
    assert _key("nvidia", "z-ai/glm-5.2") in entries


def test_watchlist_tick_respects_cooldown(tmp_path: Path, monkeypatch):
    state = tmp_path / "state"
    state.mkdir()
    now = time.time()
    e = WatchEntry(
        provider="nvidia",
        model_id="z-ai/glm-5.2",
        first_seen=now - 86400,
        last_probed=now - 100,  # recently probed
    )
    _persist(state / "watchlist.json", {e.provider + "::" + e.model_id: e})

    called = []

    def fake_run(provider, model_id, state_dir, mode="light"):
        called.append((provider, model_id, mode))
        return type("V", (), {"finished_at": 0.0, "decision": "pass"})()

    monkeypatch.setattr(
        "tools.frontier_scanner.watchlist.maintain.run_probe", fake_run
    )
    results = probe_watchlist(state, min_interval_seconds=20 * 3600)
    assert results == []  # cooldown not satisfied
    assert called == []  # type: ignore[comparison-overlap]


# Provider profile tests

def test_provider_profile_required_keys():
    from tools.frontier_scanner.signals.catalog_puller import PROVIDER_PROFILES
    for name, profile in PROVIDER_PROFILES.items():
        assert "models_url" in profile, name
        assert "auth_env" in profile, name
        assert "timeout_seconds" in profile, name
        assert "data_path" in profile or profile.get("raw_root_path") == "", name


# Cold-start / baseline-promotion tests (FI-D1 S1)

def _fake_pull(ids_by_provider):
    def pull(selected, state_dir=None):
        out = {}
        for name in selected:
            out[name] = ProviderCatalog(
                provider=name,
                fetched_at=time.time(),
                source_url="stub://",
                model_ids=list(ids_by_provider.get(name, [])),
                error=None,
                status="ok",
                raw_count=len(ids_by_provider.get(name, [])),
            )
        return out
    return pull


def test_cold_start_reports_all_new_and_promotes_baseline(tmp_path: Path, monkeypatch):
    from tools.frontier_scanner.delta import detect_new

    monkeypatch.setattr(
        detect_new, "pull_all_catalogs", _fake_pull({"nvidia": ["a/m1", "b/m2"]})
    )
    monkeypatch.setattr(detect_new, "PROVIDER_PROFILES", {"nvidia": {}})

    reports = detect_new.run_delta_pass(tmp_path, ["nvidia"], save_snapshot=False)
    r = reports["nvidia"]
    assert r.baseline_established is True
    assert sorted(r.new_ids) == ["a/m1", "b/m2"]
    # snapshot promoted to baseline — next pass diffs against it
    assert (tmp_path / "catalog__nvidia.json").exists()


def test_second_pass_diffs_against_promoted_baseline(tmp_path: Path, monkeypatch):
    from tools.frontier_scanner.delta import detect_new

    monkeypatch.setattr(detect_new, "PROVIDER_PROFILES", {"nvidia": {}})
    monkeypatch.setattr(
        detect_new, "pull_all_catalogs", _fake_pull({"nvidia": ["a/m1"]})
    )
    detect_new.run_delta_pass(tmp_path, ["nvidia"], save_snapshot=False)

    monkeypatch.setattr(
        detect_new, "pull_all_catalogs", _fake_pull({"nvidia": ["a/m1", "meituan/owl"]})
    )
    reports = detect_new.run_delta_pass(tmp_path, ["nvidia"], save_snapshot=False)
    r = reports["nvidia"]
    assert r.baseline_established is False
    assert r.new_ids == ["meituan/owl"]

    # third pass, same listing: baseline was re-promoted, so no repeat delta
    reports = detect_new.run_delta_pass(tmp_path, ["nvidia"], save_snapshot=False)
    assert reports["nvidia"].new_ids == []
