import importlib

import pytest
import requests

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
    """Test that proxy_completion calls Ollama chat API and returns OAI-compatible response."""
    calls = []

    def fake_post(url, json, timeout):
        calls.append({"url": url, "json": json, "timeout": timeout})
        # Return OAI chat completion format (v2.1 uses /v1/chat/completions)
        return _Response(
            payload={
                "choices": [{"message": {"content": "hello from ollama"}}],
                "usage": {
                    "prompt_tokens": 5,
                    "completion_tokens": 10,
                    "total_tokens": 15,
                },
            }
        )

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
    # v2.1 uses chat API, not generate API, so num_predict is not set
    assert result["usage"]["total_tokens"] == 15


@pytest.mark.asyncio
async def test_proxy_completion_fails_when_no_healthy_model(monkeypatch):
    """Test that proxy_completion returns error when all Ollama models are unhealthy."""
    monkeypatch.delenv("BASETEN_API_KEY", raising=False)
    calls = []

    def unhealthy_post(url, json, timeout):
        calls.append({"url": url, "json": json, "timeout": timeout})
        # Simulate HTTP error (model not loaded / unhealthy)
        raise requests.ConnectionError("Connection refused")

    monkeypatch.setattr(model_relay.requests, "post", unhealthy_post)
    relay = model_relay.ModelRelay()

    result = await relay.proxy_completion(
        {
            "model": "auto",
            "messages": [{"role": "user", "content": "Hello"}],
        }
    )

    assert result["choices"][0]["finish_reason"] == "error"
    # Health check fails before inference, so error is no_healthy_ollama_model
    assert result["relay_info"]["error"] == "no_healthy_ollama_model"
    # v2.1: health check happens before inference
    assert len(calls) >= 1


def test_ollama_host_allows_scheme(monkeypatch):
    monkeypatch.setenv("OLLAMA_HOST", "http://localhost:11434/")

    reloaded = importlib.reload(model_relay)

    # v2.1: OLLAMA_HOST is normalized to OLLAMA_BASE_URL
    assert reloaded.OLLAMA_BASE_URL == "http://localhost:11434"
    assert reloaded.OLLAMA_GENERATE_URL == "http://localhost:11434/api/generate"
