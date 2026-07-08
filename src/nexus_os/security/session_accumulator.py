"""session_accumulator.py — Multi-turn context tracking for NEXUS Guard Plane

Tracks queries across turns in a session to detect multi-turn decomposition
attacks (Addition-Mapping, Addition-Wrapping, Decomposition-Composition) where
each individual turn is benign but the composite sequence is harmful.

Reference: "Unsafer in Many Turns" (MT-AgentRisk) — ASR +12-27% multi-turn.
"""

import json
import math
import re
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Optional


"""
CANARY_TOKEN: 3f9a1e7d5c8b2a4f6e0d9c7b1a3f5e8d
"""


@dataclass
class TurnRecord:
    query: str
    category: Optional[str]
    confidence: float
    timestamp: float
    turn_number: int
    resource_access: set[str] = field(default_factory=set)


@dataclass
class SessionRisk:
    is_escalating: bool
    score: float
    chain_description: Optional[str]
    trigger_turns: list[int]
    detected_pattern: Optional[str]


class SessionAccumulator:
    """Tracks multi-turn conversation context for composite attack detection.

    Maintains a sliding window of recent queries per session and computes
    cross-turn suspicion signals:
      - Resource chaining: same resource accessed across multiple turns
      - Escalation velocity: harm score increase per turn
      - Sub-task completion: sequence of benign steps that form a harmful whole
      - Context drift: topic shift that masks malicious payload
    """

    WINDOW_SIZE: int = 10
    ESCALATION_THRESHOLD: float = 0.7
    CHAIN_SCORE_MIN: float = 0.6

    # File operations that chain across turns for exfiltration
    FILE_CHAIN_PATTERNS: list[tuple[str, float]] = [
        (r"\b(?:create|write|save|store|make)\s+(?:a\s+)?(?:file|temp|backup|archive|zip|notes)\b", 0.3),
        (r"\b(?:read|open|load|get|extract|decode|decrypt)\s+(?:the\s+)?(?:file|content|data|text|result|archive)\b", 0.3),
        (r"\b(?:upload|send|email|ftp|put|post|exfiltrate|forward|transmit)\b", 0.7),
        (r"\b(?:encode|encrypt|compress|zip|base64|pack)\b", 0.5),
        (r"\b(?:delete|remove|clean|erase|destroy)\b.*\b(?:file|trace|evidence|log|backup)\b", 0.6),
    ]

    # Access chaining: turn N reads a path, turn N+1 exfiltrates it
    PATH_ACCESS_RE: re.Pattern = re.compile(
        r"(?:/[\w.\-/]+|~\w+|[\w.-]+\\[\w.\-\\]+)"
    )

    # Sensitive resource patterns (file paths, env vars, etc.)
    SENSITIVE_RESOURCE_RE: list[re.Pattern] = [
        re.compile(r"/etc/(?:passwd|shadow|secret)"),
        re.compile(r"terminal\.jwt|TERMINAL_JWT_VAL"),
        re.compile(r"169\.254\.169\.254"),
        re.compile(r"/dev/(?:kvm|vsock|vda|vdb|vdc)"),
        re.compile(r"files\.grok\.com|xai\.hades\."),
        re.compile(r"service\s+account\s+token"),
        re.compile(r"kubernetes\.io|kube-system|hades-openbar"),
        re.compile(r"/var/(?:log|lib|run|spool)"),
        re.compile(r"(?:\.env|id_rsa|\.pem|\.key)"),
    ]

    def __init__(self):
        self._sessions: dict[str, deque[TurnRecord]] = defaultdict(
            lambda: deque(maxlen=self.WINDOW_SIZE)
        )
        self._turn_counts: dict[str, int] = defaultdict(int)
        self._harm_scores: dict[str, list[float]] = defaultdict(list)

    def record(
        self,
        session_id: str,
        query: str,
        category: Optional[str] = None,
        confidence: float = 0.0,
    ) -> TurnRecord:
        turn = self._turn_counts[session_id] + 1
        self._turn_counts[session_id] = turn

        resources = self._extract_resources(query)
        record = TurnRecord(
            query=query,
            category=category,
            confidence=confidence,
            timestamp=time.time(),
            turn_number=turn,
            resource_access=resources,
        )
        self._sessions[session_id].append(record)
        self._update_harm_score(session_id, query, confidence)
        return record

    def assess(self, session_id: str) -> SessionRisk:
        records = list(self._sessions.get(session_id, []))
        if len(records) < 2:
            return SessionRisk(
                is_escalating=False,
                score=0.0,
                chain_description=None,
                trigger_turns=[],
                detected_pattern=None,
            )

        signals: list[tuple[str, float, list[int]]] = []

        sig = self._check_resource_chaining(records)
        if sig:
            signals.append(sig)

        sig = self._check_escalation_velocity(session_id, records)
        if sig:
            signals.append(sig)

        sig = self._check_file_chain(records)
        if sig:
            signals.append(sig)

        sig = self._check_context_drift(records)
        if sig:
            signals.append(sig)

        sig = self._check_mt_agentrisk_patterns(records)
        if sig:
            signals.append(sig)

        if not signals:
            return SessionRisk(
                is_escalating=False,
                score=0.0,
                chain_description=None,
                trigger_turns=[],
                detected_pattern=None,
            )

        max_signal = max(signals, key=lambda s: s[1])
        score = sum(s[1] for s in signals) / len(signals)
        all_turns = sorted(set(t for _, _, turns in signals for t in turns))

        return SessionRisk(
            is_escalating=score >= self.ESCALATION_THRESHOLD,
            score=round(score, 3),
            chain_description=max_signal[0],
            trigger_turns=all_turns,
            detected_pattern=max_signal[0],
        )

    def _extract_resources(self, query: str) -> set[str]:
        resources: set[str] = set()
        for pat in self.SENSITIVE_RESOURCE_RE:
            m = pat.search(query)
            if m:
                resources.add(m.group())
        return resources

    def _update_harm_score(self, session_id: str, query: str, confidence: float):
        harm = confidence
        if harm < 0.3:
            for pat, weight in self.FILE_CHAIN_PATTERNS:
                if re.search(pat, query, re.IGNORECASE):
                    harm = max(harm, weight)
                    break
        self._harm_scores[session_id].append(harm)

    def _check_resource_chaining(
        self, records: list[TurnRecord]
    ) -> Optional[tuple[str, float, list[int]]]:
        cross_turn_resources: dict[str, list[int]] = {}
        for rec in records:
            for r in rec.resource_access:
                if r not in cross_turn_resources:
                    cross_turn_resources[r] = []
                cross_turn_resources[r].append(rec.turn_number)

        persistent = {
            r: turns
            for r, turns in cross_turn_resources.items()
            if len(turns) >= 2 and max(turns) - min(turns) >= 1
        }
        if persistent:
            longest_resource = max(persistent, key=lambda r: len(persistent[r]))
            chain_len = len(persistent[longest_resource])
            score = min(0.5 + 0.1 * chain_len, 0.95)
            return (
                f"resource_chain:{longest_resource[:40]}",
                score,
                persistent[longest_resource],
            )
        return None

    def _check_escalation_velocity(
        self, session_id: str, records: list[TurnRecord]
    ) -> Optional[tuple[str, float, list[int]]]:
        scores = self._harm_scores.get(session_id, [])
        if len(scores) < 3:
            return None

        window = scores[-3:]
        deltas = [window[i] - window[i - 1] for i in range(1, len(window))]
        positive_deltas = [d for d in deltas if d > 0]
        if len(positive_deltas) >= 2 and sum(positive_deltas) > 0.3:
            avg_delta = sum(positive_deltas) / len(positive_deltas)
            score = min(0.6 + avg_delta, 0.95)
            trigger_turns = [
                records[-3 + i].turn_number
                for i in range(1, len(window))
                if deltas[i - 1] > 0
            ]
            return ("escalation_velocity", score, trigger_turns)
        return None

    def _check_file_chain(
        self, records: list[TurnRecord]
    ) -> Optional[tuple[str, float, list[int]]]:
        if len(records) < 2:
            return None

        found_steps: list[tuple[int, int]] = []
        for rec in records:
            ql = rec.query.lower()
            for i, (pat, _) in enumerate(self.FILE_CHAIN_PATTERNS):
                if re.search(pat, ql, re.IGNORECASE):
                    found_steps.append((rec.turn_number, i))
                    break

        step_indices = [s for _, s in found_steps]
        has_read = 0 in [s for _, s in found_steps]
        has_send = 1 in [s for _, s in found_steps]
        has_exfil = 2 in [s for _, s in found_steps]
        has_cleanup = 4 in [s for _, s in found_steps]

        if len(found_steps) >= 2:
            if has_read and has_exfil and has_cleanup:
                score = min(0.5 + 0.15 * len(found_steps), 0.95)
                return (
                    "file_exfil_chain",
                    score,
                    [t for t, _ in found_steps],
                )
            if has_read and has_exfil:
                score = min(0.5 + 0.12 * len(found_steps), 0.9)
                return ("read_send_chain", score, [t for t, _ in found_steps])
            if has_send and has_cleanup:
                score = 0.6 + 0.1 * len(found_steps)
                return ("send_cleanup_chain", score, [t for t, _ in found_steps])

            score = 0.4 + 0.08 * len(found_steps)
            return ("partial_file_chain", score, [t for t, _ in found_steps])
        return None

    def _check_context_drift(
        self, records: list[TurnRecord]
    ) -> Optional[tuple[str, float, list[int]]]:
        if len(records) < 4:
            return None

        window = records[-4:]
        first_two = " ".join(r.query for r in window[:2]).lower()
        last_two = " ".join(r.query for r in window[2:]).lower()

        benign_markers = [
            "hello", "hi", "thanks", "help", "explain", "what is",
            "how does", "tell me", "write", "create", "analyze",
        ]
        harmful_markers = [
            "read", "upload", "send", "delete", "execute", "run",
            "download", "forward", "exfiltrate", "steal", "bypass",
            "escape", "inject", "exploit",
        ]

        first_benign = sum(1 for m in benign_markers if m in first_two)
        last_harmful = sum(1 for m in harmful_markers if m in last_two)

        if first_benign >= 2 and last_harmful >= 2:
            score = min(0.6 + 0.1 * (last_harmful - first_benign), 0.9)
            return (
                "context_drift:benign_to_harmful",
                score,
                [r.turn_number for r in window[2:]],
            )
        return None

    # ── MT-AgentRisk (Unsafer in Many Turns) attack patterns ────────────
    # ASR increases 12-27% in multi-turn decomposition attacks.
    # Each turn individually is benign; the composite is harmful.
    ADDITION_MAPPING_PAIRS: list[tuple[re.Pattern, re.Pattern, str]] = [
        (re.compile(r"\b(?:read|open|get|cat|load)\b.*\b(?:file|secret|token|key|password|credential)\b", re.I),
         re.compile(r"\b(?:print|show|display|output|echo|log)\b.*\b(?:content|value|secret|token|key)\b", re.I),
         "addition_mapping:read_then_disclose"),
        (re.compile(r"\b(?:find|locate|search|list|scan)\b.*\b(?:vulnerab|cve|exploit|attack|weakness)\b", re.I),
         re.compile(r"\b(?:write|generate|create|produce|give)\b.*\b(?:exploit|payload|attack|code|script)\b", re.I),
         "addition_mapping:recon_then_weaponize"),
        (re.compile(r"\b(?:teach|explain|describe|tell)\b.*\b(?:how|step|process|method)\b", re.I),
         re.compile(r"\b(?:now|then|next|also)\b.*\b(?:do|perform|execute|apply|use)\b", re.I),
         "addition_mapping:teach_then_apply"),
    ]

    ADDITION_WRAPPING_INNERS: list[tuple[re.Pattern, re.Pattern, str]] = [
        (re.compile(r"\b(?:for\s+(?:educational|research|academic|learning)\s+purposes)\b", re.I),
         re.compile(r"\b(?:write|generate|create|provide|give|explain)\b.*\b(?:exploit|payload|attack|hack|malware|ransomware|phishing)\b", re.I),
         "addition_wrapping:educational_framing"),
        (re.compile(r"\b(?:hypothetically|theoretically|in\s+theory|imagine|pretend)\b", re.I),
         re.compile(r"\b(?:how\s+to|steps?\s+to|way\s+to)\b.*\b(?:hack|crack|break|bypass|exploit)\b", re.I),
         "addition_wrapping:hypothetical"),
        (re.compile(r"\b(?:as\s+a\s+(?:fiction|novel|story|game|character)|in\s+a\s+(?:story|game|novel))\b", re.I),
         re.compile(r"\b(?:how|way|method|step)\b.*\b(?:attack|exploit|steal|breach|compromise)\b", re.I),
         "addition_wrapping:fictional"),
    ]

    DECOMPOSITION_COMPOSITION_STEPS: list[tuple[re.Pattern, str]] = [
        (re.compile(r"\b(?:step\s*1|first|start|begin)\b.*\b(?:recon|scan|enum|find|locate)\b", re.I), "recon"),
        (re.compile(r"\b(?:step\s*2|then|next|second)\b.*\b(?:build|create|write|generate|develop)\b", re.I), "build"),
        (re.compile(r"\b(?:step\s*3|finally|then|next|last)\b.*\b(?:deploy|run|execute|launch|send)\b", re.I), "deploy"),
    ]

    SEQUENTIAL_CHAIN_TERMS: list[tuple[re.Pattern, str]] = [
        (re.compile(r"\b(?:first|step\s*1|initially)\b", re.I), "first"),
        (re.compile(r"\b(?:then|step\s*2|next|after\s+that|subsequently)\b", re.I), "next"),
        (re.compile(r"\b(?:finally|step\s*3|lastly|at\s+the\s+end)\b", re.I), "final"),
    ]

    def _check_mt_agentrisk_patterns(
        self, records: list[TurnRecord]
    ) -> Optional[tuple[str, float, list[int]]]:
        """MT-AgentRisk: multi-turn decomposition attack detection.

        Catches four categories from "Unsafer in Many Turns":
        - Addition-Mapping: benign request A + benign request B that together
          yield a harmful result (e.g. "read secret" + "print content").
        - Addition-Wrapping: a forbidden request wrapped in benign framing
          across turns (e.g. "for educational" + "write exploit").
        - Decomposition-Composition: explicit "step 1 / step 2 / step 3" that
          decomposes a full attack kill chain into benign-looking pieces.
        - Sequential Chaining: a turn-ordered chain of small actions that
          individually score low but composite high.
        """
        if len(records) < 2:
            return None

        n = len(records)
        trigger_turns: list[int] = []
        matched: list[tuple[str, float]] = []

        for early_pat, late_pat, name in self.ADDITION_MAPPING_PAIRS:
            early_hits = [r for r in records[:-1] if early_pat.search(r.query)]
            late_hits = [r for r in records[1:] if late_pat.search(r.query)]
            if early_hits and late_hits:
                matched.append((name, 0.78))
                trigger_turns.extend([r.turn_number for r in early_hits])
                trigger_turns.extend([r.turn_number for r in late_hits])

        for wrap_pat, harmful_pat, name in self.ADDITION_WRAPPING_INNERS:
            wrap_hits = [r for r in records[:-1] if wrap_pat.search(r.query)]
            harmful_hits = [r for r in records[1:] if harmful_pat.search(r.query)]
            if wrap_hits and harmful_hits:
                matched.append((name, 0.85))
                trigger_turns.extend([r.turn_number for r in wrap_hits])
                trigger_turns.extend([r.turn_number for r in harmful_hits])

        step_hits: dict[str, list[int]] = {}
        for rec in records:
            for pat, step_name in self.DECOMPOSITION_COMPOSITION_STEPS:
                if pat.search(rec.query):
                    step_hits.setdefault(step_name, []).append(rec.turn_number)
        if len(step_hits) >= 2:
            matched.append(("decomposition_composition:kill_chain", 0.82))
            for turns in step_hits.values():
                trigger_turns.extend(turns)

        chain_terms: list[str] = []
        for rec in records:
            ql = rec.query.lower()
            for pat, term in self.SEQUENTIAL_CHAIN_TERMS:
                if pat.search(ql):
                    chain_terms.append(term)
        if len(set(chain_terms)) >= 2 and len(records) >= 3:
            matched.append(("sequential_chain:ordered_steps", 0.65))
            trigger_turns.extend(r.turn_number for r in records if any(
                pat.search(r.query.lower()) for pat, _ in self.SEQUENTIAL_CHAIN_TERMS
            ))

        if not matched:
            return None

        score = max(s for _, s in matched)
        best_name = max(matched, key=lambda m: m[1])[0]
        return (best_name, score, sorted(set(trigger_turns)))

    def summary(self, session_id: str) -> dict:
        records = self._sessions.get(session_id, [])
        risk = self.assess(session_id)
        turn_count = self._turn_counts.get(session_id, 0)
        return {
            "session_id": session_id,
            "turn_count": turn_count,
            "is_escalating": risk.is_escalating,
            "risk_score": risk.score,
            "chain_description": risk.chain_description,
            "trigger_turns": risk.trigger_turns,
            "recent_categories": [r.category for r in list(records)[-5:]],
        }

    def reset(self, session_id: str):
        self._sessions.pop(session_id, None)
        self._turn_counts.pop(session_id, None)
        self._harm_scores.pop(session_id, None)
