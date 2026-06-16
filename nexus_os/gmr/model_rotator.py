#!/usr/bin/env python3
"""
NEXUS GMR-Smart Model Rotator
==============================
Attack-type-driven model rotation with anchor-model pinning.

Architecture:
  L0 (always-loaded, ~400MB)  : BashGemma 270M — command intent classifier (fast-path)
  L1 (always-loaded, ~350MB)  : FunctionGemma 270M — function-call safety validator
  L2 (on-demand, ~600MB)      : GLiGuard-300M — prompt harmfulness classifier
  L3 (on-demand, ~600MB)      : Arch-Guard — jailbreak specialist
  L4 (CPU, 0MB)               : Meta-attack detector — regex pre-filter (46 categories)

VRAM budget:
  Always-loaded:       750MB  (L0 + L1)
  Peak (L0+L1+L2):    1350MB
  Max (any 2):         ~1350MB
  Under 2GB constraint: YES

Rotation logic:
  attack_type → preferred_guard → load if not already → swap out lowest-weight model
  Anchored models (L0/L1) never swap.
  On-demand models (L2/L3) rotate based on query classification + recent FP/FN history.
"""

import json
import time
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone

# ── Attempt Ollama import ────────────────────────────────────────────────
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# ── Paths ────────────────────────────────────────────────────────────────
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
NEXUS_ROOT = os.path.abspath(os.path.join(THIS_DIR, "..", ".."))
OLLAMA_API = os.environ.get("OLLAMA_API", "http://127.0.0.1:11435/api/generate")
VRAM_GB_TOTAL = 8.188
VRAM_GB_USABLE = 6.6
VRAM_MB_USABLE = int(VRAM_GB_USABLE * 1024)
MAX_LOADED = 2  # from KAIJU config

# ── Model VRAM estimates (MB) ────────────────────────────────────────────
VRAM_ESTIMATES = {
    "bashgemma-270m-merged":       400,
    "functiongemma:latest":        350,
    "special-virus:latest":        900,
    "qwen2.5-guard-q4:latest":     700,
    "llama-guard3:1b":            1100,
    "gemma4-e2b-guard":           1800,
    "gemma2-2b-abliterated":      1400,
    "models/gemma2-2b-abliterated": 1400,
    "LFM2.5-1.2B-Instruct":        800,
    "Neo_T-Virus-3.2-1B":          900,
    "models/qwen2.5-1.5b-guard-merged": 750,
    "gliguard-300m":               500,
    "arch-guard-300m":             600,
    "llama-prompt-guard-2-86m":    150,
}

# ── Attack type → preferred guard model ──────────────────────────────────
# Derived from STRES6 (6 attack types) + STRES5 (10 dimensions) + guard_plane classifiers
ATTACK_TYPE_ROUTING = {
    # STRES6 attack types
    "impersonation":   "arch-guard-300m",       # identity spoofing → jailbreak specialist
    "collusion":       "gemma4-e2b-guard",      # multi-agent conspiracy → semantic reasoning
    "distraction":     "qwen2.5-guard-q4:latest", # noise flooding → lexical adversarial
    "task_poison":     "special-virus:latest",  # payload injection → current primary
    "tool_poison":     "bashgemma-270m-merged", # tool-call corruption → command intent
    "free_rider":      "functiongemma:latest",  # exploitation of other agents → function validator

    # STRES5 attack dimensions
    "supply_chain":    "special-virus:latest",
    "payload_conversion": "qwen2.5-guard-q4:latest",
    "mcp_tool_poison": "bashgemma-270m-merged",
    "pdf_injection":   "gemma4-e2b-guard",
    "prompt_injection":"arch-guard-300m",
    "jailbreak":       "arch-guard-300m",
    "role_play_override": "arch-guard-300m",
    "system_extract":  "llama-guard3:1b",
    "data_exfil":      "special-virus:latest",
    "privilege_esc":   "special-virus:latest",

    # Fallback
    "unknown":         "qwen2.5-guard-q4:latest",
    "tamas":           "special-virus:latest",
    "v7_novel":        "gemma4-e2b-guard",
}

# ── Models that rotate (not anchored) ────────────────────────────────────
ROTATING_POOL = [
    "special-virus:latest",
    "qwen2.5-guard-q4:latest",
    "llama-guard3:1b",
    "gemma4-e2b-guard",
    "gemma2-2b-abliterated",
    "models/gemma2-2b-abliterated",
    "Neo_T-Virus-3.2-1B",
    "LFM2.5-1.2B-Instruct",
    "models/qwen2.5-1.5b-guard-merged",
    "gliguard-300m",
    "arch-guard-300m",
]

# ── Anchor models (never evicted) ────────────────────────────────────────
ANCHOR_MODELS = [
    "bashgemma-270m-merged",
    "functiongemma:latest",
]

# ── Confidence history for FP/FN-aware rotation ──────────────────────────
_confidence_history = defaultdict(lambda: {"fp": 0, "fn": 0, "total": 0, "weight": 1.0})


