"""
NEXUS OS Bridge — Vault Routing Tiers

Defines the routing_tiers dictionary that governs how models are selected
for different task types. Each tier has a detailed description explaining
its purpose, the models it uses, and when it should be invoked.

The routing system follows the GMR (General Model Rotation) protocol:
  - PREMIUM  → Critical reasoning, security, and governance tasks
  - MID      → General coding, analysis, and production work
  - FAST     → Quick lookups, brief summaries, low-latency needs
  - FREE_RESEARCH → Research experiments, bulk processing, non-critical tasks
"""

import logging
from typing import Any

logger = logging.getLogger("nexus_os.bridge.vault")

# ── Routing Tiers ────────────────────────────────────────────────
# Each tier defines: description, purpose, models, routing_rules

routing_tiers: dict[str, dict[str, Any]] = {
    "PREMIUM": {
        "description": (
            "Premium tier handles the most critical tasks requiring deep reasoning, "
            "security analysis, and governance decisions. These models have the highest "
            "tier scores (90+) and are reserved for tasks where accuracy and safety "
            "outweigh cost or latency. Includes constitutional AI checks, trust score "
            "recalibration, and cross-scope action authorization."
        ),
        "purpose": (
            "Constitutional governance, security audits, trust recalculation, "
            "cross-project authorization, and any task requiring the Kaiju gate."
        ),
        "models": [
            {
                "name": "trinity-large-preview",
                "tier_score": 97,
                "domains": ["reason", "security"],
                "cost_per_1k": 0,
                "description": "Primary reasoning model. Handles complex multi-step logic, security domain analysis, and constitutional checks. Highest tier score in the fleet.",
            },
            {
                "name": "minimax-m2.5",
                "tier_score": 92,
                "domains": ["reason", "research"],
                "cost_per_1k": 0,
                "description": "Backup reasoning model for when trinity-large is rate-limited or under circuit breaker cooldown. Strong on research synthesis.",
            },
        ],
        "routing_rules": {
            "min_tier_score": 90,
            "max_concurrent": 2,
            "circuit_breaker_threshold": 3,
            "failover_target": "MID",
        },
    },

    "MID": {
        "description": (
            "Mid tier is the workhorse of NEXUS OS. It handles general coding tasks, "
            "analysis, and production-level work that needs reliable results but doesn't "
            "require the premium models' full reasoning capabilities. Models in this tier "
            "have tier scores between 70-89 and cover the broadest range of domains."
        ),
        "purpose": (
            "Code generation, debugging, API development, documentation, "
            "test writing, and general-purpose agent tasks."
        ),
        "models": [
            {
                "name": "qwen3-coder",
                "tier_score": 82,
                "domains": ["code"],
                "cost_per_1k": 0,
                "description": "Primary code model. Optimized for code generation, debugging, and API implementation. Default selection for any task classified as Domain.CODE.",
            },
            {
                "name": "kimi-k2.5",
                "tier_score": 78,
                "domains": ["code", "reason"],
                "cost_per_1k": 0,
                "description": "Versatile mid-tier model for mixed code/reasoning tasks. Strong on multi-file refactoring and integration work.",
            },
            {
                "name": "gpt-oss-120b",
                "tier_score": 75,
                "domains": ["code", "reason"],
                "cost_per_1k": 0,
                "description": "Large open-source model for complex but non-critical tasks. Good on documentation and explanation tasks.",
            },
        ],
        "routing_rules": {
            "min_tier_score": 70,
            "max_concurrent": 4,
            "circuit_breaker_threshold": 5,
            "failover_target": "FAST",
        },
    },

    "FAST": {
        "description": (
            "Fast tier is optimized for low-latency responses. These models have "
            "smaller parameter counts but deliver sub-second responses for quick "
            "lookups, brief summaries, and simple formatting tasks. They are the "
            "first choice when the Engine classifies a task as Domain.FAST."
        ),
        "purpose": (
            "Quick lookups, brief summaries, formatting, simple Q&A, "
            "and any task where latency matters more than depth."
        ),
        "models": [
            {
                "name": "gemma-fast",
                "tier_score": 50,
                "domains": ["fast"],
                "cost_per_1k": 0,
                "description": "Primary fast model. Optimized for sub-200ms responses on simple tasks. Best for quick formatting, lookups, and brief summaries.",
            },
            {
                "name": "nemotron-3-super",
                "tier_score": 55,
                "domains": ["fast", "research"],
                "cost_per_1k": 0,
                "description": "Slightly larger fast model with better research capabilities. Fallback when gemma-fast is under circuit breaker.",
            },
        ],
        "routing_rules": {
            "min_tier_score": 40,
            "max_concurrent": 8,
            "circuit_breaker_threshold": 8,
            "failover_target": "FREE_RESEARCH",
        },
    },

    "FREE_RESEARCH": {
        "description": (
            "Free Research tier is for non-critical, experimental, and bulk processing "
            "tasks. These models are free-tier API endpoints with lower rate limits but "
            "no cost. Use for research experiments, batch data processing, and any task "
            "where occasional failures are acceptable. Not suitable for governance or "
            "production decisions."
        ),
        "purpose": (
            "Research experiments, bulk data processing, non-critical analysis, "
            "background jobs, and tasks where cost must be zero."
        ),
        "models": [
            {
                "name": "nemotron-3-nano:4b",
                "tier_score": 30,
                "domains": ["research", "code"],
                "cost_per_1k": 0,
                "description": "Free-tier nano model for basic research tasks. 4B parameters, runs locally. Good for simple code analysis and lightweight research.",
            },
            {
                "name": "deepseek-r1:8b",
                "tier_score": 35,
                "domains": ["reason", "research"],
                "cost_per_1k": 0,
                "description": "Free-tier reasoning model for research experiments. 8B parameters with chain-of-thought. Slower but more thorough than nano models.",
            },
        ],
        "routing_rules": {
            "min_tier_score": 0,
            "max_concurrent": 10,
            "circuit_breaker_threshold": 10,
            "failover_target": None,  # No fallback from free tier
        },
    },
}


def get_tier_for_score(score: int) -> str:
    """Determine which routing tier a model belongs to based on its tier score."""
    if score >= 90:
        return "PREMIUM"
    elif score >= 70:
        return "MID"
    elif score >= 40:
        return "FAST"
    else:
        return "FREE_RESEARCH"


def get_models_for_tier(tier_name: str) -> list[dict]:
    """Get all model definitions for a given tier."""
    tier = routing_tiers.get(tier_name)
    if not tier:
        logger.warning("Vault routing: unknown tier '%s'", tier_name)
        return []
    return tier["models"]


def get_failover_tier(tier_name: str) -> str | None:
    """Get the failover target tier when the current tier is exhausted."""
    tier = routing_tiers.get(tier_name)
    if not tier:
        return None
    return tier["routing_rules"]["failover_target"]
