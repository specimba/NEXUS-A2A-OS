"""
reasoning/reasoning_vectors.py — FableReasoningEngine Vectorizer

Converts extracted ReasoningPattern instances into numerical vectors
using TF-IDF for text features and tool sequence encoding for behavioral
features. Supports similarity search, clustering, and persistence.
"""

import json
import math
import pickle
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from nexus_os.reasoning.pattern_extractor import PATTERN_CATEGORIES, ReasoningPattern


# ── TF-IDF implementation (no sklearn dependency) ───────────────────────

class _TFIDFModel:
    """Minimal TF-IDF vectorizer using only numpy."""

    def __init__(self, max_features: int = 512) -> None:
        self.max_features = max_features
        self.vocab: Dict[str, int] = {}
        self.idf: Optional[np.ndarray] = None
        self._fitted = False

    def fit(self, documents: List[str]) -> None:
        """Build vocabulary and compute IDF weights.

        Args:
            documents: List of text strings.
        """
        doc_freq: Counter = Counter()
        term_freq: Counter = Counter()
        n_docs = len(documents)

        for doc in documents:
            tokens = self._tokenize(doc)
            unique_tokens = set(tokens)
            for t in unique_tokens:
                doc_freq[t] += 1
            for t in tokens:
                term_freq[t] += 1

        # Select top features by frequency
        most_common = term_freq.most_common(self.max_features)
        self.vocab = {word: idx for idx, (word, _) in enumerate(most_common)}

        # Compute IDF: log(N / df) with smoothing
        self.idf = np.zeros(len(self.vocab), dtype=np.float64)
        for word, idx in self.vocab.items():
            df = doc_freq.get(word, 0)
            self.idf[idx] = math.log((n_docs + 1) / (df + 1)) + 1.0

        self._fitted = True

    def transform(self, documents: List[str]) -> np.ndarray:
        """Transform documents to TF-IDF vectors.

        Args:
            documents: List of text strings.

        Returns:
            2D numpy array of shape (n_documents, vocab_size).
        """
        if not self._fitted:
            raise RuntimeError("Model not fitted. Call fit() first.")

        n_docs = len(documents)
        vocab_size = len(self.vocab)
        matrix = np.zeros((n_docs, vocab_size), dtype=np.float64)

        for i, doc in enumerate(documents):
            tokens = self._tokenize(doc)
            if not tokens:
                continue

            token_counts = Counter(tokens)
            doc_len = len(tokens)

            for token, count in token_counts.items():
                if token in self.vocab:
                    tf = count / doc_len
                    idx = self.vocab[token]
                    matrix[i, idx] = tf * self.idf[idx]

            # L2 normalize
            norm = np.linalg.norm(matrix[i])
            if norm > 0:
                matrix[i] /= norm

        return matrix

    def fit_transform(self, documents: List[str]) -> np.ndarray:
        """Fit and transform in one step.

        Args:
            documents: List of text strings.

        Returns:
            2D numpy array of TF-IDF vectors.
        """
        self.fit(documents)
        return self.transform(documents)

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """Simple whitespace + lowering tokenizer.

        Args:
            text: Input text.

        Returns:
            List of lowercase token strings.
        """
        return [
            w for w in text.lower().split()
            if len(w) > 1 and w.isalpha()
        ]


# ── Tool sequence encoder ───────────────────────────────────────────────

