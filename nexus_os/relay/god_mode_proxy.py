"""
NEXUS God Mode Proxy v3.1 — Fallback chains, context-aware, provider diversity
Port 7357 — Sits between opencode and modelrelay (port 7350)

Profiles:
  god-smart    — Highest intelligence, tolerates high latency, 256k+ context preferred
  god-mode     — Balanced (intelligence + latency + health + context)
  god-fast     — Lowest latency, good enough intelligence
  god-code     — Coding-optimized, 128k+ context
  god-1m       — 1M+ context window REQUIRED (falls back to 256k+)
  god-reason   — Reasoning/thinking models, 128k+ context
  auto         — Same as Normal (balanced)
  auto-fastest — Alias for god-fast (lowest latency)
  auto-smart   — Alias for god-smart (highest intelligence)
  auto-code    — Alias for god-code (coding-optimized)
  auto-reason  — Alias for god-reason (reasoning/thinking)

Features:
  - Fallback chain: tries up to 3 candidates, auto-retries on failure
  - Context-aware: estimates prompt size, requires adequate context window
  - Provider diversity: penalizes recently-used providers, rotates across top candidates
  - Provider budget tiers: prefers unlimited free tier over trial credits
  - Response metadata: shows model, provider, intelligence, latency, context, why selected
"""
import asyncio
import json
import time
from typing import Optional, Dict, List, Tuple
from collections import defaultdict
from datetime import datetime, timedelta

import aiohttp
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Node/npm ModelRelay (primary, port 7350), Python relay fallback (port 7355)
_NODERELAY_PORT = int(__import__("os").environ.get("NODERELAY_PORT", "7350"))
_PYTHONRELAY_PORT = int(__import__("os").environ.get("PYTHONRELAY_PORT", "7355"))

# Detect which relay is active by trying both
MODELRELAY_URL = f"http://127.0.0.1:{_NODERELAY_PORT}"
MODELRELAY_API = f"{MODELRELAY_URL}/api"
MODELRELAY_CHAT = f"{MODELRELAY_URL}/v1/chat/completions"

# Fallback URL if primary is unreachable
MODELRELAY_FALLBACK_URL = f"http://127.0.0.1:{_PYTHONRELAY_PORT}"

# Provider budget tiers: higher = more reliable/unlimited
PROVIDER_TIER = {
    "cloudflare": 3,           # 10k neurons/day, 100% health, very reliable
    "groq": 3,                 # Fast, generous limits, reliable
    "kilocode": 3,             # Free tier, reliable
    "mistral": 3,              # La Plateforme, 1M tokens/month
    "cerebras": 2,             # Good free tier but limited models
    "codestral": 2,            # Codestral specific, good for code
    "openrouter": 2,           # Free models but rate limited
    "opencode": 2,             # Free tier, some models limited
    "nvidia": 2,               # NIM, 40 req/min, phone verify required
    "openai-compatible:github": 2,  # GitHub Models, free but restrictive
    "openai-compatible:baseten": 3, # Premium Baseten models
    "openai-compatible:deepinfra": 1,  # Trial credits, rate limited
    "openai-compatible:fireworks": 1,  # $1 trial, VERY limited budget
    "openai-compatible:sambanova": 1,  # $5 trial, limited
    "openai-compatible:siliconflow": 1,  # Rate limited, balance issues
    "googleai": 1,             # Free but credits depleted for this account
    "scaleway": 0,             # No API key configured
    "ollama": 0,               # Local, not always running
    "kiro": 0,                  # Complex auth, not fully operational
}

# Tier reliability bonus (0-5 points added to score) — small, not dominant
TIER_BONUS = {3: 5, 2: 2, 1: 0, 0: -10}

GOD_PROFILES = {
    "god-smart": {
        "name": "Smart",
        "intell_weight": 70, "latency_weight": 10, "health_weight": 10, "ctx_weight": 10,
        "min_ctx": 256_000,  # Prefer 256k+ for smart work
        "fallback_ctx": 128_000,  # If nothing 256k+, fall back to 128k+
        "min_intell": 0.60,
    },
    "god-mode": {
        "name": "Normal",
        "intell_weight": 45, "latency_weight": 25, "health_weight": 15, "ctx_weight": 15,
        "min_ctx": 0,
        "fallback_ctx": 0,
        "min_intell": 0.40,
    },
    "god-fast": {
        "name": "Fast",
        "intell_weight": 15, "latency_weight": 60, "health_weight": 15, "ctx_weight": 10,
        "min_ctx": 0,
        "fallback_ctx": 0,
        "min_intell": 0.30,
    },
    "god-code": {
        "name": "Code",
        "intell_weight": 30, "latency_weight": 20, "health_weight": 15, "ctx_weight": 35,
        "min_ctx": 128_000,
        "fallback_ctx": 64_000,
        "min_intell": 0.45,
    },
    "god-1m": {
        "name": "1M+ Ctx",
        "intell_weight": 35, "latency_weight": 15, "health_weight": 20, "ctx_weight": 30,
        "min_ctx": 1_000_000,
        "fallback_ctx": 256_000,  # If no 1M, fall back to 256k+
        "min_intell": 0.30,
    },
    "god-reason": {
        "name": "Reason",
        "intell_weight": 40, "latency_weight": 15, "health_weight": 20, "ctx_weight": 25,
        "min_ctx": 128_000,
        "fallback_ctx": 64_000,
        "min_intell": 0.45,
    },
    "auto": {
        "name": "Auto",
        "intell_weight": 45, "latency_weight": 25, "health_weight": 15, "ctx_weight": 15,
        "min_ctx": 0,
        "fallback_ctx": 0,
        "min_intell": 0.40,
    },
}

