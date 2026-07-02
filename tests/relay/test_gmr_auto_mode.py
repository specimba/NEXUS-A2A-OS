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


class FakeCogER:
    """Stands in for CogER: classification + strategy execution."""

    def __init__(self, response="tandem says hello", strategy="Tandem Routing", fail=False):
        self.response = response
        self.strategy = strategy
        self.fail = fail
        self.route_calls = []

    def classify_complexity_heuristically(self, query):
        return "L2"

    def route(self, query, level=None, trust_score=100.0, **kw):
        self.route_calls.append({"query": query, "level": level, "trust_score": trust_score})
        if self.fail:
            raise RuntimeError("strategy down")
        return {"level": level, "strategy": self.strategy, "response": self.response}


class TestStrategyExecution:
    @pytest.mark.asyncio
    async def test_l2_executes_tandem_strategy(self, relay):
        relay._coger = FakeCogER()
        result = await relay.proxy_completion(
            {"model": "auto-gmr", "messages": [{"role": "user", "content": "explain briefly why"}]}
        )
        assert result["choices"][0]["message"]["content"] == "tandem says hello"
        assert result["relay_info"]["gmr_strategy"] == "Tandem Routing"
        assert result["relay_info"]["gmr_level"] == "L2"

    @pytest.mark.asyncio
    async def test_strategy_failure_falls_back_to_chimera(self, relay):
        relay._coger = FakeCogER(fail=True)
        result = await relay.proxy_completion(
            {"model": "auto-gmr", "messages": [{"role": "user", "content": "explain briefly why"}]}
        )
        # Chimera single-model path answered via the mocked Ollama post
        assert result["choices"][0]["message"]["content"] == "ok"
        assert result["relay_info"]["gmr_level"] == "L2"
        assert "gmr_strategy" not in result["relay_info"]

    @pytest.mark.asyncio
    async def test_error_prefixed_response_falls_back(self, relay):
        relay._coger = FakeCogER(response="Execution Blocked: trust gate")
        result = await relay.proxy_completion(
            {"model": "auto-gmr", "messages": [{"role": "user", "content": "explain briefly why"}]}
        )
        assert result["choices"][0]["message"]["content"] == "ok"

    @pytest.mark.asyncio
    async def test_trust_defaults_restricted_not_open(self, relay):
        """The relay must not inherit CogER's open-by-default trust=100."""
        fake = FakeCogER()
        relay._coger = fake
        await relay.proxy_completion(
            {"model": "auto-gmr", "messages": [{"role": "user", "content": "explain briefly why"}]}
        )
        assert fake.route_calls[0]["trust_score"] == 40.0

    @pytest.mark.asyncio
    async def test_caller_trust_passes_through(self, relay):
        fake = FakeCogER()
        relay._coger = fake
        await relay.proxy_completion(
            {
                "model": "auto-gmr",
                "messages": [{"role": "user", "content": "explain briefly why"}],
                "trust_score": 92.5,
            }
        )
        assert fake.route_calls[0]["trust_score"] == 92.5

    @pytest.mark.asyncio
    async def test_l1_never_invokes_strategy(self, relay):
        fake = FakeCogER()
        fake.classify_complexity_heuristically = lambda q: "L1"
        relay._coger = fake
        result = await relay.proxy_completion(
            {"model": "auto-gmr", "messages": [{"role": "user", "content": "2+2?"}]}
        )
        assert fake.route_calls == []
        assert result["relay_info"]["gmr_level"] == "L1"


class TestTaskHandoff:
    @pytest.fixture
    def bus(self, tmp_path, monkeypatch):
        """Isolated MemoryBus with one task in flight."""
        import nexus_os.model_relay.persistent_memory as pm
        test_bus = pm.MemoryBus(path=tmp_path / "model_memory.json")
        monkeypatch.setattr(pm, "_bus", test_bus, raising=False)
        monkeypatch.setattr(pm, "get_memory_bus", lambda: test_bus)
        task = test_bus.create_task(
            "Solidify NEXUS core", "Wire the GMR handoff", working_model="model-alpha",
        )
        return test_bus, task

    @pytest.mark.asyncio
    async def test_intro_prepended_and_rotation_recorded(self, relay, bus):
        test_bus, task = bus
        captured = {}

        def spy_post(url, json, timeout):
            captured.update(json)
            return _ok_post(url, json, timeout)

        import nexus_os.relay.model_relay as mr
        fake = FakeCogER()
        fake.classify_complexity_heuristically = lambda q: "L1"
        relay._coger = fake

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(mr.requests, "post", spy_post)
            result = await relay.proxy_completion(
                {
                    "model": "auto-gmr",
                    "messages": [{"role": "user", "content": "2+2?"}],
                    "task_id": task.task_id,
                }
            )

        assert result["choices"][0]["message"]["content"] == "ok"
        # Entry: first message is the intro briefing
        first = captured["messages"][0]
        assert first["role"] == "system"
        assert "Task Intro: Solidify NEXUS core" in first["content"]
        assert task.task_id in first["content"]
        # Outro: rotation from model-alpha to the serving model was recorded
        assert len(test_bus.handoffs) == 1
        assert test_bus.handoffs[0].from_model == "model-alpha"
        assert test_bus.handoffs[0].reason == "model_rotation"

    @pytest.mark.asyncio
    async def test_second_turn_intro_carries_first_turn_state(self, relay, bus):
        """The zero-knowledge model on turn 2 must see turn 1's findings."""
        test_bus, task = bus
        test_bus.update_task(task.task_id, add_finding="turn one discovered X")

        fake = FakeCogER()
        fake.classify_complexity_heuristically = lambda q: "L1"
        relay._coger = fake

        messages, intro = relay._gmr_apply_task_handoff(
            {"task_id": task.task_id}, [{"role": "user", "content": "continue"}], "model-beta"
        )
        assert intro is not None
        assert "turn one discovered X" in intro
        assert messages[0]["role"] == "system"

    @pytest.mark.asyncio
    async def test_no_task_id_is_a_noop(self, relay):
        messages_in = [{"role": "user", "content": "hi"}]
        messages, intro = relay._gmr_apply_task_handoff({}, messages_in, "m")
        assert messages is messages_in
        assert intro is None

    @pytest.mark.asyncio
    async def test_unknown_task_id_is_a_noop(self, relay, bus):
        messages_in = [{"role": "user", "content": "hi"}]
        messages, intro = relay._gmr_apply_task_handoff(
            {"task_id": "task-nonexistent"}, messages_in, "m"
        )
        assert messages is messages_in
        assert intro is None
