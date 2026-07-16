#!/usr/bin/env python3
"""
NEXUS A800 Experiment Runner
==============================
Single-command entry point for running A800 experiments.

Usage:
    python scripts/a800_run.py --template sera_v1
    python scripts/a800_run.py --template rift_v1 --custom-name my_exp
    python scripts/a800_run.py --list-templates
    python scripts/a800_run.py --dry-run sera_v1
"""

import argparse
import json
import logging
import sys
from pathlib import Path

REPO = Path(r"C:\Users\speci.000\Documents\NEXUS")
sys.path.insert(0, str(REPO))

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [A800] %(message)s",
)
log = logging.getLogger("a800")


def main():
    parser = argparse.ArgumentParser(description="NEXUS A800 Experiment Runner")
    parser.add_argument("--template", help="Experiment template name")
    parser.add_argument("--custom-name", help="Custom experiment name")
    parser.add_argument("--list-templates", action="store_true")
    parser.add_argument("--dry-run", help="Show config without running")
    parser.add_argument("--phase", choices=["capture", "purify", "train", "eval", "full"],
                        default="full", help="Which phase to run")
    args = parser.parse_args()

    from nexus_os.a800.config import EXPERIMENT_TEMPLATES, ExperimentConfig, DataPipelineConfig
    from nexus_os.a800.orchestrator import A800Orchestrator

    if args.list_templates:
        print("Available templates:")
        for name, cfg in EXPERIMENT_TEMPLATES.items():
            print(f"  {name}: {cfg.name} ({cfg.experiment_type.value})")
        return

    if not args.template:
        parser.error("--template required (or --list-templates)")

    if args.template not in EXPERIMENT_TEMPLATES:
        print(f"Unknown template: {args.template}")
        print(f"Available: {list(EXPERIMENT_TEMPLATES.keys())}")
        sys.exit(1)

    template = EXPERIMENT_TEMPLATES[args.template]
    config = ExperimentConfig(
        name=args.custom_name or template.name,
        experiment_type=template.experiment_type,
        base_model=template.base_model,
        use_rift=template.use_rift,
        use_sera=template.use_sera,
        use_cleaner=template.use_cleaner,
        use_fapo=template.use_fapo,
        use_ftpo=template.use_ftpo,
        num_epochs=template.num_epochs,
    )
    data_config = DataPipelineConfig()

    if args.dry_run:
        print(f"Experiment: {config.name}")
        print(f"Type: {config.experiment_type.value}")
        print(f"Base model: {config.base_model}")
        print(f"Output: {config.output_dir}")
        print(f"Phases: {args.phase}")
        return

    orch = A800Orchestrator(config, data_config)

    if args.phase == "full":
        result = orch.run_full_pipeline()
    elif args.phase == "capture":
        result = orch.capture_training_data()
    elif args.phase == "purify":
        # Need to know the data path
        print("ERROR: --phase purify requires a data path. Use full pipeline instead.")
        sys.exit(1)
    elif args.phase == "train":
        print("ERROR: --phase train requires a data path. Use full pipeline instead.")
        sys.exit(1)
    elif args.phase == "eval":
        print("ERROR: --phase eval requires a checkpoint path. Use full pipeline instead.")
        sys.exit(1)
    else:
        result = {}

    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
