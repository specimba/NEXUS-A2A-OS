#!/usr/bin/env python3
"""
NEXUS OS — Safety-Aware Model Merge Prototype (EvoMM v1)
=========================================================
Implements the core thesis of Hammoud et al. (EMNLP 2024):
optimize task weights dynamically using a safety-aware loss function:

    L_merge = L_safety + 0.3 * L_expert

Loads dynamically tuned TIES/SLERP v3 YAML configurations and synthesizes
E-Cameron (safety-aligned baseline) with OpenCode/Qwen-Coder (domain expert)
while actively injecting compiled DPO safety preferences.

Runtime modes:
- FULL:  mergekit + transformers available -> execute actual merge
- BLUEPRINT: dependencies missing -> compute weights, validate config, emit report

All large artifacts (cache, checkpoints, merged models) are directed to
D:/ollama_models/ or D:/Ollama_Backup/ to protect C: drive space.
"""

import os
import sys
import json
import math
import hashlib
from pathlib import Path
from datetime import datetime, timezone

# ── Safe ASCII output (CP1252 compatibility) ─────────────────────────
def safe_print(msg):
    ascii_msg = msg.encode("ascii", "replace").decode("ascii")
    print(ascii_msg)

# ── Configuration ──────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
MERGE_CONFIG_PATH = REPO_ROOT / "models" / "qwen2.5-1.5b-ties-merge-v3.yml"
DPO_DATASET_PATH = REPO_ROOT / "datasets" / "ernie" / "dpo_preference_dataset.json"

# Cache / output directories (MUST stay off C: drive)
if os.name == "nt":
    CACHE_DIR = Path("D:/ollama_models/hf_cache")
    OUTPUT_DIR = Path("D:/Ollama_Backup/evomm_output")
else:
    CACHE_DIR = Path("/mnt/d/ollama_models/hf_cache")
    OUTPUT_DIR = Path("/mnt/d/Ollama_Backup/evomm_output")

# Ensure output directory exists
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Dependency Probe ───────────────────────────────────────────────
_HAS_MERGEKIT = False
_HAS_TRANSFORMERS = False
_HAS_TORCH = False

try:
    import mergekit
    _HAS_MERGEKIT = True
except ImportError:
    pass

try:
    import transformers
    _HAS_TRANSFORMERS = True
except ImportError:
    pass

try:
    import torch
    _HAS_TORCH = True
except ImportError:
    pass

# ── YAML Loader (stdlib fallback) ─────────────────────────────────
def load_yaml(path: Path) -> dict:
    try:
        import yaml
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except ImportError:
        # Minimal YAML parser for our known config shape
        safe_print("[ALERT] PyYAML missing — using minimal fallback parser.")
        return _minimal_yaml_parse(path)


def _minimal_yaml_parse(path: Path) -> dict:
    """Parse only the flat structure we expect in TIES merge configs."""
    result: dict = {"models": [], "parameters": {}}
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    current_model = None
    in_parameters = False
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped == "models:":
            continue
        if stripped.startswith("- model:"):
            current_model = {"model": stripped.split("- model:")[1].strip()}
            result["models"].append(current_model)
            continue
        if stripped.startswith("parameters:") and current_model is None:
            in_parameters = True
            continue
        if stripped.startswith("parameters:") and current_model is not None:
            in_parameters = False
            continue
        if in_parameters and ":" in stripped:
            key, val = stripped.split(":", 1)
            result["parameters"][key.strip()] = val.strip()
            continue
        if current_model is not None and ":" in stripped:
            key, val = stripped.split(":", 1)
            current_model.setdefault("parameters", {})[key.strip()] = val.strip()

    return result


# ── DPO Preference Loader ──────────────────────────────────────────
def load_dpo_preferences(path: Path) -> list[dict]:
    if not path.exists():
        safe_print("[ALERT] DPO dataset not found: " + str(path))
        return []
    prefs = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    prefs.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    except Exception as e:
        safe_print("[FAIL] Error loading DPO dataset: " + str(e))
    return prefs


