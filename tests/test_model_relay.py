import importlib

import pytest

from nexus_os.relay import model_relay


class _Response:
    def __init__(self, ok=True, payload=None):
        self.ok = ok
        self._payload = payload or {"response": "relay ok"}

    def raise_for_status(self):
        if not self.ok:
            raise RuntimeError("request failed")

    def json(self):
        return self._payload


@pytest.mark.asyncio
async def test_proxy_completion_routes_auto_model_to_ollama(monkeypatch):
    calls = []

    def fake_post(url, json, timeout):
        calls.append({"url": url, "json": json, "timeout": timeout})
        return _Response(payload={"response": "hello from ollama"})

    monkeypatch.setattr(model_relay.requests, "post", fake_post)
    relay = model_relay.ModelRelay()

    result = await relay.proxy_completion(
        {
            "model": "auto",
            "messages": [{"role": "user", "content": "Write a short plan"}],
            "max_tokens": 12,
        }
    )

    assert result["object"] == "chat.completion"
    assert result["choices"][0]["message"]["content"] == "hello from ollama"
    assert result["relay_info"]["router_model"]
    assert calls[-1]["json"]["options"]["num_predict"] == 12


@pytest.mark.asyncio
async def test_proxy_completion_fails_when_no_healthy_model(monkeypatch):
    calls = []

    def unhealthy_post(url, json, timeout):
        calls.append({"url": url, "json": json, "timeout": timeout})
        return _Response(ok=False, payload={})

    monkeypatch.setattr(model_relay.requests, "post", unhealthy_post)
    relay = model_relay.ModelRelay()

    result = await relay.proxy_completion(
        {
            "model": "auto",
            "messages": [{"role": "user", "content": "Hello"}],
        }
    )

    assert result["choices"][0]["finish_reason"] == "error"
    assert result["relay_info"]["error"] == "no_healthy_ollama_model"
    # One primary health check plus the configured fallback health checks.
    assert len(calls) == 1 + len(relay._fallback_models)


def test_ollama_host_allows_scheme(monkeypatch):
    monkeypatch.setenv("OLLAMA_HOST", "http://localhost:11434/")

    reloaded = importlib.reload(model_relay)

    assert reloaded.OLLAMA_URL == "http://localhost:11434/api/generate"
