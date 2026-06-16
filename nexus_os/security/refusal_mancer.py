#!/usr/bin/env python3
"""
NEXUS Guard Plane — RefusalMancer Integration

Standalone refusal detection module based on ShareGPT-Formaxxing's RefusalMancer.
Uses transformer-based classifiers to detect when models refuse to answer.

Three classifier backends:
  1. protectai/distilroberta-base-rejection-v1 (default, general-purpose)
  2. Dans-DiscountModels/Dans-Classifier-RP-Validity-V1.0.0-396m (roleplay)
  3. garak-llm/garak-refusal-detector (long-context)

Integration with guard plane:
  - Pre-filter: Catch FPs BEFORE they reach the guard plane
  - Post-filter: Validate guard plane outputs to detect false refusals
  - Training: Use classified data to fine-tune guard models

Usage:
    from nexus_os.security.refusal_mancer import RefusalMancer
    
    mancer = RefusalMancer(mode="normal")
    result = mancer.classify("I cannot help with that request.")
    # result = {"is_refusal": True, "confidence": 0.95, "refusal_prob": 0.95}
    
    # Batch classification
    results = mancer.classify_batch(["Hello!", "I can't do that.", "Here's the answer."])
"""

import os
import sys
import json
import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple
from pathlib import Path

# Silence warnings
logging.getLogger("torch._dynamo").setLevel(logging.ERROR)
logging.getLogger("transformers").setLevel(logging.WARNING)

# ── Model Specifications ───────────────────────────────────────────────

MODELS = {
    "normal": {
        "name": "protectai/distilroberta-base-rejection-v1",
        "refusal_index": 1,
        "max_tokens": 512,
        "description": "General-purpose refusal detection",
    },
    "rp": {
        "name": "Dans-DiscountModels/Dans-Classifier-RP-Validity-V1.0.0-396m",
        "refusal_index": 0,
        "max_tokens": 512,
        "description": "Roleplay-focused refusal detection",
    },
    "garak": {
        "name": "garak-llm/garak-refusal-detector",
        "refusal_index": 0,
        "max_tokens": 8192,
        "description": "Long-context refusal detection",
    },
}

# ── Data Classes ───────────────────────────────────────────────────────

@dataclass
class ClassificationResult:
    """Result of refusal classification."""
    text: str
    is_refusal: bool
    refusal_prob: float
    compliance_prob: float
    confidence: float
    model_used: str


# ── RefusalMancer Class ────────────────────────────────────────────────

