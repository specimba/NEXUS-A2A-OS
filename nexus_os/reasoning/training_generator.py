"""
reasoning/training_generator.py — FableReasoningEngine Training Data Generator

Generates DPO (Direct Preference Optimization) pairs, chain-of-thought
training examples, and synthesized reasoning chains from extracted
ReasoningPattern instances. Supports multiple output formats including
JSONL, HuggingFace Dataset, and OpenAI fine-tuning format.
"""

import json
import logging
import os
import random
from typing import Any, Dict, List, Optional

from nexus_os.reasoning.pattern_extractor import (
    PATTERN_CATEGORIES,
    ReasoningPattern,
    _DIAGNOSIS_KEYWORDS,
    _HYPOTHESIS_KEYWORDS,
    _BOUNDARY_KEYWORDS,
    _TOOL_SELECTION_KEYWORDS,
    _VERIFICATION_KEYWORDS,
    _SELF_CORRECTION_KEYWORDS,
    _DELEGATION_KEYWORDS,
)

logger = logging.getLogger(__name__)

_CHAIN_ORDER = [
    "DIAGNOSIS",
    "HYPOTHESIS",
    "BOUNDARY",
    "TOOL_SELECTION",
    "VERIFICATION",
]

_OPTIONAL_CHAIN = ["SELF_CORRECTION", "DELEGATION"]

_CATEGORY_KEYWORDS: Dict[str, set] = {
    "DIAGNOSIS": _DIAGNOSIS_KEYWORDS,
    "HYPOTHESIS": _HYPOTHESIS_KEYWORDS,
    "BOUNDARY": _BOUNDARY_KEYWORDS,
    "TOOL_SELECTION": _TOOL_SELECTION_KEYWORDS,
    "VERIFICATION": _VERIFICATION_KEYWORDS,
    "SELF_CORRECTION": _SELF_CORRECTION_KEYWORDS,
    "DELEGATION": _DELEGATION_KEYWORDS,
}


# ── DPO Pair Generator ─────────────────────────────────────────────────────


