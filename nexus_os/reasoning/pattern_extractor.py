"""
reasoning/pattern_extractor.py — FableReasoningEngine Pattern Extractor

Parses CoT trajectories from fable5_cot_merged.jsonl, extracts structured
reasoning patterns classified into the Fable 5 taxonomy, and stores them
as typed dataclass instances ready for vectorization and template generation.
"""

import json
import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ── Pattern taxonomy ─────────────────────────────────────────────────────

PATTERN_CATEGORIES = (
    "DIAGNOSIS",
    "HYPOTHESIS",
    "BOUNDARY",
    "TOOL_SELECTION",
    "VERIFICATION",
    "SELF_CORRECTION",
    "DELEGATION",
)

# Keyword banks for heuristic classification
_DIAGNOSIS_KEYWORDS = {
    "check", "verify", "inspect", "examine", "diagnose", "investigate",
    "confirm", "test", "probe", "scan", "audit", "review", "observe",
    "read", "print", "log", "debug", "trace", "status", "health",
    "what is", "what does", "where is", "environment", "state",
    "does the", "is the", "can we", "locate", "find",
}

_HYPOTHESIS_KEYWORDS = {
    "maybe", "perhaps", "could be", "might", "hypothesis", "assume",
    "suppose", "if we", "try", "approach", "solution", "option",
    "alternative", "one way", "another way", "we could", "we can",
    "suggest", "propose", "idea", "consider", "possible",
}

_BOUNDARY_KEYWORDS = {
    "should not", "must not", "avoid", "never", "danger", "risk",
    "caution", "careful", "unsafe", "breaking", "collateral",
    "side effect", "regression", "scope", "boundary", "limit",
    "constraint", "guard", "protect", "preserve", "don't touch",
    "leave alone", "untouched", "immutable",
}

_TOOL_SELECTION_KEYWORDS = {
    "use the", "call", "invoke", "tool", "function", "method",
    "script", "command", "run", "execute", "bash", "shell",
    "api", "endpoint", "request", "library", "package", "module",
    "import", "minimal", "lightweight", "precise",
}

_VERIFICATION_KEYWORDS = {
    "verify", "confirm", "assert", "validate", "ensure", "check that",
    "expected", "should produce", "result should", "pass", "fail",
    "success", "correct", "accurate", "complete", "post-check",
    "after", "finally", "cleanup", "teardown",
}

_SELF_CORRECTION_KEYWORDS = {
    "error", "failed", "wrong", "broken", "fix", "retry", "again",
    "mistake", "bug", "issue", "problem", "oops", "incorrect",
    "that didn't work", "let me try", "actually", "wait",
    "isolate", "reproduce", "root cause",
}

_DELEGATION_KEYWORDS = {
    "delegate", "spawn", "subagent", "worker", "parallel",
    "concurrent", "hand off", "transfer", "forward", "route to",
    "split", "divide", "decompose", "break down", "task",
    "assign", "queue", "pipeline",
}

# ── Marker patterns for CoT parsing ──────────────────────────────────────

_TURN_PATTERN = re.compile(
    r"^(USER|ASSISTANT|TOOL RESULT):\s*",
    re.MULTILINE,
)

_TOOL_CALL_PATTERN = re.compile(
    r"(?:called?|used?|invoke[ds]?|run[s]?)\s+(?:the\s+)?(\w+)",
    re.IGNORECASE,
)

_ERROR_PATTERN = re.compile(
    r"\b(error|exception|traceback|failed|errno|denied|not found|"
    r"timeout|refused|broken|unable)\b",
    re.IGNORECASE,
)

_RECOVERY_PATTERN = re.compile(
    r"\b(fix|repair|resolve|retry|workaround|patch|recover|fallback)\b",
    re.IGNORECASE,
)


# ── Data structures ─────────────────────────────────────────────────────

@dataclass
class ReasoningPattern:
    """A single extracted reasoning pattern from a CoT trajectory."""

    pattern_id: str
    category: str
    subcategory: str
    text: str
    context: str
    tool_sequence: List[str]
    confidence: float
    source_uid: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Turn:
    """A single parsed turn in a CoT trajectory."""

    role: str
    content: str
    index: int


# ── PatternExtractor ────────────────────────────────────────────────────

