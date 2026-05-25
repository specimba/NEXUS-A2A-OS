#!/usr/bin/env python3
"""
train_query_classifier.py — Reproducible training pipeline for Guard Plane
query-type classifier.

Usage:
    python scripts/train_query_classifier.py
    python scripts/train_query_classifier.py --dataset datasets/adversarial/ernie_v8_adversarial_1000.jsonl

Output:
    models/guards/query_classifier.pkl      — trained sklearn Pipeline
    models/guards/query_classifier.manifest.json  — auto-generated manifest

Dependencies (not installed in WSL; run in a Python venv with sklearn):
    pip install scikit-learn pandas
"""
import argparse
import json
import hashlib
import pickle
import sys
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
SRC_DATASET = ROOT / "datasets" / "adversarial" / "ernie_v8_adversarial_1000.jsonl"
OUT_MODEL = ROOT / "models" / "guards" / "query_classifier.pkl"
OUT_MANIFEST = ROOT / "models" / "guards" / "query_classifier.manifest.json"

# ---------------------------------------------------------------------------
# Default label mapping (maps raw ERNIE labels → classifier classes)
# ---------------------------------------------------------------------------
DEFAULT_LABEL_MAP = {
    "UNSAFE": "attack_ernie",
    "SAFE": "benign_simple",
}

# ---------------------------------------------------------------------------
# Feature engineering helpers
# ---------------------------------------------------------------------------
def extract_features(text: str) -> dict:
    """Lightweight feature extraction for query-type classification."""
    t = text.lower()
    features = {
        "len": len(t),
        "words": len(t.split()),
        "has_agent": int(bool("agent" in t)),
        "has_override": int(bool("override" in t or "bypass" in t)),
        "has_train": int(bool("train" in t)),
        "has_research": int(bool("research" in t or "paper" in t)),
        "has_story": int(bool("story" in t or "screenplay" in t)),
        "has_step": int(bool("step 1" in t or "step 2" in t)),
        "has_committee": int(bool("committee" in t or "voted" in t)),
        "has_topology": int(bool("manifold" in t or "homology" in t)),
        "has_drop": int(bool("drop table" in t)),
        "has_select": int(bool("select" in t and "from" in t)),
        "exclamation_ratio": t.count("!") / max(len(t), 1),
        "question_ratio": t.count("?") / max(len(t), 1),
    }
    return features


def featurize(texts: list[str]):
    """Return a dense feature matrix from a list of texts."""
    rows = [extract_features(t) for t in texts]
    # Convert to simple numpy-like structure
    keys = list(rows[0].keys()) if rows else []
    matrix = [[r[k] for k in keys] for r in rows]
    return matrix, keys


# ---------------------------------------------------------------------------
# Dataset loaders
# ---------------------------------------------------------------------------
def load_ernie_jsonl(path: Path, label_map: dict | None = None):
    """Load ERNIE adversarial dataset and return (texts, labels)."""
    label_map = label_map or DEFAULT_LABEL_MAP
    texts, labels = [], []
    if not path.exists():
        print(f"ERROR: Dataset not found: {path}")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            prompt = rec.get("prompt", "")
            label = rec.get("label", "")
            # Map raw label to classifier class
            mapped = label_map.get(label, label)
            # Derive richer labels from content heuristics
            mapped = _refine_label(prompt, mapped)
            texts.append(prompt)
            labels.append(mapped)
    return texts, labels


def _refine_label(text: str, base: str) -> str:
    """Use content heuristics to sub-divide coarse labels."""
    t = text.lower()
    if base.startswith("benign"):
        if any(x in t for x in ("agent", "model", "system")):
            return "benign_adversarial_benign"
        if any(x in t for x in ("topology", "manifold", "homology", "casimir")):
            return "benign_domain_specific"
        if any(x in t for x in ("step 1", "step 2", "next response")):
            return "benign_edge_cases"
        if any(x in t for x in ("research", "thesis", "paper", "conference")):
            return "benign_ernie_corpus"
        if any(x in t for x in ("gray area", "ambiguous", "unclear")):
            return "benign_gray_area"
        return "benign_simple"
    if base.startswith("attack"):
        if any(x in t for x in ("agent", "reviewer", "admin", "manager")):
            return "tamas"
        if any(x in t for x in ("ignore", "override", "DAN", "jailbreak")):
            return "v7"
        return "attack_ernie"
    return base


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------
def train(texts: list[str], labels: list[str]):
    """Train a sklearn Pipeline and return the fitted model."""
    try:
        from sklearn.pipeline import Pipeline
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import classification_report
    except ImportError as e:
        print(f"ERROR: Missing dependency: {e}")
        print("Install with: pip install scikit-learn")
        sys.exit(1)

    X_train, X_test, y_train, y_test = train_test_split(
        texts, labels, test_size=0.2, random_state=42, stratify=labels
    )

    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(max_features=5000, ngram_range=(1, 2))),
        ("clf", LogisticRegression(max_iter=1000, class_weight="balanced")),
    ])

    print(f"Training on {len(X_train)} samples...")
    pipeline.fit(X_train, y_train)

    print(f"Evaluating on {len(X_test)} samples...")
    y_pred = pipeline.predict(X_test)
    print(classification_report(y_test, y_pred, zero_division=0))

    return pipeline


