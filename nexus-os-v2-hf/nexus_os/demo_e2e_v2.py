#!/usr/bin/env python3
"""
NEXUS OS v2.0 — End-to-End Unified Demo
========================================
ChimeraRouter + TWAVE/LEAD/EDT/EPR + ERNIE integration + Full pipeline.

Usage:
    python nexus_os/demo_e2e_v2.py --prompt "What is quantum entanglement?"
"""

import sys, json, random
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from nexus_os.chimera_router_v2 import (
    ChimeraRouterV2, ERNIEInterface, ERNIESuggestion, TemperaturePolicy, Tier
)
from twave.landau_ginzburg_tracker_v2 import LandauGinzburgTrackerV2, DecodingMode

def main():
    import argparse
    parser = argparse.ArgumentParser(description="NEXUS OS v2.0 E2E Demo")
    parser.add_argument("--prompt", default="Explain quantum entanglement step by step.")
    parser.add_argument("--vram", type=float, default=8.0)
    parser.add_argument("--budget", type=float, default=2000.0)
    parser.add_argument("--quality", type=float, default=0.75)
    parser.add_argument("--category", default="R2.2")
    parser.add_argument("--policy", default="auto")
    parser.add_argument("--enable-ernie", action="store_true", default=True)
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--tokens", type=int, default=50)
    args = parser.parse_args()

    # --- ERNIE callback ---
    def ernie_cb(prompt, analysis):
        if "quantum" in prompt.lower():
            return ERNIESuggestion(
                suggested_policy=TemperaturePolicy.EAD,
                confidence=0.85,
                reasoning="Quantum prompts need annealed exploration for reasoning chains",
                override_router=False,
            )
        if "code" in prompt.lower() or "function" in prompt.lower():
            return ERNIESuggestion(
                suggested_temperature=0.2,
                suggested_policy=TemperaturePolicy.FIXED,
                confidence=0.9,
                reasoning="Code generation needs low temperature for deterministic syntax",
                override_router=True,
            )
        return None

    ernie = ERNIEInterface(callback=ernie_cb) if args.enable_ernie else ERNIEInterface()

    # --- Router ---
    router = ChimeraRouterV2(
        vram_gb=args.vram,
        has_cloud_access=False,
        available_tiers=[Tier.CONTROL_PLANE, Tier.LOCAL_STANDARD, Tier.LOCAL_POWER],
        ernie_interface=ernie,
    )

    policy = {
        "auto": TemperaturePolicy.AUTO,
        "fixed": TemperaturePolicy.FIXED,
        "edt": TemperaturePolicy.EDT,
        "ead": TemperaturePolicy.EAD,
        "lead": TemperaturePolicy.LEAD,
        "ernie": TemperaturePolicy.ERNIE,
    }.get(args.policy, TemperaturePolicy.AUTO)

    decision = router.route(
        prompt=args.prompt,
        latency_budget_ms=args.budget,
        quality_target=args.quality,
        category=args.category,
        temperature_policy=policy,
    )

    print("=" * 70)
    print("NEXUS OS v2.0 — End-to-End Unified Demo")
    print("=" * 70)
    print(f"\n[PROMPT] {args.prompt[:70]}...")
    print(f"\n[ROUTING DECISION]")
    print(f"  Tier:        {decision.tier.value}")
    print(f"  Model:       {decision.model}")
    print(f"  Temperature: {decision.temperature:.3f} (policy: {decision.temperature_policy.value})")
    print(f"  Expected:    {decision.expected_latency_ms:.0f}ms latency, {decision.expected_quality:.2f} quality")
    print(f"  Max tokens:  {decision.budget.max_tokens}")
    print(f"  Features:    EDT={decision.use_edt}, LEAD={decision.use_lead}, "
          f"EPR={decision.use_epr}, LED={decision.use_led}, "
          f"CK-PLUG={decision.use_ckplug}, AttnDiv={decision.use_attention_divergence}")
    print(f"  Confidence:  {decision.confidence:.2f}")
    print(f"  Reason:      {decision.reason[:100]}...")
    if decision.ernie_suggestion:
        print(f"\n[ERNIE SUGGESTION]")
        print(f"  Confidence:  {decision.ernie_suggestion.confidence:.2f}")
        print(f"  Reasoning:   {decision.ernie_suggestion.reasoning}")
        print(f"  Override:    {decision.ernie_suggestion.override_router}")

    # --- TWAVE Tracker ---
    tracker = LandauGinzburgTrackerV2(
        category=args.category,
        enable_edt=decision.use_edt,
        enable_lead=decision.use_lead,
        enable_epr=decision.use_epr,
        enable_led=decision.use_led,
        enable_ckplug=decision.use_ckplug,
        enable_attention_divergence=decision.use_attention_divergence,
    )
    tracker.set_dry_run(args.dry_run)

    # Simulation loop
    print(f"\n[GENERATION] Simulating {args.tokens} tokens...")
    print("-" * 70)
    for i in range(args.tokens):
        action = tracker.step(
            position=i,
            current_temperature=decision.temperature if i == 0 else action["t_eff"],
        )
        mode_icon = {"discrete": "D", "latent": "L", "explore": "E", "abstain": "A"}[action["mode"]]
        if action["is_hallucinating"]:
            print(f"  [T={i:02d}] 🚨 HALLUCINATION  mode={mode_icon} T_eff={action['effective_temperature']:.3f}")
            break
        elif action["cool"]:
            print(f"  [T={i:02d}] ❄️ COOL  mode={mode_icon} T→{action['t_eff']:.3f} ({action['trigger']})")
        elif action["watch"]:
            print(f"  [T={i:02d}] 👁️ WATCH mode={mode_icon} risk={action['hallucination_risk']:.2f} H={action['order_params']['entropy']:.2f}")
        else:
            if i % 10 == 0:
                print(f"  [T={i:02d}] OK    mode={mode_icon} H={action['order_params']['entropy']:.2f}")
    
    report = tracker.get_report()
    print(f"\n[REPORT]")
    print(f"  Tokens:           {report.tokens_generated}")
    print(f"  Hallucination:    {report.hallucination_detected} @ {report.hallucination_positions}")
    print(f"  Self-corrections: {report.self_correction_positions}")
    print(f"  Cooling events:   {len(report.cooling_events)}")
    print(f"  Mean entropy:     {report.mean_entropy:.3f}")
    print(f"  Max entropy:      {report.max_entropy:.3f}")
    print(f"  EPR score:        {report.epr_score:.3f}" if report.epr_score else "  EPR: N/A")
    print(f"  Mode transitions: {len(report.mode_transitions) if report.mode_transitions else 0}")
    print(f"  LED depths:       {len(report.led_depth_selected) if report.led_depth_selected else 0}")
    print("=" * 70)

if __name__ == "__main__":
    main()
