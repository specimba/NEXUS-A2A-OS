"""
model_relay.py — Central Transparent Proxy v2.0
===============================================
Replaces v1.15.0 stub with real ChimeraRouterV2 + Ollama inference.
Routes: ChimeraRouterV2 (model selection + temperature policy)
      → Ollama local inference

TWAVE v2.0 entropy/hallucination telemetry is not wired here yet.
"""

import os, json, time, logging
from typing import Optional, Dict, Any
import requests
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

from nexus_os.twave.chimera_router_v2 import ChimeraRouterV2, TemperaturePolicy

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "127.0.0.1:11434").rstrip("/")
OLLAMA_BASE_URL = OLLAMA_HOST if OLLAMA_HOST.startswith(("http://", "https://")) else f"http://{OLLAMA_HOST}"
OLLAMA_URL = f"{OLLAMA_BASE_URL}/api/generate"

logger = logging.getLogger("nexus.model_relay")

app = FastAPI(title="Nexus ModelRelay", version="2.0.0")

class ModelRelay:
    def __init__(self):
        self.router = ChimeraRouterV2(vram_gb=8.0, has_cloud_access=False)
        self._fallback_models = ["nemotron-3-nano:4b", "functiongemma:latest"]
        self._model_health: Dict[str, bool] = {}

    def health_check(self, model: str) -> bool:
        if model in self._model_health:
            return self._model_health[model]
        try:
            resp = requests.post(OLLAMA_URL, json={
                "model": model, "prompt": "ping", "stream": False,
                "options": {"num_predict": 1},
            }, timeout=5)
            self._model_health[model] = resp.ok
            return resp.ok
        except Exception:
            self._model_health[model] = False
            return False

    async def proxy_completion(self, request_data: dict) -> dict:
        prompt = request_data.get("messages", [{}])
        if isinstance(prompt, list) and prompt:
            prompt = prompt[-1].get("content", "")
        elif isinstance(prompt, dict):
            prompt = prompt.get("content", "")
        else:
            prompt = str(prompt)

        model = request_data.get("model", "auto")
        temperature = request_data.get("temperature", None)
        max_tokens = request_data.get("max_tokens", 256)

        if model == "auto":
            decision = self.router.route(
                prompt, latency_budget_ms=2000, quality_target=0.75,
                temperature_policy=TemperaturePolicy.AUTO,
            )
            model = decision.model
            if temperature is None:
                temperature = decision.temperature
        else:
            if temperature is None:
                temperature = 0.7

        ollama_model = self._map_to_ollama(model)
        if not self.health_check(ollama_model):
            healthy_model = None
            for fallback in self._fallback_models:
                if self.health_check(fallback):
                    healthy_model = fallback
                    break
            if healthy_model is None:
                return {
                    "id": f"relay-{int(time.time())}",
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": ollama_model,
                    "choices": [{
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "[ModelRelay] No healthy Ollama model available",
                        },
                        "finish_reason": "error",
                    }],
                    "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                    "relay_info": {
                        "router_model": model,
                        "temperature": temperature,
                        "error": "no_healthy_ollama_model",
                    },
                }
            ollama_model = healthy_model

        try:
            resp = requests.post(OLLAMA_URL, json={
                "model": ollama_model, "prompt": prompt, "stream": False,
                "options": {"temperature": temperature, "num_predict": max_tokens},
            }, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            content = data.get("response", "")
            return {
                "id": f"relay-{int(time.time())}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": ollama_model,
                "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": len(prompt) // 4, "completion_tokens": len(content) // 4, "total_tokens": (len(prompt) + len(content)) // 4},
                "relay_info": {"router_model": model, "temperature": temperature},
            }
        except Exception as e:
            logger.error(f"Ollama inference failed: {e}")
            return {
                "id": f"relay-{int(time.time())}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": ollama_model,
                "choices": [{"index": 0, "message": {"role": "assistant", "content": f"[ModelRelay] Error: {e}"}, "finish_reason": "error"}],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            }

    def _map_to_ollama(self, model_name: str) -> str:
        mapping = {
            "functiongemma-270m": "functiongemma:latest",
            "qwen2.5-3b-instruct-q4_k_m": "qwen2.5-coder:7b",
            "phi-3-mini-4k-instruct-q4_k_m": "nemotron-3-nano:4b",
        }
        m = mapping.get(model_name)
        if m:
            return m
        for local in self._fallback_models:
            if model_name.lower() in local.lower():
                return local
        return "nemotron-3-nano:4b"

relay = ModelRelay()

@app.post("/v1/chat/completions")
async def chat(request: Request):
    body = await request.json()
    result = await relay.proxy_completion(body)
    return JSONResponse(result)

@app.get("/health")
async def health():
    return JSONResponse({"status": "ok", "models_healthy": relay._model_health})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7352)
