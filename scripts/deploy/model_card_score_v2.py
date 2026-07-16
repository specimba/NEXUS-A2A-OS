#!/usr/bin/env python3
"""
NEXUS Model Card / Score v2
=============================
Replaces synthetic 0.45 defaults with UNSCORED (null).
Separates canonical identity, official capabilities, license, benchmark priors,
runtime observations, confidence intervals, availability, safety, source cards.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(r"C:\Users\speci.000\Documents\NEXUS")
REGISTRY = REPO / "config" / "models.registry.json"


def build_card(model_id: str, provider: str, **overrides) -> dict:
    """Build a Model Card v2 with all required fields."""
    return {
        "id": model_id,
        "provider": provider,
        "status": "active",

        # Canonical identity
        "name": overrides.get("name", model_id),
        "aliases": overrides.get("aliases", []),
        "family": overrides.get("family", ""),
        "version": overrides.get("version", "latest"),

        # Official capabilities (from provider docs — metadata priors)
        "context_window": overrides.get("context_window", 4096),
        "max_output_tokens": overrides.get("max_output_tokens", 4096),
        "modalities": overrides.get("modalities", ["text"]),
        "tool_support": overrides.get("tool_support", False),
        "reasoning": overrides.get("reasoning", False),

        # License / residency / allowed-use
        "output_license": overrides.get("output_license", "unknown"),
        "license_url": overrides.get("license_url", ""),
        "residency": overrides.get("residency", ""),
        "allowed_use": overrides.get("allowed_use", ["research", "eval"]),

        # Task-specific benchmark priors (frozen, never overwritten by runtime)
        "benchmark_priors": overrides.get("benchmark_priors", {
            "t2_bench": None,
            "swe_bench": None,
            "swe_bench_pro": None,
            "humanitys_last_exam": None,
            "aime_2024": None,
            "bfcl_v4": None,
            "multi_turn_bfcl": None,
        }),

        # Runtime observations (updated by relay, never overwrites priors)
        "runtime_posterior": {
            "availability": None,  # 0-1 fraction
            "mean_latency_ms": None,
            "p95_latency_ms": None,
            "error_rate": None,
            "cost_per_1k_tokens": None,
            "last_observed": None,
            "sample_count": 0,
            "confidence": "low",  # low/medium/high
        },

        # Composite score (null = UNSCORED, never synthetic)
        "intelligence_score": None,

        # Safety / policy restrictions
        "safety": {
            "rai_policy": overrides.get("rai_policy", "Microsoft.DefaultV2"),
            "content_filter": overrides.get("content_filter", True),
            "blocked_categories": overrides.get("blocked_categories", []),
        },

        # Source card / provenance
        "source_card": {
            "url": overrides.get("source_url", ""),
            "hash": overrides.get("source_hash", ""),
            "fetched_at": None,
            "verification_status": "unverified",
        },
    }


def migrate_registry_v1_to_v2(old_registry: dict) -> dict:
    """Migrate registry v3 (flat) to v2 (rich cards)."""
    old_models = old_registry.get("models", [])
    new_models = []

    for old in old_models:
        new = build_card(
            model_id=old.get("id", ""),
            provider=old.get("provider", "unknown"),
            context_window=old.get("contextWindow", 4096),
            intelligence_score=None,  # NEVER synthetic 0.45
            output_license=old.get("outputLicense", "unknown"),
            rai_policy=old.get("raiPolicy", ""),
        )
        # Migrate any existing benchmark scores
        if "benchmarkScores" in old:
            new["benchmark_priors"].update(old["benchmarkScores"])
        new_models.append(new)

    return {
        "schema_version": "nexus.model.registry.v2",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model_count": len(new_models),
        "models": new_models,
    }


def remove_synthetic_scores(registry: dict) -> dict:
    """Replace any 0.45 synthetic defaults with null (UNSCORED)."""
    for model in registry.get("models", []):
        score = model.get("intelligence_score")
        if score is not None and abs(score - 0.45) < 0.001:
            model["intelligence_score"] = None
        # Also check nested runtime posterior
        posterior = model.get("runtime_posterior", {})
        if posterior.get("intelligence") is not None and abs(posterior["intelligence"] - 0.45) < 0.001:
            posterior["intelligence"] = None
    return registry


if __name__ == "__main__":
    if REGISTRY.exists():
        old = json.loads(REGISTRY.read_text(encoding="utf-8"))
        new = migrate_registry_v1_to_v2(old)
        new = remove_synthetic_scores(new)
        out = REPO / "config" / "models.registry.v2.json"
        out.write_text(json.dumps(new, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Migrated {len(new['models'])} models -> {out}")
        print(f"UNSCORED models: {sum(1 for m in new['models'] if m.get('intelligence_score') is None)}")
    else:
        print(f"Registry not found: {REGISTRY}")