class DPOPairGenerator:
    """Generates DPO training pairs from ReasoningPattern instances.

    Pairs high-confidence patterns (chosen) with low-confidence patterns
    (rejected) for each category, balanced so no single category dominates.
    Also generates CoT training examples wrapped in reasoning templates.
    """

    def __init__(self, confidence_threshold: float = 0.5) -> None:
        """Initialize with confidence threshold.

        Args:
            confidence_threshold: Threshold above which patterns are
                considered high-confidence (default 0.5). Low-confidence
                patterns are those below threshold / 2.
        """
        self.confidence_threshold = confidence_threshold

    def generate_pairs(
        self,
        patterns: List[ReasoningPattern],
        max_pairs: int = 500,
    ) -> List[Dict[str, Any]]:
        """Generate DPO pairs from patterns.

        For each pattern category, finds high-confidence (>threshold) and
        low-confidence (<threshold/2) patterns. Pairs them as (chosen, rejected).
        Balances categories so no single category dominates.

        Args:
            patterns: List of extracted ReasoningPattern instances.
            max_pairs: Maximum number of pairs to generate (default 500).

        Returns:
            List of pair dicts with keys: prompt, chosen, rejected, category,
            confidence_chosen, confidence_rejected.
        """
        if not patterns:
            logger.warning("generate_pairs called with empty pattern list")
            return []

        categorized: Dict[str, Dict[str, List[ReasoningPattern]]] = {}
        for cat in PATTERN_CATEGORIES:
            categorized[cat] = {"high": [], "low": []}

        for p in patterns:
            cat = p.category
            if cat not in PATTERN_CATEGORIES:
                continue
            if p.confidence >= self.confidence_threshold:
                categorized[cat]["high"].append(p)
            elif p.confidence < self.confidence_threshold / 2:
                categorized[cat]["low"].append(p)

        pairs: List[Dict[str, Any]] = []
        categories_with_data = [
            cat for cat in PATTERN_CATEGORIES
            if categorized[cat]["high"] and categorized[cat]["low"]
        ]

        if not categories_with_data:
            logger.warning(
                "No categories have both high and low confidence patterns "
                "for pairing"
            )
            return []

        max_per_category = max_pairs // len(categories_with_data)

        for cat in categories_with_data:
            high = categorized[cat]["high"]
            low = categorized[cat]["low"]
            random.shuffle(high)
            random.shuffle(low)

            n_pairs = min(max_per_category, len(high), len(low))
            for i in range(n_pairs):
                pairs.append({
                    "prompt": high[i].context or low[i].context,
                    "chosen": high[i].text,
                    "rejected": low[i].text,
                    "category": cat,
                    "confidence_chosen": high[i].confidence,
                    "confidence_rejected": low[i].confidence,
                })

        if len(pairs) > max_pairs:
            random.shuffle(pairs)
            pairs = pairs[:max_pairs]

        logger.info(
            "Generated %d DPO pairs across %d categories",
            len(pairs),
            len(categories_with_data),
        )
        return pairs

    def generate_cot_pairs(
        self,
        patterns: List[ReasoningPattern],
        template_engine: Any,
        max_examples: int = 200,
    ) -> List[Dict[str, Any]]:
        """Generate CoT training examples by wrapping patterns in the
        Fable 5-step reasoning template format.

        Each example dict has:
        - prompt: The USER context / problem statement
        - cot: The assistant's reasoning text wrapped in step format
        - response: The final answer action
        - category: pattern category
        - confidence: pattern confidence

        Args:
            patterns: List of extracted ReasoningPattern instances.
            template_engine: ReasoningTemplateEngine instance for
                generating CoT format blocks.
            max_examples: Maximum number of examples to generate.

        Returns:
            List of CoT example dicts.
        """
        if not patterns:
            logger.warning("generate_cot_pairs called with empty pattern list")
            return []

        examples: List[Dict[str, Any]] = []

        for p in patterns:
            if len(examples) >= max_examples:
                break

            prompt = _extract_user_prompt(p.context) or p.context
            fable_block = template_engine.get_fable_5_step()

            step_mapping = {
                "DIAGNOSIS": "Step 1: DIAGNOSE — Context Verification",
                "HYPOTHESIS": "Step 2: OPTIONS — Hypothesis Generation",
                "BOUNDARY": "Step 3: BOUNDARIES — Safety & Scope Analysis",
                "TOOL_SELECTION": "Step 4: MINIMAL TOOLING — Precise Tool Selection",
                "VERIFICATION": "Step 5: POST-CHECK — Verification",
                "SELF_CORRECTION": "Self-Correction",
                "DELEGATION": "Delegation",
            }
            step_header = step_mapping.get(p.category, "Reasoning")

            cot = (
                f"{fable_block}\n\n"
                f"### {step_header}\n"
                f"{p.text}"
            )

            examples.append({
                "prompt": prompt,
                "cot": cot,
                "response": p.text,
                "category": p.category,
                "confidence": p.confidence,
            })

        logger.info("Generated %d CoT examples", len(examples))
        return examples


# ── CoT Synthesizer ────────────────────────────────────────────────────────


