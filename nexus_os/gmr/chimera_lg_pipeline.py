"""ChimeraRouter ⇄ ModelRelay ⇄ Landau–Ginzburg pipeline.

Unifies three layers that previously only existed as separate CLIs:

    1. ChimeraRouterV2  — model/tier/temperature-policy decision
    2. ModelRelayAdapter — OpenAI-compatible execution (7350 → 7357 → 7355)
    3. LandauGinzburgTrackerV2 — EDT / LEAD / EPR telemetry (dry-run or post-hoc)

Design rules
------------
- Decision layer never needs secrets; adapter owns endpoints.
- LG tracker after black-box API responses uses **dry-run entropy** driven by
  the selected temperature and policy flags (true logprobs are optional).
  This is honest: we do not invent white-box logits from text alone.
- Default for ``execute=True`` includes cloud tier so ModelRelay catalogue IDs
  (e.g. deepseek-ai/deepseek-v4-pro) are eligible instead of only local GGUF
  profile names that cannot run on :7350.
"""

from __future__ import annotations

import os
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Optional

from nexus_os.twave.chimera_router_v2 import (
    ChimeraRouterV2,
    RoutingDecision,
    TemperaturePolicy,
    Tier,
)


@dataclass
class PipelineReport:
    """Structured result of one route → (optional execute) → LG track pass."""

    status: str
    prompt_preview: str
    route: dict[str, Any]
    execution: Optional[dict[str, Any]] = None
    lg: Optional[dict[str, Any]] = None
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _decision_to_dict(decision: RoutingDecision) -> dict[str, Any]:
    return {
        "tier": decision.tier.value,
        "model": decision.model,
        "temperature": round(float(decision.temperature), 4),
        "policy": decision.temperature_policy.value,
        "expected_latency_ms": round(float(decision.expected_latency_ms), 1),
        "expected_quality": round(float(decision.expected_quality), 3),
        "max_tokens": int(decision.budget.max_tokens),
        "confidence": round(float(decision.confidence), 3),
        "features": {
            "edt": bool(decision.use_edt),
            "lead": bool(decision.use_lead),
            "epr": bool(decision.use_epr),
            "led": bool(decision.use_led),
            "ckplug": bool(decision.use_ckplug),
            "attn_divergence": bool(decision.use_attention_divergence),
            "twave": bool(decision.use_twave),
        },
        "reason": decision.reason,
    }


def _build_tiers(*, cloud: bool, execute: bool) -> list[Tier]:
    """Include CLOUD when cloud or execute — local GGUF names cannot hit :7350."""
    tiers = [Tier.CONTROL_PLANE, Tier.LOCAL_STANDARD, Tier.LOCAL_POWER]
    if cloud or execute:
        tiers.append(Tier.CLOUD)
    return tiers


def _policy_from_name(name: str) -> TemperaturePolicy:
    mapping = {
        "auto": TemperaturePolicy.AUTO,
        "fixed": TemperaturePolicy.FIXED,
        "edt": TemperaturePolicy.EDT,
        "ead": TemperaturePolicy.EAD,
        "lead": TemperaturePolicy.LEAD,
        "ernie": TemperaturePolicy.ERNIE,
    }
    return mapping.get(name.lower(), TemperaturePolicy.AUTO)


def _live_catalogue_ids() -> set[str]:
    """Best-effort live ModelRelay/GodMode IDs; empty set if relays down."""
    try:
        from nexus_os.gmr.telemetry import TelemetryIngest

        cache = TelemetryIngest().fetch()
        return {name for name in cache if name != "godmode_summary"}
    except Exception:
        return set()


def resolve_execute_model(
    requested: str,
    catalogue: set[str],
) -> tuple[str, Optional[str]]:
    """Map Chimera decision IDs onto live catalogue names.

    Hand-authored cloud profiles (e.g. ``qwen2.5-72b-instruct-bf16``) are not
    ModelRelay model IDs. Prefer exact match, then router aliases, then known
    frontier IDs present in the live catalogue.
    """
    if not catalogue:
        return requested, "live catalogue empty; using decision model as-is"
    if requested in catalogue:
        return requested, None
    # Case-insensitive exact
    lower_map = {c.lower(): c for c in catalogue}
    if requested.lower() in lower_map:
        return lower_map[requested.lower()], f"case-normalized {requested}"

    preferred = (
        "auto-fastest",
        "auto-smart",
        "deepseek-ai/deepseek-v4-pro",
        "deepseek-ai/DeepSeek-V4-Pro",
        "z-ai/glm-5.2",
        "minimaxai/minimax-m3",
    )
    for cand in preferred:
        if cand in catalogue:
            return cand, f"remapped {requested} → {cand} (decision id not in live catalogue)"
        if cand.lower() in lower_map:
            real = lower_map[cand.lower()]
            return real, f"remapped {requested} → {real} (decision id not in live catalogue)"
    # Last resort: first catalogue entry that looks like a chat model
    for name in sorted(catalogue):
        if "embed" in name.lower():
            continue
        return name, f"remapped {requested} → {name} (fallback catalogue pick)"
    return requested, f"{requested} not in catalogue; execution may 404"


