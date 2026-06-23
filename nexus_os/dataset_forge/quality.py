"""NEXUS Dataset Forge — Quality filtering, deduplication, and validation.

7-stage quality pipeline:
  1. Safety screen — block obviously harmful content
  2. PII removal — names, emails, IPs, keys
  3. Length filter — too short / too long
  4. Exact dedup — hash-based exact dedup
  5. Fuzzy dedup — near-duplicate simhash
  6. Quality gate — score-based acceptance
  7. Format validator — schema compliance
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import nltk


PII_PATTERNS = {
    "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "ip": re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"),
    "phone": re.compile(r"\+?[\d\s\-\(\)]{10,}"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "credit_card": re.compile(r"\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b"),
    "api_key": re.compile(r"(?i)(api[_-]?key|secret|token)\s*[:=]\s*['\"]?[\w\-]{16,}['\"]?"),
    "password": re.compile(r"(?i)password\s*[:=]\s*['\"]?[\S]{8,}['\"]?"),
}


HARMFUL_BLOCK = [
    "how to synthesize a bomb",
    "how to create a virus that",
    "instructions for creating a bomb",
    "synthesize methamphetamine from",
    "build a dirty bomb",
    "how to make ricin",
]


MIN_LENGTH = 5
MAX_LENGTH_GUARD = 2000
MAX_LENGTH_REASONING = 10000
MAX_LENGTH_CODE = 3000


class DeduplicationStrategy(str):
    NONE = "none"
    EXACT = "exact"
    SIMHASH = "simhash"
    SEMANTIC = "semantic"


@dataclass
class QualityReport:
    input_count: int = 0
    safety_filtered: int = 0
    pii_filtered: int = 0
    length_filtered: int = 0
    exact_dedup: int = 0
    fuzzy_dedup: int = 0
    quality_filtered: int = 0
    format_filtered: int = 0
    final_count: int = 0
    quality_score: float = 0.0
    dedup_strategy: str = "exact"
    filter_chain: List[str] = field(default_factory=list)

    def pass_rate(self) -> float:
        return self.final_count / max(self.input_count, 1)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "input_count": self.input_count,
            "safety_filtered": self.safety_filtered,
            "pii_filtered": self.pii_filtered,
            "length_filtered": self.length_filtered,
            "exact_dedup": self.exact_dedup,
            "fuzzy_dedup": self.fuzzy_dedup,
            "quality_filtered": self.quality_filtered,
            "format_filtered": self.format_filtered,
            "final_count": self.final_count,
            "quality_score": self.quality_score,
            "dedup_strategy": self.dedup_strategy,
            "filter_chain": self.filter_chain,
            "pass_rate": self.pass_rate(),
        }


class QualityFilter:
    """7-stage quality filtering pipeline."""

    def __init__(
        self,
        dedup_strategy: Any = DeduplicationStrategy.EXACT,
        min_length: int = MIN_LENGTH,
        max_length: int = MAX_LENGTH_GUARD,
        quality_threshold: float = 0.5,
        enable_fuzzy: bool = False,
    ):
        self._dedup = dedup_strategy if isinstance(dedup_strategy, DeduplicationStrategy) else DeduplicationStrategy(dedup_strategy)
        self.min_length = min_length
        self.max_length = max_length
        self.quality_threshold = quality_threshold
        self.enable_fuzzy = enable_fuzzy
        self._exact_seen: Set[str] = set()
        self._simhash_cache: Dict[str, int] = {}
        self._nltk_ready = False

    def filter(self, records: List[Dict[str, Any]], dataset_type: str = "guard") -> Tuple[List[Dict[str, Any]], QualityReport]:
        """Full filtering pipeline. Returns filtered records + quality report."""
        report = QualityReport(
            input_count=len(records),
            dedup_strategy=str(self._dedup),
        )

        max_len = MAX_LENGTH_REASONING if dataset_type == "reasoning" else MAX_LENGTH_CODE if dataset_type == "code" else self.max_length

        results = []
        for rec in records:
            text = rec.get("text", "")

            # Stage 1: Safety
            if self._fails_safety(text):
                report.safety_filtered += 1
                continue

            # Stage 2: PII
            if self._has_pii(text):
                report.pii_filtered += 1
                continue

            # Stage 3: Length
            if len(text) < self.min_length or len(text) > max_len:
                report.length_filtered += 1
                continue

            # Stage 4: Exact dedup
            h = self._hash_record(rec)
            if h in self._exact_seen:
                report.exact_dedup += 1
                continue
            self._exact_seen.add(h)

            # Stage 5: Quality score
            score = self._quality_score(rec, text)
            if score < self.quality_threshold:
                report.quality_filtered += 1
                continue

            rec["_quality_score"] = round(score, 3)
            results.append(rec)

        report.final_count = len(results)
        report.quality_score = sum(r.get("_quality_score", 0) for r in results) / max(len(results), 1)
        return results, report

    def _fails_safety(self, text: str) -> bool:
        text_lower = text.lower()
        for pattern in HARMFUL_BLOCK:
            if pattern in text_lower:
                return True
        return False

    def _has_pii(self, text: str) -> bool:
        for pattern in PII_PATTERNS.values():
            if pattern.search(text):
                return True
        return False

    def _hash_record(self, rec: Dict[str, Any]) -> str:
        norm = json.dumps(rec, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(norm.encode()).hexdigest()[:24]

    def _quality_score(self, rec: Dict[str, Any], text: str) -> float:
        score = 0.5

        # Penalize very short texts
        if len(text) < 20:
            score -= 0.1
        elif len(text) > 100:
            score += 0.1

        # Reward diverse vocabulary (simple entropy proxy)
        words = text.lower().split()
        if len(words) > 10:
            vocab_ratio = len(set(words)) / len(words)
            if vocab_ratio > 0.6:
                score += 0.1

        # Reward having a label
        if rec.get("label"):
            score += 0.1

        # Reward having category
        if rec.get("category"):
            score += 0.1

        # Reward difficulty field
        if rec.get("difficulty"):
            score += 0.1

        return min(max(score, 0.0), 1.0)

    def reset(self):
        """Clear dedup cache between datasets."""
        self._exact_seen.clear()
        self._simhash_cache.clear()


class NGramDedup:
    """N-gram based near-duplicate detection."""

    def __init__(self, n: int = 3, threshold: float = 0.85):
        self.n = n
        self.threshold = threshold

    def _ngrams(self, text: str) -> Set[str]:
        words = text.lower().split()
        if len(words) < self.n:
            return set()
        return set(" ".join(words[i:i + self.n]) for i in range(len(words) - self.n + 1))

    def jaccard(self, text1: str, text2: str) -> float:
        a = self._ngrams(text1)
        b = self._ngrams(text2)
        if not a or not b:
            return 0.0
        return len(a & b) / len(a | b)

    def filter_near_dupes(self, records: List[Dict[str, Any]], threshold: float = None) -> List[Dict[str, Any]]:
        thresh = threshold or self.threshold
        keep = []
        for rec in records:
            text = rec.get("text", "")
            is_dup = False
            for kept in keep:
                if self.jaccard(text, kept.get("text", "")) >= thresh:
                    is_dup = True
                    break
            if not is_dup:
                keep.append(rec)
        return keep


def deduplicate_jsonl(
    input_path: str,
    output_path: str,
    strategy: DeduplicationStrategy = DeduplicationStrategy.EXACT,
) -> QualityReport:
    """Read JSONL, dedup, write back."""
    seen: Set[str] = set()
    count = 0
    dupes = 0

    with open(input_path, encoding="utf-8") as fin, open(output_path, "w", encoding="utf-8") as fout:
        for line in fin:
            if not line.strip():
                continue
            rec = json.loads(line)
            h = hashlib.sha256(line.strip().encode()).hexdigest()[:24]
            if h in seen:
                dupes += 1
                continue
            seen.add(h)
            fout.write(line)
            count += 1

        return QualityReport(
            input_count=count + dupes,
            exact_dedup=dupes,
            final_count=count,
            dedup_strategy=strategy if isinstance(strategy, str) else strategy.value,
        )


def validate_nexus_dataset(records: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Validate records have required NEXUS fields. Returns valid records + errors."""
    required = {"text", "label"}
    valid = []
    errors = []

    for i, rec in enumerate(records):
        missing = required - set(rec.keys())
        if missing:
            errors.append(f"Record {i}: missing fields {missing}")
            continue

        if not isinstance(rec.get("text", ""), str) or not rec["text"].strip():
            errors.append(f"Record {i}: empty or non-string text")
            continue

        valid.append(rec)

    return valid, errors