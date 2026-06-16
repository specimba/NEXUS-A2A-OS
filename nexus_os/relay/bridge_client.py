"""ModelRelayBridge — Python bridge to modelrelay npm on port 7352 with multi-dim scoring."""

from __future__ import annotations
import json
import logging
import threading
import time
from typing import Any, Optional
from nexus_os.relay.scorer import ModelScores, get_scores, rank_by_dimension, rank_by_intent, resolve
from nexus_os.relay.circuit_breaker import ProviderCircuitBreaker
from nexus_os.relay.quota import QuotaGuard, QuotaType

logger = logging.getLogger(__name__)


class ModelRelayBridge:
    def __init__(self, modelrelay_url: str = "http://localhost:7352", refresh_interval: int = 3600):
        self._url = modelrelay_url.rstrip("/")
        self._refresh_interval = refresh_interval
        self._models: dict[str, dict] = {}
        self._last_refresh = 0.0
        self._lock = threading.Lock()
        self.circuit_breaker = ProviderCircuitBreaker()
        self.quota_guard = QuotaGuard()
        self._init_quotas()

    def _init_quotas(self):
        for p in ["ollama", "opencode", "nvidia", "openrouter", "googleai", "groq", "cerebras", "mistral", "anthropic", "openai", "deepseek", "meta", "cohere", "xai"]:
            self.quota_guard.register(p, QuotaType.MESSAGES, limit=5000)

    @property
    def models(self) -> dict[str, dict]:
        if time.time() - self._last_refresh >= self._refresh_interval:
            self.refresh()
        return dict(self._models)

    def refresh(self) -> dict[str, dict]:
        with self._lock:
            if time.time() - self._last_refresh < self._refresh_interval:
                return dict(self._models)
            try:
                import requests
                resp = requests.get(f"{self._url}/api/models", timeout=10)
                data = resp.json()
                raw_models = data if isinstance(data, dict) else {}
                if "models" in data:
                    raw_models = {}
                    for m in data["models"]:
                        mk = m.get("name") or m.get("modelId") or m.get("id") or str(len(raw_models))
                        raw_models[mk] = m
                elif isinstance(data, list):
                    raw_models = {m.get("name", m.get("modelId", str(i))): m for i, m in enumerate(data)}
                def _resolve_scores(n: str) -> ModelScores | None:
                    s = get_scores(n)
                    if s:
                        return s
                    short = n.split("/")[-1].split(":")[0].replace("-", " ")
                    for alias in [short, short.replace(" ", "-"), short.split(" ")[0]]:
                        s = get_scores(alias)
                        if s:
                            return s
                    return None

                self._models = {}
                for name, raw in raw_models.items():
                    if not isinstance(raw, dict):
                        continue
                    provider = raw.get("provider", raw.get("providerKey", "unknown"))
                    latency_raw = raw.get("latency_ms") or raw.get("latency") or raw.get("avg") or raw.get("lastPing", 0)
                    try:
                        latency = float(latency_raw)
                    except (ValueError, TypeError):
                        latency = 0.0
                    scores = _resolve_scores(name) or _resolve_scores(raw.get("model", ""))
                    self._models[name] = {
                        "name": name,
                        "provider": provider,
                        "status": raw.get("status", "unknown"),
                        "latency_ms": latency,
                        "tier": int(raw.get("tier", 0)),
                        "uptime": float(raw.get("uptime", raw.get("uptime_pct", 1.0))),
                        "swe_score": scores.swe if scores else 0.5,
                        "math_score": scores.math if scores else 0.5,
                        "code_score": scores.code if scores else 0.5,
                        "quality_score": scores.quality if scores else 0.5,
                        "reasoning_score": scores.reasoning if scores else 0.5,
                        "speed_score": scores.speed if scores else 0.5,
                        "cost_efficiency_score": scores.cost_efficiency if scores else 0.5,
                        "overall_score": scores.overall if scores else 0.5,
                    }
                self._last_refresh = time.time()
                logger.info("Refreshed %d models from %s", len(self._models), self._url)
            except Exception as e:
                logger.warning("Failed to refresh models: %s", e)
            return dict(self._models)

    def get_refresh_status(self) -> dict:
        return {
            "last_refresh": self._last_refresh,
            "refresh_interval": self._refresh_interval,
            "models_count": len(self._models),
            "next_refresh_in": max(0, self._refresh_interval - (time.time() - self._last_refresh)) if self._last_refresh else 0,
        }

    def get_models_up(self) -> list[dict]:
        return [m for m in self.models.values() if m.get("status") == "up"]

    def get_ranked_by(self, dimension: str = "overall", top_k: int = 10) -> list[dict]:
        scored = rank_by_dimension(dimension, top_k)
        models = self.models
        result = []
        for name, score in scored:
            if name in models:
                result.append({"name": name, "score": score, **models[name]})
            else:
                resolved = resolve(name)
                if resolved != name and resolved in models:
                    result.append({"name": resolved, "score": score, **models[resolved]})
                else:
                    for mk, mv in models.items():
                        if name.lower().replace("-", " ") in mk.lower() or name.lower().replace(" ", "-") in mk.lower():
                            result.append({"name": mk, "score": score, **mv})
                            break
        return result[:top_k]

    def get_best_for_intent(self, intent: str, top_k: int = 5) -> list[dict]:
        scored = rank_by_intent(intent, top_k)
        models = self.models
        result = []
        for name, score in scored:
            if name in models:
                result.append({"name": name, "score": score, **models[name]})
            else:
                resolved = resolve(name)
                if resolved != name and resolved in models:
                    result.append({"name": resolved, "score": score, **models[resolved]})
                else:
                    for mk, mv in models.items():
                        if name.lower().replace("-", " ") in mk.lower() or name.lower().replace(" ", "-") in mk.lower():
                            result.append({"name": mk, "score": score, **mv})
                            break
        return result[:top_k]

    def get_fastest_online(self, top_k: int = 5) -> list[dict]:
        up = [m for m in self.models.values() if m.get("status") == "up"]
        up.sort(key=lambda m: m.get("latency_ms", float("inf")))
        return up[:top_k]

    def get_highest_scored(self, dimension: str = "overall", top_k: int = 5) -> list[dict]:
        return self.get_ranked_by(dimension, top_k)
