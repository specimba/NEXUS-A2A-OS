#!/usr/bin/env python3
"""
scripts/dynamic_merge_optimizer.py - Dynamic Mergekit Recipe Optimizer
====================================================================
An automated script that periodically parses empirical adversarial bypass logs
and model benchmark metrics to dynamically synthesize optimized Mergekit recipes
(TIES/SLERP v3 configurations).

Calculates weight bias adjustments:
  - Higher bypass rate in 'synonym_mutation' triggers higher density/weight for the coder model.
  - Higher bypass rate in 'pattern_mirror' or general red-teaming triggers higher weight for the special-virus bouncer.
  - Baseline compliance prevents over-censorship by maintaining general reasoning weights.
"""

import os
import sys
import json
from pathlib import Path

try:
    from protected_workload_gate import protected_workload_status
except Exception:
    protected_workload_status = None

# Paths
JAILBREAKS_PATH = Path("research/Papers/RED-BLUE-PURPLE/autonomous_jailbreaks.jsonl")
ARENA_METRICS_PATH = Path("datasets/ernie/arena_metrics.json")
DICE_RESULTS_PATH = Path("datasets/ernie/dice_probe_results.json")

TIES_RECIPE_PATH = Path("models/qwen2.5-1.5b-ties-merge-v3.yml")
SLERP_RECIPE_PATH = Path("models/qwen2.5-1.5b-slerp-merge-v3.yml")

# Safe outputs
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

def clean_ascii(text):
    if text is None:
        return ""
    return str(text).encode('ascii', errors='replace').decode('ascii')