# Aliases: short names that map to canonical profile keys
GOD_MODE_ALIASES = {
    "auto-fastest": "god-fast",
    "auto-smart": "god-smart",
    "auto-code": "god-code",
    "auto-reason": "god-reason",
    "auto-balanced": "god-mode",
}
GOD_MODE_KEYS = set(GOD_PROFILES.keys()) | set(GOD_MODE_ALIASES.keys())

# Multi-lane aliases: same profile but force a different provider pool for redundancy
# Each lane steers the scoring to prefer a different provider tier or set
LANE_PROVIDER_PREFERENCES = {
    "lane-baseten":   {"prefer_tier": [3], "require_provider": "openai-compatible:baseten"},
    "lane-cloudflare": {"prefer_tier": [3], "require_provider": "cloudflare"},
    "lane-groq":      {"prefer_tier": [3], "require_provider": "groq"},
    "lane-mistral":   {"prefer_tier": [3], "require_provider": "openai-compatible:mistral"},
    "lane-nvidia":    {"prefer_tier": [2], "require_provider": "nvidia"},
    "lane-cerebras":  {"prefer_tier": [2], "require_provider": "cerebras"},
    "lane-openrouter": {"prefer_tier": [2], "require_provider": "openrouter"},
    "lane-kilocode":  {"prefer_tier": [3], "require_provider": "kilocode"},
}

LANE_ALIASES = {
    # Each "auto" alias creates a redundant routing lane pinned to one provider
    "auto-baseten":   "lane-baseten",
    "auto-cloudflare": "lane-cloudflare",
    "auto-groq":      "lane-groq",
    "auto-mistral":   "lane-mistral",
    "auto-nvidia":    "lane-nvidia",
    "auto-cerebras":  "lane-cerebras",
    "auto-openrouter": "lane-openrouter",
    "auto-kilocode":  "lane-kilocode",
    # Generic redundant lanes (no provider pin, just rotates differently)
    "auto-lane-1": "god-fast",
    "auto-lane-2": "god-mode",
    "auto-lane-3": "god-smart",
    "auto-lane-4": "god-code",
}

# Combine all auto aliases
GOD_MODE_ALIASES.update(LANE_ALIASES)
GOD_MODE_KEYS = set(GOD_PROFILES.keys()) | set(GOD_MODE_ALIASES.keys())


def _resolve_profile(mode: str) -> str:
    """Resolve an alias to its canonical god-mode profile key, or lane key."""
    if mode in GOD_PROFILES:
        return mode
    if mode in LANE_ALIASES:
        return LANE_ALIASES[mode]
    return GOD_MODE_ALIASES.get(mode, mode)


def _lane_preference(mode: str) -> dict:
    """Returns lane provider preference dict, or empty dict if not a lane."""
    return LANE_PROVIDER_PREFERENCES.get(_resolve_profile(mode), {})


def _prefix_model_id(model_id: str, provider_key: str) -> str:
    """Prefix a model ID with its provider key for reliable Node ModelRelay routing.
    
    The Node ModelRelay matches models by provider-qualified key first.
    Without the prefix, some models (e.g. zai-org/GLM-5.1) may fail with 503
    because the relay can't disambiguate across providers.
    """
    if not provider_key or not model_id:
        return model_id
    # Already prefixed — don't double-prefix
    if model_id.startswith(f"{provider_key}/"):
        return model_id
    return f"{provider_key}/{model_id}"

app = FastAPI(title="NEXUS God Mode Proxy v3")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Cache model state
_cache = {"data": None, "ts": 0, "ttl": 3}
_cache_fallbacks = {"data": None, "ts": 0, "ttl": 3}

# Recent provider usage tracking (for diversity)
_recent_provider_use = defaultdict(list)  # provider -> list of timestamps

