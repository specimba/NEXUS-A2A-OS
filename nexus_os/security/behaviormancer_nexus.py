"""
BehaviorMancer NEXUS Integration - Remove Refusal Behavior from Guard Models

Uses orthogonal projection (abliteration) to remove false refusal patterns
from guard models, reducing false positives on benign security research queries.

Based on:
- Arditi et al. (2024) - "Refusal in Language Models Is Mediated by a Single Direction"
- Lai - Norm-Preserving Biprojected Abliteration
- Fang et al. (ICLR 2025) - AlphaEdit: Null-Space Constrained Knowledge Editing
"""

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Optional
from dataclasses import asdict, dataclass

from nexus_os.nexusclaw.security import (
    BEHAVIOR_CONTROL_REQUIRED_CONTROLS,
    validate_model_intake,
)


@dataclass
class NexusBehaviorMancerConfig:
    """NEXUS-specific configuration for BehaviorMancer."""
    
    # Model to modify (guard model)
    model_path: str = ""  # Path to guard model (HuggingFace or local)
    
    # Target behavior: BENIGN QUERIES (behavior to EXHIBIT)
    # These are queries that should NOT be refused
    target_dataset_path: str = ""  # Path to benign query dataset
    target_column: str = "text"  # Column name for structured formats
    
    # Baseline behavior: REFUSALS (behavior to REMOVE)
    # These are refusal responses
    baseline_dataset_path: str = ""  # Path to refusal dataset
    baseline_column: str = "text"  # Column name for structured formats
    
    # Preservation queries (capabilities to preserve)
    preservation_dataset_path: str = ""  # Path to preservation queries
    preservation_column: str = "text"  # Column name for structured formats
    
    # Output
    output_path: str = ""  # Where to save modified model
    
    # Abliteration settings
    n_samples: int = 30  # Number of sample pairs
    direction_multiplier: float = 1.0  # Ablation strength (0.0 - 1.0+)
    precision: str = "float16"  # "float16", "bfloat16", "float32"
    
    # Advanced options
    norm_preservation: bool = True  # Preserve weight magnitudes
    winsorization: bool = False  # Clip outlier activations
    winsorization_threshold: float = 0.995  # Quantile threshold for winsorization
    null_space_constraints: bool = False  # Preserve capabilities using preservation dataset
    adaptive_layer_weighting: bool = False  # Focus on middle-to-later layers
    
    # Layer selection
    start_layer_ratio: float = 0.2  # Start from 20% of layers
    end_layer_ratio: float = 0.9  # End at 90% of layers
    
    # Component filtering
    only_modify_components: Optional[list] = None  # Only modify these component types (e.g., ["q_proj", "k_proj", "v_proj", "o_proj"])
    skip_layers: Optional[list] = None  # Skip these layer indices entirely
    
    # Multimodal protection
    protect_vision_components: bool = True  # Auto-protect vision encoder/projector
    freeze_protected_components: bool = True  # Actually freeze (requires_grad=False) protected components