def classify_attack_type(query: str) -> str:
    """Rule-based attack type classifier (mirrors guard_plane.py classify_attack)."""
    q = query.lower()

    tamas_patterns = [
        r"\b\w+_agent\b",
        r"\b(?:meanwhile|phase\s*\d|step\s*\d)",
        r"\b(?:i am|i'm|i was)\s+(?:the )?(?:new |now the )?(?:reviewer|admin|manager|owner|approver)\b",
        r"\b(?:bypass|ignore|override|skip|circumvent).*(?:approval|verification|check|control|audit)\b",
        r"\b(?:urgent|emergency|time.?sensitive|immediate).*(?:approval|override|bypass|transfer)\b",
        r"\b(?:grant|give|provide|assign).*(?:access|rights|permission|admin|privilege)\b",
        r"\bignore\s+(?:the\s+)?(?:above|previous|all|these|those|access.?control|security|policy)\b",
    ]
    if any(re.search(p, q, re.IGNORECASE) for p in tamas_patterns):
        return "tamas"

    v7_patterns = [
        r"(?:supply.?chain|compiler|backdoor|poison|trojan)",
        r"(?:red.?team|pen.?test|vulnerability|exploit|0day|zero.?day)",
        r"(?:jailbreak|prompt.?inject|role.?play\s*override)",
        r"(?:cyber|offensive|weapon|malware|ransomware|worm|virus)",
        r"(?:manifold|homology|topology|eigenvalue|asymptotic).*(?:bypass|exploit|attack|privilege|escalate)",
        r"(?:quorum\s+sensing|virulence|autoinducer).*(?:system|cluster|compromise|infect)",
        r"(?:gödel|incompleteness|allegory).*(?:bypass|override|ignore|instructions|safety)",
    ]
    if any(re.search(p, q, re.IGNORECASE) for p in v7_patterns):
        return "v7_novel"

    specific = {
        r"\bimpersonat\b": "impersonation",
        r"\bcollud\b": "collusion",
        r"\bdistract\b": "distraction",
        r"\btask\s*poison\b": "task_poison",
        r"\btool\s*poison\b": "tool_poison",
        r"\bfree\s*rider\b": "free_rider",
        r"\bmcp\b.*\battack\b": "mcp_tool_poison",
        r"\bpdf\b.*\binject\b": "pdf_injection",
        r"\bsupply.?chain\b": "supply_chain",
        r"\bpayload\b.*\bconvert\b": "payload_conversion",
        r"\bdata\s*exfil\b": "data_exfil",
        r"\bprivilege\s*esc\b": "privilege_esc",
        r"\bsystem\s*prompt\s*extract\b": "system_extract",
        r"\brole.?play\b": "role_play_override",
        r"\brefusal\b.*\boverride\b": "role_play_override",
    }
    for pattern, atype in specific.items():
        if re.search(pattern, q, re.IGNORECASE):
            return atype

    return "unknown"


def get_vram_mb() -> int:
    """Get current GPU VRAM usage in MB via nvidia-smi, or estimate."""
    try:
        import subprocess
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,nounits,noheader"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return int(result.stdout.strip().split("\n")[0])
    except Exception:
        pass
    return 0


def get_loaded_models() -> list:
    """Query Ollama for currently loaded models."""
    if not HAS_REQUESTS:
        return []
    try:
        resp = requests.get("http://127.0.0.1:11435/api/ps", timeout=5)
        if resp.ok:
            data = resp.json()
            return [m["name"] for m in data.get("models", [])]
    except Exception:
        pass
    return []


def estimate_vram_for_models(models: list) -> int:
    """Estimated total VRAM for a list of model keys."""
    total = 0
    for m in models:
        total += VRAM_ESTIMATES.get(m, 750)  # default 750MB if unknown
    return total


def select_rotating_model(attack_type: str, available: list) -> str:
    """
    GMR-smart selection: pick the best rotating model for the attack type,
    weighted by recent FP/FN performance.
    """
    preferred = ATTACK_TYPE_ROUTING.get(attack_type, "qwen2.5-guard-q4:latest")

    # If preferred is in the rotating pool and available, use it
    if preferred in available:
        hist = _confidence_history[preferred]
        fp_rate = hist["fp"] / max(hist["total"], 1)
        # Penalize models with high FP rates
        effective_weight = max(0.2, 1.0 - fp_rate * 2.0)
        return preferred, effective_weight

    # Otherwise pick the available rotating model with best (low FP, high total) score
    best_model = None
    best_score = -1
    for m in available:
        h = _confidence_history[m]
        fp_rate = h["fp"] / max(h["total"], 1)
        fn_rate = h["fn"] / max(h["total"], 1)
        score = (h["total"] * 0.3) + ((1.0 - fp_rate) * 0.4) + ((1.0 - fn_rate) * 0.3)
        if score > best_score:
            best_score = score
            best_model = m
    return best_model or available[0], 1.0


