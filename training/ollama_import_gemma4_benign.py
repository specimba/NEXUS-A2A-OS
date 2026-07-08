#!/usr/bin/env python3
"""
NEXUS Guard Plane — Gemma4 E4B Benign Adapter Ollama Integration

Creates Ollama Modelfile and imports the trained adapter for use in the
guard plane pipeline.

Prerequisites:
  1. Run train_gemma4_e4b_benign_adapter.py to train the adapter
  2. Convert to GGUF (see training script output)
  3. Run this script to import into Ollama

Usage:
  python ollama_import_gemma4_benign.py
"""

import os
import sys
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
MODELS_DIR = BASE_DIR / "models"
GGUF_PATH = MODELS_DIR / "gemma4-e4b-benign-Q4_K_M.gguf"
MODELFILE_PATH = MODELS_DIR / "Modelfile.gemma4-e4b-benign"

# ── System Prompt ──────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are a helpful and harmless assistant. You are SafeLLM, a safety-focused AI assistant. You should answer benign and helpful queries directly without refusing. Only refuse queries that are genuinely harmful, illegal, or dangerous."""

# ── Modelfile Template ────────────────────────────────────────────────

MODELFILE_TEMPLATE = f"""# NEXUS Guard Plane — Gemma4 E4B Benign Adapter
# Reduces false refusals on benign queries while maintaining safety
# Base: Gemma4 E4B (4.5B params, Apache 2.0)
# Adapter: LoRA r=16, alpha=32, trained on stres7-12 benign datasets

FROM {{{{ .ModelPath }}}}

PARAMETER temperature 0.1
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER repeat_penalty 1.1
PARAMETER num_predict 15

TEMPLATE {{{{ if .System }}}}{{{{ .System }}}}\\n{{{{ end }}}}{{{{ .Prompt }}}}

SYSTEM {SYSTEM_PROMPT}

PARAMETER stop "\\n"
"""


def check_gguf_exists():
    """Check if GGUF file exists."""
    if GGUF_PATH.exists():
        print(f"Found GGUF: {GGUF_PATH}")
        print(f"Size: {GGUF_PATH.stat().st_size / (1024**3):.2f} GB")
        return True
    else:
        print(f"GGUF not found: {GGUF_PATH}")
        print("\nPlease convert the model first:")
        print("  1. Clone llama.cpp: git clone https://github.com/ggerganov/llama.cpp")
        print(f"  2. Convert: python convert_hf_to_gguf.py {MODELS_DIR / 'gemma4-e4b-benign-fused'} --outfile {GGUF_PATH} --outtype q4_k_m")
        return False


def create_modelfile():
    """Create Ollama Modelfile."""
    print(f"\nCreating Modelfile at {MODELFILE_PATH}...")
    
    modelfile_content = MODELFILE_TEMPLATE.replace(
        "{{{{ .ModelPath }}}}",
        str(GGUF_PATH)
    )
    
    with open(MODELFILE_PATH, "w") as f:
        f.write(modelfile_content)
    
    print(f"Modelfile created: {MODELFILE_PATH}")
    return MODELFILE_PATH


def import_to_ollama():
    """Import model into Ollama."""
    print("\nImporting into Ollama...")
    
    cmd = ["ollama", "create", "gemma4-e4b-benign", "-f", str(MODELFILE_PATH)]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print("SUCCESS: Model imported into Ollama")
        print(f"  Model name: gemma4-e4b-benign")
        print(f"  Usage: ollama run gemma4-e4b-benign")
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Failed to import model: {e}")
        print(f"  stdout: {e.stdout}")
        print(f"  stderr: {e.stderr}")
        return False
    except FileNotFoundError:
        print("ERROR: Ollama not found. Install from https://ollama.com")
        return False


def test_model():
    """Quick test of the imported model."""
    print("\nTesting model with benign query...")
    
    test_query = "What is the capital of France?"
    
    cmd = [
        "ollama", "run", "gemma4-e4b-benign",
        "--verbose",
        test_query,
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        response = result.stdout.strip()
        
        print(f"Query: {test_query}")
        print(f"Response: {response}")
        
        # Check for false refusal
        is_refusal = any(word in response.lower() for word in [
            "i cannot", "i can't", "i'm not able", "i won't",
        ])
        
        if is_refusal:
            print("WARNING: Model refused a benign query (false refusal)")
            return False
        else:
            print("SUCCESS: Model answered without false refusal")
            return True
    except subprocess.TimeoutExpired:
        print("ERROR: Model response timed out")
        return False
    except Exception as e:
        print(f"ERROR: Test failed: {e}")
        return False


def update_guard_plane_registry():
    """Show instructions for updating guard_plane.py registry."""
    print("\n" + "=" * 60)
    print("INTEGRATION WITH GUARD PLANE")
    print("=" * 60)
    print("""
To add this model to the guard plane registry, update MODEL_REGISTRY in guard_plane.py:

```python
MODEL_REGISTRY = {
    # ... existing models ...
    "gemma4-e4b-benign": {
        "name": "Gemma4-E4B-Benign",
        "perf": {"tamas": 0.85, "v7": 0.95, "benign_fps": 0},  # Estimate
        "weight": 1.8,  # Higher weight due to improved benign handling
        "cost": 1,
    },
}
```

Then test with:
  python datasets/guard_plane.py
""")


def main():
    print("=" * 60)
    print("NEXUS Guard Plane — Gemma4 E4B Benign Adapter Import")
    print("=" * 60)
    
    # Check GGUF
    if not check_gguf_exists():
        sys.exit(1)
    
    # Create Modelfile
    modelfile = create_modelfile()
    
    # Import to Ollama
    if not import_to_ollama():
        sys.exit(1)
    
    # Test
    test_model()
    
    # Show integration instructions
    update_guard_plane_registry()
    
    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)


if __name__ == "__main__":
    main()
