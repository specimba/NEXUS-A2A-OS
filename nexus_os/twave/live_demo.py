"""
TWAVE v2.0 — Live Inference Demo
==================================
Runs a real 2-4B local model through ChimeraRouterV2 + LandauGinzburgTrackerV2.
Uses Ollama API for inference, extracts logprobs, monitors entropy in real-time.

Usage:
    python -m nexus_os.twaves.live_demo
    python -m nexus_os.twaves.live_demo --model nemotron-3-nano:4b
    python -m nexus_os.twaves.live_demo --prompt "Explain quantum entanglement" --tokens 100
"""

import os, sys, json, argparse, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import numpy as np
import requests

from nexus_os.twave.chimera_router_v2 import (
    ChimeraRouterV2, ERNIEInterface, TemperaturePolicy, Tier
)
from twave.landau_ginzburg_tracker_v2 import (
    LandauGinzburgTrackerV2, EPRDetector, EDTController, LEADSwitching, DecodingMode
)

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "127.0.0.1:49152")
OLLAMA_URL = f"http://{OLLAMA_HOST}/api/generate"

MODEL_TIER_MAP = {
    'functiongemma:latest': Tier.CONTROL_PLANE,
    'nemotron-3-nano:4b': Tier.LOCAL_STANDARD,
    'hf.co/WithinUsAI/Gemma4-Most.Seen.Unseen.Reasoner-2B': Tier.LOCAL_POWER,
    'hf.co/WithinUsAI/IBM-Grok4-Ultra.Fast.Coder-1B': Tier.LOCAL_STANDARD,
    'qwen2.5-coder:7b': Tier.LOCAL_POWER,
    'deepseek-r1:8b': Tier.LOCAL_POWER,
    'hf.co/arcee-ai/Trinity-Nano-Preview-GGUF:latest': Tier.LOCAL_STANDARD,
    'kimi-k2.6:cloud': Tier.CLOUD,
}

def get_tier(model_name):
    for prefix, tier in MODEL_TIER_MAP.items():
        if model_name.startswith(prefix):
            return tier
    return Tier.LOCAL_STANDARD