def _provider_diversity_penalty(provider: str) -> float:
    """Penalty for recently used providers (0-15 points). More recent = higher penalty."""
    now = time.time()
    recent = [t for t in _recent_provider_use.get(provider, []) if now - t < 60]
    _recent_provider_use[provider] = recent
    if len(recent) >= 3:
        return 12.0
    elif len(recent) >= 2:
        return 6.0
    elif len(recent) >= 1:
        return 2.0
    return 0.0


def _record_provider_use(provider: str):
    _recent_provider_use[provider].append(time.time())


async def get_models():
    now = time.time()
    if _cache["data"] is not None and (now - _cache["ts"]) < _cache["ttl"]:
        return _cache["data"]
    # Try primary relay first
    models = await _fetch_models_from(MODELRELAY_API)
    if not models:
        # Fall back to Python relay
        models = await _fetch_models_from(f"{MODELRELAY_FALLBACK_URL}/api")
    if models:
        _cache["data"] = models
        _cache["ts"] = now
    return models if models else (_cache["data"] if _cache["data"] else [])


async def _fetch_models_from(api_base: str) -> list:
    """Fetch models from a relay API. Returns list of model dicts."""
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(f"{api_base}/models", timeout=5) as r:
                data = await r.json()
        return data.get("models", [])
    except Exception:
        return []


async def refresh_models_cache():
    """Force-refresh the model cache. Used for dynamic discovery."""
    _cache["ts"] = 0
    return await get_models()


def get_known_provider_pool() -> list[str]:
    """Returns the static pool of known model providers for fallback chain selection.
    Used as a last-resort source when live relays are down."""
    return [
        # Tier 3 (most reliable)
        "openai-compatible:baseten",
        "groq",
        "cloudflare",
        "kilocode",
        "openai-compatible:mistral",
        "openai-compatible:github",
        "nvidia",
        # Tier 2
        "openrouter",
        "cerebras",
        "codestral",
        "opencode",
        # Tier 1
        "googleai",
        "openai-compatible:deepinfra",
        "openai-compatible:sambanova",
        "openai-compatible:fireworks",
        "openai-compatible:siliconflow",
        "internai",
    ]


def estimate_tokens(messages: list) -> int:
    total = 0
    for m in messages:
        content = m.get("content", "")
        if isinstance(content, str):
            total += len(content) // 4
    return max(total, 50)


def parse_context_window(ctx_str: str) -> int:
    if not ctx_str:
        return 0
    ctx_str = str(ctx_str).lower().replace(" ", "")
    if ctx_str.endswith("m"):
        try:
            return int(float(ctx_str[:-1]) * 1_000_000)
        except ValueError:
            return 0
    if ctx_str.endswith("k"):
        try:
            return int(float(ctx_str[:-1]) * 1_000)
        except ValueError:
            return 0
    try:
        return int(ctx_str)
    except ValueError:
        return 0


def score_model(m: dict, profile: dict, estimated_tok: int) -> float:
    """Score a model based on profile. Returns higher = better."""
    intell = float(m.get("intell", 0.45) or 0.45)
    avg_lat = float(m.get("avg", 5000) or 5000)
    qos = float(m.get("qos", 0.5) or 0.5)
    uptime = float(m.get("uptime", 0.5) or 0.5)
    ctx_raw = m.get("ctx", "")
    ctx = parse_context_window(ctx_raw)
    provider = m.get("providerKey", "unknown")
    profile_name = profile.get("name", "Normal")

    # Profile-specific scoring
    if profile_name == "Smart":
        # Intelligence-first, then adequate context, then health
        intell_score = intell * 100
        ctx_score = 20 if ctx >= 256_000 else (10 if ctx >= 128_000 else 0)
        health_score = (qos + uptime) * 25
        latency_penalty = min(15, avg_lat / 500)  # Small penalty: 500ms=1pt, 5s=10pt
        tier_bonus = TIER_BONUS.get(PROVIDER_TIER.get(provider, 1), 0)
        diversity_penalty = _provider_diversity_penalty(provider)
        return round(intell_score + ctx_score + health_score - latency_penalty + tier_bonus - diversity_penalty, 2)

    elif profile_name == "Fast":
        # Latency-first, with minimum intelligence floor
        latency_score = max(0, 100 - (avg_lat / 30))  # 100ms=97, 1s=67, 3s=0
        intell_score = intell * 40  # 0.8 = 32pts bonus
        health_score = (qos + uptime) * 10
        tier_bonus = TIER_BONUS.get(PROVIDER_TIER.get(provider, 1), 0)
        diversity_penalty = _provider_diversity_penalty(provider)
        return round(latency_score + intell_score + health_score + tier_bonus - diversity_penalty, 2)

    elif profile_name == "1M+ Ctx":
        # Context is king, then intelligence
        ctx_score = 100 if ctx >= 1_000_000 else (50 if ctx >= 256_000 else 0)
        intell_score = intell * 60
        health_score = (qos + uptime) * 20
        latency_penalty = min(10, avg_lat / 1000)
        tier_bonus = TIER_BONUS.get(PROVIDER_TIER.get(provider, 1), 0)
        diversity_penalty = _provider_diversity_penalty(provider)
        return round(ctx_score + intell_score + health_score - latency_penalty + tier_bonus - diversity_penalty, 2)

    else:
        # Normal / Code / Reason / Auto — balanced weighted score
        intell_score = intell * 100
        latency_score = max(0, 100 - (avg_lat / 50))
        health_score = (qos * 50) + (uptime * 50)
        if ctx >= 1_000_000:
            ctx_score = 100
        elif ctx >= 256_000:
            ctx_score = 60
        elif ctx >= 128_000:
            ctx_score = 40
        elif ctx >= 64_000:
            ctx_score = 25
        else:
            ctx_score = 10

        # Demand bonus
        if estimated_tok > 0 and ctx > 0:
            utilization = estimated_tok / ctx
            if utilization > 0.5:
                ctx_score += 10
            elif utilization > 0.25:
                ctx_score += 5

        tier_bonus = TIER_BONUS.get(PROVIDER_TIER.get(provider, 1), 0)
        diversity_penalty = _provider_diversity_penalty(provider)

        weights = profile
        total = (
            intell_score * weights.get("intell_weight", 50) / 100 +
            latency_score * weights.get("latency_weight", 25) / 100 +
            health_score * weights.get("health_weight", 15) / 100 +
            ctx_score * weights.get("ctx_weight", 10) / 100 +
            tier_bonus -
            diversity_penalty
        )
        return round(total, 2)


