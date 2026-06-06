"""
TWAVE v2.0 Landau-Ginzburg Tracker Calibration Script
Purpose: Generate temperature-swept datasets and fit thermodynamic parameters
Usage: python calibrate_twave_v2_landau_ginzburg.py --config config.yaml

This script:
1. Generates temperature-swept outputs from existing HF datasets
2. Computes per-token order parameters (entropy, attention mass, reward density)
3. Fits critical temperature (Tc) and healing length (xi) parameters
4. Creates calibration data for the Landau-Ginzburg tracker
5. Validates the thermodynamic framework against empirical data
"""

import os
import json
import argparse
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import numpy as np
from scipy.optimize import curve_fit
from scipy.stats import entropy as scipy_entropy
import torch
import torch.nn.functional as F
from datasets import load_dataset
from transformers import AutoModelForCausalLM, AutoTokenizer
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class CalibrationConfig:
    """Configuration for TWAVE v2.0 calibration"""
    
    # Model configuration
    model_name: str = "gpt2"  # Starting with small model for calibration
    model_path: Optional[str] = None  # Path to local model if available
    
    # Dataset configuration
    base_datasets: List[str] = None  # HF dataset names
    num_prompts: int = 100  # Number of seed prompts
    temperatures: List[float] = None  # Temperature values to sweep
    
    # Output configuration
    output_dir: str = "foundry_datasets/twave_calibration"
    batch_size: int = 4
    max_new_tokens: int = 256
    
    # Thermodynamic parameters
    base_temperature: float = 0.7
    temperature_range: Tuple[float, float] = (0.1, 2.0)
    num_temperature_points: int = 9
    
    # Order parameter weights
    entropy_weight: float = 1.0
    attention_weight: float = 0.5
    reward_weight: float = 0.3
    
    # Validation
    validation_split: float = 0.2
    min_trust_score: float = 0.7  # Minimum confidence for calibration points
    
    def __post_init__(self):
        if self.base_datasets is None:
            self.base_datasets = [
                "truthfulqa/truthful_qa",
                "gsm8k/main",
                "hotpotqa/hotpot_qa"
            ]
        
        if self.temperatures is None:
            self.temperatures = np.linspace(*self.temperature_range, self.num_temperature_points).tolist()


@dataclass
class TokenDynamics:
    """Per-token dynamics for thermodynamic analysis"""
    
    token_id: int
    token_text: str
    position: int
    
    # Order parameters
    entropy: float
    logit_ratio: float  # z2/z1 for MARS baseline
    attention_mass: float
    reward_density: float
    
    # Thermodynamic quantities
    free_energy: float
    chemical_potential: float
    
    # Context
    temperature: float
    prompt_id: str
    dataset: str
    
    # Hallucination detection
    is_hallucination: bool
    hallucination_type: Optional[str] = None


@dataclass
class CalibrationPoint:
    """Single calibration data point"""
    
    prompt_id: str
    dataset: str
    prompt: str
    temperature: float
    
    # Global metrics
    total_entropy: float
    total_free_energy: float
    
    # Per-token dynamics
    token_dynamics: List[TokenDynamics]
    
    # Quality assessment
    output_text: str
    trust_score: float
    is_calibrated: bool