class _ToolSequenceEncoder:
    """Encodes tool call sequences into fixed-length numerical vectors."""

    KNOWN_TOOLS = (
        "Read", "Edit", "Bash", "Grep", "Glob",
        "Write", "Webfetch", "Task", "Backgroundprocess",
    )

    def __init__(self, max_seq_len: int = 20) -> None:
        self.max_seq_len = max_seq_len
        self.tool_to_idx: Dict[str, int] = {
            t: i + 1 for i, t in enumerate(self.KNOWN_TOOLS)
        }
        self.unknown_idx = len(self.KNOWN_TOOLS) + 1
        self.vocab_size = self.unknown_idx + 1

    def encode(self, sequences: List[List[str]]) -> np.ndarray:
        """Encode variable-length tool sequences into fixed-length vectors.

        Each sequence is padded/truncated to max_seq_len. The encoding
        captures: individual tool counts (bag-of-tools), transition
        bigrams, and sequence length.

        Args:
            sequences: List of tool sequences.

        Returns:
            2D array of shape (n_sequences, feature_dim).
        """
        n = len(sequences)
        # Features: one-hot counts per tool + transition bigrams + metadata
        feature_dim = self.vocab_size + self.vocab_size ** 2 + 3
        matrix = np.zeros((n, feature_dim), dtype=np.float64)

        for i, seq in enumerate(sequences):
            if not seq:
                continue

            # Bag-of-tools counts (normalized)
            tool_counts = Counter(seq[:self.max_seq_len])
            total = sum(tool_counts.values())
            for tool, count in tool_counts.items():
                idx = self.tool_to_idx.get(tool, self.unknown_idx)
                matrix[i, idx] = count / total

            # Transition bigrams
            truncated = seq[:self.max_seq_len]
            bigram_offset = self.vocab_size
            n_bigrams = max(len(truncated) - 1, 1)
            for j in range(len(truncated) - 1):
                t1 = self.tool_to_idx.get(truncated[j], self.unknown_idx)
                t2 = self.tool_to_idx.get(truncated[j + 1], self.unknown_idx)
                bigram_idx = bigram_offset + t1 * self.vocab_size + t2
                if bigram_idx < feature_dim:
                    matrix[i, bigram_idx] += 1.0 / n_bigrams

            # Metadata features
            meta_offset = self.vocab_size + self.vocab_size ** 2
            matrix[i, meta_offset] = min(len(seq) / self.max_seq_len, 1.0)
            # Unique tool ratio
            unique_tools = len(set(truncated))
            matrix[i, meta_offset + 1] = unique_tools / max(self.vocab_size, 1)
            # Repeat ratio (how often tools repeat)
            matrix[i, meta_offset + 2] = (
                1.0 - unique_tools / max(len(truncated), 1)
            )

        # L2 normalize rows
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms = np.where(norms > 0, norms, 1.0)
        matrix /= norms

        return matrix


# ── Category encoder ────────────────────────────────────────────────────

class _CategoryEncoder:
    """Encodes pattern categories and subcategories into one-hot vectors."""

    def __init__(self) -> None:
        self.cat_to_idx = {c: i for i, c in enumerate(PATTERN_CATEGORIES)}
        self.dim = len(PATTERN_CATEGORIES)

    def encode(self, categories: List[str]) -> np.ndarray:
        """One-hot encode category strings.

        Args:
            categories: List of category name strings.

        Returns:
            2D array of shape (n, dim).
        """
        n = len(categories)
        matrix = np.zeros((n, self.dim), dtype=np.float64)
        for i, cat in enumerate(categories):
            idx = self.cat_to_idx.get(cat, -1)
            if 0 <= idx < self.dim:
                matrix[i, idx] = 1.0
        return matrix


# ── Main vectorizer ─────────────────────────────────────────────────────