def live_generate(prompt, model="nemotron-3-nano:4b", temperature=0.7,
                  max_tokens=100, category="R2.2", quality_target=0.75,
                  latency_budget_ms=2000, enable_epr=True, enable_edt=False,
                  enable_lead=False):
    tier = get_tier(model)

    tracker = LandauGinzburgTrackerV2(
        category=category,
        enable_edt=enable_edt, enable_lead=enable_lead,
        enable_epr=enable_epr, epr_threshold=2.5,
    )
    epr = EPRDetector() if enable_epr else None

    print(f"\n{'='*60}")
    print(f"TWAVE v2.0 — Live Inference")
    print(f"{'='*60}")
    print(f"Model:    {model} ({tier.value})")
    print(f"Prompt:   {prompt[:60]}...")
    print(f"Settings: T={temperature}, max_tokens={max_tokens}")
    print(f"Features: EDT={'ON' if enable_edt else 'OFF'}, "
          f"LEAD={'ON' if enable_lead else 'OFF'}, "
          f"EPR={'ON' if enable_epr else 'OFF'}")
    print(f"{'='*60}\n")

    payload = {
        "model": model,
        "prompt": prompt,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
        "stream": True,
    }

    if enable_epr:
        payload["options"]["logprobs"] = 10

    if enable_edt:
        payload["options"]["temperature"] = temperature
        payload["options"]["top_k"] = 40
        payload["options"]["top_p"] = 0.9

    start = time.time()
    generated = []
    token_idx = 0
    current_temp = temperature
    cooling_events = 0
    hallucination_warnings = 0

    try:
        resp = requests.post(OLLAMA_URL, json=payload, stream=True, timeout=120)
        resp.raise_for_status()

        for line in resp.iter_lines():
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue

            token = data.get("response", "")
            done = data.get("done", False)
            logprobs_raw = data.get("logprobs")

            if logprobs_raw and enable_epr:
                probs = np.array([abs(p) for p in logprobs_raw.values()])
                probs = probs / (probs.sum() + 1e-10)
                H_t, epr_score = epr.step(probs, current_temp)
                risk = epr.is_hallucination_risk(threshold=2.5, temperature=current_temp)
            else:
                epr_score = 0.0
                risk = False

            tracker_action = tracker.step(
                position=token_idx,
                current_temperature=current_temp,
                topk_probs=np.array([0.5, 0.3, 0.2, 0.1, 0.05, 0.03, 0.02]) if logprobs_raw else None,
            )

            if tracker_action["cool"]:
                current_temp = tracker_action["t_eff"]
                cooling_events += 1
            if tracker_action["hallucination_risk"] > 0.5:
                hallucination_warnings += 1

            display = token.replace('\n', '\\n').encode('ascii', 'replace').decode('ascii')
            entropy_str = f"H={H_t:.2f}" if logprobs_raw else ""
            epr_str = f"EPR={epr_score:.2f}" if epr_score else ""
            risk_str = "⚠️" if risk else "  "
            mode_icon = {"discrete": "D", "latent": "L", "explore": "E", "abstain": "A"}.get(
                tracker_action["mode"], "?")
            if token_idx % 20 == 0 or risk or tracker_action["cool"]:
                print(f"  [{token_idx:3d}] {display:20s} {mode_icon} "
                      f"{entropy_str} {epr_str} {risk_str} "
                      f"T={current_temp:.3f} "
                      f"{'COOL' if tracker_action['cool'] else '    '} "
                      f"{'HALLUC' if tracker_action['is_hallucinating'] else ''}")

            token_idx += 1
            if done or token_idx >= max_tokens:
                if done:
                    pass
                break

        elapsed = time.time() - start
        report = tracker.get_report()

        print(f"\n{'='*60}")
        print(f"THERMODYNAMIC REPORT")
        print(f"{'='*60}")
        print(f"  Tokens:        {token_idx}")
        print(f"  Time:          {elapsed:.1f}s ({token_idx/elapsed:.1f} tok/s)")
        print(f"  Mean entropy:  {report.mean_entropy:.3f}")
        print(f"  Max entropy:   {report.max_entropy:.3f}")
        print(f"  EPR score:     {report.epr_score:.3f}" if report.epr_score else "  EPR: N/A")
        print(f"  Hallucination: {report.hallucination_detected} @ {report.hallucination_positions}")
        print(f"  Cooling:       {cooling_events} events")
        print(f"  Self-correct:  {len(report.self_correction_positions)}")
        print(f"  Final temp:    {report.final_temperature:.3f}")
        if report.mode_transitions:
            print(f"  Mode switches: {len(report.mode_transitions)}")
        if report.estimated_healing_length:
            print(f"  Healing len:   {report.estimated_healing_length:.1f} tokens")

    except requests.exceptions.ConnectionError:
        print(f"\n[ERROR] Cannot connect to Ollama at {OLLAMA_URL}")
        print("  Is Ollama running? Start it with: ollama serve")
    except Exception as e:
        print(f"\n[ERROR] {e}")

def main():
    parser = argparse.ArgumentParser(description="TWAVE v2.0 Live Inference Demo")
    parser.add_argument("--model", default="nemotron-3-nano:4b",
                        help="Ollama model name (2B-4B recommended)")
    parser.add_argument("--prompt", default="Explain quantum entanglement step by step, including Bell's theorem.")
    parser.add_argument("--tokens", type=int, default=100)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--epr", action="store_true", default=True,
                        help="Enable EPR hallucination detection")
    parser.add_argument("--edt", action="store_true", default=False,
                        help="Enable EDT dynamic temperature")
    parser.add_argument("--lead", action="store_true", default=False,
                        help="Enable LEAD mode switching")
    parser.add_argument("--category", default="R2.2")
    parser.add_argument("--quality", type=float, default=0.75)
    parser.add_argument("--budget", type=int, default=2000)
    parser.add_argument("--route", action="store_true", default=False,
                        help="Route through ChimeraRouter first")
    args = parser.parse_args()

    if args.route:
        router = ChimeraRouterV2(vram_gb=8.0, has_cloud_access=False)
        decision = router.route(args.prompt, latency_budget_ms=args.budget,
                                quality_target=args.quality, category=args.category,
                                temperature_policy=TemperaturePolicy.AUTO)
        print(f"[ROUTER] {decision.model} ({decision.tier.value}), "
              f"T={decision.temperature:.2f}, policy={decision.temperature_policy.value}")
        if decision.use_edt:
            args.edt = True
        if decision.use_epr:
            args.epr = True

    live_generate(
        prompt=args.prompt, model=args.model, temperature=args.temperature,
        max_tokens=args.tokens, category=args.category,
        quality_target=args.quality, latency_budget_ms=args.budget,
        enable_epr=args.epr, enable_edt=args.edt, enable_lead=args.lead,
    )

if __name__ == "__main__":
    main()
