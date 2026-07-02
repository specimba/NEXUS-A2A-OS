# GMR Domain -> Model Mapping.
#
# Two layers, merged at import:
# - LOCAL_DOMAIN_MAPPING (hand-authored): the resident local/Ollama custom
#   models (osman-* family, Bonsai) the registry doesn't model.
# - GENERATED_DOMAIN_MAPPING: role-tagged cloud/frontier entries generated
#   from config/models.registry.json (scripts/gen_model_registry.py) —
#   replaces the stale hand-edited literals ("GLM 5", "Trinity Large
#   Preview") that named retired display strings instead of model ids.
#
# Merge order: locals FIRST in every domain — the NEXUS posture is
# SLM-team-first with deliberate escalation to frontier cloud models
# (which follow, tier-sorted, as the escalation/fallback tier). Fallback
# chains: local chain + generated chain.

from nexus_os.gmr.domain_mapping_generated import GENERATED_DOMAIN_MAPPING

LOCAL_DOMAIN_MAPPING = {
    "code": {
        "primary": [
            {"model": "osman-coder", "provider": "ollama", "tier": 40, "latency_ms": 50, "cost_per_1m": 0, "status": "local"},
        ],
        "fallback_chain": ["osman-coder", "qwen2.5-coder:7b"],
    },
    "reasoning": {
        "primary": [
            {"model": "osman-reasoning", "provider": "ollama", "tier": 40, "latency_ms": 80, "cost_per_1m": 0, "status": "local"},
        ],
        "fallback_chain": ["osman-reasoning", "qwen3:8b"],
    },
    "research": {
        "primary": [],
        "fallback_chain": ["osman-reasoning"],
    },
    "fast": {
        "primary": [
            {"model": "osman-fast", "provider": "ollama", "tier": 40, "latency_ms": 20, "cost_per_1m": 0, "status": "local"},
            {"model": "Bonsai 4B IQ1_S", "provider": "ollama", "tier": 40, "latency_ms": 15, "cost_per_1m": 0, "status": "local"},
            {"model": "locooperator", "provider": "ollama", "tier": 40, "latency_ms": 30, "cost_per_1m": 0, "status": "local"},
        ],
        "fallback_chain": ["Bonsai 4B", "osman-fast", "locooperator"],
    },
    "security": {
        "primary": [],
        "fallback_chain": ["osman-reasoning"],
    },
    "general": {
        "primary": [
            {"model": "osman-agent", "provider": "ollama", "tier": 40, "latency_ms": 50, "cost_per_1m": 0, "status": "local"},
        ],
        "fallback_chain": ["osman-agent", "qwen3.5:4b"],
    },
}


def _merge() -> dict:
    merged: dict = {}
    for domain in LOCAL_DOMAIN_MAPPING:
        local = LOCAL_DOMAIN_MAPPING[domain]
        generated = GENERATED_DOMAIN_MAPPING.get(domain, {"primary": [], "fallback_chain": []})
        primary = local["primary"] + generated["primary"]
        chain = local["fallback_chain"] + generated["fallback_chain"]
        seen: set = set()
        merged[domain] = {
            "primary": primary,
            "fallback_chain": [m for m in chain if not (m in seen or seen.add(m))],
        }
    return merged


DOMAIN_MAPPING = _merge()