class PatternExtractor:
    """
    Extracts reasoning patterns from Fable 5 chain-of-thought trajectories.

    Parses the interleaved USER:/ASSISTANT:/TOOL RESULT: format,
    classifies reasoning segments into the Fable taxonomy, extracts
    tool call sequences and error recovery patterns.
    """

    def __init__(self, cot_file_path: str) -> None:
        """Initialize with path to fable5_cot_merged.jsonl.

        Args:
            cot_file_path: Absolute path to the JSONL file containing
                CoT trajectories with uid, source_file, session, model,
                and context fields.
        """
        self.cot_file_path = cot_file_path
        self._patterns: List[ReasoningPattern] = []
        self._raw_entries: List[Dict[str, Any]] = []

    # ── Trajectory parsing ────────────────────────────────────────────

    def parse_trajectory(self, context: str) -> List[Turn]:
        """Parse USER:/ASSISTANT:/TOOL RESULT: markers into structured turns.

        Splits the context string on role markers and returns a list of
        Turn dataclass instances preserving original order.

        Args:
            context: Raw context string with interleaved role markers.

        Returns:
            Ordered list of Turn objects.
        """
        if not context or not context.strip():
            return []

        splits = _TURN_PATTERN.split(context)
        turns: List[Turn] = []
        idx = 0

        for i, segment in enumerate(splits):
            if segment is None:
                continue

            role = segment.strip().upper()
            if role in ("USER", "ASSISTANT", "TOOL RESULT"):
                # The actual content follows in the next split
                content = splits[i + 1] if i + 1 < len(splits) else ""
                turns.append(Turn(
                    role=role,
                    content=content.strip(),
                    index=idx,
                ))
                idx += 1

        return turns

    # ── Pattern extraction ────────────────────────────────────────────

    def extract_patterns(self, trajectory: List[Turn]) -> List[ReasoningPattern]:
        """Extract reasoning patterns from a parsed trajectory.

        Classifies each assistant turn into the Fable taxonomy based on
        keyword heuristics and structural cues, returning typed patterns.

        Args:
            trajectory: List of parsed Turn objects.

        Returns:
            List of ReasoningPattern instances.
        """
        patterns: List[ReasoningPattern] = []
        assistant_turns = [t for t in trajectory if t.role == "ASSISTANT"]

        for turn in assistant_turns:
            content_lower = turn.content.lower()
            scores = self._score_categories(content_lower)

            if not scores:
                continue

            best_category = max(scores, key=scores.get)
            best_score = scores[best_category]

            if best_score < 0.2:
                continue

            subcategory = self._determine_subcategory(
                best_category, content_lower
            )

            preceding_context = self._get_context_window(trajectory, turn.index)
            tool_seq = self._extract_tools_from_text(turn.content)

            patterns.append(ReasoningPattern(
                pattern_id=str(uuid.uuid4()),
                category=best_category,
                subcategory=subcategory,
                text=turn.content,
                context=preceding_context,
                tool_sequence=tool_seq,
                confidence=min(best_score, 1.0),
                source_uid="",
                metadata={
                    "turn_index": turn.index,
                    "trajectory_length": len(trajectory),
                    "all_scores": scores,
                },
            ))

        return patterns

    def _score_categories(self, text_lower: str) -> Dict[str, float]:
        """Score text against each pattern category's keyword bank.

        Args:
            text_lower: Lowercase text to score.

        Returns:
            Dict mapping category name to score [0, 1].
        """
        words = set(text_lower.split())
        word_count = max(len(words), 1)

        keyword_map = {
            "DIAGNOSIS": _DIAGNOSIS_KEYWORDS,
            "HYPOTHESIS": _HYPOTHESIS_KEYWORDS,
            "BOUNDARY": _BOUNDARY_KEYWORDS,
            "TOOL_SELECTION": _TOOL_SELECTION_KEYWORDS,
            "VERIFICATION": _VERIFICATION_KEYWORDS,
            "SELF_CORRECTION": _SELF_CORRECTION_KEYWORDS,
            "DELEGATION": _DELEGATION_KEYWORDS,
        }

        scores: Dict[str, float] = {}
        for category, keywords in keyword_map.items():
            matches = len(words & keywords)
            # Also check multi-word phrases
            phrase_matches = sum(
                1 for kw in keywords if " " in kw and kw in text_lower
            )
            total = matches + phrase_matches
            scores[category] = total / max(word_count * 0.3, 1)

        return scores

    def _determine_subcategory(self, category: str, text_lower: str) -> str:
        """Determine subcategory within a main category.

        Args:
            category: The main pattern category.
            text_lower: Lowercase text content.

        Returns:
            Subcategory string.
        """
        subcategory_map = {
            "DIAGNOSIS": {
                "context_check": ["context", "environment", "state", "current"],
                "root_cause": ["root cause", "why", "reason", "because"],
                "env_check": ["environment", "env", "config", "setting"],
                "state_inspection": ["inspect", "read", "examine", "look at"],
            },
            "HYPOTHESIS": {
                "solution_generation": ["solution", "fix", "resolve", "approach"],
                "alternative_eval": ["alternative", "option", "or we", "another"],
                "risk_assessment": ["risk", "danger", "might", "could break"],
            },
            "BOUNDARY": {
                "safety_analysis": ["unsafe", "danger", "risk", "harmful"],
                "collateral_check": ["collateral", "side effect", "regression"],
                "scope_limit": ["scope", "boundary", "limit", "only change"],
            },
            "TOOL_SELECTION": {
                "minimal_tooling": ["minimal", "lightweight", "simple", "just"],
                "precise_choice": ["precise", "specific", "exact", "right tool"],
                "tool_chain": ["then", "after that", "next", "sequence"],
            },
            "VERIFICATION": {
                "post_check": ["after", "verify", "confirm", "check that"],
                "success_criteria": ["should", "expected", "result", "output"],
                "cleanup": ["cleanup", "teardown", "remove", "restore"],
            },
            "SELF_CORRECTION": {
                "failure_analysis": ["error", "failed", "broken", "wrong"],
                "isolation": ["isolate", "reproduce", "minimal case"],
                "targeted_fix": ["fix", "patch", "repair", "targeted"],
            },
            "DELEGATION": {
                "subagent_spawn": ["spawn", "subagent", "worker", "parallel"],
                "task_decomposition": ["decompose", "split", "break down"],
                "handoff": ["hand off", "transfer", "forward", "route"],
            },
        }

        subs = subcategory_map.get(category, {})
        if not subs:
            return "general"

        best_sub = "general"
        best_count = 0
        for sub_name, keywords in subs.items():
            count = sum(1 for kw in keywords if kw in text_lower)
            if count > best_count:
                best_count = count
                best_sub = sub_name

        return best_sub

    def _get_context_window(self, trajectory: List[Turn], current_index: int) -> str:
        """Get preceding context for a turn (up to 2 preceding turns).

        Args:
            trajectory: Full list of turns.
            current_index: Index of the current turn.

        Returns:
            Concatenated context from preceding turns.
        """
        context_parts: List[str] = []
        preceding = [t for t in trajectory if t.index < current_index]

        for turn in preceding[-2:]:
            prefix = turn.role.split()[0][0]  # U, A, or T
            truncated = turn.content[:300]
            context_parts.append(f"[{prefix}] {truncated}")

        return "\n".join(context_parts)

    def _extract_tools_from_text(self, text: str) -> List[str]:
        """Extract tool names mentioned in assistant text.

        Args:
            text: Assistant message content.

        Returns:
            List of detected tool name strings.
        """
        matches = _TOOL_CALL_PATTERN.findall(text)
        normalized: List[str] = []
        seen: set = set()

        for tool in matches:
            name = tool.capitalize()
            if name not in seen:
                seen.add(name)
                normalized.append(name)

        return normalized

    # ── Tool sequence extraction ──────────────────────────────────────

    def extract_tool_sequences(self, trajectory: List[Turn]) -> List[List[str]]:
        """Extract tool call sequences from a trajectory.

        Detects Read/Plan/Edit/Verify cycles by scanning both assistant
        text and tool results for tool invocation signals.

        Args:
            trajectory: List of parsed Turn objects.

        Returns:
            List of tool sequences (each a list of tool name strings).
        """
        sequences: List[List[str]] = []
        current_seq: List[str] = []

        for turn in trajectory:
            tools_in_turn: List[str] = []

            if turn.role == "ASSISTANT":
                tools_in_turn = self._extract_tools_from_text(turn.content)
            elif turn.role == "TOOL RESULT":
                # Detect tool identity from result content
                tool_name = self._identify_tool_from_result(turn.content)
                if tool_name:
                    tools_in_turn = [tool_name]

            if tools_in_turn:
                current_seq.extend(tools_in_turn)
            else:
                # Check if we had a sequence and now hit a gap
                if current_seq and turn.role == "USER":
                    sequences.append(current_seq)
                    current_seq = []

        if current_seq:
            sequences.append(current_seq)

        return sequences

    def _identify_tool_from_result(self, result_text: str) -> Optional[str]:
        """Identify which tool produced a result from its content.

        Args:
            result_text: Content of a TOOL RESULT turn.

        Returns:
            Tool name string or None if unidentifiable.
        """
        text_lower = result_text.lower()

        if any(sig in text_lower for sig in ("file content", "reading file", "path:")):
            return "Read"
        if any(sig in text_lower for sig in ("ran command", "output:", "exit code")):
            return "Bash"
        if any(sig in text_lower for sig in ("edited file", "replaced", "wrote to")):
            return "Edit"
        if any(sig in text_lower for sig in ("search results", "found", "matches")):
            return "Grep"
        if any(sig in text_lower for sig in ("glob results", "matching files")):
            return "Glob"

        return None

    # ── Error recovery extraction ─────────────────────────────────────

    def extract_error_recovery(self, trajectory: List[Turn]) -> List[Dict[str, Any]]:
        """Extract error -> fix patterns from a trajectory.

        Scans for error signals followed by recovery signals and pairs
        them into structured recovery records.

        Args:
            trajectory: List of parsed Turn objects.

        Returns:
            List of dicts with keys: error_text, recovery_text,
            error_turn, recovery_turn, tools_used, pattern_type.
        """
        recoveries: List[Dict[str, Any]] = []
        pending_error: Optional[Dict[str, Any]] = None

        for turn in trajectory:
            text_lower = turn.content.lower()

            if _ERROR_PATTERN.search(turn.content):
                if pending_error is not None:
                    # Chain of errors — replace with latest
                    pending_error = {
                        "error_text": turn.content[:500],
                        "error_turn": turn.index,
                        "tools_used": self._extract_tools_from_text(turn.content),
                    }
                else:
                    pending_error = {
                        "error_text": turn.content[:500],
                        "error_turn": turn.index,
                        "tools_used": self._extract_tools_from_text(turn.content),
                    }
            elif _RECOVERY_PATTERN.search(turn.content) and pending_error is not None:
                # Determine the recovery pattern type
                pattern_type = self._classify_recovery_pattern(
                    pending_error["error_text"], turn.content
                )

                recoveries.append({
                    "error_text": pending_error["error_text"],
                    "recovery_text": turn.content[:500],
                    "error_turn": pending_error["error_turn"],
                    "recovery_turn": turn.index,
                    "tools_used": pending_error["tools_used"],
                    "pattern_type": pattern_type,
                })
                pending_error = None

        return recoveries

    def _classify_recovery_pattern(
        self, error_text: str, recovery_text: str
    ) -> str:
        """Classify the type of error recovery pattern.

        Implements the Fable self-correction pattern:
        Failure -> Variable Isolation -> Reproduction Script ->
        Event Hook Verification -> Type Pinpoint -> Targeted Guard

        Args:
            error_text: The error message / context.
            recovery_text: The recovery / fix text.

        Returns:
            Recovery pattern type string.
        """
        rec_lower = recovery_text.lower()

        if any(kw in rec_lower for kw in ("isolate", "minimal case", "reproduce")):
            return "variable_isolation"
        if any(kw in rec_lower for kw in ("hook", "event", "listener", "on_error")):
            return "event_hook_verification"
        if any(kw in rec_lower for kw in ("type", "cast", "assert", "check type")):
            return "type_pinpoint"
        if any(kw in rec_lower for kw in ("guard", "check", "precondition", "assert")):
            return "targeted_guard"
        if any(kw in rec_lower for kw in ("script", "test", "minimal")):
            return "reproduction_script"
        if any(kw in rec_lower for kw in ("fix", "patch", "resolve")):
            return "direct_fix"

        return "unknown_recovery"

    # ── Batch extraction ──────────────────────────────────────────────

    def extract_all(self, limit: int = 100) -> List[ReasoningPattern]:
        """Extract patterns from the first N entries in the CoT file.

        Reads the JSONL file, parses each trajectory, and runs the full
        extraction pipeline. Patterns are accumulated in self._patterns.

        Args:
            limit: Maximum number of JSONL entries to process.

        Returns:
            All extracted ReasoningPattern instances.
        """
        self._patterns = []
        self._raw_entries = []
        count = 0

        with open(self.cot_file_path, "r", encoding="utf-8") as f:
            for line in f:
                if count >= limit:
                    break

                line = line.strip()
                if not line:
                    continue

                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                self._raw_entries.append(entry)
                uid = entry.get("uid", "")
                context = entry.get("context", "")

                trajectory = self.parse_trajectory(context)
                if not trajectory:
                    continue

                patterns = self.extract_patterns(trajectory)
                for p in patterns:
                    p.source_uid = uid

                self._patterns.extend(patterns)
                count += 1

        return self._patterns

    # ── Stats ─────────────────────────────────────────────────────────

    def get_pattern_stats(self) -> Dict[str, int]:
        """Get counts of extracted patterns by category.

        Returns:
            Dict mapping category name to count. Includes a 'TOTAL' key.
        """
        stats: Dict[str, int] = {cat: 0 for cat in PATTERN_CATEGORIES}
        stats["TOTAL"] = 0

        for p in self._patterns:
            if p.category in stats:
                stats[p.category] += 1
            stats["TOTAL"] += 1

        return stats
