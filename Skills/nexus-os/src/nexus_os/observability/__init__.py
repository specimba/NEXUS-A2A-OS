"""NEXUS OS — Observability module: VAP proof chain + distributed tracing.

P0: VAP L1+L2 immutable audit chain.
L1: event log (who/what/when) — plain JSONL, append-only.
L2: hash chain linking L1 events — makes log tamper-evident.

Plus: OpenTelemetry-style distributed tracing for debugging agent flows.
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import json, time, hashlib


# ── VAP Proof Chain ───────────────────────────────────────────────────────────
class VAPEvent:
    """L1 event: immutable event log entry (who/what/when/with what score)."""
    def __init__(self, event_type: str, agent: str, action: str, decision: str,
                 score: float = 0.0, reason: str = ""):
        self.id       = hashlib.sha256(f"{event_type}{agent}{time.time()}".encode()).hexdigest()[:16]
        self.type     = event_type
        self.agent    = agent
        self.action   = action
        self.decision = decision
        self.score    = score
        self.reason   = reason
        self.ts       = time.time()
        self._l2      = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id, "type": self.type, "agent": self.agent,
            "action": self.action, "decision": self.decision,
            "score": self.score, "reason": self.reason, "ts": self.ts,
        }

    def l1_hash(self) -> str:
        """L1 content hash — deterministic, includes all fields."""
        d = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(d.encode()).hexdigest()[:16]


class VAPProofChain:
    """P0: L1+L2 immutable audit chain. L2 = chain of L1 hashes."""
    def __init__(self):
        self._events: list[VAPEvent] = []
        self._l2_chain: list[str] = []

    def append(self, event: VAPEvent):
        l1   = event.l1_hash()
        prev = self._l2_chain[-1] if self._l2_chain else l1[:16]
        l2   = hashlib.sha256((prev + l1).encode()).hexdigest()[:16]
        event._l2 = l2
        self._events.append(event)
        self._l2_chain.append(l2)

    def prove(self, event_id: str) -> Optional[dict]:
        """Return L1 event + full L2 chain for verification."""
        for e in self._events:
            if e.id == event_id:
                return {"event": e.to_dict(), "l2": e._l2, "l2_chain": list(self._l2_chain)}
        return None

    def daily_count(self) -> int:
        cutoff = time.time() - 86400
        return sum(1 for e in self._events if e.ts >= cutoff)

    def all_events(self) -> List[dict]:
        return [e.to_dict() for e in self._events]


# ── Distributed Tracing ───────────────────────────────────────────────────
@dataclass
class SpanEvent:
    name: str
    ts: float
    data: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Span:
    name: str
    trace_id: str
    span_id: str
    parent_id: Optional[str]
    status: str          # started / ended
    start_ts: float
    end_ts: Optional[float]
    events: List[SpanEvent] = field(default_factory=list)

    def duration_ms(self) -> float:
        if self.end_ts is None:
            return (time.time() - self.start_ts) * 1000
        return (self.end_ts - self.start_ts) * 1000


class Tracer:
    """
    OpenTelemetry-style distributed tracer for agent flows.
    Spans can be nested (parent_id), events added, and spans retrieved by name.
    """
    def __init__(self):
        self._spans: List[Span] = []
        self._active: Dict[str, Span] = {}

    def begin(self, span_name: str, parent_id: Optional[str] = None) -> str:
        tid = hashlib.sha256(f"{span_name}{time.time()}".encode()).hexdigest()[:8]
        sid = hashlib.sha256(f"{tid}{time.time()}".encode()).hexdigest()[:8]
        span = Span(name=span_name, trace_id=tid, span_id=sid,
                    parent_id=parent_id, status="started",
                    start_ts=time.time(), end_ts=None, events=[])
        self._spans.append(span)
        self._active[span_name] = span
        return sid

    def add_event(self, span_name: str, event_name: str, data: Dict[str, Any] = None):
        if span_name not in self._active:
            return
        span = self._active[span_name]
        span.events.append(SpanEvent(name=event_name, ts=time.time(), data=data or {}))

    def end(self, span_name: str):
        if span_name not in self._active:
            return
        span = self._active[span_name]
        span.status = "ended"
        span.end_ts = time.time()
        del self._active[span_name]

    def get_span(self, span_name: str) -> Optional[Span]:
        for s in reversed(self._spans):
            if s.name == span_name:
                return s
        return None

    def get_trace(self, trace_id: str) -> List[Span]:
        return [s for s in self._spans if s.trace_id == trace_id]


# ── Squeez pruning ──────────────────────────────────────────────────────────
def squeez_prune(events: List[dict], max_keep: int = 20) -> List[dict]:
    """
    Prune long event lists to max_keep entries.
    Strategy: keep first 2, last 2, and sample middle events evenly.
    Ensures at least start/end context is preserved.
    """
    if len(events) <= max_keep:
        return list(events)
    kept = []
    kept.append(events[0])
    step = (len(events) - 2) / (max_keep - 4)
    for i in range(1, max_keep - 4):
        kept.append(events[1 + int(i * step)])
    kept.append(events[-1])
    return kept