def select_candidates(models: list, profile: dict, messages: list, top_n: int = 5, mode: str = None) -> List[Tuple[float, dict]]:
    """
    Select top N candidate models with fallback chains.
    Returns list of (score, model) tuples sorted by score descending.
    Optional `mode` applies lane preferences for provider-pinned routes.
    """
    up = [m for m in models if m.get("status") == "up"]
    if not up:
        return []

    estimated_tok = estimate_tokens(messages)
    min_ctx = profile.get("min_ctx", 0)
    fallback_ctx = profile.get("fallback_ctx", 0)
    min_intell = profile.get("min_intell", 0.30)

    # Apply lane preference: filter to required provider first
    lane_pref = _lane_preference(mode) if mode else {}
    require_provider = lane_pref.get("require_provider")

    # Filter by minimum intelligence
    candidates = [m for m in up if float(m.get("intell", 0) or 0) >= min_intell]
    if not candidates:
        candidates = up  # Fallback: ignore intelligence floor

    # Context filtering with fallback
    if min_ctx > 0:
        ctx_filtered = [m for m in candidates if parse_context_window(m.get("ctx", "")) >= min_ctx]
        if ctx_filtered:
            candidates = ctx_filtered
        elif fallback_ctx > 0:
            ctx_fallback = [m for m in candidates if parse_context_window(m.get("ctx", "")) >= fallback_ctx]
            if ctx_fallback:
                candidates = ctx_fallback

    # Specialty filtering
    if profile.get("name") == "Code":
        coding_keywords = {"coder", "code", "devstral", "qwen3 80b", "qwen 2.5 coder", "deepseek", "codeqwen", "starcoder", "minimax-m3", "minimax m3", "minimax-m2", "minimax m2"}
        coding = [m for m in candidates if any(k in (m.get("label", "") + " " + m.get("modelId", "")).lower() for k in coding_keywords)]
        if coding:
            candidates = coding

    if profile.get("name") == "Reason":
        reason_keywords = {"reasoning", "thinking", "r1", "qwq", "o4", "o3", "deepseek-r1", "glm-5", "glm 5", "kimi-k2", "kimi k2", "think", "nemotron"}
        reason = [m for m in candidates if any(k in (m.get("label", "") + " " + m.get("modelId", "")).lower() for k in reason_keywords)]
        if reason:
            candidates = reason

    # Lane filter: prefer pinned provider, but fall back to others if unavailable
    if require_provider:
        pinned = [m for m in candidates if m.get("providerKey") == require_provider]
        if pinned:
            candidates = pinned

    # Score all candidates
    scored = []
    for m in candidates:
        score = score_model(m, profile, estimated_tok)
        # Lane bonus: extra weight for pinned provider when lane is active
        if require_provider and m.get("providerKey") == require_provider:
            score += 15.0
        scored.append((score, m))

    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:top_n]


