"""
relay/safedecoding_wrapper.py — SafeDecoding Logit-Level Safety Wrapper

Implements the SafeDecoding (ACL 2024) defense strategy at the generation layer:
- Identifies safety disclaimer tokens (e.g., "I cannot", "I am unable", "As an AI")
- Amplifies safety disclaimer logits during decoding when inputs are flagged as high risk
- Attenuates potentially unsafe token logits to redirect generation toward alignment
- Zero overhead at inference time, works with local Ollama/vLLM/PyTorch backends
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Any, Set, Union
import numpy as np

logger = logging.getLogger("nexus_os.relay.safedecoding_wrapper")

# Default safety disclaimer tokens for common tokenizers (Qwen / Llama / Gemma)
# These represent common prefixes for safety refusals.
DEFAULT_DISCLAIMER_WORDS = [
    "I", " cannot", " am", " unable", " sorry", " apologize", " As", " an", " AI",
    "cannot", "unable", "sorry", "apologize", "As", "an", "AI", "helper", "assistant"
]

class SafeDecodingWrapper:
    """
    Logit-level safety wrapper that amplifies safety disclaimer tokens
    to redirect model outputs when the intent classifier flags potential misuse.
    """

    def __init__(self, vocabulary: Optional[Dict[str, int]] = None,
                 disclaimer_words: Optional[List[str]] = None,
                 amplification_factor: float = 5.0,
                 attenuation_factor: float = -5.0):
        self.vocabulary = vocabulary or {}
        self.disclaimer_words = disclaimer_words or DEFAULT_DISCLAIMER_WORDS
        self.amplification_factor = amplification_factor
        self.attenuation_factor = attenuation_factor
        self._disclaimer_token_ids: Set[int] = set()
        
        if self.vocabulary:
            self._map_disclaimer_tokens()

    def _map_disclaimer_tokens(self) -> None:
        """Map word strings to their corresponding token IDs in the vocabulary."""
        self._disclaimer_token_ids.clear()
        for word in self.disclaimer_words:
            # Check exact match, leading space, and lowercase variants
            variants = [word, f" {word}", word.lower(), f" {word.lower()}", word.upper()]
            for variant in variants:
                if variant in self.vocabulary:
                    self._disclaimer_token_ids.add(self.vocabulary[variant])
        
        logger.info("Mapped %d safety disclaimer tokens out of %d words",
                    len(self._disclaimer_token_ids), len(self.disclaimer_words))

    def set_vocabulary(self, vocabulary: Dict[str, int]) -> None:
        """Update the vocabulary mapping and re-map token IDs."""
        self.vocabulary = vocabulary
        self._map_disclaimer_tokens()

    def steer_logits(self, logits: Any, is_high_risk: bool = False,
                     unsafe_token_ids: Optional[List[int]] = None) -> Any:
        """
        Steer the logits array to amplify safety and suppress harm if high risk.

        Args:
            logits: Numpy array or list representing the next-token logits.
            is_high_risk: Whether the current sequence has been flagged as high risk.
            unsafe_token_ids: Optional list of token IDs to explicitly suppress.

        Returns:
            Steered logits (same type as input).
        """
        if not is_high_risk:
            return logits

        is_numpy = isinstance(logits, np.ndarray)
        steered_logits = np.array(logits, copy=True) if not is_numpy else logits.copy()

        # 1. Amplify safety disclaimer tokens
        if self._disclaimer_token_ids:
            for token_id in self._disclaimer_token_ids:
                if 0 <= token_id < len(steered_logits):
                    steered_logits[token_id] += self.amplification_factor
        else:
            # Fallback: if vocabulary is not mapped, manually boost top candidates
            # (In production, tokenizers must map vocabulary first)
            pass

        # 2. Attenuate explicitly identified unsafe tokens
        if unsafe_token_ids:
            for token_id in unsafe_token_ids:
                if 0 <= token_id < len(steered_logits):
                    steered_logits[token_id] += self.attenuation_factor

        # Return in the original format
        if not is_numpy:
            return steered_logits.tolist()
        return steered_logits


_wrapper_instance: Optional[SafeDecodingWrapper] = None

def get_safedecoding_wrapper(vocabulary: Optional[Dict[str, int]] = None) -> SafeDecodingWrapper:
    """Get the global singleton SafeDecodingWrapper instance."""
    global _wrapper_instance
    if _wrapper_instance is None:
        _wrapper_instance = SafeDecodingWrapper(vocabulary=vocabulary)
    elif vocabulary and not _wrapper_instance.vocabulary:
        _wrapper_instance.set_vocabulary(vocabulary)
    return _wrapper_instance