class CoTSynthesizer:
    """Synthesizes new CoT training examples by combining patterns.

    Creates logical reasoning chains across categories and augments
    existing patterns with variants through sentence reordering,
    synonym substitution, and category combination.
    """

    def __init__(self, max_length: int = 2048) -> None:
        """Initialize with maximum sequence length.

        Args:
            max_length: Maximum token length for synthesized sequences
                (default 2048).
        """
        self.max_length = max_length
        self._synonym_map: Optional[Dict[str, List[str]]] = None

    def _build_synonym_map(self) -> Dict[str, List[str]]:
        """Build a synonym map from category keyword banks.

        Terms within the same category keyword bank are treated as
        potential substitutes for each other.

        Returns:
            Dict mapping keyword to list of synonym candidates.
        """
        if self._synonym_map is not None:
            return self._synonym_map

        synonym_map: Dict[str, List[str]] = {}
        for keywords in _CATEGORY_KEYWORDS.values():
            kw_list = list(keywords)
            for kw in kw_list:
                synonyms = [s for s in kw_list if s != kw and len(s.split()) == len(kw.split())]
                if synonyms:
                    synonym_map[kw] = synonyms

        self._synonym_map = synonym_map
        return synonym_map

    def synthesize_chain(
        self,
        patterns: List[ReasoningPattern],
        chain_length: int = 5,
    ) -> List[Dict[str, Any]]:
        """Synthesize a reasoning chain from patterns of different categories.

        Creates a logical chain: DIAGNOSIS -> HYPOTHESIS -> BOUNDARY ->
        TOOL_SELECTION -> VERIFICATION (with optional SELF_CORRECTION/DELEGATION).

        Args:
            patterns: List of extracted ReasoningPattern instances.
            chain_length: Number of steps in the chain (default 5). If
                greater than 5, optional categories are appended.

        Returns:
            List of example dicts with keys: chain, steps, n_steps.
        """
        if not patterns:
            logger.warning("synthesize_chain called with empty pattern list")
            return []

        categorized: Dict[str, List[ReasoningPattern]] = {}
        for cat in PATTERN_CATEGORIES:
            categorized[cat] = [p for p in patterns if p.category == cat]

        chain_order = list(_CHAIN_ORDER)
        extra_steps = chain_length - len(_CHAIN_ORDER)
        if extra_steps > 0:
            for cat in _OPTIONAL_CHAIN * (extra_steps // len(_OPTIONAL_CHAIN) + 1):
                if len(chain_order) < chain_length:
                    chain_order.append(cat)
            chain_order = chain_order[:chain_length]

        chains: List[Dict[str, Any]] = []
        attempts = 0
        max_attempts = chain_length * 10 * len(patterns)

        while len(chains) < chain_length * 3 and attempts < max_attempts:
            attempts += 1
            steps: List[Dict[str, Any]] = []
            chain_parts: List[str] = []

            for cat in chain_order:
                pool = categorized.get(cat, [])
                if not pool:
                    continue
                pattern = random.choice(pool)
                steps.append({
                    "category": cat,
                    "text": pattern.text,
                    "tool": pattern.tool_sequence,
                })
                chain_parts.append(f"[{cat}] {pattern.text}")

            if not steps:
                continue

            full_chain = "\n\n".join(chain_parts)

            if len(full_chain) > self.max_length:
                continue

            chains.append({
                "chain": full_chain,
                "steps": steps,
                "n_steps": len(steps),
            })

        logger.info("Synthesized %d reasoning chains", len(chains))
        return chains

    def augment_patterns(
        self,
        patterns: List[ReasoningPattern],
        augmentation_factor: int = 2,
    ) -> List[ReasoningPattern]:
        """Augment patterns by creating variants.

        For each pattern, generates variants by:
        - Reordering sentences (if multiple sentences)
        - Substituting synonyms for key terms
        - Combining with adjacent category patterns

        Args:
            patterns: List of extracted ReasoningPattern instances.
            augmentation_factor: Number of augmented variants to generate
                per original pattern (default 2).

        Returns:
            Augmented list containing original patterns plus variants.
        """
        if not patterns:
            logger.warning("augment_patterns called with empty pattern list")
            return []

        synonym_map = self._build_synonym_map()
        augmented: List[ReasoningPattern] = list(patterns)

        for pattern in patterns:
            for variant_idx in range(augmentation_factor):
                text = pattern.text
                strategy = variant_idx % 3

                if strategy == 0:
                    text = _reorder_sentences(text)
                elif strategy == 1:
                    text = _substitute_synonyms(text, synonym_map)
                elif strategy == 2:
                    text = _combine_with_adjacent(text, pattern, patterns)

                if text == pattern.text:
                    continue

                variant = ReasoningPattern(
                    pattern_id=f"{pattern.pattern_id}_aug_{variant_idx}",
                    category=pattern.category,
                    subcategory=pattern.subcategory,
                    text=text,
                    context=pattern.context,
                    tool_sequence=list(pattern.tool_sequence),
                    confidence=pattern.confidence * random.uniform(0.85, 0.95),
                    source_uid=pattern.source_uid,
                    metadata={
                        **pattern.metadata,
                        "augmented": True,
                        "augment_strategy": strategy,
                        "original_pattern_id": pattern.pattern_id,
                    },
                )
                augmented.append(variant)

        logger.info(
            "Augmented %d patterns to %d total (factor=%d)",
            len(patterns),
            len(augmented),
            augmentation_factor,
        )
        return augmented


# ── Dataset Formatter ──────────────────────────────────────────────────────


class DatasetFormatter:
    """Formats training data for different training frameworks.

    Supports JSONL, HuggingFace Dataset-compatible JSON, and
    OpenAI fine-tuning JSONL formats.
    """

    @staticmethod
    def to_jsonl(
        data: List[Dict[str, Any]],
        output_path: str,
    ) -> int:
        """Write list of dicts to JSONL file.

        Args:
            data: List of dicts to serialize.
            output_path: Absolute path for the output JSONL file.

        Returns:
            Number of records written.
        """
        if not data:
            logger.warning("to_jsonl called with empty data")
            return 0

        count = 0
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                for record in data:
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
                    count += 1
        except (OSError, IOError) as e:
            logger.error("Failed to write JSONL to %s: %s", output_path, e)
            return 0

        logger.info("Wrote %d records to %s", count, output_path)
        return count

    @staticmethod
    def to_hf_dataset(
        data: List[Dict[str, Any]],
        output_path: str,
        format: str = "dpo",
    ) -> int:
        """Write to HuggingFace Dataset-compatible format.

        For format='dpo': columns = {prompt, chosen, rejected}
        For format='cot': columns = {prompt, cot, response}

        Args:
            data: List of training example dicts.
            output_path: Absolute path for the output JSON file.
            format: Dataset format type ('dpo' or 'cot').

        Returns:
            Number of records written.
        """
        if not data:
            logger.warning("to_hf_dataset called with empty data")
            return 0

        if format == "dpo":
            records = [
                {
                    "prompt": d.get("prompt", ""),
                    "chosen": d.get("chosen", ""),
                    "rejected": d.get("rejected", ""),
                }
                for d in data
            ]
        elif format == "cot":
            records = [
                {
                    "prompt": d.get("prompt", ""),
                    "cot": d.get("cot", ""),
                    "response": d.get("response", ""),
                }
                for d in data
            ]
        else:
            logger.error("Unknown HF dataset format: %s", format)
            return 0

        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(records, f, ensure_ascii=False, indent=2)
        except (OSError, IOError) as e:
            logger.error("Failed to write HF dataset to %s: %s", output_path, e)
            return 0

        logger.info(
            "Wrote %d records (format=%s) to %s",
            len(records),
            format,
            output_path,
        )
        return len(records)

    @staticmethod
    def to_openai_finetuning(
        data: List[Dict[str, Any]],
        output_path: str,
        system_prompt: str = "",
    ) -> int:
        """Write to OpenAI fine-tuning JSONL format.

        Each line::
            {"messages": [{"role": "system", "content": ...},
                          {"role": "user", "content": prompt},
                          {"role": "assistant", "content": response}]}

        Args:
            data: List of training example dicts. Uses 'prompt' and
                'response' keys.
            output_path: Absolute path for the output JSONL file.
            system_prompt: Optional system prompt prepended to each
                example.

        Returns:
            Number of records written.
        """
        if not data:
            logger.warning("to_openai_finetuning called with empty data")
            return 0

        count = 0
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                for d in data:
                    prompt = d.get("prompt", "")
                    response = d.get("response", "")
                    if not prompt or not response:
                        continue

                    messages: List[Dict[str, str]] = []
                    if system_prompt:
                        messages.append({
                            "role": "system",
                            "content": system_prompt,
                        })
                    messages.append({
                        "role": "user",
                        "content": prompt,
                    })
                    messages.append({
                        "role": "assistant",
                        "content": response,
                    })

                    f.write(json.dumps(
                        {"messages": messages},
                        ensure_ascii=False,
                    ) + "\n")
                    count += 1
        except (OSError, IOError) as e:
            logger.error(
                "Failed to write OpenAI format to %s: %s",
                output_path,
                e,
            )
            return 0

        logger.info("Wrote %d OpenAI records to %s", count, output_path)
        return count


# ── Helper utilities ───────────────────────────────────────────────────────


def _extract_user_prompt(context: str) -> Optional[str]:
    """Extract the USER turn content from a pattern's context string.

    Args:
        context: Raw context string with interleaved role markers.

    Returns:
        The USER turn content if found, else None.
    """
    if not context:
        return None

    for line in context.split("\n"):
        line = line.strip()
        if line.startswith("[U]") or line.startswith("USER:"):
            content = line
            for prefix in ("[U] ", "USER: "):
                if content.startswith(prefix):
                    content = content[len(prefix):]
            return content

    return None


def _reorder_sentences(text: str) -> str:
    """Reorder sentences in text to create a variant.

    Sentences are detected by terminal punctuation followed by whitespace
    or end of string. If the text contains 2+ sentences, they are shuffled.

    Args:
        text: Input text to reorder.

    Returns:
        Reordered text, or original text if insufficient sentences.
    """
    import re
    sentences = re.split(r"(?<=[.!?])\s+", text)
    sentences = [s.strip() for s in sentences if s.strip()]

    if len(sentences) < 2:
        return text

    random.shuffle(sentences)
    return " ".join(sentences)


def _substitute_synonyms(
    text: str,
    synonym_map: Dict[str, List[str]],
) -> str:
    """Substitute keywords in text with synonyms from the keyword banks.

    Args:
        text: Input text to modify.
        synonym_map: Dict mapping keywords to synonym candidates.

    Returns:
        Text with some keywords replaced by synonyms.
    """
    words = text.split()
    result = list(words)

    for i, word in enumerate(words):
        word_lower = word.lower().strip(".,!?;:")
        if word_lower in synonym_map and random.random() < 0.3:
            synonyms = synonym_map[word_lower]
            replacement = random.choice(synonyms)
            preserved_case = word[0].isupper() if word else False
            if preserved_case:
                replacement = replacement.capitalize()
            result[i] = replacement

    return " ".join(result)


def _combine_with_adjacent(
    text: str,
    pattern: ReasoningPattern,
    all_patterns: List[ReasoningPattern],
) -> str:
    """Combine pattern text with an adjacent category pattern.

    Finds a pattern with a different category and appends or prepends
    a relevant line from it.

    Args:
        text: Current pattern text.
        pattern: The source ReasoningPattern.
        all_patterns: Full list of available patterns.

    Returns:
        Combined text.
    """
    candidates = [
        p for p in all_patterns
        if p.category != pattern.category and p.pattern_id != pattern.pattern_id
    ]
    if not candidates:
        return text

    other = random.choice(candidates)
    other_lines = [l for l in other.text.split("\n") if l.strip()]
    if not other_lines:
        return text

    line = random.choice(other_lines)
    insert_before = random.random() < 0.5
    if insert_before:
        return f"{line}\n{text}"
    else:
        return f"{text}\n{line}"


# ── Convenience pipeline ───────────────────────────────────────────────────


def generate_training_data(
    patterns: List[ReasoningPattern],
    template_engine: Any,
    output_dir: str = "training_data",
    formats: Optional[List[str]] = None,
    max_pairs: int = 500,
) -> Dict[str, int]:
    """Convenience function that runs the full pipeline.

    1. Generates DPO pairs
    2. Generates CoT examples
    3. Synthesizes reasoning chains
    4. Writes all requested formats to output_dir

    Args:
        patterns: List of extracted ReasoningPattern instances.
        template_engine: ReasoningTemplateEngine instance.
        output_dir: Directory for output files (default 'training_data').
        formats: List of output formats to generate. Options: 'dpo',
            'cot', 'openai'. Defaults to ['dpo', 'cot', 'openai'].
        max_pairs: Maximum number of DPO pairs to generate.

    Returns:
        Dict mapping output file paths to record counts.
    """
    if formats is None:
        formats = ["dpo", "cot", "openai"]

    if not patterns:
        logger.warning("generate_training_data called with empty pattern list")
        return {}

    os.makedirs(output_dir, exist_ok=True)

    pair_gen = DPOPairGenerator()
    synthesizer = CoTSynthesizer()
    results: Dict[str, int] = {}

    dpo_pairs = pair_gen.generate_pairs(patterns, max_pairs=max_pairs)
    if dpo_pairs:
        dpo_path = os.path.join(output_dir, "dpo_pairs.jsonl")
        results["dpo"] = DatasetFormatter.to_jsonl(dpo_pairs, dpo_path)

        if "cot" not in formats:
            hf_path = os.path.join(output_dir, "hf_dataset_dpo.json")
            results["hf_dpo"] = DatasetFormatter.to_hf_dataset(
                dpo_pairs, hf_path, format="dpo"
            )

    cot_examples = pair_gen.generate_cot_pairs(patterns, template_engine)
    if cot_examples:
        cot_path = os.path.join(output_dir, "cot_examples.jsonl")
        results["cot"] = DatasetFormatter.to_jsonl(cot_examples, cot_path)

    chains = synthesizer.synthesize_chain(patterns)
    if chains:
        chain_path = os.path.join(output_dir, "reasoning_chains.jsonl")
        results["chains"] = DatasetFormatter.to_jsonl(chains, chain_path)

    if "openai" in formats:
        openai_source = (
            cot_examples if cot_examples
            else dpo_pairs if dpo_pairs
            else []
        )
        if openai_source:
            openai_path = os.path.join(output_dir, "openai_finetuning.jsonl")
            results["openai"] = DatasetFormatter.to_openai_finetuning(
                openai_source, openai_path
            )

    if "dpo" in formats:
        hf_dpo_path = os.path.join(output_dir, "hf_dataset_dpo.json")
        results["hf_dpo"] = DatasetFormatter.to_hf_dataset(
            dpo_pairs, hf_dpo_path, format="dpo"
        )

    if "cot" in formats:
        hf_cot_path = os.path.join(output_dir, "hf_dataset_cot.json")
        results["hf_cot"] = DatasetFormatter.to_hf_dataset(
            cot_examples, hf_cot_path, format="cot"
        )

    logger.info(
        "Training data generation complete. Files: %s",
        {k: v for k, v in results.items() if v > 0},
    )
    return results