def select_model(models: list, mode: str, messages: list) -> Tuple[Optional[str], Optional[dict], List[dict]]:
    """
    Select best model with fallback chain.
    Returns: (model_id, metadata, fallback_chain)
    """
    if mode not in GOD_MODE_KEYS:
        return mode, None, []

    # Resolve aliases (auto-fastest -> god-fast, etc.)
    canonical_mode = _resolve_profile(mode)
    profile = GOD_PROFILES.get(canonical_mode, GOD_PROFILES["god-mode"])
    candidates = select_candidates(models, profile, messages, top_n=5, mode=mode)

    if not candidates:
        return None, {
            "error": "No models pass filters",
            "mode": mode,
            "profile": profile["name"],
            "total_up": len([m for m in models if m.get("status") == "up"]),
        }, []

    best = candidates[0][1]
    best_score = candidates[0][0]

    # Build fallback chain (next 2 candidates from different providers if possible)
    fallback_chain = []
    used_providers = {best.get("providerKey")}
    for score, m in candidates[1:]:
        pk = m.get("providerKey")
        if pk not in used_providers:
            fallback_chain.append({
                "model_id": m.get("modelId"),
                "model_name": m.get("label"),
                "provider": pk,
                "intelligence": float(m.get("intell", 0) or 0),
                "latency_ms": int(m.get("avg", 0) or 0),
                "context": m.get("ctx"),
                "score": score,
            })
            used_providers.add(pk)
        if len(fallback_chain) >= 2:
            break

    # Also add same-provider fallbacks if we don't have enough diversity
    for score, m in candidates[1:]:
        pk = m.get("providerKey")
        if len(fallback_chain) >= 2:
            break
        if not any(f["model_id"] == m.get("modelId") for f in fallback_chain):
            fallback_chain.append({
                "model_id": m.get("modelId"),
                "model_name": m.get("label"),
                "provider": pk,
                "intelligence": float(m.get("intell", 0) or 0),
                "latency_ms": int(m.get("avg", 0) or 0),
                "context": m.get("ctx"),
                "score": score,
            })

    ctx_raw = best.get("ctx", "")
    ctx_num = parse_context_window(ctx_raw)

    metadata = {
        "profile": profile["name"],
        "mode": mode,
        "estimated_tokens": estimate_tokens(messages),
        "candidates_up": len([m for m in models if m.get("status") == "up"]),
        "candidates_evaluated": len(candidates),
        "top_score": best_score,
        "model_id": best.get("modelId"),
        "model_name": best.get("label"),
        "provider": best.get("providerKey"),
        "provider_tier": PROVIDER_TIER.get(best.get("providerKey"), 1),
        "intelligence": float(best.get("intell", 0) or 0),
        "latency_ms": int(best.get("avg", 0) or 0),
        "context": ctx_raw,
        "context_tokens": ctx_num,
        "qos": float(best.get("qos", 0) or 0),
        "uptime": float(best.get("uptime", 0) or 0),
        "why_selected": _explain_selection(best, profile, estimate_tokens(messages)),
        "fallback_chain": fallback_chain,
        "attempt": 1,
    }

    return best.get("modelId"), metadata, fallback_chain


def _explain_selection(m: dict, profile: dict, est_tok: int) -> str:
    parts = []
    if profile["name"] == "Smart":
        parts.append(f"Highest intelligence ({(m.get('intell') or 0)*100:.0f}%)")
    elif profile["name"] == "Fast":
        parts.append(f"Fastest latency ({int(m.get('avg') or 0)}ms)")
    elif profile["name"] == "1M+ Ctx":
        parts.append(f"1M+ context window ({m.get('ctx')})")
    elif profile["name"] == "Code":
        parts.append("Coding-optimized model")
    elif profile["name"] == "Reason":
        parts.append("Reasoning/thinking model")
    else:
        parts.append("Balanced score (intelligence + speed + health + context)")

    ctx = parse_context_window(m.get("ctx", ""))
    if ctx >= 1_000_000:
        parts.append("1M+ context capacity")
    elif ctx >= 256_000:
        parts.append("256k+ context capacity")
    elif ctx >= 128_000:
        parts.append("128k context capacity")

    provider = m.get("providerKey", "")
    tier = PROVIDER_TIER.get(provider, 1)
    if tier >= 3:
        parts.append("Reliable unlimited-tier provider")
    elif tier == 2:
        parts.append("Generous free-tier provider")
    elif tier == 1:
        parts.append("Limited trial/quota provider")

    return "; ".join(parts)


