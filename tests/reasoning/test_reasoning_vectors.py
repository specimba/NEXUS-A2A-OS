"""Tests for the reasoning_vectors module."""

import tempfile
import pytest
import numpy as np

from nexus_os.reasoning.reasoning_vectors import ReasoningVectorizer
from nexus_os.reasoning.pattern_extractor import ReasoningPattern, PATTERN_CATEGORIES


class TestReasoningVectorizer:
    """Tests for the ReasoningVectorizer class."""

    @pytest.fixture
    def vectorizer(self):
        """Create a fresh ReasoningVectorizer."""
        return ReasoningVectorizer(dimensions=128)

    @pytest.fixture
    def ten_patterns(self):
        """Create 10 diverse ReasoningPattern instances."""
        patterns = []
        cats = list(PATTERN_CATEGORIES)
        for i in range(10):
            cat = cats[i % len(cats)]
            patterns.append(ReasoningPattern(
                pattern_id=f"vec-test-{i}",
                category=cat,
                subcategory="general",
                text=f"This is sample reasoning text for pattern number {i}.",
                context="USER: Test query",
                tool_sequence=[],
                confidence=0.5 + i * 0.04,
                source_uid="test",
            ))
        return patterns

    def test_fit_transform_shape(self, vectorizer, ten_patterns):
        """Fit on 10 patterns, verify output shape is (10, 128)."""
        vectors = vectorizer.fit_transform(ten_patterns)
        assert vectors.shape == (10, 128)

    def test_fit_transform_identity(self, vectorizer):
        """Same text patterns produce similar vectors."""
        patterns = [
            ReasoningPattern(
                pattern_id="a-1", category="DIAGNOSIS", subcategory="general",
                text="Let me check the environment state and verify the current config.",
                context="USER: q", tool_sequence=[], confidence=0.8, source_uid="t",
            ),
            ReasoningPattern(
                pattern_id="a-2", category="DIAGNOSIS", subcategory="general",
                text="Let me check the environment state and verify the current config.",
                context="USER: q", tool_sequence=[], confidence=0.8, source_uid="t",
            ),
        ]
        vectors = vectorizer.fit_transform(patterns)
        sim = vectorizer.similarity(vectors[0], vectors[1])
        assert sim > 0.99

    def test_similarity_same(self, vectorizer, ten_patterns):
        """Same vector yields similarity ~1.0."""
        vectors = vectorizer.fit_transform(ten_patterns)
        sim = vectorizer.similarity(vectors[0], vectors[0])
        assert abs(sim - 1.0) < 1e-6

    def test_similarity_orthogonal(self, vectorizer):
        """Orthogonal vectors yield similarity ~0.0."""
        vec_a = np.array([1.0, 0.0, 0.0], dtype=np.float64)
        vec_b = np.array([0.0, 1.0, 0.0], dtype=np.float64)
        sim = vectorizer.similarity(vec_a, vec_b)
        assert abs(sim) < 1e-6

    def test_find_similar(self, vectorizer, ten_patterns):
        """After fit_transform, find_similar returns k results."""
        vectorizer.fit_transform(ten_patterns)
        query = ten_patterns[0]
        results = vectorizer.find_similar(query, k=3)
        assert len(results) == 3
        for pat, score in results:
            assert isinstance(pat, ReasoningPattern)
            assert 0.0 <= score <= 1.0

    def test_save_load(self, vectorizer, ten_patterns):
        """Save and load vectorizer, verify vectors match."""
        vectors_orig = vectorizer.fit_transform(ten_patterns)
        with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as f:
            path = f.name
            vectorizer.save(path)

        v2 = ReasoningVectorizer(dimensions=128)
        v2.load(path)
        v2._vectors = vectors_orig

        import os
        os.unlink(path)

        for pat in ten_patterns:
            vec = v2.transform([pat])[0]
            assert vec.shape == (128,)

    def test_not_fitted_error(self, vectorizer, ten_patterns):
        """transform() without fit() raises RuntimeError."""
        with pytest.raises(RuntimeError, match="not fitted"):
            vectorizer.transform(ten_patterns[:3])


class TestClustering:
    """Tests for clustering functionality."""

    def test_get_cluster_centroids(self):
        """With enough patterns, returns n_clusters centroids."""
        patterns = [
            ReasoningPattern(
                pattern_id=f"clust-{i}", category="DIAGNOSIS",
                subcategory="general",
                text=f"Check the environment state for iteration {i}.",
                context="USER: q", tool_sequence=[], confidence=0.8,
                source_uid="test",
            )
            for i in range(20)
        ]
        vz = ReasoningVectorizer(dimensions=16)
        vz.fit_transform(patterns)
        centroids = vz.get_cluster_centroids(n_clusters=3)
        assert len(centroids) == 3
        for cid, vec in centroids.items():
            assert cid.startswith("cluster_")
            assert isinstance(vec, np.ndarray)
            assert vec.shape == (16,)

    def test_get_cluster_centroids_empty(self):
        """With 0 vectors, returns {} (skip if no patterns)."""
        vz = ReasoningVectorizer(dimensions=16)
        with pytest.raises(RuntimeError):
            vz.get_cluster_centroids(n_clusters=3)