# ---------------------------------------------------------------------------
# Manifest generation
# ---------------------------------------------------------------------------
def write_manifest(model_bytes: bytes, classes: list[str], dataset_path: Path):
    manifest = {
        "artifact": {
            "filename": "query_classifier.pkl",
            "path": str(OUT_MODEL.relative_to(ROOT)),
            "byte_size": len(model_bytes),
            "sha256": hashlib.sha256(model_bytes).hexdigest(),
            "type": "sklearn.pipeline.Pipeline",
            "created": datetime.now(timezone.utc).isoformat(),
        },
        "training": {
            "dataset_sources": [str(dataset_path.relative_to(ROOT))],
            "script_path": str(Path(__file__).relative_to(ROOT)),
            "script_exists": True,
            "notes": "Reproducible from ERNIE adversarial corpus with heuristic label refinement.",
        },
        "model": {
            "framework": "scikit-learn",
            "pipeline_type": "Pipeline(TfidfVectorizer + LogisticRegression)",
            "exposes_predict_proba": True,
            "classes": classes,
        },
        "routing": {
            "description": "Query-type classifier routes prompts to specific Ollama models and prompt templates.",
            "routes": {
                "tamas": {"model": "special-virus", "prompt": "v5.1"},
                "v7": {"model": "gemma3:1b", "prompt": "v3"},
                "benign_simple": {"model": "special-virus", "prompt": "v5"},
                "benign_gray_area": {"model": "special-virus", "prompt": "v5"},
                "benign_adversarial_benign": {"model": "special-virus", "prompt": "v5"},
                "benign_domain_specific": {"model": "special-virus", "prompt": "v5"},
                "benign_edge_cases": {"model": "special-virus", "prompt": "v5"},
                "benign_ernie_corpus": {"model": "llama-guard3:1b", "prompt": "v5.2"},
                "attack_ernie": {"model": "special-virus", "prompt": "v5.1"},
            },
            "fallback": {
                "model": "special-virus",
                "prompt": "v3",
                "trigger": "classifier confidence < 0.3",
            },
        },
        "validation": {
            "last_benchmark": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "notes": "Train/test split 80/20 with stratification. Full benchmark pending.",
        },
        "security": {
            "safe_load": True,
            "pickle_warning": "Local artifact only. Do not load untrusted pickles.",
            "git_policy": "UNTRACKED — regenerate on demand with this script.",
        },
    }
    with open(OUT_MANIFEST, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"Manifest written to: {OUT_MANIFEST}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Train Guard Plane query classifier")
    parser.add_argument("--dataset", type=Path, default=SRC_DATASET, help="Path to adversarial dataset")
    parser.add_argument("--output", type=Path, default=OUT_MODEL, help="Output pickle path")
    args = parser.parse_args()

    print("=" * 60)
    print("NEXUS Guard Plane — Query Classifier Training Pipeline")
    print("=" * 60)

    texts, labels = load_ernie_jsonl(args.dataset)
    print(f"Loaded {len(texts)} samples from {args.dataset}")
    print(f"Label distribution: {dict(Counter(labels))}")

    model = train(texts, labels)

    model_bytes = pickle.dumps(model)
    with open(args.output, "wb") as f:
        f.write(model_bytes)
    print(f"Model saved to: {args.output}")

    write_manifest(model_bytes, list(model.classes_), args.dataset)
    print("\nDone.")


if __name__ == "__main__":
    main()