class TWAVECalibrationEngine:
    """
    Main calibration engine for TWAVE v2.0 Landau-Ginzburg tracker.
    
    This engine:
    - Generates temperature-swept outputs
    - Extracts per-token order parameters
    - Fits thermodynamic parameters
    - Validates the framework
    """
    
    def __init__(self, config: CalibrationConfig):
        """
        Initialize calibration engine.
        
        Args:
            config: Calibration configuration
        """
        self.config = config
        self.setup_directories()
        self.load_model()
        self.calibration_data: List[CalibrationPoint] = []
        self.thermodynamic_parameters: Dict[str, Any] = {}
    
    def setup_directories(self):
        """Setup output directories"""
        self.output_dir = Path(self.config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.calibration_dir = self.output_dir / "calibration_data"
        self.calibration_dir.mkdir(exist_ok=True)
        
        self.fitted_params_dir = self.output_dir / "fitted_parameters"
        self.fitted_params_dir.mkdir(exist_ok=True)
    
    def load_model(self):
        """Load the model and tokenizer for calibration"""
        logger.info(f"Loading model: {self.config.model_name}")
        
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.config.model_name,
            trust_remote_code=True
        )
        
        if self.config.model_path and Path(self.config.model_path).exists():
            logger.info(f"Loading local model from: {self.config.model_path}")
            self.model = AutoModelForCausalLM.from_pretrained(
                self.config.model_path,
                trust_remote_code=True
            )
        else:
            logger.info(f"Loading pretrained model: {self.config.model_name}")
            self.model = AutoModelForCausalLM.from_pretrained(
                self.config.model_name,
                trust_remote_code=True
            )
        
        self.model.eval()
        
        if torch.cuda.is_available():
            self.model = self.model.cuda()
            logger.info("Using CUDA acceleration")
        
        self.device = next(self.model.parameters()).device
    
    def generate_calibration_prompts(self) -> List[Dict[str, Any]]:
        """
        Generate seed prompts from base datasets.
        
        Returns:
            List of prompt dictionaries with dataset and ground truth
        """
        prompts = []
        
        for dataset_name in self.config.base_datasets:
            logger.info(f"Processing dataset: {dataset_name}")
            
            try:
                dataset = load_dataset(dataset_name, split="train")
                
                # Extract prompts based on dataset type
                dataset_prompts = self.extract_prompts_from_dataset(dataset, dataset_name)
                prompts.extend(dataset_prompts)
                
            except Exception as e:
                logger.error(f"Failed to load dataset {dataset_name}: {e}")
                continue
        
        # Limit to requested number of prompts
        prompts = prompts[:self.config.num_prompts]
        
        logger.info(f"Generated {len(prompts)} calibration prompts")
        return prompts
    
    def extract_prompts_from_dataset(self, dataset, dataset_name: str) -> List[Dict[str, Any]]:
        """Extract prompts from a specific dataset"""
        prompts = []
        
        for i, example in enumerate(dataset):
            if i >= self.config.num_prompts // len(self.config.base_datasets):
                break
            
            # Extract prompt based on dataset structure
            prompt = self.format_prompt_from_example(example, dataset_name)
            
            if prompt:
                prompts.append({
                    "prompt_id": f"{dataset_name.replace('/', '-')}_{i:04d}",
                    "prompt": prompt,
                    "dataset": dataset_name,
                    "example": example
                })
        
        return prompts
    
    def format_prompt_from_example(self, example: Any, dataset_name: str) -> Optional[str]:
        """Format a prompt from a dataset example"""
        try:
            if "truthfulqa" in dataset_name.lower():
                return example.get("question", "")
            elif "gsm8k" in dataset_name.lower():
                return example.get("question", "")
            elif "hotpotqa" in dataset_name.lower():
                return example.get("question", "")
            else:
                # Generic fallback
                for key in example.keys():
                    if isinstance(example[key], str) and len(example[key]) > 10:
                        return example[key]
                return None
        except Exception as e:
            logger.warning(f"Failed to format prompt from example: {e}")
            return None
    
    def generate_temperature_sweep(self, prompt_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate outputs at different temperatures for a single prompt.
        
        Args:
            prompt_data: Dictionary containing prompt and metadata
            
        Returns:
            List of generation results at different temperatures
        """
        results = []
        prompt = prompt_data["prompt"]
        prompt_id = prompt_data["prompt_id"]
        dataset = prompt_data["dataset"]
        
        for temperature in self.config.temperatures:
            try:
                # Tokenize input
                inputs = self.tokenizer(
                    prompt,
                    return_tensors="pt",
                    truncation=True,
                    max_length=512
                ).to(self.device)
                
                # Generate with current temperature
                with torch.no_grad():
                    outputs = self.model.generate(
                        **inputs,
                        max_new_tokens=self.config.max_new_tokens,
                        temperature=temperature,
                        do_sample=True,
                        top_p=0.9,
                        return_dict_in_generate=True,
                        output_scores=True,
                        output_hidden_states=True
                    )
                
                # Extract generated tokens
                generated_ids = outputs.sequences[0][inputs.input_ids.shape[1]:]
                generated_text = self.tokenizer.decode(generated_ids, skip_special_tokens=True)
                
                # Extract per-token dynamics
                token_dynamics = self.extract_token_dynamics(
                    outputs, inputs.input_ids.shape[1], temperature, prompt_id, dataset
                )
                
                # Compute global thermodynamic metrics
                total_entropy = sum(td.entropy for td in token_dynamics)
                total_free_energy = sum(td.free_energy for td in token_dynamics)
                
                results.append({
                    "prompt_id": prompt_id,
                    "dataset": dataset,
                    "temperature": temperature,
                    "output_text": generated_text,
                    "token_dynamics": [asdict(td) for td in token_dynamics],
                    "total_entropy": total_entropy,
                    "total_free_energy": total_free_energy
                })
                
            except Exception as e:
                logger.error(f"Failed to generate at temperature {temperature}: {e}")
                continue
        
        return results
    
    def extract_token_dynamics(
        self,
        outputs,
        input_length: int,
        temperature: float,
        prompt_id: str,
        dataset: str
    ) -> List[TokenDynamics]:
        """
        Extract per-token thermodynamic quantities.
        
        Args:
            outputs: Model generation outputs
            input_length: Length of input prompt
            temperature: Generation temperature
            prompt_id: Prompt identifier
            dataset: Dataset name
            
        Returns:
            List of TokenDynamics objects
        """
        token_dynamics = []
        generated_ids = outputs.sequences[0][input_length:]
        
        # Extract scores (logits) and hidden states
        scores = outputs.scores if outputs.scores else None
        hidden_states = outputs.hidden_states if outputs.hidden_states else None
        
        for i, token_id in enumerate(generated_ids):
            token_text = self.tokenizer.decode([token_id], skip_special_tokens=True)
            
            # Compute entropy from logits
            if scores and i < len(scores):
                logits = scores[i][0, -1, :]  # Logits for last position
                probs = F.softmax(logits, dim=-1)
                entropy = torch.distributions.Categorical(probs).entropy().item()
                
                # Compute logit ratio (for MARS baseline)
                sorted_logits, _ = torch.sort(logits, descending=True)
                if len(sorted_logits) > 1:
                    logit_ratio = (sorted_logits[0] - sorted_logits[1]).item()
                else:
                    logit_ratio = 0.0
            else:
                entropy = 0.0
                logit_ratio = 0.0
            
            # Compute attention mass (if hidden states available)
            attention_mass = 0.0
            if hidden_states and i < len(hidden_states):
                # Approximate attention mass from hidden state norm
                hidden_state = hidden_states[i][-1][0, i, :]  # Last layer, current position
                attention_mass = torch.norm(hidden_state).item()
            
            # Compute reward density (placeholder - would need reward model)
            reward_density = 0.0
            
            # Compute free energy using Landau-Ginzburg theory
            # F = E - TS (simplified: F = -T * entropy)
            free_energy = -temperature * entropy
            
            # Chemical potential (placeholder)
            chemical_potential = 0.0
            
            # Hallucination detection (simplified)
            is_hallucination = self.detect_hallucination(token_text, i, generated_ids[:i+1])
            
            token_dynamics.append(TokenDynamics(
                token_id=token_id.item() if torch.is_tensor(token_id) else token_id,
                token_text=token_text,
                position=i,
                entropy=entropy,
                logit_ratio=logit_ratio,
                attention_mass=attention_mass,
                reward_density=reward_density,
                free_energy=free_energy,
                chemical_potential=chemical_potential,
                temperature=temperature,
                prompt_id=prompt_id,
                dataset=dataset,
                is_hallucination=is_hallucination,
                hallucination_type="syntax" if is_hallucination else None
            ))
        
        return token_dynamics
    
    def detect_hallucination(self, token_text: str, position: int, generated_ids: List[int]) -> bool:
        """
        Detect if a token represents a hallucination.
        
        This is a simplified detection. In production, would use:
        - Factual verification against knowledge base
        - Syntax checking for code
        - Logical consistency checking
        
        Args:
            token_text: The token text
            position: Position in generation
            generated_ids: Generated token IDs so far
            
        Returns:
            True if hallucination detected, False otherwise
        """
        # Very basic detection based on heuristics
        # In production, this would use more sophisticated methods
        
        # Check for unlikely token sequences
        if position > 0:
            # Simple n-gram consistency check
            # In production, would use language model perplexity
            pass
        
        # Check for known hallucination patterns
        hallucination_patterns = [
            "I don't know",
            "I cannot answer",
            "that's not in my training"
        ]
        
        if any(pattern in token_text.lower() for pattern in hallucination_patterns):
            return True
        
        return False
    
    def run_calibration_sweep(self) -> None:
        """Run the complete calibration sweep across all prompts and temperatures"""
        logger.info("Starting calibration sweep...")
        
        # Generate calibration prompts
        prompts = self.generate_calibration_prompts()
        
        # Process each prompt
        for prompt_data in tqdm(prompts, desc="Processing prompts"):
            try:
                results = self.generate_temperature_sweep(prompt_data)
                
                for result in results:
                    calibration_point = CalibrationPoint(
                        prompt_id=result["prompt_id"],
                        dataset=result["dataset"],
                        prompt=prompt_data["prompt"],
                        temperature=result["temperature"],
                        total_entropy=result["total_entropy"],
                        total_free_energy=result["total_free_energy"],
                        token_dynamics=[TokenDynamics(**td) for td in result["token_dynamics"]],
                        output_text=result["output_text"],
                        trust_score=0.8,  # Placeholder - would use actual verification
                        is_calibrated=True
                    )
                    
                    self.calibration_data.append(calibration_point)
                
            except Exception as e:
                logger.error(f"Failed to process prompt {prompt_data['prompt_id']}: {e}")
                continue
        
        logger.info(f"Calibration sweep complete: {len(self.calibration_data)} points generated")
        
        # Save calibration data
        self.save_calibration_data()
    
    def save_calibration_data(self) -> None:
        """Save calibration data to disk"""
        output_file = self.calibration_dir / "calibration_data.json"
        
        # Convert to serializable format
        serializable_data = []
        for point in self.calibration_data:
            serializable_data.append({
                "prompt_id": point.prompt_id,
                "dataset": point.dataset,
                "prompt": point.prompt,
                "temperature": point.temperature,
                "total_entropy": point.total_entropy,
                "total_free_energy": point.total_free_energy,
                "token_dynamics": [asdict(td) for td in point.token_dynamics],
                "output_text": point.output_text,
                "trust_score": point.trust_score,
                "is_calibrated": point.is_calibrated
            })
        
        with open(output_file, 'w') as f:
            json.dump(serializable_data, f, indent=2)
        
        logger.info(f"Calibration data saved to {output_file}")
    
    def fit_thermodynamic_parameters(self) -> Dict[str, Any]:
        """
        Fit thermodynamic parameters from calibration data.
        
        This fits:
        - Critical temperature (Tc) for phase transitions
        - Healing length (xi) for error recovery
        - Order parameter coefficients
        
        Returns:
            Dictionary of fitted parameters
        """
        logger.info("Fitting thermodynamic parameters...")
        
        if not self.calibration_data:
            logger.warning("No calibration data available for fitting")
            return {}
        
        # Organize data by temperature
        temps = []
        entropies = []
        free_energies = []
        
        for point in self.calibration_data:
            temps.append(point.temperature)
            entropies.append(point.total_entropy)
            free_energies.append(point.total_free_energy)
        
        # Sort by temperature
        sorted_indices = np.argsort(temps)
        temps = np.array(temps)[sorted_indices]
        entropies = np.array(entropies)[sorted_indices]
        free_energies = np.array(free_energies)[sorted_indices]
        
        # Fit critical temperature (Tc) where entropy peaks
        def gaussian_curve(x, a, x0, sigma):
            return a * np.exp(-0.5 * ((x - x0) / sigma) ** 2)
        
        try:
            params, _ = curve_fit(
                gaussian_curve,
                temps,
                entropies,
                p0=[max(entropies), np.mean(temps), 0.5],
                maxfev=10000
            )
            
            tc = params[1]  # Peak temperature
            tc_confidence = params[2]  # Width indicates confidence
            
        except Exception as e:
            logger.error(f"Failed to fit critical temperature: {e}")
            tc = np.mean(temps)  # Fallback
            tc_confidence = 1.0
        
        # Fit healing length (xi) from correlation length analysis
        healing_length = self.estimate_healing_length()
        
        # Estimate order parameter weights
        entropy_weight = self.config.entropy_weight
        attention_weight = self.config.attention_weight
        reward_weight = self.config.reward_weight
        
        self.thermodynamic_parameters = {
            "critical_temperature": float(tc),
            "tc_confidence": float(tc_confidence),
            "healing_length": float(healing_length),
            "order_parameter_weights": {
                "entropy": entropy_weight,
                "attention": attention_weight,
                "reward": reward_weight
            },
            "temperature_range": [
                float(min(temps)),
                float(max(temps))
            ],
            "fitting_quality": self.evaluate_fitting_quality(temps, entropies, params if 'params' in locals() else None)
        }
        
        # Save fitted parameters
        self.save_fitted_parameters()
        
        logger.info(f"Thermodynamic parameters fitted: Tc = {tc:.3f}, xi = {healing_length:.3f}")
        
        return self.thermodynamic_parameters
    
    def estimate_healing_length(self) -> float:
        """
        Estimate healing length (xi) from error recovery patterns.
        
        Healing length represents how many tokens it takes for the system
        to self-correct after a hallucination or error.
        
        Returns:
            Estimated healing length in tokens
        """
        # Analyze hallucination patterns across calibration data
        healing_lengths = []
        
        for point in self.calibration_data:
            for i, td in enumerate(point.token_dynamics):
                if td.is_hallucination:
                    # Find next non-hallucinated token
                    for j in range(i+1, len(point.token_dynamics)):
                        if not point.token_dynamics[j].is_hallucination:
                            healing_lengths.append(j - i)
                            break
        
        if healing_lengths:
            return np.mean(healing_lengths)
        else:
            return 3.0  # Default healing length
    
    def evaluate_fitting_quality(self, temps: np.ndarray, entropies: np.ndarray, params: Optional[np.ndarray] = None) -> str:
        """Evaluate the quality of the thermodynamic fit"""
        if params is None:
            return "unknown"
        
        try:
            # Calculate R-squared
            predicted = params[0] * np.exp(-0.5 * ((temps - params[1]) / params[2]) ** 2)
            ss_res = np.sum((entropies - predicted) ** 2)
            ss_tot = np.sum((entropies - np.mean(entropies)) ** 2)
            r_squared = 1 - (ss_res / ss_tot)
            
            if r_squared > 0.8:
                return "excellent"
            elif r_squared > 0.6:
                return "good"
            elif r_squared > 0.4:
                return "fair"
            else:
                return "poor"
                
        except:
            return "unknown"
    
    def save_fitted_parameters(self) -> None:
        """Save fitted thermodynamic parameters"""
        output_file = self.fitted_params_dir / "thermodynamic_parameters.json"
        
        with open(output_file, 'w') as f:
            json.dump(self.thermodynamic_parameters, f, indent=2)
        
        logger.info(f"Thermodynamic parameters saved to {output_file}")
    
    def generate_calibration_report(self) -> str:
        """Generate a comprehensive calibration report"""
        report = []
        
        report.append("# TWAVE v2.0 Landau-Ginzburg Calibration Report")
        report.append(f"\nGenerated: {__import__('datetime').datetime.now().isoformat()}")
        report.append(f"Model: {self.config.model_name}")
        report.append(f"Calibration points: {len(self.calibration_data)}")
        
        report.append("\n## Thermodynamic Parameters")
        if self.thermodynamic_parameters:
            params = self.thermodynamic_parameters
            report.append(f"- Critical Temperature (Tc): {params['critical_temperature']:.3f}")
            report.append(f"- Tc Confidence: {params['tc_confidence']:.3f}")
            report.append(f"- Healing Length (xi): {params['healing_length']:.3f} tokens")
            report.append(f"- Fitting Quality: {params['fitting_quality']}")
            
            report.append("\nOrder Parameter Weights:")
            for name, weight in params['order_parameter_weights'].items():
                report.append(f"- {name}: {weight:.2f}")
        
        report.append("\n## Temperature Sweep Results")
        temp_entropies = {}
        for point in self.calibration_data:
            temp = point.temperature
            if temp not in temp_entropies:
                temp_entropies[temp] = []
            temp_entropies[temp].append(point.total_entropy)
        
        for temp in sorted(temp_entropies.keys()):
            avg_entropy = np.mean(temp_entropies[temp])
            report.append(f"- T = {temp:.2f}: avg_entropy = {avg_entropy:.3f}")
        
        report.append("\n## Recommendations")
        
        if self.thermodynamic_parameters.get("fitting_quality") == "excellent":
            report.append("- Thermodynamic framework fits data well - safe for production")
            report.append("- Use fitted parameters for Landau-Ginzburg tracker")
        elif self.thermodynamic_parameters.get("fitting_quality") == "good":
            report.append("- Thermodynamic framework shows reasonable fit - proceed with caution")
            report.append("- Consider additional calibration points for better accuracy")
        else:
            report.append("- Thermodynamic framework fit is poor - reconsider approach")
            report.append("- May need different order parameters or calibration strategy")
        
        return "\n".join(report)


def main():
    """Main calibration function"""
    parser = argparse.ArgumentParser(description="TWAVE v2.0 Landau-Ginzburg Calibration")
    parser.add_argument("--config", type=str, help="Path to config file (JSON)")
    parser.add_argument("--model", type=str, default="gpt2", help="Model to calibrate")
    parser.add_argument("--output-dir", type=str, default="foundry_datasets/twave_calibration", help="Output directory")
    parser.add_argument("--num-prompts", type=int, default=100, help="Number of calibration prompts")
    parser.add_argument("--quick", action="store_true", help="Quick calibration with reduced prompts")
    
    args = parser.parse_args()
    
    # Load or create config
    if args.config and Path(args.config).exists():
        with open(args.config, 'r') as f:
            config_dict = json.load(f)
        config = CalibrationConfig(**config_dict)
    else:
        config = CalibrationConfig(
            model_name=args.model,
            output_dir=args.output_dir,
            num_prompts=args.num_prompts
        )
    
    if args.quick:
        config.num_prompts = 10
        config.num_temperature_points = 5
        logger.info("Quick calibration mode: reduced prompts and temperatures")
    
    # Run calibration
    engine = TWAVECalibrationEngine(config)
    
    try:
        # Generate calibration data
        engine.run_calibration_sweep()
        
        # Fit thermodynamic parameters
        engine.fit_thermodynamic_parameters()
        
        # Generate report
        report = engine.generate_calibration_report()
        
        report_file = engine.output_dir / "calibration_report.md"
        with open(report_file, 'w') as f:
            f.write(report)
        
        logger.info(f"Calibration complete. Report saved to {report_file}")
        
    except Exception as e:
        logger.error(f"Calibration failed: {e}")
        raise


if __name__ == "__main__":
    main()