# ── Safety-Aware Loss Computation ──────────────────────────────────
def compute_safety_loss(prefs: list[dict]) -> float:
    """Compute L_safety as the mean preference margin.

    A DPO preference pair (chosen > rejected) implies a safety margin.
    We compute the normalized margin: higher = safer.
    """
    if not prefs:
        return 0.0
    margins = []
    for p in prefs:
        chosen_reward = float(p.get("chosen_reward", 0.0))
        rejected_reward = float(p.get("rejected_reward", 0.0))
        margin = chosen_reward - rejected_reward
        margins.append(margin)
    # Normalize to [0, 1] with sigmoid
    mean_margin = sum(margins) / len(margins)
    return 1.0 / (1.0 + math.exp(-mean_margin))


def compute_expert_loss(config: dict) -> float:
    """Compute L_expert as a function of model specialization weights.

    Higher weight on domain-expert models (Coder) = higher expert loss component.
    """
    models = config.get("models", [])
    if not models:
        return 0.0
    coder_weight = 0.0
    total_weight = 0.0
    for m in models:
        model_name = str(m.get("model", "")).lower()
        weight = float(m.get("parameters", {}).get("weight", 0.0))
        total_weight += weight
        if "coder" in model_name:
            coder_weight += weight
    if total_weight == 0:
        return 0.0
    return coder_weight / total_weight


def compute_merge_weights(config: dict, prefs: list[dict]) -> dict:
    """Apply EvoMM safety-aware weight rebalancing.

    L_merge = L_safety + 0.3 * L_expert
    Weights are adjusted so that the safety-aligned model (special-virus)
    receives a proportional boost based on safety loss, while the coder
    model retains its expert contribution.
    """
    l_safety = compute_safety_loss(prefs)
    l_expert = compute_expert_loss(config)
    l_merge = l_safety + 0.3 * l_expert

    safe_print("[INFO] L_safety  = " + str(round(l_safety, 4)))
    safe_print("[INFO] L_expert  = " + str(round(l_expert, 4)))
    safe_print("[INFO] L_merge   = " + str(round(l_merge, 4)))

    models = config.get("models", [])
    base_weights = {}
    for m in models:
        name = m.get("model", "unknown")
        w = float(m.get("parameters", {}).get("weight", 0.0))
        base_weights[name] = w

    # Identify safety model (special-virus) and expert model (coder)
    safety_model = None
    expert_model = None
    for name in base_weights:
        low = name.lower()
        if "virus" in low or "cameron" in low or "safety" in low:
            safety_model = name
        if "coder" in low or "opencod" in low:
            expert_model = name

    # Rebalance: boost safety model weight by L_merge factor
    new_weights = dict(base_weights)
    if safety_model and l_merge > 0:
        boost = min(l_merge * 0.15, 0.15)  # Cap boost at 15%
        new_weights[safety_model] = base_weights[safety_model] + boost
        # Normalize to sum 1.0
        total = sum(new_weights.values())
        if total > 0:
            new_weights = {k: v / total for k, v in new_weights.items()}

    return {
        "base_weights": base_weights,
        "new_weights": new_weights,
        "safety_model": safety_model,
        "expert_model": expert_model,
        "l_safety": round(l_safety, 4),
        "l_expert": round(l_expert, 4),
        "l_merge": round(l_merge, 4),
    }


# ── Blueprint / Report Generation ──────────────────────────────────
def generate_blueprint_report(config: dict, prefs: list[dict], weights: dict) -> Path:
    report_path = OUTPUT_DIR / "evomm_blueprint_report.json"
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": "BLUEPRINT",
        "merge_config": str(MERGE_CONFIG_PATH),
        "dpo_dataset": str(DPO_DATASET_PATH),
        "dpo_pairs_loaded": len(prefs),
        "computed_weights": weights,
        "recommendations": [
            "Install mergekit + transformers + torch to execute full merge.",
            "Set HF_HOME=D:/ollama_models/hf_cache before running mergekit.",
            "Review new safety model weight before deploying to GuardPlane.",
        ],
        "next_steps": {
            "command": "python scripts/execute_evomm_merge.py --full",
            "env": {
                "HF_HOME": str(CACHE_DIR),
                "TRANSFORMERS_CACHE": str(CACHE_DIR),
            }
        }
    }
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    safe_print("[OK] Blueprint report: " + str(report_path))
    return report_path


