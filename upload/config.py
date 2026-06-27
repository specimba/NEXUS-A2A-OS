"""ModelRelay Configuration — Provider endpoints, credentials, and defaults."""

import os

# ─── Provider Endpoints ────────────────────────────────────────────────────

PROVIDERS = {
    "minimax": {
        "name": "MiniMax M2.7",
        "provider": "minimax",
        "base_url": "https://api.minimax.io",
        "chat_path": "/v1/text/chatcompletion_v2",
        "models_path": "/v1/models",
        "auth_type": "bearer",  # Authorization header
        "quota_type": "messages",  # messages|tokens|time
        "quota_remaining": 5,  # Approximate remaining
        "quota_reset": None,  # ISO timestamp or None
        "cost_per_1m": 0.0,  # Free tier
        "latency_ms": 300,  # Estimated
        "status": "up",  # up|degraded|down|cooldown
        "tier": 99,  # Quality tier (0-100)
        "priority": 1,  # Lower = higher priority
        "is_free": True,
        "is_local": False,
    },
    "openrouter": {
        "name": "OpenRouter",
        "provider": "openrouter",
        "base_url": "https://openrouter.ai",
        "chat_path": "/api/v1/chat/completions",
        "models_path": "/api/v1/models",
        "auth_type": "bearer",
        "quota_type": "credits",
        "quota_remaining": "varies",  # Credits-based
        "quota_reset": None,
        "cost_per_1m": 0.0,  # Many free models
        "latency_ms": 200,
        "status": "up",
        "tier": 80,
        "priority": 2,
        "is_free": True,
        "is_local": False,
        "models": ["openrouter/auto", "nvidia/llama-3.3-nemotron-super-128k", "deepseek/deepseek-chat-v3-0324"],
    },
    "ollama": {
        "name": "Ollama (Local)",
        "provider": "ollama",
        "base_url": "http://localhost:11434",
        "chat_path": "/api/chat",
        "models_path": "/api/tags",
        "auth_type": "none",
        "quota_type": "unlimited",
        "quota_remaining": "unlimited",
        "quota_reset": None,
        "cost_per_1m": 0.0,
        "latency_ms": 50,  # Very fast locally
        "status": "up",
        "tier": 40,  # Local models are lower tier
        "priority": 3,
        "is_free": True,
        "is_local": True,
        "models": ["osman-coder", "osman-fast", "osman-reasoning", "osman-agent"],
    },
    "groq": {
        "name": "Groq",
        "provider": "groq",
        "base_url": "https://api.groq.com",
        "chat_path": "/openai/v1/chat/completions",
        "models_path": "/openai/v1/models",
        "auth_type": "bearer",
        "quota_type": "requests",
        "quota_remaining": "free_tier",
        "quota_reset": None,
        "cost_per_1m": 0.5,  # Cheap
        "latency_ms": 150,
        "status": "up",
        "tier": 70,
        "priority": 4,
        "is_free": False,
        "is_local": False,
    },
    "cerebras": {
        "name": "Cerebras",
        "provider": "cerebras",
        "base_url": "https://api.cerebras.ai",
        "chat_path": "/v1/chat/completions",
        "models_path": "/v1/models",
        "auth_type": "bearer",
        "quota_type": "free_tier",
        "quota_remaining": "free_tier",
        "quota_reset": None,
        "cost_per_1m": 0.6,
        "latency_ms": 120,
        "status": "up",
        "tier": 65,
        "priority": 5,
        "is_free": False,
        "is_local": False,
    },
    "together": {
        "name": "Together AI",
        "provider": "together",
        "base_url": "https://api.together.ai",
        "chat_path": "/v1/chat/completions",
        "models_path": "/v1/models",
        "auth_type": "bearer",
        "quota_type": "free_tier",
        "quota_remaining": "free_tier",
        "quota_reset": None,
        "cost_per_1m": 1.0,
        "latency_ms": 250,
        "status": "up",
        "tier": 75,
        "priority": 6,
        "is_free": False,
        "is_local": False,
    },
    "deepseek": {
        "name": "DeepSeek",
        "provider": "deepseek",
        "base_url": "https://api.deepseek.com",
        "chat_path": "/v1/chat/completions",
        "models_path": "/v1/models",
        "auth_type": "bearer",
        "quota_type": "free_tier",
        "quota_remaining": "free_tier",
        "quota_reset": None,
        "cost_per_1m": 0.5,
        "latency_ms": 200,
        "status": "up",
        "tier": 72,
        "priority": 7,
        "is_free": False,
        "is_local": False,
    },
    "internai": {
        "name": "InternAI",
        "provider": "internai",
        "base_url": "https://chat.intern-ai.org.cn/api/v1",
        "chat_path": "/chat/completions",
        "models_path": "/models",
        "auth_type": "bearer",
        "quota_type": "requests",
        "quota_remaining": "unlimited",
        "quota_reset": None,
        "cost_per_1m": 0.0,
        "latency_ms": 250,
        "status": "up",
        "tier": 95,
        "priority": 8,
        "is_free": True,
        "is_local": False,
    },
    "openmodel": {
        "name": "OpenModel DeepSeek V4 Flash",
        "provider": "openmodel",
        "base_url": "https://api.openmodel.ai",
        "chat_path": "/v1/chat/completions",
        "models_path": "/v1/models",
        "auth_type": "bearer",
        "quota_type": "free_tier",
        "quota_remaining": "free_event",
        "quota_reset": None,
        "cost_per_1m": 0.0,
        "latency_ms": 450,
        "status": "up",
        "tier": 86,
        "priority": 10,
        "is_free": True,
        "is_local": False,
        "models": ["deepseek-v4-flash-free"],
    },
    "sakana": {
        "name": "Sakana Fugu",
        "provider": "sakana",
        "base_url": "https://api.sakana.ai/v1",
        "chat_path": "/chat/completions",
        "models_path": "/models",
        "auth_type": "bearer",
        "quota_type": "credits",
        "quota_remaining": "account_quota",
        "quota_reset": None,
        "cost_per_1m": 0.0,
        "latency_ms": 1200,
        "status": "up",
        "tier": 90,
        "priority": 11,
        "is_free": True,
        "is_local": False,
        "models": ["fugu", "fugu-ultra"],
    },
    "longcat": {
        "name": "LongCat 2.0 Preview",
        "provider": "longcat",
        "base_url": "https://api.longcat.chat/openai/v1",
        "chat_path": "/chat/completions",
        "models_path": "/models",
        "auth_type": "bearer",
        "quota_type": "tokens",
        "quota_remaining": "beta_quota",
        "quota_reset": None,
        "cost_per_1m": 0.0,
        "latency_ms": 1000,
        "status": "up",
        "tier": 94,
        "priority": 9,
        "is_free": True,
        "is_local": False,
        "models": ["LongCat-2.0-Preview"],
    },
}

