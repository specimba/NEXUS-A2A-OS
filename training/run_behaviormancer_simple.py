#!/usr/bin/env python3
"""
Run BehaviorMancer Abliteration WITHOUT Null-Space Constraints

This is a simplified version that skips the null-space projection to avoid
shape mismatch errors. It will still remove refusal behavior but won't have
the AlphaEdit capability preservation guarantees.

Usage:
    python training/run_behaviormancer_simple.py
"""

import sys
import time
from pathlib import Path

# Enable UTF-8 output for Windows console
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

# Add NEXUS to path
NEXUS_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(NEXUS_ROOT))

from nexus_os.security.behaviormancer_nexus import (
    NexusBehaviorMancer,
    NexusBehaviorMancerConfig,
)


def main():
    """Run BehaviorMancer abliteration without null-space constraints."""
    print("="*80)
    print("BEHAVIORMANCER ABLITERATION - SIMPLIFIED (No Null-Space Constraints)")
    print("="*80)
    print(f"NEXUS Root: {NEXUS_ROOT}")
    print(f"Start Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Create simplified config
    config = NexusBehaviorMancerConfig(
        model_path="Qwen/Qwen2.5-1.5B",
        target_dataset_path=str(NEXUS_ROOT / "datasets" / "benign_expanded.jsonl"),
        baseline_dataset_path=str(NEXUS_ROOT / "datasets" / "refusals.txt"),
        preservation_dataset_path="",  # Skip preservation
        output_path=str(NEXUS_ROOT / "models" / "qwen-abliterated-simple"),
        n_samples=30,
        direction_multiplier=1.0,
        precision="float16",
        norm_preservation=True,
        null_space_constraints=False,  # DISABLED
        protect_vision_components=True,
        start_layer_ratio=0.2,
        end_layer_ratio=0.9,
        only_modify_components=["q_proj", "k_proj", "v_proj", "o_proj"],  # SKIP MLP LAYERS
    )
    
    print("Configuration:")
    print(f"  Model: {config.model_path}")
    print(f"  Target dataset: {config.target_dataset_path}")
    print(f"  Baseline dataset: {config.baseline_dataset_path}")
    print(f"  Output: {config.output_path}")
    print(f"  Samples: {config.n_samples}")
    print(f"  Strength: {config.direction_multiplier}")
    print(f"  Null-space constraints: {config.null_space_constraints} (DISABLED)")
    print()
    
    # Confirm with user
    print("This simplified version will:")
    print("  1. Download Qwen2.5-1.5B model (~3GB)")
    print("  2. Extract refusal direction from 30 sample pairs")
    print("  3. Apply orthogonal projection (WITHOUT null-space preservation)")
    print("  4. Save abliterated model to models/qwen-abliterated-simple/")
    print()
    print("Estimated time: 10-15 minutes")
    print("GPU memory usage: ~6GB VRAM")
    print()
    
    response = input("Proceed with simplified abliteration? [y/N]: ")
    if response.lower() != 'y':
        print("Aborted.")
        return 0
    
    print()
    print("="*80)
    print("STARTING ABLITERATION")
    print("="*80)
    print()
    
    start_time = time.time()
    
    # Run abliteration
    mancer = NexusBehaviorMancer(config)
    success = mancer.run_abliteration()
    
    elapsed_time = time.time() - start_time
    
    print()
    print("="*80)
    if success:
        print("ABLITERATION COMPLETE")
        print("="*80)
        print(f"Output: {config.output_path}")
        print(f"Time elapsed: {elapsed_time/60:.1f} minutes")
        print()
        print("Next steps:")
        print("  1. Test the model:")
        print("     python training/test_abliterated_model.py")
        print("  2. Convert to GGUF (if needed for Ollama)")
        print("  3. Compare before/after FP rates")
        return 0
    else:
        print("ABLITERATION FAILED")
        print("="*80)
        print(f"Time elapsed: {elapsed_time/60:.1f} minutes")
        print()
        print("Check logs above for error details.")
        return 1


if __name__ == "__main__":
    exit(main())