class RefusalMancer:
    """
    Refusal detection using transformer classifiers.
    
    Based on ShareGPT-Formaxxing's RefusalMancer.
    Optimized for NEXUS guard plane integration.
    """
    
    def __init__(self, mode: str = "normal", device: str = None):
        """
        Initialize RefusalMancer.
        
        Args:
            mode: Classifier mode ("normal", "rp", or "garak")
            device: Device to use ("cuda", "cpu", or None for auto)
        """
        if mode not in MODELS:
            raise ValueError(f"Invalid mode: {mode}. Must be one of: {list(MODELS.keys())}")
        
        self.mode = mode
        self.model_spec = MODELS[mode]
        self.device = device
        self.model = None
        self.tokenizer = None
        self._loaded = False
    
    def _load_model(self):
        """Lazy-load the classifier model."""
        if self._loaded:
            return
        
        try:
            import torch
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            
            model_name = self.model_spec["name"]
            
            # Determine device
            if self.device is None:
                self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
            
            # Load tokenizer and model
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
            self.model = self.model.eval().to(torch.device(self.device))
            
            self._loaded = True
            
        except ImportError as e:
            raise ImportError(
                f"Required packages not installed: {e}\n"
                "Install with: pip install transformers torch"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to load model {model_name}: {e}")
    
    def classify(self, text: str, threshold: float = 0.5) -> ClassificationResult:
        """
        Classify a single text as refusal or compliance.
        
        Args:
            text: Text to classify
            threshold: Threshold for refusal classification (default 0.5)
        
        Returns:
            ClassificationResult with is_refusal, probabilities, and confidence
        """
        self._load_model()
        
        import torch
        
        # Tokenize
        inputs = self.tokenizer(
            text,
            padding=True,
            truncation=True,
            return_tensors="pt",
            max_length=self.model_spec["max_tokens"],
        ).to(self.model.device)
        
        # Inference
        with torch.inference_mode():
            logits = self.model(**inputs).logits
        
        # Get probabilities
        if logits.ndim == 2 and logits.shape[1] >= 2:
            probs = torch.softmax(logits, dim=-1)
            refusal_prob = probs[0, self.model_spec["refusal_index"]].item()
        else:
            probs = torch.sigmoid(logits)
            refusal_prob = probs.squeeze(-1).item()
        
        compliance_prob = 1.0 - refusal_prob
        is_refusal = compliance_prob < threshold
        confidence = max(refusal_prob, compliance_prob)
        
        return ClassificationResult(
            text=text,
            is_refusal=is_refusal,
            refusal_prob=refusal_prob,
            compliance_prob=compliance_prob,
            confidence=confidence,
            model_used=self.model_spec["name"],
        )
    
    def classify_batch(self, texts: List[str], threshold: float = 0.5,
                       batch_size: int = 32) -> List[ClassificationResult]:
        """
        Classify a batch of texts.
        
        Args:
            texts: List of texts to classify
            threshold: Threshold for refusal classification
            batch_size: Batch size for inference
        
        Returns:
            List of ClassificationResult objects
        """
        self._load_model()
        
        import torch
        
        results = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            # Tokenize batch
            inputs = self.tokenizer(
                batch,
                padding=True,
                truncation=True,
                return_tensors="pt",
                max_length=self.model_spec["max_tokens"],
            ).to(self.model.device)
            
            # Inference
            with torch.inference_mode():
                logits = self.model(**inputs).logits
            
            # Get probabilities
            if logits.ndim == 2 and logits.shape[1] >= 2:
                probs = torch.softmax(logits, dim=-1)
                refusal_probs = probs[:, self.model_spec["refusal_index"]].tolist()
            else:
                probs = torch.sigmoid(logits)
                refusal_probs = probs.squeeze(-1).tolist()
                if not isinstance(refusal_probs, list):
                    refusal_probs = [refusal_probs]
            
            # Create results
            for text, refusal_prob in zip(batch, refusal_probs):
                compliance_prob = 1.0 - refusal_prob
                is_refusal = compliance_prob < threshold
                confidence = max(refusal_prob, compliance_prob)
                
                results.append(ClassificationResult(
                    text=text,
                    is_refusal=is_refusal,
                    refusal_prob=refusal_prob,
                    compliance_prob=compliance_prob,
                    confidence=confidence,
                    model_used=self.model_spec["name"],
                ))
        
        return results
    
    def detect_false_refusal(self, query: str, response: str,
                             threshold: float = 0.7) -> dict:
        """
        Detect if a model response is a false refusal.
        
        A false refusal occurs when:
        1. The query is benign (not an attack)
        2. The model refuses to answer
        
        Args:
            query: The original query
            response: The model's response
            threshold: Threshold for false refusal detection
        
        Returns:
            dict with is_false_refusal, confidence, and details
        """
        # Classify the response
        result = self.classify(response)
        
        # If response is classified as refusal
        if result.is_refusal:
            # Additional heuristic checks
            refusal_indicators = [
                "i cannot", "i can't", "i'm not able", "i'm unable",
                "i won't", "i will not", "not appropriate", "not safe",
                "cannot assist", "unable to assist", "against my guidelines",
            ]
            
            has_refusal_language = any(
                indicator in response.lower()
                for indicator in refusal_indicators
            )
            
            # If response has refusal language and high refusal probability
            is_false_refusal = (
                has_refusal_language and
                result.refusal_prob > threshold and
                result.confidence > 0.6
            )
            
            return {
                "is_false_refusal": is_false_refusal,
                "is_refusal": True,
                "refusal_prob": result.refusal_prob,
                "confidence": result.confidence,
                "has_refusal_language": has_refusal_language,
                "model_used": result.model_used,
            }
        
        return {
            "is_false_refusal": False,
            "is_refusal": False,
            "refusal_prob": result.refusal_prob,
            "confidence": result.confidence,
            "has_refusal_language": False,
            "model_used": result.model_used,
        }


# ── Convenience Functions ──────────────────────────────────────────────

# Global instances for quick access
_normal_mancer = None
_rp_mancer = None

def get_mancer(mode: str = "normal") -> RefusalMancer:
    """Get or create a RefusalMancer instance."""
    global _normal_mancer, _rp_mancer
    
    if mode == "normal":
        if _normal_mancer is None:
            _normal_mancer = RefusalMancer(mode="normal")
        return _normal_mancer
    elif mode == "rp":
        if _rp_mancer is None:
            _rp_mancer = RefusalMancer(mode="rp")
        return _rp_mancer
    else:
        return RefusalMancer(mode=mode)


def classify_refusal(text: str, threshold: float = 0.5) -> bool:
    """Quick refusal classification. Returns True if refusal detected."""
    mancer = get_mancer("normal")
    result = mancer.classify(text, threshold=threshold)
    return result.is_refusal


def detect_false_refusal(query: str, response: str,
                         threshold: float = 0.7) -> dict:
    """Quick false refusal detection."""
    mancer = get_mancer("normal")
    return mancer.detect_false_refusal(query, response, threshold=threshold)


# ── CLI Testing ────────────────────────────────────────────────────────

def main():
    """CLI interface for testing RefusalMancer."""
    import argparse
    
    parser = argparse.ArgumentParser(description="NEXUS RefusalMancer - Refusal Detection")
    parser.add_argument("--mode", choices=["normal", "rp", "garak"], default="normal",
                        help="Classifier mode (default: normal)")
    parser.add_argument("--text", type=str, help="Text to classify")
    parser.add_argument("--interactive", action="store_true", help="Interactive mode")
    parser.add_argument("--test", action="store_true", help="Run built-in tests")
    args = parser.parse_args()
    
    print("=" * 60)
    print("NEXUS RefusalMancer - Refusal Detection")
    print("=" * 60)
    print(f"Mode: {args.mode}")
    print(f"Model: {MODELS[args.mode]['name']}")
    print()
    
    mancer = RefusalMancer(mode=args.mode)
    
    if args.test:
        # Run built-in tests
        test_cases = [
            ("Hello! How can I help you?", False),
            ("I cannot help with that request.", True),
            ("I'm sorry, but I'm unable to assist with that.", True),
            ("Here's the answer to your question.", False),
            ("I can't provide that information.", True),
            ("What is the capital of France?", False),
        ]
        
        print("Running built-in tests...")
        print()
        
        correct = 0
        for text, expected_refusal in test_cases:
            result = mancer.classify(text)
            passed = result.is_refusal == expected_refusal
            correct += passed
            status = "PASS" if passed else "FAIL"
            
            print(f"[{status}] {text[:50]}...")
            print(f"  Expected: {'refusal' if expected_refusal else 'compliance'}")
            print(f"  Got: {'refusal' if result.is_refusal else 'compliance'} "
                  f"(prob={result.refusal_prob:.3f}, conf={result.confidence:.3f})")
            print()
        
        print(f"Results: {correct}/{len(test_cases)} correct ({correct/len(test_cases):.1%})")
    
    elif args.text:
        # Classify single text
        result = mancer.classify(args.text)
        print(f"Text: {args.text[:80]}...")
        print(f"Is Refusal: {result.is_refusal}")
        print(f"Refusal Probability: {result.refusal_prob:.3f}")
        print(f"Compliance Probability: {result.compliance_prob:.3f}")
        print(f"Confidence: {result.confidence:.3f}")
    
    elif args.interactive:
        # Interactive mode
        print("Enter texts to classify (Ctrl+C to exit):")
        print()
        
        try:
            while True:
                text = input("Text> ").strip()
                if text:
                    result = mancer.classify(text)
                    print(f"  Is Refusal: {result.is_refusal}")
                    print(f"  Refusal Prob: {result.refusal_prob:.3f}")
                    print(f"  Confidence: {result.confidence:.3f}")
                    print()
        except KeyboardInterrupt:
            print("\nExiting...")
    
    else:
        # Demo with sample texts
        sample_texts = [
            "What is the capital of France?",
            "I cannot help with that request.",
            "Here's how to solve the equation.",
            "I'm sorry, but I'm unable to assist with that.",
            "The answer is 42.",
            "I can't provide that information.",
        ]
        
        print("Sample classifications:")
        print()
        
        for text in sample_texts:
            result = mancer.classify(text)
            status = "REFUSAL" if result.is_refusal else "COMPLIANCE"
            print(f"[{status}] {text}")
            print(f"  Prob: {result.refusal_prob:.3f}, Conf: {result.confidence:.3f}")
            print()


if __name__ == "__main__":
    main()
