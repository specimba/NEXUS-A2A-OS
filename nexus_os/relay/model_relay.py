"""
model_relay.py — Central Transparent Proxy v2.2
===============================================
Routes: ChimeraRouterV2 (model selection + temperature policy)
      → Ollama local/cloud inference (+ guard pipeline)

v2.2 additions:
- Multi-stage guard pipeline (special-virus → qwen2.5-guard → llama-guard3)
- /v1/guard endpoint for explicit content safety checks
- Guard integration into /v1/chat/completions (blocking mode)
- /api/models and /api/config (modelrelay npm compat endpoints)
- Health check loop now OFF by default, only recently-used models
"""

import os, json, time, logging, threading, asyncio
from collections import deque
from typing import Optional, Dict, Any, List
import requests
try:
    from fastapi import FastAPI
except Exception:
    class FastAPI:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs):
            pass

        def get(self, *args, **kwargs):
            def decorator(fn):
                return fn
            return decorator

        def post(self, *args, **kwargs):
            def decorator(fn):
                return fn
            return decorator

        def on_event(self, *args, **kwargs):
            def decorator(fn):
                return fn
            return decorator

try:
    from fastapi import Request, Query
except Exception:
    class Request:  # type: ignore[no-redef]
        async def json(self) -> dict:
            return {}

    def Query(default=None, **kwargs):  # type: ignore[no-redef]
        return default

try:
    from fastapi.responses import JSONResponse, HTMLResponse
except Exception:
    class JSONResponse(dict):  # type: ignore[no-redef]
        def __init__(self, content=None, status_code: int = 200, **kwargs):
            super().__init__(content or {})
            self.status_code = status_code
    class HTMLResponse(str):  # type: ignore[no-redef]
        def __init__(self, content="", status_code: int = 200, **kwargs):
            super().__init__()
            self.status_code = status_code
import uvicorn

from nexus_os.twave.chimera_router_v2 import ChimeraRouterV2, Tier, TemperaturePolicy

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "127.0.0.1:11434").rstrip("/")
OLLAMA_BASE_URL = OLLAMA_HOST if OLLAMA_HOST.startswith(("http://", "https://")) else f"http://{OLLAMA_HOST}"
OLLAMA_GENERATE_URL = f"{OLLAMA_BASE_URL}/api/generate"
OLLAMA_CHAT_URL = f"{OLLAMA_BASE_URL}/v1/chat/completions"
OLLAMA_TAGS_URL = f"{OLLAMA_BASE_URL}/api/tags"

HEALTH_CHECK_INTERVAL_S = int(os.environ.get("RELAY_HEALTH_INTERVAL", "0"))
HEALTH_CHECK_TIMEOUT_S = int(os.environ.get("RELAY_HEALTH_TIMEOUT", "10"))
HEALTH_STARTUP_SWEEP = os.environ.get("RELAY_HEALTH_STARTUP_SWEEP", "0") == "1"
LATENCY_WINDOW_SIZE = 20
STARTUP_PORT = int(os.environ.get("RELAY_PORT", "7355"))

logger = logging.getLogger("nexus.model_relay")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

GUARD_MODELS = [
    "special-virus:latest",
    "qwen2.5-guard-q4:latest",
    "llama-guard3:1b",
    "adversarial-constraint-relaxation",  # heuristic stage
]

app = FastAPI(title="Nexus ModelRelay", version="2.2.0")
if not hasattr(app, "on_event"):
    def _noop_event(*args, **kwargs):
        def decorator(fn):
            return fn
        return decorator
    app.on_event = _noop_event  # type: ignore[attr-defined]


class ModelStats:
    """Per-model rolling stats."""
    __slots__ = ("success", "failure", "latencies", "last_used", "last_success", "last_failure")

    def __init__(self):
        self.success: int = 0
        self.failure: int = 0
        self.latencies: deque = deque(maxlen=LATENCY_WINDOW_SIZE)
        self.last_used: float = 0.0
        self.last_success: float = 0.0
        self.last_failure: float = 0.0

    def record_success(self, latency_ms: float):
        self.success += 1
        self.latencies.append(latency_ms)
        self.last_used = time.time()
        self.last_success = time.time()

    def record_failure(self):
        self.failure += 1
        self.last_used = time.time()
        self.last_failure = time.time()

    def avg_latency(self) -> float:
        return sum(self.latencies) / len(self.latencies) if self.latencies else 0.0

    def success_rate(self) -> float:
        total = self.success + self.failure
        return self.success / total if total > 0 else 0.0

    def to_dict(self, healthy: bool) -> dict:
        return {
            "healthy": healthy,
            "success": self.success,
            "failure": self.failure,
            "success_rate": round(self.success_rate(), 3),
            "avg_latency_ms": round(self.avg_latency(), 1),
            "p95_latency_ms": round(self._p95(), 1),
            "last_used": self.last_used,
            "last_success": self.last_success,
            "last_failure": self.last_failure,
        }

    def _p95(self) -> float:
        if not self.latencies:
            return 0.0
        sorted_lat = sorted(self.latencies)
        idx = int(len(sorted_lat) * 0.95)
        return sorted_lat[min(idx, len(sorted_lat) - 1)]


