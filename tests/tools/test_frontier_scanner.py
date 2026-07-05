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