# ─── Routing Defaults ──────────────────────────────────────────────────────

DEFAULT_STRATEGY = "quota_aware"

ROUTING_STRATEGIES = {
    "quota_aware": {
        "description": "Prioritize free tier, switch when quota exhausted",
        "pool_filter": "all",  # all|free|premium|local
        "cost_weight": 0.30,
        "latency_weight": 0.20,
        "quality_weight": 0.30,
        "availability_weight": 0.20,
    },
    "cost_optimized": {
        "description": "Always prefer cheapest option",
        "pool_filter": "free",  # Prefer free
        "cost_weight": 0.50,
        "latency_weight": 0.15,
        "quality_weight": 0.20,
        "availability_weight": 0.15,
    },
    "quality_first": {
        "description": "Use best available model within budget",
        "pool_filter": "all",
        "cost_weight": 0.15,
        "latency_weight": 0.20,
        "quality_weight": 0.45,
        "availability_weight": 0.20,
    },
    "latency": {
        "description": "Minimize response time",
        "pool_filter": "all",
        "cost_weight": 0.10,
        "latency_weight": 0.50,
        "quality_weight": 0.25,
        "availability_weight": 0.15,
    },
}

# ─── Intent → Domain Mapping ────────────────────────────────────────────────

INTENT_TO_DOMAIN = {
    "code": ["code"],
    "reasoning": ["reasoning"],
    "research": ["research"],
    "fast": ["fast", "speed"],
    "general": ["general"],
    "security": ["security"],
}

# ─── Model Fallback Chains ──────────────────────────────────────────────────

FALLBACK_CHAINS = {
    "code": ["osman-coder", "qwen2.5-coder:7b", "Codestral", "deepseek-v4-flash-free", "deepseek-chat"],
    "reasoning": ["osman-reasoning", "qwen3:8b", "Qwen3-80B-Thinking", "intern-s2-preview", "deepseek-v4-flash-free", "LongCat-2.0-Preview", "fugu"],
    "research": ["GLM-5", "Kimi-K2.5", "Nemotron-3-Super", "LongCat-2.0-Preview", "fugu-ultra"],
    "fast": ["osman-fast", "Bonsai-4B", "locooperator"],
    "security": ["Trinity-Large-Preview", "MiniMax-M2.5", "GLM-5"],
    "general": ["osman-agent", "qwen3.5:4b", "llama3.3-nemotron-super"],
}

# ─── Health Check Intervals (seconds) ─────────────────────────────────────

HEALTH_CHECK_INTERVAL = 60  # 1 minute
LATENCY_SAMPLE_SIZE = 5  # Rolling average samples
CIRCUIT_BREAKER_THRESHOLD = 3  # Failures before opening
CIRCUIT_BREAKER_COOLDOWN = 60  # Seconds before retry

# ─── Logging ────────────────────────────────────────────────────────────────

import logging

LOGGER = logging.getLogger("nexus.modelrelay")
LOGGER.setLevel(logging.INFO)

if not LOGGER.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s"))
    LOGGER.addHandler(handler)

