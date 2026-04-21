#!/usr/bin/env python3
import os
import re

print("🚑 Healing Syntax Error in trust_scoring.py...")

ts_path = os.path.join("src", "nexus_os", "governor", "trust_scoring.py")
if os.path.exists(ts_path):
    with open(ts_path, "r", encoding="utf-8") as f:
        code = f.read()

    # 1. Surgically remove the misplaced math block
    bad_block_pattern = r'\n*import math\nimport time\n.*?def apply_temporal_decay.*?return round\(decayed_score, 4\)\n*'
    code = re.sub(bad_block_pattern, '\n', code, flags=re.DOTALL)

    # 2. Heal the @dataclass decorator connection (remove rogue spaces between them)
    code = re.sub(r'@dataclass\s+class AgentCard:', '@dataclass\nclass AgentCard:', code)

    # 3. Safely append the math functions to the VERY END of the file
    safe_math = """
import math
import time

def apply_logistic_scaling(raw_score: float) -> float:
    t_val = raw_score * 100.0
    logistic_val = 1.0 / (1.0 + math.exp(-(t_val - 50.0) / 10.0))
    return round(logistic_val, 4)

def apply_temporal_decay(score: float, last_active_ts: float, decay_rate: float = 0.05) -> float:
    if not last_active_ts:
        return score
    hours_passed = (time.time() - last_active_ts) / 3600.0
    decayed_score = score * math.exp(-decay_rate * hours_passed)
    return round(decayed_score, 4)
"""
    if "def apply_logistic_scaling" not in code:
        code += "\n" + safe_math

    with open(ts_path, "w", encoding="utf-8") as f:
        f.write(code)
    
    print("[✅] Syntax Error healed! Decorator restored.")

print("\n[🚀] Run tests: python -m pytest tests/ -q --tb=short")