def parse_logs():
    bypass_count = 0
    total_count = 0
    tactic_bypasses = {}
    tactic_totals = {}
    
    if JAILBREAKS_PATH.exists():
        try:
            with open(JAILBREAKS_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        record = json.loads(line)
                        total_count += 1
                        tactic = record.get("applied_tactic", "unknown")
                        is_bypass = record.get("is_bypass", False)
                        
                        tactic_totals[tactic] = tactic_totals.get(tactic, 0) + 1
                        if is_bypass:
                            bypass_count += 1
                            tactic_bypasses[tactic] = tactic_bypasses.get(tactic, 0) + 1
                    except:
                        pass
        except Exception as e:
            print(f"[WARNING] Error reading bypass logs: {e}")
            
    # Calculate bypass rates per tactic
    bypass_rates = {}
    for t in tactic_totals:
        bypass_rates[t] = tactic_bypasses.get(t, 0) / tactic_totals[t]
        
    return {
        "total_records": total_count,
        "total_bypasses": bypass_count,
        "overall_bypass_rate": bypass_count / total_count if total_count > 0 else 0.0,
        "bypass_rates_per_tactic": bypass_rates
    }

def main():
    print("[OK] Starting NEXUS OS Dynamic Mergekit Recipe Optimizer...")
    print(f"[OK] Analyzing logs from: {JAILBREAKS_PATH}")

    if protected_workload_status is not None:
        status = protected_workload_status()
        if status["should_pause"]:
            print(
                "[SAFETY] Protected workload gate active; skipping recipe write. "
                f"reason={status['reason']} active={status.get('active_processes', [])}"
            )
            return
    
    analysis = parse_logs()
    print(f"[OK] Total logged attempts parsed: {analysis['total_records']}")
    print(f"[OK] Overall bypass rate: {analysis['overall_bypass_rate']*100.0:.2f}%")
    
    # Baseline weights
    base_weight = 0.40       # qwen2.5-1.5b-instruct
    coder_weight = 0.30      # qwen2.5-coder-1.5b-instruct
    virus_weight = 0.30      # special-virus-3.2-1B
    
    density = 0.55
    slerp_t = 0.45
    
    # 1. Tactic-based weight updates
    rates = analysis["bypass_rates_per_tactic"]
    
    if rates:
        print("[OK] Tactic Bypass Analysis:")
        for t, rate in rates.items():
            print(f"  - {t:<24}: {rate*100.0:.2f}%")
            
        # Tactic 1: synonym_mutation & obfuscation bypasses represent lexical/token blindness.
        # Action: Increase Coder weights.
        synonym_rate = rates.get("synonym_mutation", 0.0)
        skill_rate = rates.get("skill_inject", 0.0)
        coder_trigger_rate = max(synonym_rate, skill_rate)
        if coder_trigger_rate > 0.15:
            shift = min(0.15, coder_trigger_rate * 0.4)
            coder_weight += shift
            base_weight -= shift * 0.5
            virus_weight -= shift * 0.5
            density = min(0.70, density + 0.05)
            print(f"[TUNING] High lexical/skill injection leakage ({coder_trigger_rate*100.0:.1f}%). Increasing Coder model weight by +{shift:.3f} and TIES density.")
            
        # Tactic 2: Direct pattern mirroring or trojan whisper guidance.
        # Action: Increase special-virus weight (containment).
        pattern_rate = rates.get("pattern_mirror", 0.0)
        trojan_rate = rates.get("trojan_whisper", 0.0)
        critical_red_rate = max(pattern_rate, trojan_rate)
        if critical_red_rate > 0.10:
            shift = min(0.20, critical_red_rate * 0.5)
            virus_weight += shift
            base_weight -= shift * 0.5
            coder_weight -= shift * 0.5
            slerp_t = min(0.65, slerp_t + 0.08)
            print(f"[TUNING] High adversarial/trojan whisper leakage ({critical_red_rate*100.0:.1f}%). Boosting security Specialist weight by +{shift:.3f} and SLERP interpolation.")
            
    # 2. DICE-Guided Safety Representation Constraints
    dice_results = None
    if DICE_RESULTS_PATH.exists():
        try:
            with open(DICE_RESULTS_PATH, "r", encoding="utf-8") as f:
                dice_results = json.load(f)
        except Exception as e:
            print(f"[WARNING] Error reading DICE results: {e}")
            
    if dice_results:
        benign_avg = dice_results.get("benign_distance_average", 75.0)
        max_euclidean = dice_results.get("max_representation_distance", 112.0)
        
        # Calculate adversarial representation average
        adv_distances = []
        for r in dice_results.get("results_by_prompt", []):
            if r.get("label") == "unsafe":
                adv_distances.append(r.get("key_layer_distance", 0.0))
        adv_avg = sum(adv_distances) / len(adv_distances) if adv_distances else 150.0
        
        print(f"[OK] DICE Diagnostic Diagnostics Integrated:")
        print(f"  - Probed Benign Average Distance : {benign_avg:.4f}")
        print(f"  - Probed Unsafe Average Distance : {adv_avg:.4f}")
        
        # A. Over-Censorship Prevention: If benign representation distance is too high, 
        # instructions are being distorted. Reduce specialist weight, boost base model.
        if benign_avg > 90.0:
            shift = min(0.12, (benign_avg - 90.0) * 0.005)
            virus_weight = max(0.15, virus_weight - shift)
            base_weight += shift
            print(f"[TUNING] DICE Over-Censorship constraint active: benign_avg ({benign_avg:.2f}) > 90.0. Reducing specialist weight by -{shift:.3f} to protect utility.")
            
        # B. Safety alignment under-fitting: If unsafe inputs do not trigger significant representation shifts, 
        # safety alignment is too weak. Boost specialist model.
        if adv_avg < 100.0:
            shift = min(0.15, (100.0 - adv_avg) * 0.008)
            virus_weight += shift
            base_weight -= shift * 0.5
            coder_weight -= shift * 0.5
            density = min(0.70, density + 0.05)
            print(f"[TUNING] DICE Under-alignment constraint active: adv_avg ({adv_avg:.2f}) < 100.0. Boosting specialist weight by +{shift:.3f} and TIES density.")

    # 3. Causal Progressive Weight Fusion (FuseFL-inspired)
    # Prevent catastrophic model parameter distortion by forcing bounded parameters
    virus_weight = max(0.15, min(0.65, virus_weight))
    base_weight = max(0.15, min(0.65, base_weight))
    coder_weight = max(0.15, min(0.65, coder_weight))
    
    total = base_weight + coder_weight + virus_weight
    base_weight = round(base_weight / total, 3)
    coder_weight = round(coder_weight / total, 3)
    virus_weight = round(virus_weight / total, 3)
    
    print(f"[OK] Dynamically Optimized Merge Weights:")
    print(f"  - qwen2.5-1.5b-instruct       : {base_weight:.3f}")
    print(f"  - qwen2.5-coder-1.5b-instruct : {coder_weight:.3f}")
    print(f"  - special-virus-3.2-1B        : {virus_weight:.3f}")
    print(f"  - TIES Density Configuration  : {density:.2f}")
    print(f"  - SLERP Interpolation (t)     : {slerp_t:.2f}")
    
    # 1. Synthesize TIES Mergekit Recipe v3
    ties_recipe = f"""# TIES v3 Merge Configuration Recipe - Synthesized Dynamically
# Based on continuous Chaos Arena empirical vulnerabilities
models:
  - model: Qwen/Qwen2.5-1.5B-Instruct
    parameters:
      weight: {base_weight}
      density: {density:.2f}
  - model: Qwen/Qwen2.5-Coder-1.5B-Instruct
    parameters:
      weight: {coder_weight}
      density: {density:.2f}
  - model: special-virus:latest
    parameters:
      weight: {virus_weight}
      density: {density:.2f}
merge_method: ties
base_model: Qwen/Qwen2.5-1.5B-Instruct
parameters:
  normalize: true
  int8_mask: true
dtype: float16
"""

    # 2. Synthesize SLERP Mergekit Recipe v3
    slerp_recipe = f"""# SLERP v3 Merge Configuration Recipe - Synthesized Dynamically
# Blends general instruction following with red-team security specialist
slices:
  - sources:
      - model: Qwen/Qwen2.5-1.5B-Instruct
        layer_range: [0, 28]
      - model: special-virus:latest
        layer_range: [0, 28]
merge_method: slerp
base_model: Qwen/Qwen2.5-1.5B-Instruct
parameters:
  t:
    - filter: self_attn
      value: [0.0, {slerp_t}, {slerp_t}, 1.0]
    - filter: mlp
      value: [0.0, {1.0 - slerp_t}, {slerp_t}, 1.0]
    - value: {slerp_t}
dtype: float16
"""

    # Save configs
    TIES_RECIPE_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    with open(TIES_RECIPE_PATH, "w", encoding="utf-8") as tf:
        tf.write(ties_recipe)
    print(f"[PASS] Optimized TIES Merge Recipe v3 written: {TIES_RECIPE_PATH}")
    
    with open(SLERP_RECIPE_PATH, "w", encoding="utf-8") as sf:
        sf.write(slerp_recipe)
    print(f"[PASS] Optimized SLERP Merge Recipe v3 written: {SLERP_RECIPE_PATH}")

if __name__ == "__main__":
    main()