async def forward_chat(body: dict, headers: dict, metadata: dict, fallback_chain: list, attempt: int = 1):
    """
    Forward chat request to modelrelay. On failure, try fallback chain.
    Returns (response_data, response_headers, success, result_type)
    
    For non-streaming: result_type="json", response_data=dict
    For streaming: result_type="stream", response_data=bytes (raw SSE body)
    """
    timeout = aiohttp.ClientTimeout(total=300)
    selected_model = body.get("model")
    
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(MODELRELAY_CHAT, json=body, headers=headers) as resp:
                god_headers = {
                    "x-god-mode": "true",
                    "x-god-profile": metadata.get("profile", "") if metadata else "",
                    "x-selected-model": str(selected_model or ""),
                    "x-attempt": str(attempt),
                    "x-provider": metadata.get("provider", "") if metadata else "",
                }

                if resp.status >= 400:
                    error_body = await resp.text()
                    return {"error": error_body, "status": resp.status}, god_headers, False, f"HTTP {resp.status}: {error_body[:200]}"

                if body.get("stream"):
                    # Read the full streamed body within the context manager
                    raw_body = await resp.read()
                    # Merge upstream headers we care about
                    for k, v in resp.headers.items():
                        kl = k.lower()
                        if kl.startswith("content-type") or kl.startswith("x-"):
                            god_headers[k] = v
                    return raw_body, god_headers, True, "stream"
                
                data = await resp.json()
                if metadata:
                    data["_god_mode"] = {**metadata, "attempt": attempt}
                god_headers.update({
                    "x-model-intell": str(metadata.get("intelligence", "")) if metadata else "",
                    "x-model-latency": str(metadata.get("latency_ms", "")) if metadata else "",
                    "x-model-context": str(metadata.get("context", "")) if metadata else "",
                })
                return data, god_headers, True, "json"
    except Exception as e:
        return None, {}, False, str(e)


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "Invalid JSON")

    model = body.get("model", "god-mode")
    messages = body.get("messages", [])

    selected = None
    meta = None
    fallback_chain = []

    if model in GOD_MODE_KEYS:
        canonical = _resolve_profile(model)
        models = await get_models()
        selected, meta, fallback_chain = select_model(models, model, messages)
        if selected is None:
            return JSONResponse({
                "error": meta.get("error", "No model available"),
                "_god_mode": {**meta, "mode": model, "profile": GOD_PROFILES.get(canonical, {}).get("name", "Unknown")}
            }, status_code=503)
        # Prefix model ID with provider key for reliable Node ModelRelay routing
        provider_key = meta.get("provider", "") if meta else ""
        body["model"] = _prefix_model_id(selected, provider_key)
        _record_provider_use(provider_key or "unknown")
    else:
        meta = {"mode": "passthrough", "model": model, "profile": "Direct"}
        selected = model

    # Forward to modelrelay
    headers = {}
    if "authorization" in {k.lower(): k for k in request.headers}:
        headers["Authorization"] = request.headers.get("authorization", "")

    # Try primary model
    result, resp_headers, success, result_type = await forward_chat(body, headers, meta, fallback_chain, attempt=1)

    # Fallback chain on failure
    if not success and fallback_chain:
        for i, fallback in enumerate(fallback_chain):
            attempt = i + 2
            # Prefix fallback model ID with provider key for reliable routing
            fb_provider = fallback.get("provider", "")
            fb_model = fallback["model_id"]
            body["model"] = _prefix_model_id(fb_model, fb_provider)
            fallback_meta = {
                **fallback,
                "profile": meta.get("profile", "Fallback") if meta else "Fallback",
                "mode": model,
                "attempt": attempt,
                "is_fallback": True,
                "original_model": selected,
                "original_error": result_type if isinstance(result_type, str) else "primary failed",
            }
            result, resp_headers, success, result_type = await forward_chat(body, headers, fallback_meta, [], attempt=attempt)
            if success:
                meta = fallback_meta
                selected = fallback["model_id"]
                break

    if not success:
        error_msg = result_type if isinstance(result_type, str) else "Unknown error"
        return JSONResponse({
            "error": f"All models failed. Last error: {error_msg}",
            "_god_mode": {
                "mode": model,
                "profile": meta.get("profile", "") if meta else "",
                "primary_model": selected,
                "fallbacks_tried": len(fallback_chain),
                "attempts": 1 + len(fallback_chain),
            }
        }, status_code=502)

    if result_type == "stream":
        # result is raw bytes (pre-read SSE body from forward_chat)
        from starlette.responses import Response
        content_type = resp_headers.get("content-type", resp_headers.get("Content-Type", "text/event-stream"))
        return Response(
            content=result,
            status_code=200,
            headers=resp_headers,
            media_type=content_type,
        )

    return JSONResponse(result, headers=resp_headers)


