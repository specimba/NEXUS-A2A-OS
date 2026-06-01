#!/usr/bin/env python3
"""
NEXUS OS v2.0 CLI
=================
Commands:
    nexus-os route  "prompt" [--vram 8] [--budget 2000] [--quality 0.75]
    nexus-os track  --tokens 50 --category F1.1 --temperature 0.7
    nexus-os demo   [--prompt "..."] [--ernie] [--policy auto]
"""
import sys, argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from nexus_os.chimera_router_v2 import ChimeraRouterV2, ERNIEInterface, ERNIESuggestion, TemperaturePolicy, Tier
from twave.landau_ginzburg_tracker_v2 import LandauGinzburgTrackerV2


def cmd_route(args):
    router = ChimeraRouterV2(vram_gb=args.vram, has_cloud_access=args.cloud,
                              available_tiers=[Tier.CONTROL_PLANE, Tier.LOCAL_STANDARD, Tier.LOCAL_POWER])
    policy = {
        "auto": TemperaturePolicy.AUTO, "fixed": TemperaturePolicy.FIXED,
        "edt": TemperaturePolicy.EDT, "ead": TemperaturePolicy.EAD,
        "lead": TemperaturePolicy.LEAD, "ernie": TemperaturePolicy.ERNIE,
    }.get(args.policy, TemperaturePolicy.AUTO)
    decision = router.route(args.prompt, latency_budget_ms=args.budget,
                             quality_target=args.quality, category=args.category,
                             temperature_policy=policy)
    print(json.dumps({
        "tier": decision.tier.value,
        "model": decision.model,
        "temperature": round(decision.temperature, 3),
        "policy": decision.temperature_policy.value,
        "expected_latency_ms": round(decision.expected_latency_ms, 0),
        "expected_quality": round(decision.expected_quality, 2),
        "max_tokens": decision.budget.max_tokens,
        "features": {
            "edt": decision.use_edt, "lead": decision.use_lead,
            "epr": decision.use_epr, "led": decision.use_led,
            "ckplug": decision.use_ckplug, "attn_divergence": decision.use_attention_divergence,
        },
        "confidence": round(decision.confidence, 2),
        "reason": decision.reason,
    }, indent=2))


def cmd_track(args):
    tracker = LandauGinzburgTrackerV2(
        category=args.category,
        enable_edt=args.edt, enable_lead=args.lead,
        enable_epr=args.epr, enable_led=args.led,
        enable_ckplug=args.ckplug,
    )
    tracker.set_dry_run(args.dry_run)
    for i in range(args.tokens):
        tracker.step(position=i, current_temperature=args.temperature)
    report = tracker.get_report()
    print(json.dumps({
        "tokens": report.tokens_generated,
        "hallucination_detected": report.hallucination_detected,
        "hallucination_positions": report.hallucination_positions,
        "cooling_events": len(report.cooling_events),
        "mean_entropy": round(report.mean_entropy, 3),
        "max_entropy": round(report.max_entropy, 3),
        "epr_score": round(report.epr_score, 3) if report.epr_score else None,
        "mode_transitions": len(report.mode_transitions) if report.mode_transitions else 0,
    }, indent=2))


def cmd_demo(args):
    from nexus_os.demo_e2e_v2 import main as e2e_main
    sys.argv = ["demo_e2e_v2", "--prompt", args.prompt, "--vram", str(args.vram),
                "--budget", str(args.budget), "--quality", str(args.quality),
                "--category", args.category, "--policy", args.policy,
                "--tokens", str(args.tokens)]
    e2e_main()


def main():
    parser = argparse.ArgumentParser(description="NEXUS OS v2.0 CLI")
    subparsers = parser.add_subparsers(dest="cmd")

    route_parser = subparsers.add_parser("route", help="Route a prompt")
    route_parser.add_argument("prompt")
    route_parser.add_argument("--vram", type=float, default=8.0)
    route_parser.add_argument("--budget", type=float, default=2000.0)
    route_parser.add_argument("--quality", type=float, default=0.75)
    route_parser.add_argument("--category", default="default")
    route_parser.add_argument("--policy", default="auto")
    route_parser.add_argument("--cloud", action="store_true", default=False)

    track_parser = subparsers.add_parser("track", help="Run TWAVE tracker")
    track_parser.add_argument("--tokens", type=int, default=30)
    track_parser.add_argument("--category", default="F1.1")
    track_parser.add_argument("--temperature", type=float, default=0.7)
    track_parser.add_argument("--dry-run", action="store_true", default=True)
    track_parser.add_argument("--edt", action="store_true", default=True)
    track_parser.add_argument("--lead", action="store_true", default=True)
    track_parser.add_argument("--epr", action="store_true", default=True)
    track_parser.add_argument("--led", action="store_true", default=False)
    track_parser.add_argument("--ckplug", action="store_true", default=False)

    demo_parser = subparsers.add_parser("demo", help="Full E2E demo")
    demo_parser.add_argument("--prompt", default="Explain quantum entanglement step by step.")
    demo_parser.add_argument("--vram", type=float, default=8.0)
    demo_parser.add_argument("--budget", type=float, default=2000.0)
    demo_parser.add_argument("--quality", type=float, default=0.75)
    demo_parser.add_argument("--category", default="R2.2")
    demo_parser.add_argument("--policy", default="auto")
    demo_parser.add_argument("--tokens", type=int, default=50)

    args = parser.parse_args()
    if args.cmd == "route": cmd_route(args)
    elif args.cmd == "track": cmd_track(args)
    elif args.cmd == "demo": cmd_demo(args)
    else: parser.print_help()


if __name__ == "__main__":
    import json
    main()