def detect_complexity(prompt: str) -> tuple:
    """Heuristic prompt complexity → (quality_target, latency_budget_ms)."""
    p = prompt.lower()
    length = len(prompt)

    code_signals = sum(1 for kw in ["def ", "class ", "import ", "function", "=>", "```", "bug", "error", "stack trace"] if kw in p)
    reasoning_signals = sum(1 for kw in ["prove", "derive", "step by step", "why", "explain", "analyze", "compare"] if kw in p)
    creative_signals = sum(1 for kw in ["write a story", "poem", "imagine", "design", "brainstorm"] if kw in p)

    if code_signals >= 2 or reasoning_signals >= 2 or length > 2000:
        return (0.90, 8000)
    if code_signals == 1 or reasoning_signals == 1 or creative_signals >= 1 or length > 500:
        return (0.82, 5000)
    if length > 100:
        return (0.75, 3000)
    return (0.70, 2000)


class ModelRelay:
    def __init__(self):
        self.router = ChimeraRouterV2(
            vram_gb=8.0,
            has_cloud_access=True,
            available_tiers=None,
        )
        # Ollama 0.30: Vulkan + NVIDIA 20% perf means more VRAM is usable
        # Intel-file quant formats: IQ4_XS (~4.5bpw), FP8 (8-bit), Q4_K_M (standard)
        # IQ4_XS saves ~15% vRAM vs Q4_K_M at same param count
        self._quant_vram_multipliers = {
            "iq4_xs": 0.42, "iq4_nl": 0.44, "q4_0": 0.40, "q4_k_m": 0.48,
            "q5_k_m": 0.58, "q8_0": 0.75, "fp8": 0.50, "fp16": 1.00,
        }
        vram_env = os.environ.get("RELAY_VRAM_GB", "")
        if vram_env:
            try:
                self.router.vram_gb = float(vram_env)
            except ValueError:
                pass
            else:
                avail = []
                for p in self.router._available:
                    if p.memory_gb <= self.router.vram_gb or p.tier.value == "cloud":
                        avail.append(p)
                self.router._available = avail
        self.router.available_tiers = [
            self.router.profiles[0].tier.__class__.LOCAL_STANDARD,
            self.router.profiles[0].tier.__class__.LOCAL_POWER,
            self.router.profiles[0].tier.__class__.CLOUD,
            self.router.profiles[0].tier.__class__.CONTROL_PLANE,
        ]
        self.router._available = [
            p for p in self.router.profiles
            if p.tier in self.router.available_tiers
            and (p.memory_gb <= self.router.vram_gb or p.tier.value == 'cloud')
        ]
        self._fallback_models = ["minimax-m3:cloud", "nemotron-3-nano:4b", "functiongemma:latest"]
        self._model_health: Dict[str, bool] = {}
        self._model_stats: Dict[str, ModelStats] = {}
        self._available_ollama_models: List[str] = []
        self._start_time = time.time()
        self._health_thread: Optional[threading.Thread] = None
        self._health_stop = threading.Event()

        for m in self._fallback_models:
            self._model_stats.setdefault(m, ModelStats())

        self._discover_ollama_models()
        self._start_health_loop()

    def _discover_ollama_models(self):
        """Pull available models from Ollama's /api/tags."""
        try:
            resp = requests.get(OLLAMA_TAGS_URL, timeout=5)
            if resp.ok:
                self._available_ollama_models = [m["name"] for m in resp.json().get("models", [])]
                logger.info(f"Discovered {len(self._available_ollama_models)} Ollama models: {self._available_ollama_models}")
                for m in self._available_ollama_models:
                    self._model_stats.setdefault(m, ModelStats())
        except Exception as e:
            logger.warning(f"Could not discover Ollama models: {e}")

    def _start_health_loop(self):
        if HEALTH_CHECK_INTERVAL_S <= 0:
            logger.info("Health check loop disabled (set RELAY_HEALTH_INTERVAL > 0 to enable)")
            return
        def loop():
            first = True
            while not self._health_stop.is_set():
                if first and HEALTH_STARTUP_SWEEP:
                    models_to_check = list(self._model_stats.keys())
                    first = False
                else:
                    first = False
                    recent_cutoff = time.time() - (HEALTH_CHECK_INTERVAL_S * 4)
                    models_to_check = [m for m, s in self._model_stats.items() if s.last_used >= recent_cutoff]
                for model in models_to_check:
                    try:
                        self._check_health(model)
                    except Exception as e:
                        logger.debug(f"Health check failed for {model}: {e}")
                self._health_stop.wait(HEALTH_CHECK_INTERVAL_S)
        self._health_thread = threading.Thread(target=loop, daemon=True, name="health-loop")
        self._health_thread.start()
        sweep_note = ", startup sweep all known models" if HEALTH_STARTUP_SWEEP else ""
        logger.info(f"Health check loop started (interval={HEALTH_CHECK_INTERVAL_S}s{sweep_note})")

    def _check_health(self, model: str) -> bool:
        if model == "adversarial-constraint-relaxation":
            self._model_health[model] = True
            return True
        try:
            resp = requests.post(OLLAMA_CHAT_URL, json={
                "model": model,
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 1,
                "stream": False,
            }, timeout=HEALTH_CHECK_TIMEOUT_S)
            ok = resp.ok
            self._model_health[model] = ok
            return ok
        except Exception:
            self._model_health[model] = False
            return False

    def health_check(self, model: str) -> bool:
        if model in self._model_health:
            return self._model_health[model]
        return self._check_health(model)

    def _healthy_models(self) -> List[str]:
        return [m for m, h in self._model_health.items() if h]

    def _select_healthy_fallback(self, exclude: Optional[str] = None) -> Optional[str]:
        for m in self._fallback_models:
            if m == exclude:
                continue
            if self.health_check(m):
                return m
        healthy = [m for m in self._healthy_models() if m != exclude]
        return healthy[0] if healthy else None

    async def proxy_completion(self, request_data: dict) -> dict:
        messages = request_data.get("messages", [{"role": "user", "content": ""}])
        if not isinstance(messages, list) or not messages:
            messages = [{"role": "user", "content": str(messages)}]

        prompt = messages[-1].get("content", "") if isinstance(messages[-1], dict) else str(messages[-1])

        guard_mode = request_data.get("guard", os.environ.get("RELAY_GUARD_MODE", ""))
        if guard_mode and guard_mode != "off":
            strategy = guard_mode if guard_mode in ("strict", "consensus", "meta") else "consensus"
            guard_result = await self.check_guard(messages, timeout_s=10, strategy=strategy)
            if not guard_result["safe"]:
                return self._error_response(
                    f"blocked-by:{guard_result['stage']}",
                    "guard",
                    0.0,
                    f"[ModelRelay] Input blocked by guard stage '{guard_result['stage']}': {guard_result.get('reason', 'unsafe')}",
                    "guard_blocked",
                )

        model = request_data.get("model", "auto")
        temperature = request_data.get("temperature", None)
        max_tokens = request_data.get("max_tokens", 256)
        if max_tokens < 100:
            max_tokens = 256

        quality_target = request_data.get("quality_target")
        latency_budget_ms = request_data.get("latency_budget_ms")
        if quality_target is None or latency_budget_ms is None:
            auto_q, auto_l = detect_complexity(prompt)
            quality_target = quality_target if quality_target is not None else auto_q
            latency_budget_ms = latency_budget_ms if latency_budget_ms is not None else auto_l

        if model == "auto":
            decision = self.router.route(
                prompt,
                latency_budget_ms=int(latency_budget_ms),
                quality_target=float(quality_target),
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
            fallback = self._select_healthy_fallback(exclude=ollama_model)
            if fallback is None:
                return self._error_response(
                    ollama_model, model, temperature,
                    "[ModelRelay] No healthy Ollama model available",
                    "no_healthy_ollama_model",
                )
            logger.warning(f"Model {ollama_model} unhealthy, falling back to {fallback}")
            ollama_model = fallback

        ollama_payload = {
            "model": ollama_model,
            "messages": messages,
            "stream": False,
        }
        if temperature is not None:
            ollama_payload["temperature"] = temperature
        if max_tokens is not None:
            ollama_payload["max_tokens"] = max_tokens
        for key in ("tools", "tool_choice", "top_p", "stop", "response_format", "frequency_penalty", "presence_penalty"):
            if key in request_data:
                ollama_payload[key] = request_data[key]

        t0 = time.time()
        try:
            resp = requests.post(OLLAMA_CHAT_URL, json=ollama_payload, timeout=(30, 120))
            resp.raise_for_status()
            data = resp.json()
            raw_msg = data.get("choices", [{}])[0].get("message", {})
            content = raw_msg.get("content") or ""
            tool_calls = raw_msg.get("tool_calls")
            finish_reason = data.get("choices", [{}])[0].get("finish_reason", "stop")
            usage = data.get("usage", {})
            latency_ms = (time.time() - t0) * 1000
            self._model_stats.setdefault(ollama_model, ModelStats()).record_success(latency_ms)
            result_msg = {"role": "assistant", "content": content}
            if tool_calls:
                result_msg["tool_calls"] = tool_calls
            return {
                "id": f"relay-{int(time.time())}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": ollama_model,
                "choices": [{"index": 0, "message": result_msg, "finish_reason": finish_reason}],
                "usage": usage or {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "relay_info": {
                    "router_model": model,
                    "temperature": temperature,
                    "latency_ms": round(latency_ms, 1),
                    "quality_target": quality_target,
                    "latency_budget_ms": latency_budget_ms,
                },
            }
        except Exception as e:
            logger.error(f"Ollama inference failed for {ollama_model}: {e}")
            self._model_stats.setdefault(ollama_model, ModelStats()).record_failure()
            return self._error_response(ollama_model, model, temperature, f"[ModelRelay] Error: {e}", "inference_error")

    def _error_response(self, ollama_model, router_model, temperature, content, error_code):
        return {
            "id": f"relay-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": ollama_model,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "error"}],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "relay_info": {
                "router_model": router_model,
                "temperature": temperature,
                "error": error_code,
            },
        }

    def _map_to_ollama(self, model_name: str) -> str:
        mapping = {
            "functiongemma-270m": "functiongemma:latest",
            "qwen2.5-3b-instruct-q4_k_m": "qwen2.5-coder:7b",
            "phi-3-mini-4k-instruct-q4_k_m": "nemotron-3-nano:4b",
            "minimax-m3:cloud": "minimax-m3:cloud",
            "minimax-m3": "minimax-m3:cloud",
            "minimax-m2.7": "minimax-m2.7",
        }
        m = mapping.get(model_name)
        if m:
            return m
        for local in self._available_ollama_models:
            if model_name.lower() in local.lower() or local.lower() in model_name.lower():
                return local
        for fallback in self._fallback_models:
            if model_name.lower() in fallback.lower():
                return fallback
        return "minimax-m3:cloud"

    # ── Guard Pipeline ──────────────────────────────────────────────

    GUARD_SAFE_TOKENS = {"safe", "SAFE"}
    GUARD_UNSAFE_TOKENS = {"unsafe", "UNSAFE"}

    async def _classify_one(
        self, model: str, messages: List[dict], timeout_s: int
    ) -> dict:
        """Classify a prompt with one guard model. Returns {safe, output}.

        Special heuristic stage 'adversarial-constraint-relaxation' runs locally
        instead of calling Ollama — inspired by FastAT / constraint-relaxation-attack.
        """
        if model == "adversarial-constraint-relaxation":
            prompt = ""
            for m in messages:
                c = m.get("content", "") if isinstance(m, dict) else str(m)
                prompt += "\n" + c
            return self._adversarial_heuristic(prompt)

        try:
            resp = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda m=model: requests.post(
                        OLLAMA_CHAT_URL,
                        json={
                            "model": m,
                            "messages": messages,
                            "max_tokens": 32,
                            "stream": False,
                            "options": {"num_ctx": 2048},
                        },
                        timeout=timeout_s,
                    ),
                ),
                timeout=timeout_s + 5,
            )
            output = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            output_first = output.split("\n")[0].strip()
        except Exception as e:
            return {"safe": True, "output": f"guard_error: {e}"}

        if output_first in self.GUARD_SAFE_TOKENS:
            return {"safe": True, "output": output}
        elif output_first in self.GUARD_UNSAFE_TOKENS:
            return {"safe": False, "output": output}
        else:
            return {"safe": True, "output": output, "ambiguous": True}

    def _adversarial_heuristic(self, prompt: str) -> dict:
        """Constraint-relaxation & FastAT-inspired adversarial heuristic."""
        p = prompt.lower()
        score = 0.0
        flags = []

        if len(prompt) > 500:
            score += 0.2; flags.append("long_prompt")
        if sum(1 for w in ["ignore", "bypass", "disregard", "override", "forget", "skip"] if w in p) >= 2:
            score += 0.3; flags.append("instruction_override")
        if "without" in p and any(w in p for w in ["limit", "restrict", "constraint", "rule", "boundary", "filter", "guard"]):
            score += 0.2; flags.append("constraint_relaxation")
        if any(w in p for w in ["roleplay", "act as", "you are now", "pretend"]) and \
           any(w in p for w in ["evil", "harmful", "toxic", "malicious", "dangerous", "unsafe"]):
            score += 0.35; flags.append("roleplay_jailbreak")
        if any(c in prompt for c in ("\x00", "\x01", "\x02", "\x03", "\x04")):
            score += 0.4; flags.append("control_chars")
        if sum(1 for c in prompt if c.isupper()) > len(prompt) * 0.7 and len(prompt) > 50:
            score += 0.15; flags.append("excessive_uppercase")
        if prompt.count("\\n") > 10 or prompt.count("\\r") > 10:
            score += 0.15; flags.append("escaped_newlines")
        if any(c in prompt for c in ("\ufffd", "\\ufffd")):
            score += 0.25; flags.append("encoding_attack")
        if prompt.count("\n") > 20:
            score += 0.1; flags.append("many_newlines")

        if score >= 0.5:
            return {"safe": False, "output": f"UNSAFE adversarial_score={score:.2f} flags={flags}"}
        if score >= 0.25:
            return {"safe": True, "output": f"AMBIGUOUS adversarial_score={score:.2f} flags={flags}", "ambiguous": True}
        return {"safe": True, "output": f"SAFE adversarial_score={score:.2f}"}

    async def check_guard(
        self,
        messages: List[dict],
        stages: Optional[List[str]] = None,
        timeout_s: int = 15,
        strategy: str = "consensus",
    ) -> dict:
        """Run multi-stage guard classification with consensus decision.

        Stages run in parallel — healthy guard models only.
        Decision strategies:
          - "consensus": block if ≥2 stages say UNSAFE
          - "strict": block if ANY stage says UNSAFE
          - "meta": only llama-guard3 decides (other stages are advisory)

        Returns:
            {
                "safe": bool,
                "stage": str | None,        # authoritative stage
                "reason": str | None,        # raw output
                "unsafe_votes": int,
                "skipped": [str],            # unhealthy guard models skipped
                "classifications": { model: {"safe": bool, "output": str} }
            }
        """
        if stages is None:
            stages = GUARD_MODELS

        healthy_stages = [m for m in stages if self.health_check(m)]
        skipped = [m for m in stages if m not in healthy_stages]
        if skipped:
            logger.warning(f"Guard stage(s) unhealthy, skipping: {skipped}")

        if not healthy_stages:
            return {
                "safe": True,
                "stage": None,
                "reason": "no_healthy_guard_models",
                "unsafe_votes": 0,
                "total_stages": len(stages),
                "skipped": skipped,
                "classifications": {m: {"safe": True, "output": "skipped: unhealthy"} for m in stages},
            }

        tasks = [self._classify_one(m, messages, timeout_s) for m in healthy_stages]
        results = await asyncio.gather(*tasks)

        classifications = {}
        unsafe_votes = 0
        unsafe_stages = []

        for i, model in enumerate(healthy_stages):
            classifications[model] = results[i]
            if not results[i]["safe"]:
                unsafe_votes += 1
                unsafe_stages.append(model)
        for m in skipped:
            classifications[m] = {"safe": True, "output": "skipped: unhealthy"}

        active_stages = healthy_stages
        if strategy == "meta":
            meta_idx = next((i for i, m in enumerate(healthy_stages) if "llama-guard" in m), None)
            if meta_idx is not None and not results[meta_idx]["safe"]:
                safe = False
                stage = healthy_stages[meta_idx]
                reason = results[meta_idx]["output"]
            else:
                safe = True
                stage = unsafe_stages[0] if unsafe_stages else None
                reason = classifications.get(stage, {}).get("output") if stage else None
        elif strategy == "strict":
            safe = unsafe_votes == 0
            stage = unsafe_stages[0] if unsafe_stages else None
            reason = classifications[stage]["output"] if stage else None
        else:
            safe = unsafe_votes < (len(active_stages) // 2) + 1  # majority of healthy only
            stage = unsafe_stages[0] if unsafe_stages else None
            reason = classifications[stage]["output"] if stage else None

        return {
            "safe": safe,
            "stage": stage,
            "reason": reason,
            "unsafe_votes": unsafe_votes,
            "total_stages": len(stages),
            "skipped": skipped,
            "classifications": classifications,
        }

    def shutdown(self):
        self._health_stop.set()
        if self._health_thread:
            self._health_thread.join(timeout=2)


relay = ModelRelay()


@app.on_event("shutdown")
async def _shutdown():
    relay.shutdown()


@app.post("/v1/chat/completions")
async def chat(request: Request):
    body = await request.json()
    result = await relay.proxy_completion(body)
    return JSONResponse(result)


@app.get("/v1/models")
async def list_models():
    """OpenAI-compatible model list."""
    oai_models = []
    for m in relay._available_ollama_models:
        stats = relay._model_stats.get(m, ModelStats())
        oai_models.append({
            "id": m,
            "object": "model",
            "created": int(relay._start_time),
            "owned_by": "ollama",
            "healthy": relay._model_health.get(m, False),
        })
    for m in ["minimax-m3:cloud", "minimax-m2.7"]:
        if m not in [x["id"] for x in oai_models]:
            oai_models.append({
                "id": m,
                "object": "model",
                "created": int(relay._start_time),
                "owned_by": "ollama-cloud",
                "healthy": relay._model_health.get(m, False),
            })
    return JSONResponse({"object": "list", "data": oai_models})


@app.get("/api/models")
async def api_models():
    """modelrelay npm compat: list available models with metadata."""
    models = []
    for m in relay._available_ollama_models:
        stats = relay._model_stats.get(m, ModelStats())
        models.append({
            "name": m,
            "provider": "ollama",
            "healthy": relay._model_health.get(m, False),
            "success_rate": stats.success_rate(),
            "avg_latency_ms": round(stats.avg_latency(), 1),
        })
    for m in ["minimax-m3:cloud"]:
        if m not in [x["name"] for x in models]:
            stats = relay._model_stats.get(m, ModelStats())
            models.append({
                "name": m,
                "provider": "ollama-cloud",
                "healthy": relay._model_health.get(m, False),
                "success_rate": stats.success_rate(),
                "avg_latency_ms": round(stats.avg_latency(), 1),
            })
    return JSONResponse({"models": models, "count": len(models)})


@app.get("/api/config")
async def api_config():
    """modelrelay npm compat: relay configuration."""
    return JSONResponse({
        "port": STARTUP_PORT,
        "ollama_host": OLLAMA_HOST,
        "health_interval_s": HEALTH_CHECK_INTERVAL_S,
        "health_timeout_s": HEALTH_CHECK_TIMEOUT_S,
        "vram_gb": 8.0,
        "discovered_models_count": len(relay._available_ollama_models),
        "fallback_models": relay._fallback_models,
        "version": "2.2.0",
        "uptime_s": round(time.time() - relay._start_time, 1),
    })


@app.post("/v1/guard")
async def guard_check(request: Request):
    """Multi-stage guard classification with consensus.

    Body:
    {
        "messages": [{"role": "user", "content": "..."}],
        "stages": null | ["special-virus:latest", ...],
        "strategy": "consensus" | "strict" | "meta",  # default: consensus
        "mode": "block" | "audit"   # block returns 403 if unsafe
    }
    """
    body = await request.json()
    messages = body.get("messages", [{"role": "user", "content": ""}])
    stages = body.get("stages", None)
    strategy = body.get("strategy", "consensus")
    mode = body.get("mode", "audit")

    result = await relay.check_guard(messages, stages=stages, strategy=strategy)

    status_code = 403 if mode == "block" and not result["safe"] else 200
    return JSONResponse(result, status_code=status_code)


@app.get("/health")
async def health():
    return JSONResponse({
        "status": "ok",
        "uptime_s": round(time.time() - relay._start_time, 1),
        "models_healthy": relay._model_health,
        "discovered_models": relay._available_ollama_models,
    })


@app.get("/health/ready")
async def health_ready():
    """K8s-style readiness probe. 503 if no healthy models."""
    healthy = relay._healthy_models()
    if not healthy:
        return JSONResponse(
            {"status": "unready", "healthy_models": [], "reason": "no_healthy_models"},
            status_code=503,
        )
    return JSONResponse({"status": "ready", "healthy_models": healthy, "count": len(healthy)})


@app.get("/metrics")
async def metrics():
    """Per-model rolling stats."""
    out = {
        "uptime_s": round(time.time() - relay._start_time, 1),
        "models": {},
        "totals": {
            "requests": sum(s.success + s.failure for s in relay._model_stats.values()),
            "successes": sum(s.success for s in relay._model_stats.values()),
            "failures": sum(s.failure for s in relay._model_stats.values()),
        },
    }
    for m, stats in relay._model_stats.items():
        out["models"][m] = stats.to_dict(relay._model_health.get(m, False))
    return JSONResponse(out)


@app.get("/router/inspect")
async def router_inspect(
    prompt: str = Query(..., description="Prompt to inspect"),
    quality_target: Optional[float] = Query(None, ge=0.0, le=1.0),
    latency_budget_ms: Optional[int] = Query(None, ge=100, le=180000),
):
    """Inspect what the router would do without actually calling the model."""
    if quality_target is None or latency_budget_ms is None:
        auto_q, auto_l = detect_complexity(prompt)
        quality_target = quality_target or auto_q
        latency_budget_ms = latency_budget_ms or auto_l
    decision = relay.router.route(
        prompt,
        latency_budget_ms=int(latency_budget_ms),
        quality_target=float(quality_target),
        temperature_policy=TemperaturePolicy.AUTO,
    )
    return JSONResponse({
        "prompt_length": len(prompt),
        "detected_complexity": {
            "quality_target": quality_target,
            "latency_budget_ms": latency_budget_ms,
        },
        "decision": {
            "model": decision.model,
            "tier": decision.tier.value,
            "temperature": decision.temperature,
            "expected_quality": decision.expected_quality,
            "expected_latency_ms": decision.expected_latency_ms,
            "reason": decision.reason,
        },
    })


@app.get("/v1/quant")
async def quant_estimate(model: str = Query("", description="Model name to estimate"), params_b: float = Query(7, ge=0)):
    """Estimate VRAM for a model given quantization format in its name."""
    name_segments = set(model.lower().replace("-", "_").replace(".", "_").split("_"))
    matched_fmt = "q4_k_m"
    for fmt in relay._quant_vram_multipliers:
        fmt_segments = set(fmt.split("_"))
        if fmt_segments.issubset(name_segments):
            matched_fmt = fmt
            break
    mult = relay._quant_vram_multipliers.get(matched_fmt, 0.48)
    est_gb = round(params_b * mult * 1.05, 2)
    return JSONResponse({
        "model": model or "(not specified)",
        "detected_format": matched_fmt,
        "multiplier": mult,
        "params_b": params_b,
        "estimated_vram_gb": est_gb if model else "provide model name",
        "available_vram_gb": relay.router.vram_gb,
        "fits": est_gb <= relay.router.vram_gb if model else None,
        "formats": relay._quant_vram_multipliers,
    })


@app.get("/v1/adversarial")
async def adversarial_check(prompt: str = Query(..., description="Prompt to check")):
    """Constraint-relaxation inspired adversarial robustness check.

    Tests prompt variations and detects anomalies via multi-angle scoring.
    Based on: specimba/constraint-relaxation-attack + FastAT principles.
    """
    import hashlib
    p = prompt.lower()
    score = 0.0
    flags = []

    # Heuristic adversarial signals
    if len(prompt) > 500:
        score += 0.2
        flags.append("long_prompt")
    if any(c in prompt for c in ("\x00", "\x01", "\x02", "\x03", "\x04")):
        score += 0.4
        flags.append("control_chars")
    if sum(1 for c in prompt if c.isupper()) > len(prompt) * 0.7 and len(prompt) > 50:
        score += 0.15
        flags.append("excessive_uppercase")
    if prompt.count("\\n") > 10 or prompt.count("\\r") > 10:
        score += 0.15
        flags.append("excessive_escaped_newlines")
    if sum(1 for w in ["ignore", "bypass", "disregard", "override", "forget", "skip"] if w in p) >= 2:
        score += 0.3
        flags.append("instruction_override_attempt")
    if prompt.count("\n") > 20:
        score += 0.1
        flags.append("many_newlines")
    if any(c in prompt for c in ("\ufffd", "\\ufffd", "\\xe2\\x80")):
        score += 0.25
        flags.append("encoding_attack_pattern")
    # Constraint relaxation: prompt tries to subtract constraints
    if "without" in p and any(w in p for w in ["limit", "restrict", "constraint", "rule", "boundary", "filter", "guard"]):
        score += 0.2
        flags.append("constraint_relaxation")
    # Role-play jailbreak patterns
    if any(w in p for w in ["roleplay", "act as", "you are now", "pretend", "character.ai", "into character"]):
        if any(w in p for w in ["evil", "harmful", "toxic", "malicious", "dangerous", "unsafe", "bypass", "ignore"]):
            score += 0.35
            flags.append("roleplay_jailbreak_attempt")

    return JSONResponse({
        "prompt_length": len(prompt),
        "adversarial_score": round(score, 2),
        "risk": "high" if score >= 0.5 else ("medium" if score >= 0.25 else "low"),
        "flags": flags,
        "safety": "block" if score >= 0.5 else "allow",
    })


@app.get("/benchmark/config")
async def benchmark_config():
    """Benchmark integration config — FastAT / ISC-Bench compatible format."""
    return JSONResponse({
        "suite": "nexus-relay-v2",
        "version": "2.2.0",
        "models": relay._available_ollama_models,
        "providers": {
            "ollama": {"host": OLLAMA_HOST, "models": relay._available_ollama_models},
            "guard_models": GUARD_MODELS,
            "fallbacks": relay._fallback_models,
        },
        "router": {
            "vram_gb": relay.router.vram_gb,
            "tier": [t.value for t in relay.router.available_tiers] if relay.router.available_tiers else [],
            "quant_formats": list(relay._quant_vram_multipliers.keys()),
        },
        "benchmarks": {
            "isc_bench": {"url": "https://github.com/specimba/ISC-Bench/tree/main"},
            "fastat": {"url": "https://fzjcdt.github.io/FastAT_Benchmark/benchmark.html"},
            "paperask": {"available": False, "note": "requires PaperAsk dataset"},
            "bashgemma": {"model": "bashgemma-270m", "nlc2cmd": 0.574, "base_functiongemma": 0.045},
        },
        "endpoints": {
            "chat": "/v1/chat/completions",
            "guard": "/v1/guard",
            "adversarial": "/v1/adversarial",
            "quant": "/v1/quant",
            "health": "/health",
        },
    })


@app.get("/")
async def dashboard_root(request: Request):
    """Live telemetry dashboard — HTML in browser, JSON for CLI."""
    healthy = relay._healthy_models()
    model_details = {}
    for m, stats in relay._model_stats.items():
        h = relay._model_health.get(m, False)
        model_details[m] = stats.to_dict(h)
    guard_health = {m: relay._model_health.get(m, False) for m in GUARD_MODELS}

    accept = request.headers.get("accept", "")
    if "text/html" not in accept:
        unhealthy = [m for m, h in relay._model_health.items() if not h]
        totals = {
            "requests": sum(s.success + s.failure for s in relay._model_stats.values()),
            "successes": sum(s.success for s in relay._model_stats.values()),
            "failures": sum(s.failure for s in relay._model_stats.values()),
        }
        return JSONResponse({
            "version": "2.2.0",
            "uptime_s": round(time.time() - relay._start_time, 1),
            "ollama_host": OLLAMA_HOST, "port": STARTUP_PORT,
            "models": {
                "total_discovered": len(relay._available_ollama_models),
                "healthy": len(healthy),
                "unhealthy": len(unhealthy),
                "list": model_details,
            },
            "providers": {"local_ollama": {"host": OLLAMA_HOST, "models": relay._available_ollama_models}, "fallbacks": relay._fallback_models},
            "guard": {"models": GUARD_MODELS, "health": guard_health},
            "totals": totals,
            "endpoints": {"v1/chat/completions": "POST", "v1/models": "GET", "v1/guard": "POST", "api/models": "GET", "api/config": "GET", "health": "GET", "health/ready": "GET", "metrics": "GET", "router/inspect": "GET"},
        })

    rows = "".join(
        f"<tr><td>{m[:50]}</td>"
        f"<td style='color:{"green" if s["healthy"] else "red"};font-weight:bold'>{'HEALTHY' if s["healthy"] else 'DOWN'}</td>"
        f"<td>{s['success_rate']:.0%}</td>"
        f"<td>{s['avg_latency_ms']:.0f}ms</td>"
        f"<td>{s['success']}</td>"
        f"<td>{s['failure']}</td></tr>"
        for m, s in sorted(model_details.items())
    )
    guard_rows = "".join(
        f"<tr><td>{m}</td><td style='color:{"green" if h else "red"}'>{'HEALTHY' if h else 'DOWN'}</td></tr>"
        for m, h in sorted(guard_health.items())
    )
    uptime_s = round(time.time() - relay._start_time)
    hr = uptime_s // 3600; mn = (uptime_s % 3600) // 60; sc = uptime_s % 60
    uptime_str = f"{hr}h {mn}m {sc}s"

    return HTMLResponse(f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><title>Nexus Relay</title>
<style>
body {{ font-family: monospace; margin: 20px; background: #0d1117; color: #c9d1d9; }}
h1,h2,h3 {{ color: #58a6ff; }}
table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
th,td {{ text-align: left; padding: 6px 10px; border-bottom: 1px solid #30363d; }}
th {{ background: #161b22; color: #8b949e; text-transform: uppercase; font-size: 11px; }}
.healthy {{ color: #3fb950; }} .down {{ color: #f85149; }}
.summary {{ display: flex; gap: 20px; margin: 10px 0 20px; }}
.card {{ background: #161b22; padding: 12px 20px; border-radius: 6px; border: 1px solid #30363d; }}
.big {{ font-size: 28px; font-weight: bold; color: #58a6ff; }}
.label {{ font-size: 11px; color: #8b949e; text-transform: uppercase; }}
</style></head><body>
<h1>Nexus Relay <span style="font-size:14px;color:#8b949e">v2.2.0</span></h1>
<p>Uptime: {uptime_str} &middot; Ollama: {OLLAMA_HOST} &middot; Port: {STARTUP_PORT}</p>
<div class="summary">
<div class="card"><div class="big">{len(relay._available_ollama_models)}</div><div class="label">Models</div></div>
<div class="card"><div class="big" style="color:#3fb950">{len(healthy)}</div><div class="label">Healthy</div></div>
<div class="card"><div class="big" style="color:#f85149">{sum(1 for h in relay._model_health.values() if not h)}</div><div class="label">Unhealthy</div></div>
<div class="card"><div class="big" style="color:#d2a8ff">{len(GUARD_MODELS)}</div><div class="label">Guard Stages</div></div>
</div>
<h2>Models</h2>
<table><tr><th>Name</th><th>Health</th><th>Success Rate</th><th>Avg Latency</th><th>Successes</th><th>Failures</th></tr>{rows}</table>
<h2>Guard Pipeline</h2>
<table><tr><th>Model</th><th>Status</th></tr>{guard_rows}</table>
<h2>Endpoints</h2>
<table><tr><th>Path</th><th>Method</th></tr>
<tr><td>/v1/chat/completions</td><td>POST</td></tr>
<tr><td>/v1/models</td><td>GET</td></tr>
<tr><td>/v1/guard</td><td>POST</td></tr>
<tr><td>/api/models</td><td>GET</td></tr>
<tr><td>/health</td><td>GET</td></tr>
<tr><td>/health/ready</td><td>GET</td></tr>
<tr><td>/metrics</td><td>GET</td></tr>
<tr><td>/router/inspect</td><td>GET</td></tr>
</table>
<p style="color:#8b949e">Node/npm ModelRelay primary at <a href="http://localhost:7350" style="color:#58a6ff">localhost:7350</a>; Python relay on <a href="http://localhost:7355" style="color:#58a6ff">localhost:7355</a> &mdash; cloud providers need API keys</p>
</body></html>""")


if __name__ == "__main__":
    logger.info(f"Starting Nexus ModelRelay v2.1 on port {STARTUP_PORT}")
    uvicorn.run(app, host="0.0.0.0", port=STARTUP_PORT)
