import sys, argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from nexus_os.twave.chimera_router_v2 import (
    ChimeraRouterV2, ERNIEInterface, ERNIESuggestion, TemperaturePolicy, Tier
)
from twave.landau_ginzburg_tracker_v2 import LandauGinzburgTrackerV2

def ernie_cb(prompt, analysis):
    if "quantum" in prompt.lower():
        return ERNIESuggestion(
            suggested_policy=TemperaturePolicy.EAD, confidence=0.85,
            reasoning="Quantum prompts need annealed exploration", override_router=False)
    if "code" in prompt.lower() or "function" in prompt.lower():
        return ERNIESuggestion(
            suggested_temperature=0.2, suggested_policy=TemperaturePolicy.FIXED,
            confidence=0.9, reasoning="Code needs low temperature", override_router=True)
    return None

def main():
    parser = argparse.ArgumentParser(description="NEXUS OS v2.0 E2E Demo")
    parser.add_argument("--prompt", default="Explain quantum entanglement step by step.")
    parser.add_argument("--vram", type=float, default=8.0); parser.add_argument("--budget", type=float, default=2000.0)
    parser.add_argument("--quality", type=float, default=0.75); parser.add_argument("--category", default="R2.2")
    parser.add_argument("--policy", default="auto"); parser.add_argument("--enable-ernie", action="store_true", default=True)
    parser.add_argument("--dry-run", action="store_true", default=True); parser.add_argument("--tokens", type=int, default=50)
    args = parser.parse_args()
    ernie = ERNIEInterface(callback=ernie_cb) if args.enable_ernie else ERNIEInterface()
    router = ChimeraRouterV2(vram_gb=args.vram, has_cloud_access=False,
        available_tiers=[Tier.CONTROL_PLANE, Tier.LOCAL_STANDARD, Tier.LOCAL_POWER], ernie_interface=ernie)
    policy = {"auto": TemperaturePolicy.AUTO, "fixed": TemperaturePolicy.FIXED, "edt": TemperaturePolicy.EDT,
        "ead": TemperaturePolicy.EAD, "lead": TemperaturePolicy.LEAD, "ernie": TemperaturePolicy.ERNIE
    }.get(args.policy, TemperaturePolicy.AUTO)
    decision = router.route(prompt=args.prompt, latency_budget_ms=args.budget, quality_target=args.quality,
        category=args.category, temperature_policy=policy)
    print(f"[ROUTE] Tier={decision.tier.value}, Model={decision.model}, T={decision.temperature:.2f} ({decision.temperature_policy.value})")
    print(f"[TWAVE] EDT={decision.use_edt} LEAD={decision.use_lead} EPR={decision.use_epr} LED={decision.use_led}")
    tracker = LandauGinzburgTrackerV2(category=args.category, enable_edt=decision.use_edt, enable_lead=decision.use_lead,
        enable_epr=decision.use_epr, enable_led=decision.use_led, enable_ckplug=decision.use_ckplug)
    tracker.set_dry_run(args.dry_run)
    for i in range(args.tokens):
        action = tracker.step(position=i, current_temperature=decision.temperature if i == 0 else action["t_eff"])
    report = tracker.get_report()
    print(f"[REPORT] tokens={report.tokens_generated}, halluc={report.hallucination_detected}, cooling={len(report.cooling_events)}")

if __name__ == "__main__":
    main()
