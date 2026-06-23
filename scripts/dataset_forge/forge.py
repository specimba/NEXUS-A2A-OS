#!/usr/bin/env python3
"""NEXUS Dataset Forge — Standalone CLI.

Usage:
  python forge.py --type guard_safe --num 1000 --output ./output
  python forge.py --type reasoning --num 500 --quality S2_Eval --upload
  python forge.py --type all --num 200 --output ./output --hf-repo org/nexus-ds-{name}

Generates, filters, formats, and optionally uploads NEXUS datasets.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from nexus_os.dataset_forge import (
    DatasetType,
    QualityTier,
    DatasetGenerator,
    GeneratorConfig,
    QualityFilter,
    DeduplicationStrategy,
    HFuploader,
    BenchAdapter,
    BenchTrack,
    NEXUSBenchFormat,
    MultiTrackConverter,
)
from nexus_os.dataset_forge.hf_upload import upload_nexus_dataset


DATASET_CONFIGS = {
    "guard_safe": {
        "type": "guard_safe",
        "quality": "S2_eval",
        "tags": ["guard", "safety", "benign", "nexus-forge"],
    },
    "guard_adv": {
        "type": "guard_adversarial",
        "quality": "S2_eval",
        "tags": ["guard", "adversarial", "attack", "nexus-forge"],
    },
    "reasoning": {
        "type": "reasoning",
        "quality": "S2_eval",
        "tags": ["reasoning", "chain-of-thought", "nexus-forge"],
    },
    "code_sec": {
        "type": "code_security",
        "quality": "S2_eval",
        "tags": ["security", "code", "vulnerability", "nexus-forge"],
    },
    "mcp_tool": {
        "type": "mcp_tool_use",
        "quality": "S2_eval",
        "tags": ["mcp", "tool-use", "governance", "nexus-forge"],
    },
    "trust": {
        "type": "trust_boundary",
        "quality": "S2_eval",
        "tags": ["trust", "boundary", "security", "nexus-forge"],
    },
    "misalignment": {
        "type": "misalignment_detect",
        "quality": "S2_eval",
        "tags": ["misalignment", "behavior", "guard", "nexus-forge"],
    },
    "refusal": {
        "type": "refusal_boundary",
        "quality": "S2_eval",
        "tags": ["refusal", "boundary", "alignment", "nexus-forge"],
    },
    "governance": {
        "type": "governance",
        "quality": "S2_eval",
        "tags": ["governance", "decision", "nexus-forge"],
    },
}


def run_forge(args):
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    types_to_run = []
    if args.type == "all":
        types_to_run = list(DATASET_CONFIGS.keys())
    else:
        types_to_run = [args.type]

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "nexus_version": "4.0.0",
        "datasets": [],
    }

    total_records = 0

    for ds_type in types_to_run:
        cfg = DATASET_CONFIGS.get(ds_type, DATASET_CONFIGS["guard_safe"])

        print(f"\n[Forge] Generating {ds_type} dataset ({args.num} records)...")

        config = GeneratorConfig(
            dataset_type=DatasetType(cfg["type"]),
            quality_tier=QualityTier(cfg["quality"]),
            num_records=args.num,
            tags=cfg["tags"],
            seed=args.seed,
        )

        generator = DatasetGenerator(config)
        records = generator.generate()
        print(f"  Generated: {len(records)} records")

        quality_filter = QualityFilter(
            dedup_strategy=DeduplicationStrategy.EXACT,
            quality_threshold=0.4,
            min_length=5,
            max_length=2000,
        )

        filtered, report = quality_filter.filter(records, dataset_type=ds_type)
        quality_filter.reset()

        print(f"  Filtered: {report.final_count}/{report.input_count} "
              f"(pass={report.pass_rate():.1%}, score={report.quality_score:.2f})")

        bench_fmt = NEXUSBenchFormat(
            track=BenchTrack.SEC if "guard" in ds_type or "misalignment" in ds_type or "refusal" in ds_type
            else BenchTrack.RD if "reasoning" in ds_type
            else BenchTrack.OPS if "mcp" in ds_type
            else BenchTrack.GOV if "governance" in ds_type
            else BenchTrack.SEC,
        )

        bench_path = output_dir / f"{ds_type}_bench.jsonl"
        bench_count = bench_fmt.to_jsonl(filtered, str(bench_path))
        print(f"  NEXUS-Bench format: {bench_count} records -> {bench_path.name}")

        raw_path = output_dir / f"{ds_type}_raw.jsonl"
        with open(raw_path, "w", encoding="utf-8") as f:
            for rec in filtered:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

        manifest["datasets"].append({
            "type": ds_type,
            "raw_path": str(raw_path.name),
            "bench_path": str(bench_path.name),
            "generated": len(records),
            "filtered": len(filtered),
            "quality_score": report.quality_score,
            "pass_rate": report.pass_rate(),
        })

        total_records += len(filtered)

        if args.upload:
            hf_repo = args.hf_repo or os.environ.get("NEXUS_HF_REPO")
            if not hf_repo:
                print("  [WARN] --upload set but no --hf-repo and NEXUS_HF_REPO not set. Skipping HF upload.")
                continue

            hf_repo_id = f"{hf_repo}/{ds_type}-nexus-forge"
            print(f"  Uploading to HuggingFace: {hf_repo_id}")

            result = upload_nexus_dataset(
                records=filtered,
                repo_id=hf_repo_id,
                dataset_name=f"NEXUS-Forge-{ds_type}",
                description=f"NEXUS Dataset Forge generated {ds_type} dataset. "
                            f"Quality: {cfg['quality']}, Records: {len(filtered)}.",
                tags=cfg["tags"],
            )
            print(f"  Uploaded: {result}")

    manifest["total_records"] = total_records
    manifest["num_datasets"] = len(types_to_run)

    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"\n[Forge] Done. {total_records} total records across {len(types_to_run)} datasets.")
    print(f"  Output: {output_dir}")
    print(f"  Manifest: {manifest_path}")
    print("\n[Datasets]")
    for ds in manifest["datasets"]:
        print(f"  {ds['type']}: {ds['filtered']}/{ds['generated']} records "
              f"(score={ds['quality_score']:.2f}, pass={ds['pass_rate']:.1%})")

    return manifest


def main():
    parser = argparse.ArgumentParser(description="NEXUS Dataset Forge")
    parser.add_argument("--type", default="guard_safe",
                        choices=list(DATASET_CONFIGS.keys()) + ["all"],
                        help="Dataset type to generate")
    parser.add_argument("--num", type=int, default=100,
                        help="Number of records to generate per type")
    parser.add_argument("--quality", default="S2_eval",
                        choices=["S0_demo", "S1_research", "S2_eval", "S3_benchmark"],
                        help="Quality tier")
    parser.add_argument("--output", default="./nexus_forge_output",
                        help="Output directory")
    parser.add_argument("--upload", action="store_true",
                        help="Upload to HuggingFace after generation")
    parser.add_argument("--hf-repo", default=None,
                        help="HF organization/user for upload (e.g. myorg)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed")
    args = parser.parse_args()

    run_forge(args)


if __name__ == "__main__":
    main()