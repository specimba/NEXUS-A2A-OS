#!/usr/bin/env python3
import os
import re

print("🛡️ Applying METAresearch Hard Wall Defenses to Trust Scoring...")

ts_path = os.path.join("src", "nexus_os", "governor", "trust_scoring.py")

if os.path.exists(ts_path):
    with open(ts_path, "r", encoding="utf-8") as f:
        code = f.read()

    # Inject the math functions if they don't exist
    if "def apply_logistic_scaling" not in code:
        hardwall_math = """
import math
import time

def apply_logistic_scaling(raw_score: float) -> float:
    \"\"\"
    Applies $f(T) = 1/(1+e^{-(T-50)/10})$ to prevent linear trust inflation.
    Assuming raw_score is normalized 0.0 to 1.0 internally, we map it to the 0-100 scale for the logistic curve,
    then normalize back to 0.0-1.0.
    \"\"\"
    t_val = raw_score * 100.0
    logistic_val = 1.0 / (1.0 + math.exp(-(t_val - 50.0) / 10.0))
    return round(logistic_val, 4)

def apply_temporal_decay(score: float, last_active_ts: float, decay_rate: float = 0.05) -> float:
    \"\"\"
    Trust rots over time. Applies exponential decay based on hours passed.
    \"\"\"
    if not last_active_ts:
        return score
    hours_passed = (time.time() - last_active_ts) / 3600.0
    decayed_score = score * math.exp(-decay_rate * hours_passed)
    return round(decayed_score, 4)
"""
        # Inject after imports
        code = re.sub(r'^(.*?)(class AgentCard:)', r'\1' + hardwall_math + r'\n\2', code, count=1, flags=re.DOTALL)
        
        with open(ts_path, "w", encoding="utf-8") as f:
            f.write(code)
        print("[✅] Hard Wall Mathematics (Logistic Scaling & Temporal Decay) injected.")
    else:
        print("[OK] Hard Wall Mathematics already present.")

print("\n[🚀] Mathematical limits applied. Run: python -m pytest tests/governor/ -q --tb=short")