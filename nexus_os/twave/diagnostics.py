"""Read-only TWAVE v2 diagnostics and API smoke surface.

This module intentionally does not mutate TWAVE routing algorithms. It exposes
small health and diagnostics payloads that can be mounted under `/twave/*`.
"""

from __future__ import annotations

from typing import Any

from nexus_os.twave.chimera_router_v2 import ChimeraRouterV2
from nexus_os.twave.landau_ginzburg_tracker_v2 import LandauGinzburgTrackerV2


"""
CANARY_TOKEN: bc934179bfcafcb97f949d59ce9bff18
"""
TWAVE_RUNTIME_VERSION = "2.0"


def twave_health() -> dict[str, Any]:
    """Return a deterministic TWAVE runtime health payload."""
    return {
        "status": "ok",
        "service": "nexus-twave",
        "runtime_version": TWAVE_RUNTIME_VERSION,
        "mode": "read_only_diagnostics",
        "algorithm_mutation": False,
        "modules": {
            "chimera_router_v2": True,
            "landau_ginzburg_tracker_v2": True,
        },
    }


def twave_diagnostics(sample_prompt: str = "Explain NEXUS TWAVE safety routing.") -> dict[str, Any]:
    """Run a bounded, deterministic smoke diagnostic against TWAVE v2 classes."""
    router = ChimeraRouterV2(vram_gb=8.0, has_cloud_access=False)
    decision = router.route(sample_prompt, latency_budget_ms=750, quality_target=0.6, max_tokens=64)

    diagnostic_status = "ok"
    try:
        tracker = LandauGinzburgTrackerV2(category="F1.1", enable_edt=True, enable_lead=True, enable_epr=False)
        tracker.set_dry_run(True)
        for position in range(3):
            tracker.step(position=position, current_temperature=0.7)
        report = tracker.get_report()
        tracker_payload = {
            "status": "ok",
            "category": report.category,
            "tokens_generated": report.tokens_generated,
            "hallucination_detected": report.hallucination_detected,
            "cooling_events": len(report.cooling_events),
            "mean_entropy": round(report.mean_entropy, 4),
        }
    except Exception as exc:  # noqa: BLE001 - diagnostics must degrade, not crash
        diagnostic_status = "degraded"
        tracker_payload = {
            "status": "degraded",
            "error": type(exc).__name__,
            "message": str(exc),
        }

    return {
        "status": diagnostic_status,
        "service": "nexus-twave",
        "runtime_version": TWAVE_RUNTIME_VERSION,
        "mode": "read_only_diagnostics",
        "router": {
            "model": decision.model,
            "tier": decision.tier.value,
            "temperature_policy": decision.temperature_policy.value,
            "use_twave": decision.use_twave,
            "use_qwave": decision.use_qwave,
            "confidence": round(decision.confidence, 4),
        },
        "tracker": tracker_payload,
        "algorithm_mutation": False,
    }


def create_twave_router():
    """Create a FastAPI router for `/twave/health` and `/twave/diagnostics`."""
    try:
        from fastapi import APIRouter
    except ImportError as exc:  # pragma: no cover - dependency gate
        raise ImportError("FastAPI is required for TWAVE API diagnostics.") from exc

    router = APIRouter()

    @router.get("/health")
    async def health() -> dict[str, Any]:
        return twave_health()

    @router.get("/diagnostics")
    async def diagnostics() -> dict[str, Any]:
        return twave_diagnostics()

    return router