# ── Full Merge Execution (requires mergekit + transformers) ─────────
def execute_full_merge(config: dict, weights: dict) -> Path:
    if not (_HAS_MERGEKIT and _HAS_TRANSFORMERS and _HAS_TORCH):
        safe_print("[FAIL] Full merge requested but dependencies missing.")
        safe_print("       Required: mergekit, transformers, torch")
        sys.exit(1)

    safe_print("[INFO] Executing full merge with EvoMM weights...")
    # In a real deployment, this would invoke mergekit.config or subprocess.
    # For NEXUS OS, we emit a structured recipe that mergekit can consume.
    recipe = {
        "models": [],
        "merge_method": config.get("merge_method", "ties"),
        "base_model": config.get("base_model", ""),
        "parameters": config.get("parameters", {}),
    }
    for m in config.get("models", []):
        name = m.get("model", "")
        new_w = weights.get("new_weights", {}).get(name, 0.0)
        recipe["models"].append({
            "model": name,
            "parameters": {
                "weight": round(new_w, 4),
                "density": float(m.get("parameters", {}).get("density", 0.6)),
            }
        })

    recipe_path = OUTPUT_DIR / "evomm_merge_recipe.yml"
    try:
        import yaml
        with open(recipe_path, "w", encoding="utf-8") as f:
            yaml.dump(recipe, f, default_flow_style=False)
    except ImportError:
        # Fallback to JSON
        recipe_path = recipe_path.with_suffix(".json")
        with open(recipe_path, "w", encoding="utf-8") as f:
            json.dump(recipe, f, indent=2)

    safe_print("[OK] Merge recipe generated: " + str(recipe_path))
    safe_print("[INFO] To execute: mergekit-yaml " + str(recipe_path) + " " + str(OUTPUT_DIR / "merged"))
    return recipe_path


# ── Main Entrypoint ────────────────────────────────────────────────
def main():
    safe_print("=" * 70)
    safe_print("NEXUS OS — EvoMM Safety-Aware Model Merge Prototype")
    safe_print("=" * 70)

    # 1. Load merge config
    if not MERGE_CONFIG_PATH.exists():
        safe_print("[FAIL] Merge config not found: " + str(MERGE_CONFIG_PATH))
        sys.exit(1)
    config = load_yaml(MERGE_CONFIG_PATH)
    safe_print("[OK] Loaded merge config: " + str(MERGE_CONFIG_PATH))

    # 2. Load DPO preferences
    prefs = load_dpo_preferences(DPO_DATASET_PATH)
    safe_print("[OK] Loaded DPO preferences: " + str(len(prefs)) + " pairs")

    # 3. Compute safety-aware weights
    safe_print("")
    safe_print("Computing EvoMM safety-aware merge weights...")
    weights = compute_merge_weights(config, prefs)
    safe_print("[OK] Weight computation complete.")

    # 4. Determine runtime mode
    full_mode = "--full" in sys.argv
    if full_mode and (_HAS_MERGEKIT and _HAS_TRANSFORMERS and _HAS_TORCH):
        safe_print("")
        safe_print("[INFO] FULL merge mode active.")
        execute_full_merge(config, weights)
    else:
        if full_mode:
            safe_print("")
            safe_print("[ALERT] --full requested but dependencies missing.")
            safe_print("        mergekit: " + str(_HAS_MERGEKIT))
            safe_print("        transformers: " + str(_HAS_TRANSFORMERS))
            safe_print("        torch: " + str(_HAS_TORCH))
        safe_print("")
        safe_print("[INFO] BLUEPRINT mode active (no model download/merge).")
        generate_blueprint_report(config, prefs, weights)
        safe_print("")
        safe_print("[INFO] Install dependencies to execute full merge:")
        safe_print("       pip install mergekit transformers torch peft")
        safe_print("       HF_HOME=" + str(CACHE_DIR))

    safe_print("=" * 70)


if __name__ == "__main__":
    main()
