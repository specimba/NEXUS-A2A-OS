# src\nexus_os\gmr\domain_mapping.py
# GMR Domain → Model Mapping (wired from real model data in ROTATION_TABLE.md + models_registry.json)

DOMAIN_MAPPING = {
    "code": {
        "primary": [
            {"model": "osman-coder", "provider": "ollama", "tier": 40, "latency_ms": 50, "cost_per_1m": 0, "status": "local"},
            {"model": "Devstral 2 123B", "provider": "nvidia", "tier": 86, "latency_ms": 542, "cost_per_1m": 4.0, "status": "up"},
            {"model": "Qwen3 Coder 480B", "provider": "nvidia", "tier": 82, "latency_ms": 9897, "cost_per_1m": 8.0, "status": "up"},
            {"model": "GPT OSS 120B", "provider": "nvidia", "tier": 58, "latency_ms": 398, "cost_per_1m": 3.0, "status": "up"},
            {"model": "Codestral", "provider": "codestral", "tier": 53, "latency_ms": 464, "cost_per_1m": 2.0, "status": "up"},
        ],
        "fallback_chain": ["osman-coder", "qwen2.5-coder:7b", "Codestral", "GPT OSS 20B"]
    },
    "reasoning": {
        "primary": [
            {"model": "Trinity Large Preview", "provider": "opencode", "tier": 97, "latency_ms": 1707, "cost_per_1m": 5.0, "status": "up"},
            {"model": "Kimi K2 Thinking", "provider": "nvidia", "tier": 84, "latency_ms": 709, "cost_per_1m": 4.0, "status": "up"},
            {"model": "Qwen3 80B Thinking", "provider": "nvidia", "tier": 72, "latency_ms": 522, "cost_per_1m": 3.0, "status": "up"},
            {"model": "osman-reasoning", "provider": "ollama", "tier": 40, "latency_ms": 80, "cost_per_1m": 0, "status": "local"},
        ],
        "fallback_chain": ["osman-reasoning", "qwen3:8b", "Qwen3 80B Thinking"]
    },
    "research": {
        "primary": [
            {"model": "GLM 5", "provider": "nvidia", "tier": 97, "latency_ms": 4539, "cost_per_1m": 5.0, "status": "up"},
            {"model": "Kimi K2.5", "provider": "nvidia", "tier": 95, "latency_ms": 2288, "cost_per_1m": 4.0, "status": "up"},
            {"model": "Nemotron 3 Super", "provider": "opencode", "tier": 60, "latency_ms": 1275, "cost_per_1m": 2.0, "status": "up"},
        ],
        "fallback_chain": ["GLM 5", "Nemotron 3 Super", "osman-reasoning"]
    },
    "fast": {
        "primary": [
            {"model": "osman-fast", "provider": "ollama", "tier": 40, "latency_ms": 20, "cost_per_1m": 0, "status": "local"},
            {"model": "Bonsai 4B IQ1_S", "provider": "ollama", "tier": 40, "latency_ms": 15, "cost_per_1m": 0, "status": "local"},
            {"model": "locooperator", "provider": "ollama", "tier": 40, "latency_ms": 30, "cost_per_1m": 0, "status": "local"},
        ],
        "fallback_chain": ["Bonsai 4B", "osman-fast", "locooperator"]
    },
    "security": {
        "primary": [
            {"model": "Trinity Large Preview", "provider": "opencode", "tier": 97, "latency_ms": 1707, "cost_per_1m": 5.0, "status": "up"},
            {"model": "MiniMax M2.5", "provider": "opencode", "tier": 99, "latency_ms": 1224, "cost_per_1m": 6.0, "status": "up"},
        ],
        "fallback_chain": ["Trinity Large Preview", "GLM 5", "osman-reasoning"]
    },
    "general": {
        "primary": [
            {"model": "osman-agent", "provider": "ollama", "tier": 40, "latency_ms": 50, "cost_per_1m": 0, "status": "local"},
            {"model": "MiniMax M2.5", "provider": "opencode", "tier": 99, "latency_ms": 1224, "cost_per_1m": 6.0, "status": "up"},
        ],
        "fallback_chain": ["osman-agent", "qwen3.5:4b"]
    }
}

print("[GMR] Domain mapping loaded with real model data from registry")