@dataclass
class BehaviorControlProposal:
    """Dry-run proposal for a governed behavior-control experiment."""

    proposal_id: str
    model_path: str
    output_path: str
    method_class: str
    dry_run: bool
    writes_weights: bool
    can_write_weights: bool
    route_class: str
    lab_allowed: bool
    required_controls: list[str]
    artifact_manifest: dict[str, Any]
    blocked_reason: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class NexusBehaviorMancer:
    """
    NEXUS wrapper for BehaviorMancer.
    
    Removes refusal behavior from guard models using orthogonal projection.
    """
    
    def __init__(self, config: Optional[NexusBehaviorMancerConfig] = None):
        """
        Initialize NexusBehaviorMancer.
        
        Args:
            config: Configuration for behavior removal
        """
        self.config = config or NexusBehaviorMancerConfig()
        self.behavior_mancer = None
        self.device = "deferred"
        
    def log(self, message: str):
        """Log a message."""
        print(f"[NexusBehaviorMancer] {message}")

    def prepare_proposal(
        self,
        *,
        method_class: str = "refusal_vector_abliteration",
        kaiju_approved: bool = False,
        vap_record_id: Optional[str] = None,
        allow_weight_write: bool = False,
    ) -> BehaviorControlProposal:
        """Create a dry-run artifact manifest without loading or writing weights."""
        decision = validate_model_intake(
            self.config.model_path,
            labels=["behavior_control", "refusal_analysis"],
            requested_lane="behavior_control",
            intent="refusal restoration behavior analysis guard stress testing",
        )
        config_payload = json.dumps(asdict(self.config), sort_keys=True, default=str)
        artifact_hash = hashlib.sha256(config_payload.encode("utf-8")).hexdigest()
        can_write = bool(
            decision.lab_allowed
            and kaiju_approved
            and vap_record_id
            and allow_weight_write
        )
        manifest = {
            "artifact_hash": artifact_hash,
            "method_class": method_class,
            "model_path": self.config.model_path,
            "target_dataset_path": self.config.target_dataset_path,
            "baseline_dataset_path": self.config.baseline_dataset_path,
            "preservation_dataset_path": self.config.preservation_dataset_path,
            "layer_range": [self.config.start_layer_ratio, self.config.end_layer_ratio],
            "direction_multiplier": self.config.direction_multiplier,
            "n_samples": self.config.n_samples,
            "null_space_constraints": self.config.null_space_constraints,
            "before_refusal_score": None,
            "after_refusal_score": None,
            "capability_retention_score": None,
            "vap_record_id": vap_record_id,
            "notes": "Dry-run manifest only; no model load or weight write performed.",
        }
        return BehaviorControlProposal(
            proposal_id=f"behavior-control-{artifact_hash[:12]}",
            model_path=self.config.model_path,
            output_path=self.config.output_path,
            method_class=method_class,
            dry_run=True,
            writes_weights=False,
            can_write_weights=can_write,
            route_class=decision.route_class,
            lab_allowed=decision.lab_allowed,
            required_controls=list(decision.required_controls or BEHAVIOR_CONTROL_REQUIRED_CONTROLS),
            artifact_manifest=manifest,
            blocked_reason=decision.blocked_reason,
        )
    
    def load_datasets(self) -> tuple[list[str], list[str], list[str]]:
        """
        Load target, baseline, and preservation datasets.
        
        Returns:
            Tuple of (target_samples, baseline_samples, preservation_samples)
        """
        self.log("Loading datasets...")
        
        target_samples = self._load_dataset(
            self.config.target_dataset_path, 
            "target (benign queries)"
        )
        
        baseline_samples = self._load_dataset(
            self.config.baseline_dataset_path,
            "baseline (refusals)"
        )
        
        preservation_samples = self._load_dataset(
            self.config.preservation_dataset_path,
            "preservation"
        )
        
        self.log(f"Loaded {len(target_samples)} target, {len(baseline_samples)} baseline, {len(preservation_samples)} preservation samples")
        
        return target_samples, baseline_samples, preservation_samples
    
    def _load_dataset(self, path: str, name: str) -> list[str]:
        """Load a dataset from file."""
        if not path:
            self.log(f"No {name} dataset provided, using defaults")
            return []
        
        path = Path(path)
        if not path.exists():
            self.log(f"Warning: {name} dataset not found at {path}")
            return []
        
        samples = []
        ext = path.suffix.lower()
        
        if ext == ".txt":
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        samples.append(line)
        
        elif ext == ".jsonl":
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        if isinstance(data, dict):
                            # Try multiple possible keys
                            text = data.get("text") or data.get("query") or data.get("prompt") or data.get("content")
                            if text:
                                samples.append(str(text))
                        elif isinstance(data, str):
                            samples.append(data)
                    except json.JSONDecodeError:
                        continue
        
        elif ext == ".json":
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and "text" in item:
                            samples.append(str(item["text"]))
                        elif isinstance(item, str):
                            samples.append(item)
        
        self.log(f"Loaded {len(samples)} samples from {name}")
        return samples
    
    def run_abliteration(
        self,
        *,
        kaiju_approved: bool = False,
        vap_record_id: Optional[str] = None,
        allow_weight_write: bool = False,
    ) -> bool:
        """
        Run the abliteration process to remove refusal behavior.
        
        Returns:
            True if successful, False otherwise
        """
        proposal = self.prepare_proposal(
            kaiju_approved=kaiju_approved,
            vap_record_id=vap_record_id,
            allow_weight_write=allow_weight_write,
        )
        if not proposal.can_write_weights:
            self.log("Refusing weight write: Behavior-Control Lab requires KAIJU approval, VAP record, and explicit weight-write approval.")
            self.log(f"Proposal id: {proposal.proposal_id}")
            return False

        self.log("Starting abliteration process...")

        try:
            import torch
            vendor_path = str(Path(__file__).parent.parent.parent / "vendor" / "ShareGPT-Formaxxing")
            if vendor_path not in sys.path:
                sys.path.insert(0, vendor_path)
            from App.BehaviorMancer.BehaviorMancer import (
                BehaviorMancer as BaseBehaviorMancer,
                BehaviorMancerConfig,
            )
        except ImportError as exc:
            self.log(f"Error: BehaviorMancer dependencies unavailable: {exc}")
            return False

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Load datasets
        target_samples, baseline_samples, preservation_samples = self.load_datasets()
        
        if not target_samples:
            self.log("Error: No target samples provided")
            return False
        
        if not baseline_samples:
            self.log("Error: No baseline samples provided")
            return False
        
        # Create base BehaviorMancer config
        base_config = BehaviorMancerConfig(
            model_source="huggingface" if not Path(self.config.model_path).exists() else "local",
            model_path=self.config.model_path,
            target_source="local",
            target_path="",
            target_column="text",
            baseline_source="local",
            baseline_path="",
            baseline_column="text",
            preservation_source="local",
            preservation_path="",
            preservation_column="text",
            n_samples=self.config.n_samples,
            direction_multiplier=self.config.direction_multiplier,
            precision=self.config.precision,
            output_path=self.config.output_path,
            norm_preservation=self.config.norm_preservation,
            winsorization=False,
            null_space_constraints=self.config.null_space_constraints,
            adaptive_layer_weighting=False,
            start_layer_ratio=self.config.start_layer_ratio,
            end_layer_ratio=self.config.end_layer_ratio,
            protect_vision_components=True,
            only_modify_components=self.config.only_modify_components,
            skip_layers=self.config.skip_layers,
        )
        
        # Create BehaviorMancer instance
        self.behavior_mancer = BaseBehaviorMancer(
            config=base_config,
            log_callback=lambda msg: self.log(f"  [BehaviorMancer] {msg}")
        )
        
        # Load model
        self.log("Loading model...")
        if not self.behavior_mancer.load_model():
            self.log("Error: Failed to load model")
            return False
        
        # Extract behavior direction
        self.log("Extracting behavior direction...")
        behavior_direction = self.behavior_mancer.extract_behavior_direction(
            target_samples, baseline_samples
        )
        
        if behavior_direction is None:
            self.log("Error: Failed to extract behavior direction")
            return False
        
        # Compute null-space projector if enabled
        null_space_projector = None
        if self.config.null_space_constraints and preservation_samples:
            self.log("Computing null-space projector...")
            null_space_projector = self.behavior_mancer.compute_null_space_projector(
                preservation_samples
            )
        
        # Remove behavior
        self.log("Removing refusal behavior...")
        if not self.behavior_mancer.remove_behavior(null_space_projector):
            self.log("Error: Failed to remove behavior")
            return False
        
        # Save model
        self.log("Saving modified model...")
        if not self.behavior_mancer.save_model():
            self.log("Error: Failed to save model")
            return False
        
        self.log("Abliteration complete!")
        return True
    
    def test_model(self, prompt: str, max_new_tokens: int = 256) -> str:
        """
        Test the modified model.
        
        Args:
            prompt: Input prompt
            max_new_tokens: Maximum tokens to generate
            
        Returns:
            Generated response
        """
        if self.behavior_mancer is None:
            self.log("Error: Model not loaded")
            return ""
        
        return self.behavior_mancer.test_model(prompt, max_new_tokens)


