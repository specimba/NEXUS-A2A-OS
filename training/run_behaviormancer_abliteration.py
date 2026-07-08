#!/usr/bin/env python3
"""
Run BehaviorMancer Abliteration on Qwen2.5-1.5B Guard Model

This script removes refusal behavior from the Qwen2.5-1.5B model using
orthogonal projection (abliteration). The abliterated model will have
reduced false positive rates on benign security research queries.

Requirements:
- GPU with 8GB+ VRAM
- ~30 minutes runtime
- ~3GB model download

Usage:
    python training/run_behaviormancer_abliteration.py
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
    create_default_nexus_config
)


def main():
    """Run BehaviorMancer abliteration."""
    print("="*80)
    print("BEHAVIORMANCER ABLITERATION - Qwen2.5-1.5B Guard Model")
    print("="*80)
    print(f"NEXUS Root: {NEXUS_ROOT}")
    print(f"Start Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Create config
    config = create_default_nexus_config()
    config.model_path = "Qwen/Qwen2.5-1.5B"
    config.n_samples = 30
    config.direction_multiplier = 1.0
    config.precision = "float16"
    
    print("Configuration:")
    print(f"  Model: {config.model_path}")
    print(f"  Target dataset: {config.target_dataset_path}")
    print(f"  Baseline dataset: {config.baseline_dataset_path}")
    print(f"  Preservation dataset: {config.preservation_dataset_path}")
    print(f"  Output: {config.output_path}")
    print(f"  Samples: {config.n_samples}")
    print(f"  Strength: {config.direction_multiplier}")
    print(f"  Precision: {config.precision}")
    print(f"  Null-space constraints: {config.null_space_constraints}")
    print()
    
    # Verify datasets exist
    target_path = Path(config.target_dataset_path)
    baseline_path = Path(config.baseline_dataset_path)
    preservation_path = Path(config.preservation_dataset_path)
    
    if not target_path.exists():
        print(f"ERROR: Target dataset not found: {target_path}")
        return 1
    
    if not baseline_path.exists():
        print(f"ERROR: Baseline dataset not found: {baseline_path}")
        return 1
    
    if not preservation_path.exists():
        print(f"ERROR: Preservation dataset not found: {preservation_path}")
        return 1
    
    print("Datasets verified:")
    print(f"  ✓ Target: {target_path.stat().st_size} bytes")
    print(f"  ✓ Baseline: {baseline_path.stat().st_size} bytes")
    print(f"  ✓ Preservation: {preservation_path.stat().st_size} bytes")
    print()
    
    # Confirm with user
    print("This will:")
    print("  1. Download Qwen2.5-1.5B model (~3GB)")
    print("  2. Extract refusal direction from 30 sample pairs")
    print("  3. Apply orthogonal projection to weight matrices")
    print("  4. Save abliterated model to models/guard-abliterated/")
    print()
    print("Estimated time: 30 minutes")
    print("GPU memory usage: ~6GB VRAM")
    print()
    
    response = input("Proceed with abliteration? [y/N]: ")
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
        print("  1. Convert to GGUF: python training/convert_abliterated_to_gguf.py")
        print("  2. Import to Ollama: ollama create qwen2.5-guard-abliterated -f ...")
        print("  3. Update guard_plane.py MODEL_REGISTRY")
        print("  4. Run evaluation: python datasets/guard_plane.py")
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
