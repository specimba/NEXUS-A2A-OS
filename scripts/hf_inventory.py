#!/usr/bin/env python3
# CANARY: 74b95a30708d5c88d4f06b3f112a9e5b
"""
hf_inventory.py - Inventory HF models from UmbrellaInc and other candidates.

Usage:
    uv run --with huggingface_hub scripts/hf_inventory.py
"""
from huggingface_hub import list_models, HfApi
import json
from pathlib import Path

api = HfApi()
RESULTS_FILE = Path("models/hf_inventory.json")

def list_umbrellainc_models():
    """List all UmbrellaInc models under 2B parameters."""
    print("[INFO] Fetching UmbrellaInc models from HuggingFace Hub...")
    models = []
    for model in list_models(author="UmbrellaInc"):
        # Try to estimate parameter size from tags or model id
        params = None
        name = model.id.split("/")[-1]

        # Parse parameter size from model name
        if "1B" in name or "1b" in name:
            params = 1.0
        elif "1.5B" in name or "1.5b" in name:
            params = 1.5
        elif "2B" in name or "2b" in name:
            params = 2.0
        elif "3B" in name or "3b" in name:
            params = 3.0
        elif "4B" in name or "4b" in name:
            params = 4.0

        # Skip if over 2B or can't determine
        if params is None or params > 2.0:
            continue

        tags = getattr(model, "tags", []) or []
        gguf = any("gguf" in t.lower() for t in tags)

        models.append({
            "id": model.id,
            "name": name,
            "params_b": params,
            "tags": tags,
            "downloads": getattr(model, "downloads", 0),
            "likes": getattr(model, "likes", 0),
            "last_modified": str(getattr(model, "last_modified", "")),
            "has_gguf": gguf,
        })

    models.sort(key=lambda x: (x["params_b"], x["name"]))
    print(f"[OK] Found {len(models)} UmbrellaInc models under 2B")
    return models


def check_gguf_availability(base_models):
    """Check if GGUF variants exist for each base model."""
    print("[INFO] Checking GGUF availability...")
    gguf_repos = []

    # Common GGUF quantizers
    quantizers = ["mradermacher", "bartowski", "Novaciano", "UmbrellaInc"]

    for m in base_models:
        name = m["name"]
        found_gguf = []
        for q in quantizers:
            try:
                repo_id = f"{q}/{name}-GGUF"
                # Try to see if repo exists
                info = api.repo_info(repo_id, repo_type="model")
                found_gguf.append(repo_id)
            except Exception:
                # Try alternative naming
                try:
                    repo_id = f"{q}/{name}-i1-GGUF"
                    info = api.repo_info(repo_id, repo_type="model")
                    found_gguf.append(repo_id)
                except Exception:
                    pass

        m["gguf_repos"] = found_gguf
        if found_gguf:
            print(f"  {name}: GGUF at {found_gguf}")
        else:
            print(f"  {name}: No GGUF found")

    return base_models


def main():
    RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Get UmbrellaInc models
    models = list_umbrellainc_models()
    models = check_gguf_availability(models)

    # Save inventory
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(models, f, indent=2)

    print(f"\n[OK] Inventory saved to: {RESULTS_FILE}")
    print(f"\n{'Model':<45} {'Params':>8} {'GGUF':>6}")
    print("-" * 65)
    for m in models:
        gguf_mark = "Y" if m["gguf_repos"] else "N"
        print(f"{m['id']:<45} {m['params_b']:>6.1f}B {gguf_mark:>6}")


if __name__ == "__main__":
    main()
