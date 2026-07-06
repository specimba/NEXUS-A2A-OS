"""
reasoning/fable_engine.py — FableReasoningEngine Top-Level Orchestrator

Wires together PatternExtractor, ReasoningVectorizer, and
ReasoningTemplateEngine into a unified interface for extracting,
vectorizing, and generating reasoning templates from CoT trajectories.

Provides CLI entry point for nexusctl reasoning subcommands.
"""

import argparse
import json
import logging
import pickle
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from nexus_os.reasoning.pattern_extractor import (
    PATTERN_CATEGORIES,
    PatternExtractor,
    ReasoningPattern,
)
from nexus_os.reasoning.reasoning_vectors import (
    ReasoningVectorizer,
    _TFIDFModel,
    _ToolSequenceEncoder,
)
from nexus_os.reasoning.reasoning_templates import (
    ReasoningStyle,
    ReasoningTemplateEngine,
)

logger = logging.getLogger(__name__)

_DEFAULT_COT_PATH = (
    Path.home()
    / "Downloads"
    / "ARCHIVIST"
    / "PAPERS"
    / "DATASETs"
    / "fable5_cot_merged.jsonl"
)


class FableReasoningEngine:
    """Top-level orchestrator for the Fable reasoning pipeline.

    Manages the lifecycle of pattern extraction, vectorization, and
    template generation. Provides a unified API for analysis, prompt
    generation, similarity search, clustering, and training data export.
    """

    def __init__(
        self,
        cot_path: Optional[str] = None,
        vectorizer_path: Optional[str] = None,
        template_style: str = "fable",
        patterns: Optional[List[ReasoningPattern]] = None,
    ) -> None:
        """Initialize the FableReasoningEngine.

        Args:
            cot_path: Path to fable5_cot_merged.jsonl. If None, no
                CoT data is loaded at init time.
            vectorizer_path: Path to load a pre-saved vectorizer state.
                If None, the vectorizer is fitted from scratch during
                initialize().
            template_style: Default reasoning style for template
                generation. One of "fable", "nexus", "hybrid".
            patterns: Pre-built patterns to seed the engine with,
                bypassing CoT extraction (e.g. from a live trace source
                or in tests).
        """
        self.cot_path = cot_path
        self.vectorizer_path = vectorizer_path

        style_map = {
            "fable": ReasoningStyle.FABLE,
            "nexus": ReasoningStyle.NEXUS,
            "hybrid": ReasoningStyle.HYBRID,
        }
        resolved_style = style_map.get(template_style, ReasoningStyle.FABLE)

        self.extractor: Optional[PatternExtractor] = None
        self.vectorizer: Optional[ReasoningVectorizer] = None
        self.template_engine = ReasoningTemplateEngine(style=resolved_style)
        self.patterns: List[ReasoningPattern] = list(patterns) if patterns else []

    # ── Initialization ────────────────────────────────────────────────

    def initialize(self) -> None:
        """Load patterns from CoT file and prepare the vectorizer.

        If cot_path was provided, patterns are extracted from the CoT
        dataset. If vectorizer_path was provided, the vectorizer state
        is loaded from disk. Otherwise the vectorizer is fitted from
        scratch on the extracted patterns.
        """
        if self.cot_path:
            try:
                path = Path(self.cot_path)
                if path.exists():
                    self.extractor = PatternExtractor(str(path))
                    count = self._do_extract(limit=500)
                    logger.info(
                        "Extracted %d patterns from %s", count, self.cot_path
                    )
                else:
                    logger.warning("CoT path does not exist: %s", self.cot_path)
                    self.extractor = None
            except Exception:
                logger.exception("Failed to load CoT file: %s", self.cot_path)
                self.extractor = None

        if self.vectorizer_path:
            try:
                path = Path(self.vectorizer_path)
                if path.exists():
                    self.vectorizer = ReasoningVectorizer()
                    self.vectorizer.load(str(path))
                    self.patterns = list(self.vectorizer._patterns)
                    logger.info(
                        "Loaded vectorizer from %s (%d patterns)",
                        self.vectorizer_path,
                        len(self.patterns),
                    )
                else:
                    logger.warning(
                        "Vectorizer path does not exist: %s", self.vectorizer_path
                    )
                    self.vectorizer = None
            except Exception:
                logger.exception(
                    "Failed to load vectorizer: %s", self.vectorizer_path
                )
                self.vectorizer = None

        if self.vectorizer is None and self.patterns:
            self.vectorizer = ReasoningVectorizer()
            try:
                self.vectorizer.fit_transform(self.patterns)
                logger.info(
                    "Fitted vectorizer on %d patterns", len(self.patterns)
                )
            except Exception:
                logger.exception("Failed to fit vectorizer")

        if self.patterns and self.extractor:
            stats = self.extractor.get_pattern_stats()
            _log_pattern_stats(stats)

    def _do_extract(self, limit: int = 500) -> int:
        """Run extraction and store patterns internally.

        Args:
            limit: Maximum entries to process from the CoT file.

        Returns:
            Number of patterns extracted.
        """
        if self.extractor is None:
            return 0
        self.patterns = self.extractor.extract_all(limit=limit)
        return len(self.patterns)

    # ── Pattern extraction ─────────────────────────────────────────────

    def extract_patterns(self, limit: int = 100) -> Dict[str, int]:
        """Extract patterns from the CoT file.

        Args:
            limit: Maximum number of JSONL entries to process.

        Returns:
            Dict mapping category name to pattern count.
        """
        if self.extractor is None:
            if self.cot_path:
                try:
                    path = Path(self.cot_path)
                    if path.exists():
                        self.extractor = PatternExtractor(str(path))
                    else:
                        logger.warning("CoT file not found: %s", self.cot_path)
                        return {}
                except Exception:
                    logger.exception("Failed to create extractor")
                    return {}
            else:
                logger.warning("No cot_path configured for extraction")
                return {}

        self._do_extract(limit=limit)

        if self.vectorizer is None and self.patterns:
            self.vectorizer = ReasoningVectorizer()
            try:
                self.vectorizer.fit_transform(self.patterns)
            except Exception:
                logger.exception("Failed to fit vectorizer after extraction")

        stats = self.extractor.get_pattern_stats()
        _log_pattern_stats(stats)
        return {k: v for k, v in stats.items() if k != "TOTAL"}

    def extract_patterns_from_file(
        self, path: str, limit: int = 100
    ) -> List[ReasoningPattern]:
        """Extract patterns from an arbitrary CoT JSONL file.

        Unlike extract_patterns(), this does not require cot_path to be
        configured; extracted patterns are appended to the engine's
        pattern store.

        Args:
            path: Path to a CoT-format JSONL file.
            limit: Maximum number of JSONL entries to process.

        Returns:
            The list of patterns extracted from this file.
        """
        extractor = PatternExtractor(str(path))
        extracted = extractor.extract_all(limit=limit)
        self.patterns.extend(extracted)
        return extracted

    # ── Trajectory analysis ────────────────────────────────────────────

    def analyze_trajectory(self, context: str) -> Dict[str, Any]:
        """Analyze a single CoT trajectory string.

        Parses the context into turns, extracts patterns, tool sequences,
        and error recovery records.

        Args:
            context: Raw CoT trajectory string containing USER:,
                ASSISTANT:, and TOOL RESULT: markers.

        Returns:
            Dict with keys: turns, patterns, tool_sequences,
            error_recoveries, stats.
        """
        result: Dict[str, Any] = {
            "turns": [],
            "patterns": [],
            "tool_sequences": [],
            "error_recoveries": [],
            "stats": {},
        }

        if not context or not context.strip():
            return result

        if self.extractor is None:
            placeholder = PatternExtractor.__new__(PatternExtractor)
            placeholder.cot_file_path = ""
            placeholder._patterns = []
            placeholder._raw_entries = []
            # Minimal instance to access methods
            extractor = placeholder
            # Re-bind to avoid __init__ requirement
            extractor.parse_trajectory = PatternExtractor.parse_trajectory.__get__(
                extractor, PatternExtractor
            )
            extractor.extract_patterns = PatternExtractor.extract_patterns.__get__(
                extractor, PatternExtractor
            )
            extractor.extract_tool_sequences = (
                PatternExtractor.extract_tool_sequences.__get__(
                    extractor, PatternExtractor
                )
            )
            extractor.extract_error_recovery = (
                PatternExtractor.extract_error_recovery.__get__(
                    extractor, PatternExtractor
                )
            )
        else:
            extractor = self.extractor

        try:
            turns = extractor.parse_trajectory(context)
            result["turns"] = [
                {"role": t.role, "content": t.content[:200], "index": t.index}
                for t in turns
            ]

            patterns = extractor.extract_patterns(turns)
            result["patterns"] = [
                {
                    "category": p.category,
                    "subcategory": p.subcategory,
                    "confidence": p.confidence,
                    "text_preview": p.text[:200],
                }
                for p in patterns
            ]

            tool_sequences = extractor.extract_tool_sequences(turns)
            result["tool_sequences"] = tool_sequences

            error_recoveries = extractor.extract_error_recovery(turns)
            result["error_recoveries"] = error_recoveries

            # Compute per-category counts
            cat_counts: Dict[str, int] = {}
            for p in patterns:
                cat_counts[p.category] = cat_counts.get(p.category, 0) + 1
            result["stats"] = {
                "total_turns": len(turns),
                "total_patterns": len(patterns),
                "tool_sequence_count": len(tool_sequences),
                "error_recovery_count": len(error_recoveries),
                "category_counts": cat_counts,
            }
        except Exception:
            logger.exception("Failed to analyze trajectory")
            result["stats"] = {"error": "analysis_failed"}

        return result

    # ── Prompt generation ──────────────────────────────────────────────

    def generate_prompt(
        self,
        task_type: str = "debug",
        complexity: str = "L2",
        query: str = "",
    ) -> str:
        """Generate a full system prompt with reasoning template.

        Delegates to ReasoningTemplateEngine.generate_system_prompt()
        and appends the user query if provided.

        Args:
            task_type: Category of task (e.g. 'debug', 'feature',
                'refactor', 'security', 'analysis').
            complexity: CogER complexity level ('L1'-'L4').
            query: Optional user query to append.

        Returns:
            Complete system prompt string.
        """
        prompt = self.template_engine.generate_system_prompt(
            task_type=task_type, complexity=complexity
        )
        if query:
            prompt += f"\n\n## User Query\n{query}"
        return prompt

    # ── Reasoning injection ────────────────────────────────────────────

    def inject_reasoning(
        self,
        base_prompt: str,
        query: str,
        style: Optional[str] = None,
    ) -> str:
        """Inject reasoning template into an existing prompt.

        Args:
            base_prompt: The existing system prompt to extend.
            query: The user query to append after the injection.
            style: Optional override of the default reasoning style.
                One of "fable", "nexus", "hybrid". Uses the engine's
                default if None.

        Returns:
            Modified prompt with reasoning instructions injected.
        """
        if style is not None:
            original = self.template_engine.style
            style_map = {
                "fable": ReasoningStyle.FABLE,
                "nexus": ReasoningStyle.NEXUS,
                "hybrid": ReasoningStyle.HYBRID,
            }
            self.template_engine.style = style_map.get(
                style, ReasoningStyle.FABLE
            )

        try:
            result = self.template_engine.inject_into_prompt(base_prompt, query)
        finally:
            if style is not None:
                self.template_engine.style = original

        return result

    # ── Similarity search ──────────────────────────────────────────────

    def find_similar_patterns(
        self,
        query_text: str,
        k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Find patterns similar to query text.

        Creates a temporary ReasoningPattern from the query text and
        searches the vectorizer's stored patterns for nearest neighbours.

        Args:
            query_text: Text to find similar patterns for.
            k: Number of results to return.

        Returns:
            List of dicts with keys: category, text, confidence,
            similarity_score.
        """
        if self.vectorizer is None or not self.vectorizer._fitted:
            logger.warning("Vectorizer not fitted; cannot search similar patterns")
            return []

        if not self.vectorizer._patterns:
            return []

        query_pattern = ReasoningPattern(
            pattern_id="__query__",
            category="QUERY",
            subcategory="user_query",
            text=query_text,
            context="",
            tool_sequence=[],
            confidence=1.0,
            source_uid="",
        )

        try:
            results = self.vectorizer.find_similar(query_pattern, k=k)
        except (RuntimeError, Exception):
            logger.exception("Similarity search failed")
            return []

        return [
            {
                "category": p.category,
                "text": p.text[:300],
                "confidence": p.confidence,
                "similarity_score": round(score, 4),
            }
            for p, score in results
        ]

    # ── Clustering ─────────────────────────────────────────────────────

    def get_cluster_summary(self, n_clusters: int = 10) -> Dict[str, Any]:
        """Get k-means cluster mapping from the vectorizer.

        Args:
            n_clusters: Number of clusters to compute.

        Returns:
            Dict mapping cluster_id to list of pattern dicts in that
            cluster. Returns empty dict if vectorizer is not fitted.
        """
        if self.vectorizer is None or not self.vectorizer._fitted:
            logger.warning("Vectorizer not fitted; cannot compute clusters")
            return {}

        try:
            centroids = self.vectorizer.get_cluster_centroids(
                n_clusters=n_clusters
            )
        except (RuntimeError, Exception):
            logger.exception("Clustering failed")
            return {}

        if not centroids:
            return {}

        patterns = self.vectorizer._patterns
        vectors = self.vectorizer._vectors
        if vectors is None or len(patterns) == 0:
            return {}

        # Assign each pattern to the nearest centroid
        cluster_ids = sorted(centroids.keys(), key=_cluster_sort_key)
        centroid_arr = np.array([centroids[cid] for cid in cluster_ids])

        dists = np.zeros((len(patterns), len(cluster_ids)), dtype=np.float64)
        for i, vec in enumerate(vectors):
            for j, centroid in enumerate(centroid_arr):
                dists[i, j] = np.linalg.norm(vec - centroid)

        labels = np.argmin(dists, axis=1)

        summary: Dict[str, List[Dict[str, Any]]] = {}
        for i, pattern in enumerate(patterns):
            cid = cluster_ids[labels[i]]
            if cid not in summary:
                summary[cid] = []
            summary[cid].append({
                "category": pattern.category,
                "subcategory": pattern.subcategory,
                "confidence": pattern.confidence,
                "text_preview": pattern.text[:200],
                "tool_sequence": pattern.tool_sequence,
            })

        return summary

    # ── Training data export ───────────────────────────────────────────

    def get_training_data(
        self,
        output_path: str,
        format: str = "dpo",
        limit: int = 100,
    ) -> int:
        """Generate training data from extracted patterns.

        Supports DPO and CoT export formats.

        DPO format produces JSONL with 'chosen' and 'rejected' fields
        based on confidence thresholds. High-confidence (>= 0.7) patterns
        become 'chosen', low-confidence (< 0.3) become 'rejected'.

        CoT format produces JSONL with a 'cot' field containing
        template-based chain-of-thought reasoning generated from the
        pattern text.

        Args:
            output_path: Path to write the output JSONL file.
            format: Output format — "dpo" or "cot".
            limit: Maximum number of examples to generate.

        Returns:
            Number of examples written.
        """
        if not self.patterns:
            logger.warning("No patterns available for training data generation")
            return 0

        patterns = self.patterns[:limit]
        count = 0

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                if format == "dpo":
                    count = self._write_dpo(patterns, f)
                elif format == "cot":
                    count = self._write_cot(patterns, f)
                else:
                    logger.warning("Unknown training format: %s", format)
                    return 0
        except OSError:
            logger.exception("Failed to write training data to %s", output_path)
            return 0

        logger.info("Wrote %d %s examples to %s", count, format, output_path)
        return count

    def _write_dpo(
        self,
        patterns: List[ReasoningPattern],
        f: Any,
    ) -> int:
        """Write DPO-format training data.

        Creates chosen/rejected pairs from high/low confidence patterns.
        """
        high_conf = [p for p in patterns if p.confidence >= 0.7]
        low_conf = [p for p in patterns if p.confidence < 0.3]

        count = 0
        for chosen in high_conf:
            # Find a rejected example or use a low-confidence neighbor
            if low_conf:
                rejected_idx = hash(chosen.pattern_id) % len(low_conf)
                rejected = low_conf[rejected_idx]
            else:
                continue

            record = {
                "chosen": self._pattern_to_training_text(chosen),
                "rejected": self._pattern_to_training_text(rejected),
                "chosen_category": chosen.category,
                "rejected_category": rejected.category,
                "chosen_confidence": chosen.confidence,
                "rejected_confidence": rejected.confidence,
            }
            f.write(json.dumps(record) + "\n")
            count += 1

        return count

    def _write_cot(
        self,
        patterns: List[ReasoningPattern],
        f: Any,
    ) -> int:
        """Write CoT-format training data using template expansion."""
        count = 0
        for pattern in patterns:
            template_block = self.template_engine.generate_thinking_block(
                pattern.text[:200]
            )
            record = {
                "uid": pattern.pattern_id,
                "category": pattern.category,
                "subcategory": pattern.subcategory,
                "text": pattern.text,
                "cot": template_block,
                "tool_sequence": pattern.tool_sequence,
                "confidence": pattern.confidence,
            }
            f.write(json.dumps(record) + "\n")
            count += 1

        return count

    @staticmethod
    def _pattern_to_training_text(pattern: ReasoningPattern) -> str:
        """Convert a pattern into a training text snippet."""
        return (
            f"Category: {pattern.category}\n"
            f"Subcategory: {pattern.subcategory}\n"
            f"Confidence: {pattern.confidence:.2f}\n"
            f"Context: {pattern.context[:200]}\n"
            f"Reasoning: {pattern.text[:500]}"
        )

    # ── Save / Load ────────────────────────────────────────────────────

    def save(self, path: str) -> None:
        """Save engine state (patterns + vectorizer) to a pickle file.

        Args:
            path: Destination file path.
        """
        state: Dict[str, Any] = {
            "patterns": self.patterns,
            "vectorizer_state": None,
            "cot_path": self.cot_path,
            "template_style": self.template_engine.style.value,
        }

        if self.vectorizer is not None and self.vectorizer._fitted:
            state["vectorizer_state"] = {
                "dimensions": self.vectorizer.dimensions,
                "tfidf": {
                    "max_features": self.vectorizer._tfidf.max_features,
                    "vocab": self.vectorizer._tfidf.vocab,
                    "idf": self.vectorizer._tfidf.idf,
                    "_fitted": self.vectorizer._tfidf._fitted,
                },
                "tool_encoder": {
                    "max_seq_len": self.vectorizer._tool_encoder.max_seq_len,
                },
                "projection": self.vectorizer._projection,
                "patterns": self.vectorizer._patterns,
                "vectors": self.vectorizer._vectors,
                "_fitted": self.vectorizer._fitted,
            }

        try:
            with open(path, "wb") as f:
                pickle.dump(state, f, protocol=pickle.HIGHEST_PROTOCOL)
            logger.info("Saved engine state to %s", path)
        except OSError:
            logger.exception("Failed to save engine state to %s", path)

    def load(self, path: str) -> None:
        """Load engine state from a previously saved pickle file.

        Restores patterns, vectorizer, and configuration.

        Args:
            path: Source file path.
        """
        try:
            with open(path, "rb") as f:
                state: Dict[str, Any] = pickle.load(f)  # noqa: S301
        except (OSError, pickle.UnpicklingError):
            logger.exception("Failed to load engine state from %s", path)
            return

        self.patterns = state.get("patterns", [])

        vs = state.get("vectorizer_state")
        if vs is not None:
            self.vectorizer = ReasoningVectorizer(
                dimensions=vs.get("dimensions", 128)
            )
            tfidf_state = vs.get("tfidf", {})
            self.vectorizer._tfidf = _TFIDFModel(
                max_features=tfidf_state.get("max_features", 256)
            )
            self.vectorizer._tfidf.vocab = tfidf_state.get("vocab", {})
            self.vectorizer._tfidf.idf = tfidf_state.get("idf")
            self.vectorizer._tfidf._fitted = tfidf_state.get("_fitted", False)

            te_state = vs.get("tool_encoder", {})
            self.vectorizer._tool_encoder = _ToolSequenceEncoder(
                max_seq_len=te_state.get("max_seq_len", 20)
            )

            self.vectorizer._projection = vs.get("projection")
            self.vectorizer._patterns = vs.get("patterns", [])
            self.vectorizer._vectors = vs.get("vectors")
            self.vectorizer._fitted = vs.get("_fitted", False)

        self.cot_path = state.get("cot_path")

        style_str = state.get("template_style", "fable")
        style_map = {
            "fable": ReasoningStyle.FABLE,
            "nexus": ReasoningStyle.NEXUS,
            "hybrid": ReasoningStyle.HYBRID,
        }
        self.template_engine = ReasoningTemplateEngine(
            style=style_map.get(style_str, ReasoningStyle.FABLE)
        )

        logger.info(
            "Loaded engine state from %s (%d patterns)",
            path,
            len(self.patterns),
        )

    # ── Status ─────────────────────────────────────────────────────────

    def status(self) -> Dict[str, Any]:
        """Return a summary of the engine's current state.

        Returns:
            Dict with keys: pattern_count, vectorizer_fitted,
            template_style, cot_path, loaded_paths, category_counts.
        """
        cat_counts: Dict[str, int] = {}
        for p in self.patterns:
            cat_counts[p.category] = cat_counts.get(p.category, 0) + 1

        return {
            "pattern_count": len(self.patterns),
            "vectorizer_fitted": (
                self.vectorizer is not None and self.vectorizer._fitted
            ),
            "template_style": self.template_engine.style.value,
            "cot_path": self.cot_path,
            "loaded_paths": {
                "cot": self.cot_path,
            },
            "category_counts": cat_counts,
        }

    def get_status(self) -> Dict[str, Any]:
        """Alias for status()."""
        return self.status()


# ── Module-level helpers ──────────────────────────────────────────────


def create_default_engine() -> FableReasoningEngine:
    """Create a FableReasoningEngine with the default CoT dataset path.

    Uses the canonical location of fable5_cot_merged.jsonl under the
    user's Downloads/ARCHIVIST/PAPERS/DATASETs directory.

    Returns:
        Initialized FableReasoningEngine instance.
    """
    return FableReasoningEngine(
        cot_path=str(_DEFAULT_COT_PATH),
        template_style="fable",
    )


def _log_pattern_stats(stats: Dict[str, int]) -> None:
    """Log pattern category statistics.

    Args:
        stats: Dict with category names as keys and counts as values.
    """
    total = stats.get("TOTAL", 0)
    if total == 0:
        logger.info("No patterns extracted")
        return

    parts: List[str] = []
    for cat in PATTERN_CATEGORIES:
        count = stats.get(cat, 0)
        if count:
            pct = count / total * 100
            parts.append(f"{cat}={count} ({pct:.0f}%)")
    logger.info("Pattern categories: %s | TOTAL=%d", "  ".join(parts), total)


def _cluster_sort_key(cid: str) -> int:
    """Sort key for cluster_id strings like 'cluster_0'."""
    parts = cid.split("_")
    return int(parts[-1]) if parts[-1].isdigit() else 0


# ── CLI entry point ───────────────────────────────────────────────────


def run_cli(args: argparse.Namespace) -> int:
    """CLI entry point for the nexusctl reasoning command.

    Handles subcommands:
      extract   — Extract patterns from the CoT file
      analyze   — Analyze a single trajectory
      prompt    — Generate a system prompt
      inject    — Inject reasoning into an existing prompt
      similar   — Find similar patterns
      clusters  — Get cluster summary
      train     — Generate training data
      status    — Show engine status

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0 for success, 1 for error).
    """
    if args.action == "extract":
        return _cli_extract(args)
    elif args.action == "analyze":
        return _cli_analyze(args)
    elif args.action == "prompt":
        return _cli_prompt(args)
    elif args.action == "inject":
        return _cli_inject(args)
    elif args.action == "similar":
        return _cli_similar(args)
    elif args.action == "clusters":
        return _cli_clusters(args)
    elif args.action == "train":
        return _cli_train(args)
    elif args.action == "status":
        return _cli_status(args)
    else:
        logger.error("Unknown subcommand: %s", args.action)
        return 1


def _build_engine(args: argparse.Namespace) -> FableReasoningEngine:
    """Build an engine from CLI args or defaults.

    Args:
        args: Parsed CLI arguments.

    Returns:
        Configured FableReasoningEngine instance.
    """
    style = getattr(args, "style", "fable")
    cot_path = getattr(args, "cot_path", None) or str(_DEFAULT_COT_PATH)
    vectorizer_path = getattr(args, "vectorizer_path", None)

    engine = FableReasoningEngine(
        cot_path=cot_path,
        vectorizer_path=vectorizer_path,
        template_style=style,
    )

    if getattr(args, "load", None):
        engine.load(args.load)
    elif getattr(args, "skip_init", False):
        pass
    else:
        engine.initialize()

    return engine


def _cli_extract(args: argparse.Namespace) -> int:
    """CLI handler for the extract subcommand."""
    engine = _build_engine(args)
    limit = getattr(args, "limit", 100)
    stats = engine.extract_patterns(limit=limit)
    print(json.dumps(stats, indent=2))
    return 0


def _cli_analyze(args: argparse.Namespace) -> int:
    """CLI handler for the analyze subcommand."""
    if not args.trajectory and not args.trajectory_file:
        logger.error("Provide --trajectory or --trajectory-file")
        return 1

    context = args.trajectory or ""
    if args.trajectory_file:
        try:
            with open(args.trajectory_file, "r", encoding="utf-8") as f:
                context = f.read()
        except OSError:
            logger.exception("Failed to read trajectory file")
            return 1

    engine = _build_engine(args)
    result = engine.analyze_trajectory(context)
    print(json.dumps(result, indent=2, default=str))
    return 0


def _cli_prompt(args: argparse.Namespace) -> int:
    """CLI handler for the prompt subcommand."""
    engine = _build_engine(args)
    task_type = getattr(args, "task_type", "debug")
    complexity = getattr(args, "complexity", "L2")
    query = getattr(args, "query", "")
    prompt = engine.generate_prompt(
        task_type=task_type, complexity=complexity, query=query
    )
    print(prompt)
    return 0


def _cli_inject(args: argparse.Namespace) -> int:
    """CLI handler for the inject subcommand."""
    engine = _build_engine(args)
    prompt = getattr(args, "prompt", "")
    query = getattr(args, "query", "")
    style = getattr(args, "style", None)

    if args.prompt_file:
        try:
            with open(args.prompt_file, "r", encoding="utf-8") as f:
                prompt = f.read()
        except OSError:
            logger.exception("Failed to read prompt file")
            return 1

    result = engine.inject_reasoning(base_prompt=prompt, query=query, style=style)
    print(result)
    return 0


def _cli_similar(args: argparse.Namespace) -> int:
    """CLI handler for the similar subcommand."""
    engine = _build_engine(args)
    query = getattr(args, "query", "")
    k = getattr(args, "k", 5)

    if not query:
        logger.error("Provide --query text")
        return 1

    results = engine.find_similar_patterns(query_text=query, k=k)
    print(json.dumps(results, indent=2))
    return 0


def _cli_clusters(args: argparse.Namespace) -> int:
    """CLI handler for the clusters subcommand."""
    engine = _build_engine(args)
    n_clusters = getattr(args, "n_clusters", 10)
    summary = engine.get_cluster_summary(n_clusters=n_clusters)
    print(json.dumps(summary, indent=2, default=str))
    return 0


def _cli_train(args: argparse.Namespace) -> int:
    """CLI handler for the train subcommand."""
    engine = _build_engine(args)
    output = getattr(args, "output", "training_data.jsonl")
    fmt = getattr(args, "format", "dpo")
    limit = getattr(args, "limit", 100)
    count = engine.get_training_data(
        output_path=output, format=fmt, limit=limit
    )
    print(json.dumps({"examples_written": count, "output": output}))
    return 0


def _cli_status(args: argparse.Namespace) -> int:
    """CLI handler for the status subcommand."""
    engine = _build_engine(args)
    status = engine.status()
    print(json.dumps(status, indent=2, default=str))
    return 0