def run_lg_track(
    *,
    category: str,
    temperature: float,
    tokens: int,
    enable_edt: bool = True,
    enable_lead: bool = True,
    enable_epr: bool = True,
    enable_led: bool = False,
    enable_ckplug: bool = False,
) -> dict[str, Any]:
    """Run LandauGinzburgTrackerV2 for *tokens* steps (dry-run entropy path)."""
    from nexus_os.twave.landau_ginzburg_tracker_v2 import LandauGinzburgTrackerV2

    tracker = LandauGinzburgTrackerV2(
        category=category,
        enable_edt=enable_edt,
        enable_lead=enable_lead,
        enable_epr=enable_epr,
        enable_led=enable_led,
        enable_ckplug=enable_ckplug,
    )
    tracker.set_dry_run(True)
    n = max(1, min(int(tokens), 256))
    t0 = time.perf_counter()
    for i in range(n):
        tracker.step(position=i, current_temperature=float(temperature))
    report = tracker.get_report()
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    return {
        "mode": "dry_run",
        "category": report.category,
        "tokens_simulated": report.tokens_generated,
        "elapsed_ms": round(elapsed_ms, 2),
        "hallucination_detected": report.hallucination_detected,
        "hallucination_positions": list(report.hallucination_positions),
        "self_correction_positions": list(report.self_correction_positions),
        "cooling_events": len(report.cooling_events),
        "mean_entropy": round(float(report.mean_entropy), 4),
        "max_entropy": round(float(report.max_entropy), 4),
        "entropy_variance": round(float(report.entropy_variance), 4),
        "final_temperature": round(float(report.final_temperature), 4),
        "epr_score": round(float(report.epr_score), 4) if report.epr_score is not None else None,
        "mode_transitions": len(report.mode_transitions or []),
        "edt_schedule_points": len(report.edt_temperature_schedule or []),
        "honesty": (
            "Black-box API replies do not supply logits; LG runs in dry-run "
            "entropy mode driven by Chimera temperature/policy flags."
        ),
    }


def run_pipeline(
    prompt: str,
    *,
    execute: bool = False,
    cloud: bool = True,
    category: str = "F1.1",
    policy: str = "auto",
    quality: float = 0.75,
    latency_budget_ms: float = 4000.0,
    vram_gb: float = 8.0,
    track: bool = True,
    track_tokens: int = 32,
    relay_url: Optional[str] = None,
    fallback_url: Optional[str] = None,
    godmode_url: Optional[str] = None,
    max_tokens_cap: int = 256,
) -> PipelineReport:
    """Run Chimera route, optional ModelRelay execute, optional LG track."""
    notes: list[str] = []
    use_cloud = bool(cloud or execute)
    if execute and not cloud:
        notes.append("execute=True implies cloud tier eligibility for ModelRelay IDs")

    router = ChimeraRouterV2(
        vram_gb=vram_gb,
        has_cloud_access=use_cloud,
        available_tiers=_build_tiers(cloud=use_cloud, execute=execute),
    )
    decision = router.route(
        prompt,
        latency_budget_ms=latency_budget_ms,
        quality_target=quality,
        category=category,
        temperature_policy=_policy_from_name(policy),
    )
    route_dict = _decision_to_dict(decision)

    # Cap max_tokens for live execute safety (operator can raise via max_tokens_cap).
    if decision.budget.max_tokens > max_tokens_cap:
        notes.append(
            f"capped max_tokens {decision.budget.max_tokens} → {max_tokens_cap} for safety"
        )

    execution: Optional[dict[str, Any]] = None
    if execute:
        from nexus_os.relay.model_relay_adapter import ModelRelayAdapter, RelayRequest

        primary = (
            relay_url
            or os.environ.get("NODERELAY_URL")
            or f"http://127.0.0.1:{os.environ.get('NODERELAY_PORT', '7350')}"
        )
        catalogue = _live_catalogue_ids()
        exec_model, remap_note = resolve_execute_model(decision.model, catalogue)
        if remap_note:
            notes.append(remap_note)

        adapter = ModelRelayAdapter(
            primary_url=primary,
            fallback_url=fallback_url,
            godmode_url=godmode_url,
        )
        max_tok = min(int(decision.budget.max_tokens), max_tokens_cap)
        req = RelayRequest(
            model=exec_model,
            prompt=prompt,
            temperature=float(decision.temperature),
            max_tokens=max_tok,
            relay_url=primary,
            metadata={
                "category": category,
                "policy": decision.temperature_policy.value,
                "pipeline": "chimera_lg",
                "chimera_decision_model": decision.model,
            },
        )
        result = adapter.execute(req)
        execution = {
            "status": result.status,
            "provider": result.provider,
            "model_requested": decision.model,
            "model_executed": exec_model,
            "used_fallback": result.used_fallback,
            "latency_ms": result.latency_ms,
            "attempts": result.attempts,
            "response_preview": (result.raw or "")[:400] if result.raw else None,
            "response_chars": len(result.raw or ""),
            "catalogue_size": len(catalogue),
        }
        if result.status != "ok":
            notes.append(f"execution status={result.status}")

    lg: Optional[dict[str, Any]] = None
    if track:
        # Align LG enable flags with Chimera feature selection.
        lg = run_lg_track(
            category=category,
            temperature=float(decision.temperature),
            tokens=track_tokens,
            enable_edt=bool(decision.use_edt),
            enable_lead=bool(decision.use_lead),
            enable_epr=bool(decision.use_epr or decision.use_twave),
            enable_led=bool(decision.use_led),
            enable_ckplug=bool(decision.use_ckplug),
        )
        lg["chimera_policy"] = decision.temperature_policy.value
        lg["chimera_temperature"] = round(float(decision.temperature), 4)

    status = "ok"
    if execute and execution is not None and execution.get("status") != "ok":
        status = "degraded"
    if track and lg is not None and lg.get("hallucination_detected"):
        status = "degraded" if status == "ok" else status
        notes.append("LG dry-run flagged hallucination_detected")

    preview = prompt if len(prompt) <= 120 else prompt[:117] + "..."
    return PipelineReport(
        status=status,
        prompt_preview=preview,
        route=route_dict,
        execution=execution,
        lg=lg,
        notes=notes,
    )