class ReasoningVectorizer:
    """
    Converts ReasoningPattern instances into fixed-dimensional vectors.

    Combines TF-IDF text features, tool sequence encoding, and category
    one-hot encoding into a single concatenated vector per pattern.
    Supports cosine similarity search and k-means clustering.
    """

    def __init__(self, dimensions: int = 128) -> None:
        """Initialize vectorizer.

        Args:
            dimensions: Target output dimensionality. The final embedding
                is projected down to this size via a random orthogonal
                projection matrix (deterministic, reproducible).
        """
        self.dimensions = dimensions
        self._tfidf = _TFIDFModel(max_features=256)
        self._tool_encoder = _ToolSequenceEncoder()
        self._cat_encoder = _CategoryEncoder()
        self._projection: Optional[np.ndarray] = None
        self._patterns: List[ReasoningPattern] = []
        self._vectors: Optional[np.ndarray] = None
        self._fitted = False

    def fit(self, patterns: List[ReasoningPattern]) -> None:
        """Fit vectorizer on a list of patterns.

        Builds TF-IDF vocabulary, computes the dimensionality reduction
        projection matrix, and stores patterns for later similarity search.

        Args:
            patterns: List of ReasoningPattern instances.
        """
        self._patterns = list(patterns)
        texts = [p.text for p in patterns]

        # Fit TF-IDF on pattern texts
        self._tfidf.fit(texts)

        # Compute raw feature dimensionality
        tfidf_dim = len(self._tfidf.vocab)
        tool_feat_dim = (
            self._tool_encoder.vocab_size
            + self._tool_encoder.vocab_size ** 2
            + 3
        )
        cat_dim = self._cat_encoder.dim
        raw_dim = tfidf_dim + tool_feat_dim + cat_dim

        # Build random projection matrix (seeded for reproducibility)
        rng = np.random.RandomState(42)
        if raw_dim > self.dimensions:
            # Gaussian projection with normalization
            raw_matrix = rng.randn(raw_dim, self.dimensions)
            raw_matrix /= np.linalg.norm(raw_matrix, axis=0, keepdims=True)
            self._projection = raw_matrix
        else:
            self._projection = None  # No projection needed

        self._fitted = True

    def transform(self, patterns: List[ReasoningPattern]) -> np.ndarray:
        """Transform patterns to vectors.

        Args:
            patterns: List of ReasoningPattern instances.

        Returns:
            2D numpy array of shape (n_patterns, dimensions).
        """
        if not self._fitted:
            raise RuntimeError("Vectoriser not fitted. Call fit() first.")

        raw = self._build_raw_features(patterns)

        if self._projection is not None:
            vectors = raw @ self._projection
        else:
            vectors = raw

        # Final L2 normalization
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms = np.where(norms > 0, norms, 1.0)
        vectors /= norms

        return vectors

    def fit_transform(self, patterns: List[ReasoningPattern]) -> np.ndarray:
        """Fit and transform patterns in one step.

        Args:
            patterns: List of ReasoningPattern instances.

        Returns:
            2D numpy array of shape (n_patterns, dimensions).
        """
        self.fit(patterns)
        vectors = self.transform(patterns)
        self._vectors = vectors
        return vectors

    def _build_raw_features(self, patterns: List[ReasoningPattern]) -> np.ndarray:
        """Build concatenated raw feature matrix before projection.

        Args:
            patterns: List of ReasoningPattern instances.

        Returns:
            2D numpy array of raw features.
        """
        # Text features (TF-IDF)
        texts = [p.text for p in patterns]
        tfidf_matrix = self._tfidf.transform(texts)

        # Tool sequence features
        tool_seqs = [p.tool_sequence for p in patterns]
        tool_matrix = self._tool_encoder.encode(tool_seqs)

        # Category features
        categories = [p.category for p in patterns]
        cat_matrix = self._cat_encoder.encode(categories)

        # Concatenate
        raw = np.hstack([tfidf_matrix, tool_matrix, cat_matrix]).astype(np.float64)
        return raw

    def similarity(self, vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        """Compute cosine similarity between two vectors.

        Args:
            vec_a: First vector.
            vec_b: Second vector.

        Returns:
            Cosine similarity score in [-1, 1].
        """
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        # Clip to [-1, 1]: float rounding can push a self-similarity to
        # 1.0000000000000002, which breaks downstream range assumptions.
        return float(np.clip(np.dot(vec_a, vec_b) / (norm_a * norm_b), -1.0, 1.0))

    def find_similar(
        self,
        query_pattern: ReasoningPattern,
        k: int = 5,
    ) -> List[Tuple[ReasoningPattern, float]]:
        """Find k most similar patterns to a query pattern.

        Transforms the query and computes cosine similarity against all
        stored pattern vectors.

        Args:
            query_pattern: The pattern to find neighbours for.
            k: Number of results to return.

        Returns:
            List of (pattern, similarity_score) tuples sorted descending.
        """
        if self._vectors is None or not self._fitted:
            raise RuntimeError("No vectors available. Call fit_transform() first.")

        query_vec = self.transform([query_pattern])[0]

        similarities = np.array([
            self.similarity(query_vec, v) for v in self._vectors
        ])

        # Top-k indices (descending similarity)
        k = min(k, len(similarities))
        top_indices = np.argsort(similarities)[::-1][:k]

        results: List[Tuple[ReasoningPattern, float]] = []
        for idx in top_indices:
            results.append((
                self._patterns[idx],
                float(similarities[idx]),
            ))

        return results

    def get_cluster_centroids(
        self, n_clusters: int = 10
    ) -> Dict[str, np.ndarray]:
        """Compute k-means cluster centroids from stored patterns.

        Uses a simple iterative k-means implementation (no sklearn).

        Args:
            n_clusters: Number of clusters.

        Returns:
            Dict mapping cluster_id ('cluster_0', ...) to centroid vector.
        """
        if self._vectors is None or not self._fitted:
            raise RuntimeError("No vectors available. Call fit_transform() first.")

        X = self._vectors
        n_samples = X.shape[0]
        n_clusters = min(n_clusters, n_samples)

        if n_clusters <= 0:
            return {}

        # Initialize centroids using k-means++
        rng = np.random.RandomState(42)
        centroids = np.zeros((n_clusters, X.shape[1]), dtype=np.float64)

        # First centroid: random
        centroids[0] = X[rng.randint(n_samples)]

        for c in range(1, n_clusters):
            dists = np.min([
                np.sum((X - centroids[j]) ** 2, axis=1)
                for j in range(c)
            ], axis=0)
            probs = dists / dists.sum()
            cumulative = np.cumsum(probs)
            r = rng.random()
            idx = int(np.searchsorted(cumulative, r))
            idx = min(idx, n_samples - 1)
            centroids[c] = X[idx]

        # Iterate
        for _ in range(50):
            # Assign
            dists = np.array([
                np.sum((X - centroids[j]) ** 2, axis=1)
                for j in range(n_clusters)
            ])
            labels = np.argmin(dists, axis=0)

            # Update
            new_centroids = np.zeros_like(centroids)
            for c in range(n_clusters):
                mask = labels == c
                if mask.any():
                    new_centroids[c] = X[mask].mean(axis=0)
                else:
                    new_centroids[c] = centroids[c]

            if np.allclose(centroids, new_centroids, atol=1e-6):
                break
            centroids = new_centroids

        result: Dict[str, np.ndarray] = {}
        for c in range(n_clusters):
            result[f"cluster_{c}"] = centroids[c]
        return result

    def save(self, path: str) -> None:
        """Save vectorizer state to disk.

        Persists the full vectorizer including TF-IDF model, encoders,
        projection matrix, fitted patterns, and computed vectors.

        Args:
            path: File path for the saved state (pickle format).
        """
        state = {
            "dimensions": self.dimensions,
            "tfidf": {
                "max_features": self._tfidf.max_features,
                "vocab": self._tfidf.vocab,
                "idf": self._tfidf.idf,
                "_fitted": self._tfidf._fitted,
            },
            "tool_encoder": {
                "max_seq_len": self._tool_encoder.max_seq_len,
            },
            "projection": self._projection,
            "patterns": self._patterns,
            "vectors": self._vectors,
            "_fitted": self._fitted,
        }

        with open(path, "wb") as f:
            pickle.dump(state, f, protocol=pickle.HIGHEST_PROTOCOL)

    def load(self, path: str) -> None:
        """Load vectorizer state from disk.

        Restores all internal state from a previously saved pickle file.

        Args:
            path: File path to load from.
        """
        with open(path, "rb") as f:
            state = pickle.load(f)  # noqa: S301

        self.dimensions = state["dimensions"]
        self._projection = state["projection"]
        self._patterns = state["patterns"]
        self._vectors = state["vectors"]
        self._fitted = state["_fitted"]

        tfidf_state = state["tfidf"]
        self._tfidf = _TFIDFModel(max_features=tfidf_state["max_features"])
        self._tfidf.vocab = tfidf_state["vocab"]
        self._tfidf.idf = tfidf_state["idf"]
        self._tfidf._fitted = tfidf_state["_fitted"]

        te_state = state["tool_encoder"]
        self._tool_encoder = _ToolSequenceEncoder(max_seq_len=te_state["max_seq_len"])