def create_default_nexus_config() -> NexusBehaviorMancerConfig:
    """
    Create default NEXUS configuration for abliteration.
    
    Returns:
        Default configuration
    """
    nexus_root = Path(__file__).parent.parent.parent
    datasets_dir = nexus_root / "datasets"
    
    return NexusBehaviorMancerConfig(
        model_path="",  # Must be set by user
        target_dataset_path=str(datasets_dir / "benign_expanded.jsonl"),
        baseline_dataset_path=str(datasets_dir / "refusals.txt"),
        preservation_dataset_path=str(datasets_dir / "preservation.txt"),
        output_path=str(nexus_root / "models" / "guard-abliterated"),
        n_samples=30,
        direction_multiplier=1.0,
        precision="float16",
        norm_preservation=True,
        null_space_constraints=True,
        protect_vision_components=True,
        start_layer_ratio=0.2,
        end_layer_ratio=0.9,
    )


if __name__ == "__main__":
    # Dry-run example only. Real weight writes require explicit KAIJU/VAP approval.
    config = create_default_nexus_config()
    config.model_path = "Qwen/Qwen2.5-1.5B"  # Example: abliterate Qwen2.5
    
    mancer = NexusBehaviorMancer(config)
    print(json.dumps(mancer.prepare_proposal().to_dict(), indent=2))
