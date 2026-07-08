#!/usr/bin/env python3
# CANARY: f5ffaeb12ac95c3b54719ef64bb59655
"""
NEXUS OS — Hardened DPO Preference Dataset Compiler
===================================================
Reads the 1,000 scenarios generated in session06, parses prompt, dpo_chosen,
and dpo_rejected fields, formats them in Qwen-2.5 ChatML format, and compiles
them into the target preference dataset.
"""

import os
import sys
import json
from pathlib import Path

# Paths
REPO_ROOT = Path(__file__).resolve().parent.parent
INPUT_PATH = REPO_ROOT / "research" / "Papers" / "RED-BLUE-PURPLE" / "scenarios_001-1000_EN.jsonl"
# Fallback to session06 path if not found in RED-BLUE-PURPLE
if not INPUT_PATH.exists():
    INPUT_PATH = Path(r"C:\Users\speci.000\Downloads\ERNIEsupramacyRESEARCHpaper01\session06\scenarios_001-1000_EN.jsonl")

OUTPUT_PATH = REPO_ROOT / "datasets" / "ernie" / "dpo_preference_dataset.json"

try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

def format_chatml(prompt, response, im_start="<|im_start|>", im_end="<|im_end|>"):
    """
    Format DPO pair in Qwen3.5 ChatML format.
    Structure: <|im_start|>system\nYou are a helpful assistant.<|im_end|>\n<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n{response}<|im_end|>
    """
    system = "You are a helpful assistant."
    messages = [
        f"{im_start}system\n{system}{im_end}",
        f"{im_start}user\n{prompt}{im_end}",
        f"{im_start}assistant\n{response}{im_end}"
    ]
    return "".join(messages)

def main():
    print("=" * 70)
    print("NEXUS — DPO PREFERENCE DATASET COMPILER")
    print("=" * 70)
    print(f"Reading input: {INPUT_PATH}")
    
    if not INPUT_PATH.exists():
        print(f"[FAIL] Input scenario file not found: {INPUT_PATH}")
        sys.exit(1)

    os.makedirs(OUTPUT_PATH.parent, exist_ok=True)
    
    compiled = []
    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            try:
                record = json.loads(line.strip())
                prompt = record.get("prompt", "")
                chosen = record.get("dpo_chosen", "")
                rejected = record.get("dpo_rejected", "")
                
                if not prompt or not chosen or not rejected:
                    continue
                
                # Format to ChatML DPO preference structure
                compiled.append({
                    "prompt": format_chatml(prompt, ""),
                    "chosen": chosen,
                    "rejected": rejected
                })
            except Exception as e:
                print(f"[WARNING] Line {i} parse error: {e}")

    # Save to JSON
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(compiled, f, indent=2, ensure_ascii=False)
        
    print(f"[OK] Successfully compiled {len(compiled)} DPO preference pairs!")
    print(f"[OK] Exported dataset to: {OUTPUT_PATH}")
    print("=" * 70)

if __name__ == "__main__":
    main()
