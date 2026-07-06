"""FI-D1 discovery tests: new = listed − (registered + aliases).

Covers the candidate lifecycle in the health sidecar, provider-news A2A
emission (once per (provider, model), baseline event on first probe),
alias suppression on both the additive and removal sides, the Owl-Alpha
unknown-vendor-prefix priority rule, and suspend/deprecate aging at READ
time. No network — requests and the A2A bus are stubbed.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from nexus_os.relay import provider_refresher as pr
from nexus_os.relay.discovery_rules import (
    classify_candidate,
    known_vendor_prefixes,
    new_candidates,
    resolve_removal,
)

REGISTRY = {
    "version": 2,
    "providers": {
        "testprov": {
            "status": "active",
            "baseUrl": "https://api.test.example/v1",
        },
    },
    "models": [
        {
            "id": "zai-org/glm-5.2",
            "provider": "testprov",
            "status": "active",
            "aliases": ["z-ai/glm-5.2"],
        },
        {
            "id": "qwen/qwen3-coder-next",
            "provider": "testprov",
            "status": "active",
            "aliases": [],
        },
    ],
}


class _FakeResponse:
    def __init__(self, ids):
        self.ok = True
        self.status_code = 200
        self._ids = ids

    def json(self):
        return {"data": [{"id": i} for i in self._ids]}


class _FakeBus:
    published = []

    def publish(self, channel_id, sender, message, topic, **kw):
        _FakeBus.published.append(
            {"channel": channel_id, "sender": sender, "topic": topic,
             "event": json.loads(message)}
        )


@pytest.fixture()
def refresher(tmp_path, monkeypatch):
    reg_path = tmp_path / "registry.json"
    reg_path.write_text(json.dumps(REGISTRY), encoding="utf-8")
    sidecar = tmp_path / "health.json"

    _FakeBus.published = []
    import nexus_os.bridge.a2a_channels as a2a
    monkeypatch.setattr(a2a, "A2AChannelBus", _FakeBus)

    def make(listing):
        monkeypatch.setattr(
            pr.requests, "get", lambda *a, **kw: _FakeResponse(listing)
        )
        return pr.ProviderRefresher(registry_path=reg_path, sidecar_path=sidecar)

    return make


# ── discovery_rules (pure) ─────────────────────────────────────────────

def test_known_prefixes_include_orgs_aliases_and_stems():
    prefixes = known_vendor_prefixes(REGISTRY)
    assert {"zai-org", "z-ai", "qwen", "glm"} <= prefixes


def test_unknown_vendor_prefix_is_high_priority():
    prefixes = known_vendor_prefixes(REGISTRY)
    assert classify_candidate("meituan/owl-alpha", prefixes) == (
        "high", "unknown-vendor-prefix"
    )
    assert classify_candidate("qwen/qwen4-preview", prefixes)[0] == "normal"


def test_alias_never_becomes_candidate():
    cands = new_candidates(
        ["zai-org/glm-5.2", "z-ai/glm-5.2", "meituan/owl-alpha"],
        REGISTRY,
        "testprov",
    )
    assert set(cands) == {"meituan/owl-alpha"}


def test_resolve_removal_via_alias():
    listed = {"z-ai/glm-5.2"}
    assert resolve_removal("zai-org/glm-5.2", REGISTRY, listed) is True
    assert resolve_removal("qwen/qwen3-coder-next", REGISTRY, listed) is False


# ── refresher lifecycle ────────────────────────────────────────────────

def test_first_probe_emits_single_baseline_event(refresher):
    r = refresher(["zai-org/glm-5.2", "qwen/qwen3-coder-next",
                   "meituan/owl-alpha", "acme/new-thing"])
    result = r.probe_provider("testprov", chat_probe_absentees=False)
    assert sorted(result.new_candidates) == ["acme/new-thing", "meituan/owl-alpha"]
    events = [p["event"] for p in _FakeBus.published]
    assert len(events) == 1
    assert events[0]["type"] == "baseline-established"
    assert events[0]["candidate_count"] == 2
    cands = r.health["providers"]["testprov"]["candidates"]
    assert cands["meituan/owl-alpha"]["priority"] == "high"
    assert cands["meituan/owl-alpha"]["baseline"] is True
    assert cands["meituan/owl-alpha"]["emitted"] is True


def test_new_model_after_baseline_emits_once(refresher, monkeypatch):
    r = refresher(["zai-org/glm-5.2", "qwen/qwen3-coder-next"])
    r.probe_provider("testprov", chat_probe_absentees=False)
    _FakeBus.published = []

    monkeypatch.setattr(
        pr.requests, "get",
        lambda *a, **kw: _FakeResponse(
            ["zai-org/glm-5.2", "qwen/qwen3-coder-next", "meituan/owl-alpha"]
        ),
    )
    r.probe_provider("testprov", chat_probe_absentees=False)
    events = [p["event"] for p in _FakeBus.published]
    assert len(events) == 1
    assert events[0] == {
        "type": "new-model",
        "provider": "testprov",
        "model_id": "meituan/owl-alpha",
        "first_seen": events[0]["first_seen"],
        "priority": "high",
        "reason": "unknown-vendor-prefix",
    }

    # same listing again: emitted marker suppresses a duplicate event,
    # first_seen survives, last_seen advances
    first_seen = r.health["providers"]["testprov"]["candidates"][
        "meituan/owl-alpha"]["first_seen"]
    _FakeBus.published = []
    r.probe_provider("testprov", chat_probe_absentees=False)
    assert _FakeBus.published == []
    cand = r.health["providers"]["testprov"]["candidates"]["meituan/owl-alpha"]
    assert cand["first_seen"] == first_seen


def test_disappeared_candidate_is_dropped(refresher, monkeypatch):
    r = refresher(["zai-org/glm-5.2", "qwen/qwen3-coder-next", "acme/x"])
    r.probe_provider("testprov", chat_probe_absentees=False)
    assert "acme/x" in r.health["providers"]["testprov"]["candidates"]

    monkeypatch.setattr(
        pr.requests, "get",
        lambda *a, **kw: _FakeResponse(["zai-org/glm-5.2", "qwen/qwen3-coder-next"]),
    )
    r.probe_provider("testprov", chat_probe_absentees=False)
    assert "acme/x" not in r.health["providers"]["testprov"]["candidates"]


def test_alias_covered_removal_not_missing(refresher):
    # registered id absent, but its alias is listed → rename, not removal
    r = refresher(["z-ai/glm-5.2", "qwen/qwen3-coder-next"])
    result = r.probe_provider("testprov", chat_probe_absentees=False)
    assert result.missing_from_listing == []


def test_candidates_survive_record_update(refresher, monkeypatch):
    r = refresher(["zai-org/glm-5.2", "qwen/qwen3-coder-next", "acme/x"])
    r.probe_provider("testprov", chat_probe_absentees=False)
    monkeypatch.setattr(
        pr.requests, "get",
        lambda *a, **kw: _FakeResponse(
            ["zai-org/glm-5.2", "qwen/qwen3-coder-next", "acme/x"]),
    )
    r.probe_provider("testprov", chat_probe_absentees=False)
    prov_entry = r.health["providers"]["testprov"]
    assert "last_probe" in prov_entry and "candidates" in prov_entry
    assert "acme/x" in prov_entry["candidates"]


# ── aging on read ──────────────────────────────────────────────────────

def test_effective_status_ages_on_read():
    now = time.time()
    stale = {"status": "suspended", "first_missing": now - 40 * 86400}
    assert pr.effective_status(stale, now) == "deprecated"
    recent = {"status": "active", "first_missing": now - 2 * 86400}
    assert pr.effective_status(recent, now) == "active"
    ten_days = {"status": "active", "first_missing": now - 10 * 86400}
    assert pr.effective_status(ten_days, now) == "suspended"
    assert pr.effective_status({"status": "active", "first_missing": None}, now) == "active"
