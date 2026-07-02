"""
NEXUS OS v2.0 — End-to-End Unified Demo
========================================
ChimeraRouter + TWAVE/LEAD/EDT/EPR + ERNIE integration + Full pipeline.
"""
import argparse, sys

from nexus_os.twave.chimera_router_v2 import (
    ChimeraRouterV2, ERNIEInterface, ERNIESuggestion, TemperaturePolicy, Tier
)
from nexus_os.twave.landau_ginzburg_tracker_v2 import LandauGinzburgTrackerV2

def ernie_cb(prompt, analysis):
    if "quantum" in prompt.lower():
        return ERNIESuggestion(
            suggested_policy=TemperaturePolicy.EAD, confidence=0.85,
            reasoning="Quantum prompts need annealed exploration",
            override_router=False,
        )
    if "code" in prompt.lower() or "function" in prompt.lower():
        return ERNIESuggestion(
            suggested_temperature=0.2, suggested_policy=TemperaturePolicy.FIXED,
            confidence=0.9, reasoning="Code needs low temperature for syntax",
            override_router=True,
        )
    return None

def main():
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

    ernie = ERNIEInterface(callback=ernie_cb) if args.enable_ernie else ERNIEInterface()
    router = ChimeraRouterV2(
        vram_gb=args.vram, has_cloud_access=False,
        available_tiers=[Tier.CONTROL_PLANE, Tier.LOCAL_STANDARD, Tier.LOCAL_POWER],
        ernie_interface=ernie,
    )
    policy = {
        "auto": TemperaturePolicy.AUTO, "fixed": TemperaturePolicy.FIXED,
        "edt": TemperaturePolicy.EDT, "ead": TemperaturePolicy.EAD,
        "lead": TemperaturePolicy.LEAD, "ernie": TemperaturePolicy.ERNIE,
    }.get(args.policy, TemperaturePolicy.AUTO)

    decision = router.route(
        prompt=args.prompt, latency_budget_ms=args.budget,
        quality_target=args.quality, category=args.category,
        temperature_policy=policy,
    )

    print("=" * 70)
    print("NEXUS OS v2.0 — End-to-End Unified Demo")
    print("=" * 70)
    print(f"\n[PROMPT] {args.prompt[:70]}...")
    print(f"\n[ROUTING] Tier={decision.tier.value}, Model={decision.model}")
    print(f"  T={decision.temperature:.3f} ({decision.temperature_policy.value})")
    print(f"  Latency={decision.expected_latency_ms:.0f}ms, Quality={decision.expected_quality:.2f}")
    print(f"  Max tokens={decision.budget.max_tokens}")
    print(f"  Features: EDT={decision.use_edt}, LEAD={decision.use_lead}, "
          f"EPR={decision.use_epr}, LED={decision.use_led}")
    if decision.ernie_suggestion:
        print(f"  ERNIE: conf={decision.ernie_suggestion.confidence:.2f}, "
              f"'{decision.ernie_suggestion.reasoning[:50]}'")

    tracker = LandauGinzburgTrackerV2(
        category=args.category,
        enable_edt=decision.use_edt, enable_lead=decision.use_lead,
        enable_epr=decision.use_epr, enable_led=decision.use_led,
        enable_ckplug=decision.use_ckplug,
        enable_attention_divergence=decision.use_attention_divergence,
    )
    tracker.set_dry_run(args.dry_run)

    print(f"\n[GENERATION] {args.tokens} tokens...")
    action = {"t_eff": decision.temperature}
    for i in range(args.tokens):
        action = tracker.step(
            position=i,
            current_temperature=action["t_eff"],
        )
        mode_icon = {"discrete": "D", "latent": "L", "explore": "E", "abstain": "A"}[action["mode"]]
        if action["is_hallucinating"]:
            print(f"  [T={i:02d}] HALLUC mode={mode_icon} T_eff={action['effective_temperature']:.3f}")
            break
        elif action["cool"]:
            print(f"  [T={i:02d}] COOL  mode={mode_icon} T->{action['t_eff']:.3f} ({action['trigger']})")
        elif action["watch"]:
            print(f"  [T={i:02d}] WATCH mode={mode_icon} risk={action['hallucination_risk']:.2f}")
        elif i % 10 == 0:
            print(f"  [T={i:02d}] OK    mode={mode_icon}")

    report = tracker.get_report()
    print(f"\n[REPORT] tokens={report.tokens_generated}, "
          f"halluc={report.hallucination_detected} @ {report.hallucination_positions}, "
          f"cooling={len(report.cooling_events)}")

if __name__ == "__main__":
    main()
