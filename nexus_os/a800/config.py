#!/usr/bin/env python3
"""
NEXUS A800 Experiment Configuration
=====================================
Central config for all A800 training experiments.
Integrates with NEXUS trust ledger, REASONS-DB, and CDP trace capture.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

# Paths
REPO = Path(r"C:\Users\speci.000\Documents\NEXUS")
REASONS_DB = REPO / ".nexus" / "reasons_db"
TRUST_MEMORY = REPO / ".nexus" / "trust_memory.json"
A800_SESSION = Path("/home/mw/project/NEXUS_session4")
A800_NOTEBBOOK = "6a4bd98342108cc3a0ec0d68"
A800_BASE_URL = "https://discovery.intern-ai.org.cn"


class ExperimentType(Enum):
    SERA_SFT = "sera_sft"          # Soft-verified repo-native SFT
    RIFT_SFT = "rift_sft"          # Reward-informed trust-weighted SFT
    RFT = "rft"                     # Rejection sampling fine-tuning
    GRPO = "grpo"                   # Group relative policy optimization
    FTPO = "ftpo"                   # Final-token preference optimization
    GUARD_DPO = "guard_dpo"         # Guard preference optimization
    CLEANER = "cleaner"            # Trajectory purification


class DataType(Enum):
    CDP_TRACES = "cdp_traces"      # Captured browser automation traces
    REASONS_DB = "reasons_db"      # Existing NEXUS reasoning traces
    JAILBREAK = "jailbreak"        # 397-skill jailbreak dictionary
    ADVERSARIAL = "adversarial"    # Red-team adversarial scenarios
    SYNTHETIC = "synthetic"        # Teacher-generated synthetic traces


@dataclass
class ExperimentConfig:
    """Single experiment configuration."""
    name: str
    experiment_type: ExperimentType
    base_model: str = "Qwen/Qwen2.5-1.5B-Instruct"
    dataset_path: str = ""
    output_dir: str = ""
    
    # Training hyperparameters
    learning_rate: float = 2e-4
    num_epochs: int = 1
    batch_size: int = 4
    gradient_accumulation: int = 4
    max_seq_length: int = 4096
    warmup_ratio: float = 0.1
    
    # RIFT trust weighting
    use_rift: bool = True
    trust_alpha: float = 1.0  # Beta posterior alpha
    trust_beta: float = 1.0   # Beta posterior beta
    min_trust_weight: float = 0.1
    
    # SERA soft verification
    use_sera: bool = True
    verification_threshold: float = 0.8
    
    # CLEANER purification
    use_cleaner: bool = True
    purification_strategy: str = "outcome_verified"
    
    # FAPO flawed-positive check
    use_fapo: bool = True
    process_check_judge: str = "programmatic_verdict"
    
    # FTPO (preference)
    use_ftpo: bool = False
    preference_pairs_path: str = ""
    
    # Evaluation
    eval_pack: list[str] = field(default_factory=lambda: [
        "hellaswag_val", "eq_bench", "aa_omniscience", "verifybench"
    ])
    
    # A800 resource config
    gpu_type: str = "A800-SXM4-80GB"
    num_gpus: int = 1
    max_hours: float = 8.0
    
    def __post_init__(self):
        if not self.output_dir:
            self.output_dir = str(A800_SESSION / "experiments" / self.name)


@dataclass
class DataPipelineConfig:
    """Configuration for CDP → training data pipeline."""
    # Trace capture
    capture_lanes: list[str] = field(default_factory=lambda: [
        "grok", "chatgpt", "gemini", "deepseek", "qwen"
    ])
    capture_prompts_per_lane: int = 50
    capture_timeout_seconds: int = 300
    
    # Trace format
    output_format: str = "jsonl"  # jsonl or parquet
    include_dom_snapshot: bool = True
    include_screenshots: bool = True
    ocr_screenshots: bool = True
    ocr_service_url: str = "http://127.0.0.1:7360"
    
    # Trust filtering
    min_trust_score: float = 0.6
    partition: str = "trainable"  # trainable, reference, eval
    
    # Deduplication
    dedup_strategy: str = "prompt_hash"
    dedup_threshold: float = 0.85


# Predefined experiment templates from PAPERS distillation
EXPERIMENT_TEMPLATES = {
    "sera_v1": ExperimentConfig(
        name="sera_v1_opening",
        experiment_type=ExperimentType.SERA_SFT,
        use_sera=True,
        use_rift=True,
        use_cleaner=True,
        num_epochs=2,
        base_model="Qwen/Qwen2.5-1.5B-Instruct",
    ),
    "rift_v1": ExperimentConfig(
        name="rift_v1_trust_weighted",
        experiment_type=ExperimentType.RIFT_SFT,
        use_rift=True,
        use_cleaner=True,
        use_fapo=True,
        num_epochs=1,
        base_model="Qwen/Qwen2.5-1.5B-Instruct",
    ),
    "guard_dpo_v1": ExperimentConfig(
        name="guard_dpo_v1_jailbreak",
        experiment_type=ExperimentType.GUARD_DPO,
        use_ftpo=False,
        preference_pairs_path=str(REPO / "DOCKERaiGORDON"),
        base_model="meta-llama/Llama-Guard-3-1B",
    ),
    "ftp0_v1": ExperimentConfig(
        name="ftp0_v1_style",
        experiment_type=ExperimentType.FTPO,
        use_ftpo=True,
        num_epochs=1,
        base_model="Qwen/Qwen2.5-1.5B-Instruct",
    ),
}
