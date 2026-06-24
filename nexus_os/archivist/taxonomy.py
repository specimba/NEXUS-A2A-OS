"""nexus_os/archivist/taxonomy.py — Canonical unified taxonomies.

Single source of truth for the 14-topic unified taxonomy and the
topic→DG source_kind mapping. Both compile.py (for tagging) and
doppelground_bridge.py (for routing to vault channels) MUST import
from here to avoid drift.

Unified taxonomy merges:
- Archivist's original 8 topics
- DoppelGround's 12 source_kinds (subset aliased to 6 new topics)
- AlphaXiv's 6 folder categories
"""

from typing import Dict

# 14-topic keywords (used by compile.tag_topics)
TOPIC_KEYWORDS: Dict[str, set] = {
    # Original 8
    "trust": {"trust", "reputation", "bayesian", "grinding", "gaming", "sigmoid", "logistic"},
    "memory": {"memory", "episodic", "semantic", "procedural", "consolidation", "retrieval", "rag", "context"},
    "security": {"security", "attack", "threat", "jailbreak", "prompt injection", "exfiltration", "cve", "vulnerability"},
    "benchmark": {"benchmark", "evaluation", "arena", "mmlu", "gpqa", "aime", "score", "metric"},
    "model": {"model", "llm", "transformer", "diffusion", "embedding", "quantization", "inference"},
    "governance": {"governance", "policy", "regulation", "compliance", "audit", "cdr", "risk"},
    "multimodal": {"multimodal", "vision", "image", "vlm", "audio", "speech"},
    "agent": {"agent", "autonomous", "tool use", "orchestration", "multi-agent", "mas"},
    # 6 New topics from DoppelGround source_kinds + AlphaXiv folders
    "code": {"code", "implementation", "software", "programming", "sdk", "api", "module", "pipeline"},
    "spec": {"spec", "specification", "design doc", "architect", "blueprint", "requirements", "srd"},
    "rules": {"rules", "config", "configuration", "yaml", "policy file", "guardrail"},
    "role": {"role", "persona", "system prompt", "identity", "operator", "dispatcher"},
    "dataset": {"dataset", "golden", "benchmark data", "corpus", "evaluation set", "training data"},
    "rejection": {"rejection", "failure", "failure pattern", "anti-pattern", "negative example", "hallucination"},
}

# Topic → DoppelGround source_kind (used by bridge.infer_source_kind).
# Single source of truth — compile.py tags a record with multiple topics;
# bridge prioritizes first match in this mapping.
TOPIC_TO_SOURCE_KIND: Dict[str, str] = {
    # Direct topic → source_kind matches
    "rules": "rules",
    "config": "config",
    "mission": "mission",
    "doc": "doc",
    "spec": "spec",
    "code": "code",
    "role": "role",
    "dataset": "golden_dataset",
    "rejection": "rejection_example",
    # Aliased topics → canonical source_kind
    "governance": "rules",       # governance → rules (policy)
    "security": "rules",         # security rules → rules
    "benchmark": "golden_dataset",  # benchmark data → golden_dataset
    # Topics without a strong source_kind mapping get "doc" (fallback in bridge)
}

# File-type → topic heuristics (used by bridge.infer_source_kind fallback)
FILE_TYPE_TO_TOPIC: Dict[str, str] = {
    "code": "code",
    "config": "rules",
    "prompt": "role",
    "benchmark": "dataset",
    "markdown": "doc",
    "paper": "deep_research",
    "log": "doc",
}


def source_kind_for_topic(topic: str) -> str:
    """Map a topic tag to its canonical DoppelGround source_kind.

    Returns "doc" as default if topic is unknown.
    """
    return TOPIC_TO_SOURCE_KIND.get(topic, "doc")
