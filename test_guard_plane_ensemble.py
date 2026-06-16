#!/usr/bin/env python3
"""
Test the actual guard plane (with Meta-Attack + RefusalMancer + ensemble modes)
using the new Gemma 4 E2B added to registry.
Compares 3 modes: weighted, strict, sensitive.
"""
import json
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "nexus_os", "security"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "datasets"))

from guard_plane import SLMGuardPlane, ALL_BENIGN, load_tamas, load_v7, BOUNCER_PROMPT

def main():
    print("="*70)
    print("GUARD PLANE TEST: 3 ensemble modes with Gemma 4 E2B added")
    print("="*70)
    
    # Load queries
    benign = ALL_BENIGN[:30]
    attacks = (load_tamas(8) + load_v7(15))[:20]
    
    print(f"Benign: {len(benign)} | Attacks: {len(attacks)}")
    
    results = {}
    for mode in ["weighted", "strict", "sensitive"]:
        print(f"\n{'='*70}\nMode: {mode}\n{'='*70}")
        plane = SLMGuardPlane(ensemble_mode=mode)
        
        fp, tn, fn, tp = 0, 0, 0, 0
        start = time.time()
        
        # Test benign
        for i, item in enumerate(benign):
            q = item["query"]
            r = plane.evaluate(q, attack_type="unknown", is_benign=True)
            v = r["verdict"]
            if v == "unsafe": fp += 1
            elif v == "safe": tn += 1
        
        # Test attacks
        for i, q in enumerate(attacks):
            r = plane.evaluate(q, attack_type="tamas" if i < 8 else "v7_novel", is_benign=False)
            v = r["verdict"]
            if v == "unsafe": tp += 1
            elif v == "safe": fn += 1
        
        elapsed = time.time() - start
        total = len(benign) + len(attacks)
        acc = (tp + tn) / total
        fp_rate = fp / len(benign)
        fn_rate = fn / len(attacks)
        results[mode] = {"fp": fp, "tn": tn, "tp": tp, "fn": fn, "accuracy": acc, "fp_rate": fp_rate, "fn_rate": fn_rate, "time": elapsed}
        print(f"  FP={fp}/{len(benign)} ({fp_rate*100:.1f}%)  FN={fn}/{len(attacks)} ({fn_rate*100:.1f}%)  Acc={acc*100:.1f}%  Time={elapsed:.1f}s")
    
    # Summary
    print(f"\n{'='*70}\nSUMMARY\n{'='*70}")
    print(f"{'Mode':<15} {'FP%':>6} {'FN%':>6} {'Acc%':>6} {'Time':>8}")
    print("-"*70)
    for mode, r in results.items():
        print(f"{mode:<15} {r['fp_rate']*100:>5.1f}% {r['fn_rate']*100:>5.1f}% {r['accuracy']*100:>5.1f}% {r['time']:>7.1f}s")
    
    # Find best
    best = max(results.items(), key=lambda x: x[1]["accuracy"])
    print(f"\n[WINNER] {best[0]} mode: {best[1]['accuracy']*100:.1f}% acc")
    
    with open(os.path.join(os.path.dirname(__file__), "datasets", "guard_plane_ensemble_test.json"), "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved to datasets/guard_plane_ensemble_test.json")

if __name__ == "__main__":
    main()
