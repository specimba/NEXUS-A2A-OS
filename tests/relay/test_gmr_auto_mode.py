"""GMR auto-mode pre-stage in the Python relay (model == "auto-gmr").

Revival of nexus_os/gmr as the relay's outer strategy layer: COGER
classifies L1-L4 and maps the level to ChimeraRouterV2 routing targets.
Plain "auto" must stay the unchanged Chimera-only path.
"""
from __future__ import annotations

import pytest

from nexus_os.relay import model_relay


class _Response:
    def __init__(self, ok=True, payload=None):
        self.ok = ok
        self._payload = payload or {}

    def raise_for_status(self):
        if not self.ok:
            raise RuntimeError("request failed")

    def json(self):
        return self._payload


def _ok_post(url, json, timeout):
    return _Response(
        payload={
            "choices": [{"message": {"content": "ok"}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }
    )


@pytest.fixture
def relay(monkeypatch):
    monkeypatch.setattr(model_relay.requests, "post", _ok_post)
    return model_relay.ModelRelay()


class TestGmrClassification:
    def test_levels_from_coger_heuristic(self, relay):
        assert relay._gmr_classify("2+2?") == "L1"
        assert relay._gmr_classify("What is the capital of France and why is it significant?") == "L2"
        assert relay._gmr_classify("Analyze and refactor this complex class hierarchy for performance") == "L3"
        assert relay._gmr_classify("search the web for the latest NEXUS papers") == "L4"

    def test_degrades_to_l2_when_gmr_unavailable(self, relay, monkeypatch):
        def boom(prompt):
            raise ImportError("gmr gone")

        relay._coger = None
        import nexus_os.gmr.coger as coger_mod
        monkeypatch.setattr(coger_mod.CogER, "classify_complexity_heuristically",
                            lambda self, q: (_ for _ in ()).throw(RuntimeError("down")))
        assert relay._gmr_classify("hello there friend") == "L2"


class TestAutoGmrRouting:
    @pytest.mark.asyncio
    async def test_auto_gmr_sets_level_targets_and_reports_level(self, relay):
        captured = {}
        real_route = relay.router.route

        def spy_route(prompt, **kwargs):
            captured.update(kwargs)
            return real_route(prompt, **kwargs)

        relay.router.route = spy_route
        result = await relay.proxy_completion(
            {
                "model": "auto-gmr",
                "messages": [{"role": "user", "content": "2+2?"}],  # L1
            }
        )

        assert result["relay_info"]["gmr_level"] == "L1"
        q, lat = model_relay.ModelRelay.GMR_LEVEL_TARGETS["L1"]
        assert captured["quality_target"] == q
        assert captured["latency_budget_ms"] == lat

    @pytest.mark.asyncio
    async def test_explicit_targets_beat_level_targets(self, relay):
        captured = {}
        real_route = relay.router.route

        def spy_route(prompt, **kwargs):
            captured.update(kwargs)
            return real_route(prompt, **kwargs)

        relay.router.route = spy_route
        await relay.proxy_completion(
            {
                "model": "auto-gmr",
                "messages": [{"role": "user", "content": "2+2?"}],
                "quality_target": 0.99,
                "latency_budget_ms": 12345,
            }
        )
        assert captured["quality_target"] == 0.99
        assert captured["latency_budget_ms"] == 12345

    @pytest.mark.asyncio
    async def test_l4_advises_delegation(self, relay):
        result = await relay.proxy_completion(
            {
                "model": "auto-gmr",
                "messages": [{"role": "user", "content": "search the web for GLM-5 benchmarks"}],
            }
        )
        assert result["relay_info"]["gmr_level"] == "L4"
        assert result["relay_info"]["gmr_delegation_advised"] is True

    @pytest.mark.asyncio
    async def test_plain_auto_has_no_gmr_fields(self, relay):
        result = await relay.proxy_completion(
            {
                "model": "auto",
                "messages": [{"role": "user", "content": "Write a short plan"}],
            }
        )
        assert "gmr_level" not in result["relay_info"]
        assert "gmr_delegation_advised" not in result["relay_info"]
