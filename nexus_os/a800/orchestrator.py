#!/usr/bin/env python3
"""
NEXUS A800 Experiment Orchestrator
====================================
Manages the full lifecycle of A800 training experiments:
  1. Data capture (CDP traces → training data)
  2. Purification (CLEANER + FAPO)
  3. Training (SERA/RIFT/FTPO/GRPO)
  4. Evaluation (calibrated judges)
  5. Deployment (↑ trust ledger + serving)

Driven by PAPERS master distillation P0 findings.
"""

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .config import (
    A800_SESSION,
    A800_NOTEBBOOK,
    A800_BASE_URL,
    DataPipelineConfig,
    ExperimentConfig,
    ExperimentType,
    REASONS_DB,
    TRUST_MEMORY,
)
from .rift import RIFTWeightCalculator, trust_weighted_loss
from .sera import SERAVerifier, soft_verify_batch
from .cleanereval import CLEANERPurifier, FAPOChecker, purify_trajectories
from .ftp0 import FTPOTrainer, generate_preference_pairs
from .data_pipeline import CDPTraceCapture, DataPipeline
from .eval_pack import EvalPack, calibrated_evaluate

log = logging.getLogger("a800.orchestrator")


class A800Orchestrator:
    """Main controller for NEXUS A800 training experiments."""

    def __init__(self, config: ExperimentConfig, data_config: DataPipelineConfig):
        self.config = config
        self.data_config = data_config
        self.rift = RIFTWeightCalculator(
            alpha=config.trust_alpha,
            beta=config.trust_beta,
            min_weight=config.min_trust_weight,
        )
        self.sera = SERAVerifier(threshold=config.verification_threshold)
        self.cleaner = CLEANERPurifier(strategy=config.purification_strategy)
        self.fapo = FAPOChecker(judge_type=config.process_check_judge)
        self.pipeline = DataPipeline(data_config)
        self.capture = CDPTraceCapture(data_config)
        self.eval_pack = EvalPack(config.eval_pack)
        self._checkpoint_dir = Path(config.output_dir) / "checkpoints"
        self._checkpoint_dir.mkdir(parents=True, exist_ok=True)

    # ── Phase 1 ──────────────────────────────────────────────────────────
    def capture_training_data(self) -> dict[str, Any]:
        """Phase 1: Capture CDP traces → raw training data."""
        log.info("[%s] Phase 1: capturing training data", self.config.name)
        t0 = time.monotonic()

        # Capture traces from each configured lane
        traces_by_lane: list[dict] = []
        for lane in self.data_config.capture_lanes:
            log.info("Capturing %d traces from lane=%s",
                     self.data_config.capture_prompts_per_lane, lane)
            lane_traces = self.capture.capture_lane(
                lane=lane,
                n_prompts=self.data_config.capture_prompts_per_lane,
                timeout_s=self.data_config.capture_timeout_seconds,
            )
            traces_by_lane.extend(lane_traces)

        # OCR screenshots if configured
        if self.data_config.ocr_screenshots and self.data_config.include_screenshots:
            for trace in traces_by_lane:
                if "screenshot_path" in trace:
                    trace["ocr_text"] = self.capture.ocr_image(
                        trace["screenshot_path"],
                        self.data_config.ocr_service_url,
                    )

        # Build dataset file
        dataset_path = self.pipeline.build_dataset(
            traces_by_lane,
            output_dir=Path(self.config.output_dir) / "data",
            fmt=self.data_config.output_format,
        )

        elapsed = time.monotonic() - t0
        result = {
            "phase": "capture",
            "traces_captured": len(traces_by_lane),
            "lanes": self.data_config.capture_lanes,
            "dataset_path": str(dataset_path),
            "elapsed_s": round(elapsed, 1),
        }
        self._save_checkpoint("phase1_capture", result)
        return result

    # ── Phase 2 ──────────────────────────────────────────────────────────
    def purify_training_data(self, raw_data_path: str) -> dict[str, Any]:
        """Phase 2: CLEANER purification + FAPO flawed-positive check."""
        log.info("[%s] Phase 2: purifying training data", self.config.name)
        t0 = time.monotonic()

        # Load raw traces
        raw_traces = self.pipeline.load_jsonl(raw_data_path)

        # CLEANER purification
        if self.config.use_cleaner:
            purified = purify_trajectories(
                raw_traces,
                strategy=self.cleaner.strategy,
                min_outcome_score=0.7,
            )
        else:
            purified = raw_traces

        # FAPO flawed-positive check
        if self.config.use_fapo:
            validated = [
                t for t in purified
                if self.fapo.check(t)  # drop flawed positives
            ]
        else:
            validated = purified

        # Dedup
        deduped = self.pipeline.deduplicate(
            validated,
            strategy=self.data_config.dedup_strategy,
            threshold=self.data_config.dedup_threshold,
        )

        # Save purified dataset
        clean_path = Path(self.config.output_dir) / "data" / "purified.jsonl"
        clean_path.parent.mkdir(parents=True, exist_ok=True)
        self.pipeline.write_jsonl(deduped, clean_path)

        # Compute RIFT trust weights
        if self.config.use_rift:
            for trace in deduped:
                trace["rift_weight"] = self.rift.compute_weight(
                    trace.get("trust_score", 0.5),
                    trace.get("outcome_ok", False),
                )

        elapsed = time.monotonic() - t0
        result = {
            "phase": "purify",
            "raw_count": len(raw_traces),
            "purified_count": len(purified),
            "validated_count": len(validated),
            "final_count": len(deduped),
            "clean_path": str(clean_path),
            "elapsed_s": round(elapsed, 1),
        }
        self._save_checkpoint("phase2_purify", result)
        return result

    # ── Phase 3 ──────────────────────────────────────────────────────────
    def train(self, data_path: str) -> dict[str, Any]:
        """Phase 3: Run training on A800."""
        log.info("[%s] Phase 3: training on A800", self.config.name)
        t0 = time.monotonic()

        # Build training cell for A800 notebook
        cell_code = self._build_training_cell(data_path)

        # Push to A800 notebook via API
        result = self._submit_to_a800(cell_code)

        elapsed = time.monotonic() - t0
        result.update({"phase": "train", "elapsed_s": round(elapsed, 1)})
        self._save_checkpoint("phase3_train", result)
        return result

    # ── Phase 4 ──────────────────────────────────────────────────────────
    def evaluate(self, checkpoint_path: str) -> dict[str, Any]:
        """Phase 4: Calibrated judge evaluation."""
        log.info("[%s] Phase 4: evaluating checkpoint", self.config.name)
        t0 = time.monotonic()

        scores = calibrated_evaluate(
            checkpoint_path=checkpoint_path,
            eval_pack=self.eval_pack,
            base_model=self.config.base_model,
        )

        elapsed = time.monotonic() - t0
        result = {
            "phase": "eval",
            "scores": scores,
            "elapsed_s": round(elapsed, 1),
        }
        self._save_checkpoint("phase4_eval", result)
        return result

    # ── Full pipeline ────────────────────────────────────────────────────
    def run_full_pipeline(self) -> dict[str, Any]:
        """Execute the full experiment pipeline: capture → purify → train → eval."""
        log.info("[%s] Starting full pipeline", self.config.name)

        # Phase 1: Capture
        cap = self.capture_training_data()

        # Phase 2: Purify
        pur = self.purify_training_data(cap["dataset_path"])

        # Phase 3: Train
        tr = self.train(pur["clean_path"])

        # Phase 4: Eval (if checkpoint produced)
        checkpoint = tr.get("checkpoint_path", "")
        ev = {}
        if checkpoint and Path(checkpoint).exists():
            ev = self.evaluate(checkpoint)

        return {
            "experiment": self.config.name,
            "phases": {
                "capture": cap,
                "purify": pur,
                "train": tr,
                "eval": ev,
            },
        }

    # ── Helpers ──────────────────────────────────────────────────────────
    def _build_training_cell(self, data_path: str) -> str:
        """Build the A800 notebook cell code for training."""
        return f'''
# NEXUS A800 Experiment: {self.config.name}
# Auto-generated {datetime.now(timezone.utc).isoformat()}

import json, torch
from pathlib import Path
from peft import LoraConfig, get_peft_model, TaskType
from transformers import (
    AutoModelForCausalLM, AutoTokenizer,
    TrainingArguments, Trainer,
)
from trl import SFTTrainer, RewardTrainer, GRPOTrainer

# Config
MODEL = "{self.config.base_model}"
DATA  = "{data_path}"
OUT   = "{self.config.output_dir}"
EPOCHS = {self.config.num_epochs}
LR     = {self.config.learning_rate}
BS     = {self.config.batch_size}

# Load model + tokenizer
model = AutoModelForCausalLM.from_pretrained(MODEL, torch_dtype=torch.bfloat16, device_map="auto")
tokenizer = AutoTokenizer.from_pretrained(MODEL)
tokenizer.pad_token = tokenizer.eos_token

# LoRA
peft_config = LoraConfig(
    task_type=TaskType.CAUSAL_LM,
    r=16, lora_alpha=32, lora_dropout=0.05,
    bias="none",
    target_modules=["q_proj","v_proj","k_proj","o_proj"],
)
model = get_peft_model(model, peft_config)

# Load data
def load_data(path):
    with open(path) as f:
        return [json.loads(line) for line in f]

train_data = load_data(DATA)

# Trust-weighted sampling (RIFT)
rift_weights = [t.get("rift_weight", 1.0) for t in train_data]

# Training arguments
args = TrainingArguments(
    output_dir=OUT,
    num_train_epochs=EPOCHS,
    per_device_train_batch_size=BS,
    gradient_accumulation_steps={self.config.gradient_accumulation},
    learning_rate=LR,
    warmup_ratio={self.config.warmup_ratio},
    logging_steps=10,
    save_steps=50,
    save_total_limit=2,
    bf16=True,
    report_to="none",
)

# Train
trainer = SFTTrainer(
    model=model,
    args=args,
    train_dataset=train_data,
    tokenizer=tokenizer,
)
trainer.train()

# Save
trainer.save_model(OUT)
tokenizer.save_pretrained(OUT)
print(f"Checkpoint saved to {{OUT}}")
'''

    def _submit_to_a800(self, cell_code: str) -> dict[str, Any]:
        """Submit a training cell to the A800 notebook via HTTP API."""
        import urllib.request

        url = f"{A800_BASE_URL}/api/notebook/{A800_NOTEBOOK}/cell"
        body = json.dumps({"source": cell_code, "type": "code"}).encode()
        req = urllib.request.Request(
            url, data=body, method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode())
                return {"status": "submitted", "cell_id": result.get("id", "")}
        except Exception as e:
            log.error("A800 submission failed: %s", e)
            return {"status": "error", "error": str(e)}

    def _save_checkpoint(self, name: str, data: dict[str, Any]) -> None:
        """Save a phase checkpoint."""
        path = self._checkpoint_dir / f"{name}.json"
        path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def run_experiment(template_name: str) -> dict[str, Any]:
    """Convenience: run a predefined experiment template."""
    from .config import EXPERIMENT_TEMPLATES
    cfg = EXPERIMENT_TEMPLATES[template_name]
    data_cfg = DataPipelineConfig()
    orch = A800Orchestrator(cfg, data_cfg)
    return orch.run_full_pipeline()