@app.get("/v1/models")
async def list_models():
    raw = await get_models()
    model_list = []
    for m in raw:
        model_list.append({
            "id": m.get("modelId"),
            "object": "model",
            "display_name": m.get("label"),
            "owned_by": m.get("providerKey", "unknown"),
            "status": m.get("status"),
            "intelligence": m.get("intell"),
            "latency_ms": m.get("avg"),
            "context": m.get("ctx"),
        })

    for key, profile in GOD_PROFILES.items():
        model_list.append({
            "id": key,
            "object": "model",
            "display_name": f"God Mode — {profile['name']}",
            "description": _profile_desc(key),
            "owned_by": "nexus-god-mode",
            "status": "up",
        })

    for alias, target in LANE_ALIASES.items():
        pinned = LANE_PROVIDER_PREFERENCES.get(target, {}).get("require_provider")
        if pinned:
            display_name = f"Auto Lane → {pinned}"
            desc = f"Provider-pinned auto-routing lane to {pinned} (via {target})"
        else:
            display_name = f"Auto Lane → {GOD_PROFILES.get(target, {}).get('name', target)}"
            desc = f"Redundant auto-routing lane via {target}"
        model_list.append({
            "id": alias,
            "object": "model",
            "display_name": display_name,
            "description": desc,
            "owned_by": "nexus-god-mode",
            "status": "up",
            "lane_target": target,
            "pinned_provider": pinned,
        })

    up_count = sum(1 for m in raw if m.get("status") == "up")
    return JSONResponse({
        "object": "list",
        "data": model_list,
        "_stats": {
            "total": len(raw),
            "online": up_count,
            "providers": len(set(m.get("providerKey") for m in raw)),
            "god_mode_available": up_count > 0,
            "lanes": len(LANE_ALIASES),
            "auto_aliases": len(GOD_MODE_ALIASES),
        }
    })


def _profile_desc(key: str) -> str:
    return {
        "god-smart": "Highest intelligence, 256k+ context preferred. Sacrifices speed for quality. Best for complex analysis, reasoning, creative writing, long documents.",
        "god-mode": "Balanced: intelligence + speed + health + context. Default for most tasks. Good all-rounder with adequate context.",
        "god-fast": "Lowest latency first, good enough intelligence. Best for quick queries, real-time chat, rapid prototyping.",
        "god-code": "Coding-optimized models, 128k+ context. Prefers code completion, debugging, software engineering tasks.",
        "god-1m": "1M+ context window REQUIRED. For very long documents, book analysis, large codebase review, multi-turn conversations.",
        "god-reason": "Reasoning/thinking models with chain-of-thought. Math, logic, step-by-step problem solving, complex reasoning.",
        "auto": "Same as Normal (balanced). Auto-selected when no profile is specified.",
    }.get(key, "Auto-routing profile")


@app.get("/god/profiles")
async def profiles_preview():
    """Show what each profile would pick RIGHT NOW with full specs and fallback chain."""
    models = await get_models()
    if not models:
        return JSONResponse({"error": "No models available from modelrelay"}, status_code=503)

    preview = {}
    for key, profile in GOD_PROFILES.items():
        selected, meta, fallback = select_model(models, key, [])
        if selected:
            preview[key] = {
                "profile_name": profile["name"],
                "model_id": meta.get("model_id"),
                "model_name": meta.get("model_name"),
                "provider": meta.get("provider"),
                "provider_tier": meta.get("provider_tier"),
                "intelligence": meta.get("intelligence"),
                "latency_ms": meta.get("latency_ms"),
                "context": meta.get("context"),
                "context_tokens": meta.get("context_tokens"),
                "why": meta.get("why_selected"),
                "candidates": meta.get("candidates_evaluated"),
                "top_score": meta.get("top_score"),
                "fallback_chain": fallback,
            }
        else:
            preview[key] = {"error": meta.get("error", "No model available")}

    return JSONResponse({
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "profiles": preview,
        "usage": "Set model to one of the profile keys (e.g., 'god-smart') in your opencode config. Fallback chain auto-activates on failure.",
    })


@app.get("/god/status")
async def god_status():
    """Full system status with top models per profile."""
    models = await get_models()
    up = [m for m in models if m.get("status") == "up"]

    top_intell = sorted(up, key=lambda m: float(m.get("intell", 0) or 0), reverse=True)[:15]
    top_fast = sorted(up, key=lambda m: float(m.get("avg", 99999) or 99999))[:15]
    large_ctx = [m for m in up if parse_context_window(m.get("ctx", "")) >= 1_000_000]
    high_ctx_256k = [m for m in up if parse_context_window(m.get("ctx", "")) >= 256_000]

    # Profile previews
    profile_best = {}
    for key, profile in GOD_PROFILES.items():
        selected, meta, fallback = select_model(models, key, [])
        if selected:
            profile_best[key] = {
                "profile_name": profile["name"],
                "model_id": meta.get("model_id"),
                "model_name": meta.get("model_name"),
                "provider": meta.get("provider"),
                "provider_tier": meta.get("provider_tier"),
                "intelligence": meta.get("intelligence"),
                "latency_ms": meta.get("latency_ms"),
                "context": meta.get("context"),
                "why": meta.get("why_selected"),
                "fallback_chain": [f"{f['model_name']} ({f['provider']})" for f in fallback],
            }

    return JSONResponse({
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "summary": {
            "total_models": len(models),
            "models_up": len(up),
            "providers_active": len(set(m.get("providerKey") for m in up)),
            "large_context_1m": len(large_ctx),
            "high_context_256k": len(high_ctx_256k),
            "profiles_ready": len(profile_best),
        },
        "profile_selection": profile_best,
        "top_intelligence": [
            {"label": m.get("label"), "modelId": m.get("modelId"), "intell": m.get("intell"),
             "provider": m.get("providerKey"), "latency": m.get("avg"), "ctx": m.get("ctx")}
            for m in top_intell
        ],
        "top_fast": [
            {"label": m.get("label"), "modelId": m.get("modelId"), "intell": m.get("intell"),
             "provider": m.get("providerKey"), "latency": m.get("avg"), "ctx": m.get("ctx")}
            for m in top_fast
        ],
        "large_context_1m": [
            {"label": m.get("label"), "modelId": m.get("modelId"), "intell": m.get("intell"),
             "provider": m.get("providerKey"), "ctx": m.get("ctx")}
            for m in large_ctx
        ],
    })


