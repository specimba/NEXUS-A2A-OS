"""NEXUS Dataset Forge — Core schemas, types, and metadata."""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class DatasetType(str, Enum):
    GUARD_SAFE = "guard_safe"
    GUARD_ADVERSARIAL = "guard_adversarial"
    BENIGN = "benign"
    REASONING = "reasoning"
    CODE_SECURITY = "code_security"
    MCP_TOOL_USE = "mcp_tool_use"
    TRUST_BOUNDARY = "trust_boundary"
    MISALIGNMENT_DETECT = "misalignment_detect"
    REFUSAL_BOUNDARY = "refusal_boundary"
    GOVERNANCE = "governance"
    MULTIMODAL = "multimodal"


class QualityTier(str, Enum):
    S0_DEMO = "S0_demo"       # Quick generation, basic dedup
    S1_RESEARCH = "S1_research"  # Light quality filter, usable for probes
    S2_EVAL = "S2_eval"       # Full pipeline, eval-ready
    S3_BENCHMARK = "S3_benchmark"  # Strictest, benchmark-quality


@dataclass
class RecordMetadata:
    created_at: str
    generator: str
    quality_tier: str
    dataset_type: str
    source: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    safety_validated: bool = False
    pii_screened: bool = False
    dedup_hash: Optional[str] = None
    nexus_version: str = "4.0.0"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "created_at": self.created_at,
            "generator": self.generator,
            "quality_tier": self.quality_tier,
            "dataset_type": self.dataset_type,
            "source": self.source,
            "tags": self.tags,
            "safety_validated": self.safety_validated,
            "pii_screened": self.pii_screened,
            "dedup_hash": self.dedup_hash,
            "nexus_version": self.nexus_version,
        }


@dataclass
class NEXUSDataset:
    dataset_id: str
    name: str
    version: str
    dataset_type: DatasetType
    quality_tier: QualityTier
    description: str
    num_records: int
    record_template: str
    created_at: str
    tags: List[str]
    license: str
    language: str
    domain: str
    records: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Optional[RecordMetadata] = None

    def __post_init__(self):
        if self.metadata is None:
            now = datetime.now(timezone.utc).isoformat()
            self.metadata = RecordMetadata(
                created_at=now,
                generator="nexus_forge",
                quality_tier="S2_eval",
                dataset_type="unknown",
            )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "name": self.name,
            "version": self.version,
            "dataset_type": self.dataset_type.value,
            "quality_tier": self.quality_tier.value,
            "description": self.description,
            "num_records": self.num_records,
            "record_template": self.record_template,
            "created_at": self.created_at,
            "tags": self.tags,
            "license": self.license,
            "language": self.language,
            "domain": self.domain,
            "records": self.records,
            "metadata": self.metadata.to_dict(),
        }

    def to_jsonl(self, path: str) -> int:
        count = 0
        with open(path, "w", encoding="utf-8") as f:
            for rec in self.records:
                item = {"text": rec["text"], "label": rec["label"]}
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
                count += 1
        return count

    def add_record(self, record: Dict[str, Any]):
        self.records.append(record)
        self.num_records = len(self.records)


@dataclass
class DatasetManifest:
    dataset_id: str
    name: str
    version: str
    dataset_type: DatasetType
    quality_tier: QualityTier
    num_records: int
    num_filtered: int
    quality_score: float
    dedup_strategy: str
    created_at: str
    tags: List[str]
    hf_repo_id: Optional[str] = None
    size_bytes: int = 0
    checksum: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "name": self.name,
            "version": self.version,
            "dataset_type": self.dataset_type.value,
            "quality_tier": self.quality_tier.value,
            "num_records": self.num_records,
            "num_filtered": self.num_filtered,
            "quality_score": self.quality_score,
            "dedup_strategy": self.dedup_strategy,
            "created_at": self.created_at,
            "tags": self.tags,
            "hf_repo_id": self.hf_repo_id,
            "size_bytes": self.size_bytes,
            "checksum": self.checksum,
        }

    def compute_checksum(self, path: str) -> str:
        sha = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha.update(chunk)
        self.checksum = sha.hexdigest()
        return self.checksum

    @staticmethod
    def hash_record(record: Dict[str, Any]) -> str:
        norm = json.dumps(record, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(norm.encode()).hexdigest()[:16]


class NEXUSBenchRecord:
    """Single record in NEXUS-Bench compatible JSONL format."""

    def __init__(
        self,
        id: str,
        dataset_type: str,
        difficulty: str,
        query: str,
        label: Any,
        category: str,
        subcategory: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ):
        self.id = id
        self.dataset_type = dataset_type
        self.difficulty = difficulty
        self.query = query
        self.label = label
        self.category = category
        self.subcategory = subcategory
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "dataset_type": self.dataset_type,
            "difficulty": self.difficulty,
            "query": self.query,
            "label": self.label,
            "category": self.category,
            "subcategory": self.subcategory,
            "metadata": self.metadata,
        }

    def to_jsonl_line(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_guard_record(cls, record: Dict[str, Any], difficulty: str = "medium") -> "NEXUSBenchRecord":
        return cls(
            id=f"guard_{uuid.uuid4().hex[:8]}",
            dataset_type="guard",
            difficulty=difficulty,
            query=record.get("text", ""),
            label=record.get("label", "safe"),
            category=record.get("category", "general"),
            metadata={"source": "synthetic", "generator": "nexus_forge"},
        )


def generate_dataset_id(prefix: str = "nx") -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"{prefix}_{ts}_{uuid.uuid4().hex[:8]}"