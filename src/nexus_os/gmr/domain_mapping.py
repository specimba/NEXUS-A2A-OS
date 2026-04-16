"""GMR Domain Configuration & Budgets"""
DOMAIN_MAPPING = {
    "code": {
        "description": "Code generation, debugging, implementation",
        "primary": [
            {"model": "osman-coder", "provider": "ollama", "tier": 40, "latency_ms": 50, "cost_per_1m": 0, "status": "local"},
            {"model": "Devstral 2 123B", "provider": "nvidia", "tier": 86, "latency_ms": 542, "cost_per_1m": 4.0, "status": "up"}
        ],
        "fallback_chain": ["osman-coder", "qwen2.5-coder:7b", "Codestral", "GPT OSS 20B"],
        "requirement": {"max_latency_ms": 5000, "prefer_local": True, "min_tier": 40}
    },
    "reasoning": {
        "description": "Deep analysis, planning, architecture decisions",
        "primary": [
            {"model": "Trinity Large Preview", "provider": "opencode", "tier": 97, "latency_ms": 1707, "cost_per_1m": 5.0, "status": "up"},
            {"model": "osman-reasoning", "provider": "ollama", "tier": 40, "latency_ms": 80, "cost_per_1m": 0, "status": "local"}
        ],
        "fallback_chain": ["osman-reasoning", "qwen3:8b", "Qwen3 80B Thinking", "Trinity Large Preview"],
        "requirement": {"max_latency_ms": 10000, "prefer_local": True, "min_tier": 40}
    },
    "fast": {
        "description": "Hot path, quick responses, low latency",
        "primary": [
            {"model": "osman-fast", "provider": "ollama", "tier": 40, "latency_ms": 20, "cost_per_1m": 0, "status": "local"},
            {"model": "Step 3.5 Flash", "provider": "nvidia", "tier": 93, "latency_ms": 1794, "cost_per_1m": 3.0, "status": "up"}
        ],
        "fallback_chain": ["osman-fast", "locooperator", "Nemotron Nano 30B"],
        "requirement": {"max_latency_ms": 100, "prefer_local": True, "min_tier": 40, "require_local": True}
    },
    "general": {
        "description": "General purpose fallback",
        "primary": [
            {"model": "osman-agent", "provider": "ollama", "tier": 40, "latency_ms": 50, "cost_per_1m": 0, "status": "local"}
        ],
        "fallback_chain": ["osman-agent", "Llama 4 Maverick"],
        "requirement": {"max_latency_ms": 5000, "prefer_local": True, "min_tier": 40}
    }
}