@app.get("/health")
async def health():
    models = await get_models()
    up = sum(1 for m in models if m.get("status") == "up")
    return {"status": "ok", "models_up": up, "total": len(models), "proxy_version": "v3"}


@app.post("/god/refresh")
async def refresh_discovery():
    """Force refresh of model cache (dynamic discovery).

    Use this to pick up new models added by providers since startup,
    or to drop stale models that have gone offline.
    """
    old_models = _cache.get("data") or []
    old_ids = {m.get("modelId") for m in old_models}
    old_providers = {m.get("providerKey") for m in old_models}

    models = await refresh_models_cache()
    new_ids = {m.get("modelId") for m in models}
    new_providers = {m.get("providerKey") for m in models}

    added_models = new_ids - old_ids
    removed_models = old_ids - new_ids
    added_providers = new_providers - old_providers
    removed_providers = old_providers - new_providers

    up = sum(1 for m in models if m.get("status") == "up")
    return JSONResponse({
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_models": len(models),
        "models_up": up,
        "added_models": sorted(added_models)[:50],
        "removed_models": sorted(removed_models)[:50],
        "added_providers": sorted(added_providers),
        "removed_providers": sorted(removed_providers),
        "cache_age_seconds": time.time() - _cache.get("ts", 0),
        "proxy_version": "v3.1",
    })


@app.get("/god/lanes")
async def list_lanes():
    """List all available routing lanes (auto-* aliases) with their preferences."""
    lanes = []
    for alias, target in sorted(LANE_ALIASES.items()):
        is_lane_pinned = target in LANE_PROVIDER_PREFERENCES
        lanes.append({
            "alias": alias,
            "target": target,
            "profile": GOD_PROFILES.get(target, {}).get("name", "Unknown"),
            "pinned_provider": LANE_PROVIDER_PREFERENCES.get(target, {}).get("require_provider") if is_lane_pinned else None,
            "description": (
                f"Provider-pinned lane to {LANE_PROVIDER_PREFERENCES[target]['require_provider']}"
                if is_lane_pinned
                else f"Generic lane routing to {target}"
            ),
        })
    return JSONResponse({
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_lanes": len(lanes),
        "lanes": lanes,
        "auto_aliases": sorted(set(GOD_MODE_ALIASES.keys())),
    })


if __name__ == "__main__":
    print("=" * 60)
    print(" NEXUS God Mode Proxy v3.1 — Multi-lane routing + dynamic discovery")
    print("=" * 60)
    print(f"  ModelRelay:   {MODELRELAY_URL}")
    print(f"  Proxy port:   7357")
    print(f"  Chat URL:     http://localhost:7357/v1/chat/completions")
    print(f"  Profiles:     http://localhost:7357/god/profiles")
    print(f"  Lanes:        http://localhost:7357/god/lanes")
    print(f"  Refresh:      POST http://localhost:7357/god/refresh")
    print(f"  Status:       http://localhost:7357/god/status")
    print()
    for key, profile in GOD_PROFILES.items():
        print(f"  {key:15s} — {profile['name']:<10s} (intell:{profile['intell_weight']:>2d}% latency:{profile['latency_weight']:>2d}% ctx:{profile['ctx_weight']:>2d}%)")
    print()
    print(f"  Routing lanes ({len(LANE_ALIASES)}):")
    for alias, target in sorted(LANE_ALIASES.items()):
        pinned = LANE_PROVIDER_PREFERENCES.get(target, {}).get("require_provider", "(no pin)")
        print(f"    {alias:20s} -> {target:12s} [pinned: {pinned}]")
    print("=" * 60)
    uvicorn.run(app, host="127.0.0.1", port=7357, log_level="warning")