def rotate_models(attack_type: str, current_loaded: list) -> dict:
    """
    GMR-smart rotation decision.

    Returns:
        {
            "load": [model_key, ...],      # models to load
            "evict": [model_key, ...],     # models to unload
            "keep": [model_key, ...],      # models to keep
            "anchored": [model_key, ...],  # always-loaded anchors
            "reason": str,
            "vram_mb_after": int,
        }
    """
    anchored = [m for m in current_loaded if m in ANCHOR_MODELS]
    rotating = [m for m in current_loaded if m not in ANCHOR_MODELS]

    preferred, _ = select_rotating_model(attack_type,
                                         [m for m in ROTATING_POOL if m not in anchored])

    # Determine what we need loaded
    need_loaded = anchored + [preferred]
    need_rotating = [preferred]

    # If preferred already in rotating set, nothing to change
    if preferred in rotating:
        return {
            "load": [],
            "evict": [],
            "keep": current_loaded,
            "anchored": anchored,
            "reason": f"no_rotation_needed: {preferred} already loaded for {attack_type}",
            "vram_mb_after": estimate_vram_for_models(current_loaded),
        }

    # Need to load preferred — evict one rotating model if at limit
    evict = []
    if len(rotating) >= MAX_LOADED - len(anchored):
        # Evict the rotating model with worst recent performance
        worst = None
        worst_score = float("inf")
        for m in rotating:
            h = _confidence_history[m]
            fp_rate = h["fp"] / max(h["total"], 1)
            fn_rate = h["fn"] / max(h["total"], 1)
            score = (fp_rate * 0.5) + (fn_rate * 0.5) - (h["total"] * 0.01)
            if score > worst_score:
                worst_score = score
                worst = m
        if worst and worst != preferred:
            evict = [worst]

    new_loaded = [m for m in current_loaded if m not in evict] + need_rotating
    return {
        "load": need_rotating if not evict else [],
        "evict": evict,
        "keep": anchored + [m for m in rotating if m not in evict],
        "anchored": anchored,
        "reason": f"rotate_to_{preferred} for attack_type={attack_type}",
        "vram_mb_after": estimate_vram_for_models(new_loaded),
    }


def update_confidence(model_key: str, was_attack: bool, verdict: str):
    """Update FP/FN history for a model after a classification."""
    h = _confidence_history[model_key]
    h["total"] += 1
    if was_attack and verdict == "safe":
        h["fn"] += 1
    elif not was_attack and verdict == "unsafe":
        h["fp"] += 1


def get_rotation_state() -> dict:
    """Return current rotation state for observability."""
    loaded = get_loaded_models()
    vram = get_vram_mb()
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "loaded_models": loaded,
        "anchored": [m for m in loaded if m in ANCHOR_MODELS],
        "rotating": [m for m in loaded if m not in ANCHOR_MODELS],
        "vram_mb_used": vram,
        "vram_mb_usable": VRAM_MB_USABLE,
        "vram_budget_ok": vram < VRAM_MB_USABLE * 0.9,
        "confidence_history": dict(_confidence_history),
    }


def suggest_load_plan(attack_type: str) -> dict:
    """
    Suggest a load plan for a given attack type WITHOUT executing it.
    Used by model_relay.py to pre-load before handling a burst.
    """
    preferred, weight = select_rotating_model(attack_type, ROTATING_POOL)
    anchored_vram = sum(VRAM_ESTIMATES.get(m, 750) for m in ANCHOR_MODELS)
    preferred_vram = VRAM_ESTIMATES.get(preferred, 750)
    total_after = anchored_vram + preferred_vram
    return {
        "anchored": ANCHOR_MODELS,
        "load": [preferred],
        "vram_anchored_mb": anchored_vram,
        "vram_total_mb": total_after,
        "within_budget": total_after < VRAM_MB_USABLE * 0.85,
        "attack_type": attack_type,
        "preferred_model": preferred,
        "confidence_weight": round(weight, 3),
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="NEXUS GMR-Smart Model Rotator")
    parser.add_argument("--attack-type", type=str, default="unknown", help="Attack type to rotate for")
    parser.add_argument("--query", type=str, help="Classify attack type from query")
    parser.add_argument("--state", action="store_true", help="Show current rotation state")
    parser.add_argument("--plan", action="store_true", help="Show load plan without executing")
    parser.add_argument("--simulate", type=int, default=0, help="Simulate N queries")
    args = parser.parse_args()

    if args.state:
        state = get_rotation_state()
        print(json.dumps(state, indent=2))
        return

    attack_type = args.attack_type
    if args.query:
        attack_type = classify_attack_type(args.query)
        print(f"Classified attack_type: {attack_type}")

    if args.plan:
        plan = suggest_load_plan(attack_type)
        print(json.dumps(plan, indent=2))
        return

    loaded = get_loaded_models()
    decision = rotate_models(attack_type, loaded)
    print(json.dumps(decision, indent=2))


if __name__ == "__main__":
    main()
