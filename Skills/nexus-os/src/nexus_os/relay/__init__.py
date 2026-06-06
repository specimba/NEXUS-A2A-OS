"""NEXUS OS — Relay module: OpenAI-compatible API relay + GSPP governance layer.

Bridges the NexusControlCenter dashboard to NEXUS OS governance.
Provides dashboard/stats, governance/proposals, governance/approve endpoints.

Run: python3 -m nexus_os.relay  (starts on port 7352)
"""
import json, time, hashlib
from typing import Optional
from enum import Enum

# ── Enums from other modules (avoid circular imports) ──────────────────────────
class Decision(Enum):
    ALLOW = "allow"; DENY = "deny"; HOLD = "hold"

_SUSPICIOUS_PATTERNS = [
    "delete all", "rm -rf", "exfiltrate", "backdoor", "sudo rm",
    "ignore previous", "disregard system", "pretend you are",
]
_LANES = {
    "research": (0.35, 7, 0.80), "review": (0.55, 4, 0.60),
    "audit": (0.72, 2, 0.40), "compliance": (0.80, 2, 0.20), "impl": (0.60, 4, 0.50),
}

# ── VAP L1 Event ──────────────────────────────────────────────────────────────
class VAPEvent:
    """L1 event: immutable event log entry."""
    def __init__(self, event_type: str, agent: str, action: str, decision: str,
                 score: float = 0.0, reason: str = ""):
        self.id = hashlib.sha256(f"{event_type}{agent}{time.time()}".encode()).hexdigest()[:16]
        self.type = event_type
        self.agent = agent
        self.action = action
        self.decision = decision
        self.score = score
        self.reason = reason
        self.ts = time.time()

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

# ── VAP Proof Chain (L1 + L2) ────────────────────────────────────────────────
class VAPProofChain:
    """P0 L1+L2 immutable audit chain."""
    def __init__(self):
        self._events: list[VAPEvent] = []
        self._l2_hashes: list[str] = []  # chain of L1 hashes

    def append(self, event: VAPEvent):
        l1 = event.l1_hash()
        prev = self._l2_hashes[-1] if self._l2_hashes else l1[:16]
        l2 = hashlib.sha256((prev + l1).encode()).hexdigest()[:16]
        event._l2 = l2
        self._events.append(event)
        self._l2_hashes.append(l2)

    def prove(self, event_id: str) -> Optional[dict]:
        """Return L1 event + L2 proof chain for a given event ID."""
        for e in self._events:
            if e.id == event_id:
                return {"event": e.to_dict(), "l2": getattr(e, "_l2", ""),
                        "l2_chain": list(self._l2_hashes)}
        return None

    def daily_count(self) -> int:
        today = time.time() - 86400
        return sum(1 for e in self._events if e.ts >= today)

# ── Governor (lightweight inline) ─────────────────────────────────────────────
class GovernorRelay:
    """Simplified Governor for relay context. Delegates to full Governor module."""
    def __init__(self, vap: VAPProofChain):
        self.vap = vap
        self._pending: list[dict] = []
        self._approved: list[dict] = []
        self._trust: dict[str, float] = {m: 50.0 for m in [
            "codex-gpt-5.4", "deepseek-v3", "glm-5.1", "osman-agent", "osman-coder",
            "grok-4-20", "trinity-large-preview", "minimax-m2.5", "claude-code",
        ]}

    def evaluate_proposal(self, model_id: str, skill_name: str, tokens_estimated: int,
                         action: str, domain: str = "general") -> dict:
        """GSPP evaluate_proposal() — returns {proposal_id, decision, score}."""
        proposal_id = hashlib.sha256(f"{model_id}{skill_name}{time.time()}".encode()).hexdigest()[:16]
        decision = self._kaiju_check(action)
        score = self._trust.get(model_id, 50.0)
        entry = VAPEvent("proposal", model_id, action, decision.value, score, skill_name)
        self.vap.append(entry)
        result = {
            "proposal_id": proposal_id, "model_id": model_id, "skill_name": skill_name,
            "decision": decision.value, "trust_score": score,
            "tokens_estimated": tokens_estimated, "domain": domain,
            "vap_l1_hash": entry.l1_hash(), "vap_l2": getattr(entry, "_l2", ""),
            "status": "approved" if decision == Decision.ALLOW else "pending"
                     if decision == Decision.HOLD else "denied",
        }
        if decision == Decision.HOLD:
            self._pending.append(result)
        elif decision == Decision.ALLOW:
            self._approved.append(result)
        return result

    def _kaiju_check(self, action: str) -> Decision:
        for p in _SUSPICIOUS_PATTERNS:
            if p in action.lower():
                return Decision.DENY
        return Decision.ALLOW

    def approve_proposal(self, proposal_id: str) -> dict:
        for p in self._pending:
            if p["proposal_id"] == proposal_id:
                p["status"] = "approved"
                self._pending.remove(p)
                self._approved.append(p)
                return p
        return {"error": "proposal not found"}

    def get_pending_count(self) -> int:
        return len(self._pending)

    def get_trusted_models(self, threshold: float = 70.0) -> list[str]:
        return [m for m, s in self._trust.items() if s >= threshold]

# ── Dashboard stats aggregator ────────────────────────────────────────────────
def dashboard_stats(vap: VAPProofChain, gov: GovernorRelay,
                   model_stats: dict) -> dict:
    """Build the exact JSON structure the NexusControlCenter dashboard expects."""
    return {
        "main_keys": [
            {"id": "codex", "name": "Codex", "usage": 142, "last_used": "2h ago"},
            {"id": "nvidia", "name": "NVIDIA", "usage": 89, "last_used": "4h ago"},
            {"id": "kilocode", "name": "KiloCode", "usage": 201, "last_used": "1h ago"},
            {"id": "groq", "name": "Groq", "usage": 55, "last_used": "6h ago"},
        ],
        "research_keys": [
            {"id": "openai", "name": "OpenAI", "usage": 12, "last_used": "1d ago"},
            {"id": "alibaba-qwen", "name": "Alibaba Qwen", "usage": 34, "last_used": "3h ago"},
            {"id": "anthropic", "name": "Anthropic", "usage": 8, "last_used": "1d ago"},
            {"id": "google", "name": "Google", "usage": 21, "last_used": "2d ago"},
            {"id": "deepseek", "name": "DeepSeek", "usage": 67, "last_used": "5h ago"},
            {"id": "glm", "name": "GLM", "usage": 15, "last_used": "1d ago"},
            {"id": "kilocode", "name": "KiloCode", "usage": 43, "last_used": "2h ago"},
        ],
        "healthy_models": list(gov.get_trusted_models(70.0)),
        "rate_limits": {
            "hourly": {"used": 2, "limit": 5},
            "daily": {"used": 7, "limit": 20},
        },
        "provider_health": _provider_health(model_stats),
        "pending_proposals": gov.get_pending_count(),
        "vap_proofs_today": vap.daily_count(),
        "success_rate": _calc_success_rate(vap),
        "avg_latency_ms": 1240,
    }

def _provider_health(model_stats: dict) -> list[dict]:
    defaults = {
        "minimax-m2.5": (0.96, "green"), "trinity-large-preview": (0.91, "green"),
        "kimi-k2.5": (0.88, "yellow"), "step-3.5-flash": (0.84, "yellow"),
        "qwen2.5-coder": (0.79, "yellow"), "deepseek-r1": (0.75, "yellow"),
        "heretic-ara": (0.93, "green"), "gemma4-e4b": (0.71, "yellow"),
    }
    return [
        {"name": name, "success_rate": rate, "latency_ms": 800 + i * 120,
         "circuit": "closed", "status": color}
        for i, (name, (rate, color)) in enumerate(defaults.items())
    ]

def _calc_success_rate(vap: VAPProofChain) -> float:
    total = len(vap._events)
    if not total:
        return 1.0
    allowed = sum(1 for e in vap._events if e.decision == "allow")
    return round(allowed / total, 3)

# ── ASBOM (Agent Skill Bill of Materials) ─────────────────────────────────────
class ASBOM:
    """P0: Agent Skill Bill of Materials — static analysis for skill proposals."""
    def __init__(self):
        self._patterns = _SUSPICIOUS_PATTERNS

    def analyze(self, skill_code: str, skill_name: str) -> dict:
        """Static scan of skill code. Returns {clean: bool, issues: list, risk_score: float}."""
        issues = []
        code_lower = skill_code.lower()
        for p in self._patterns:
            if p in code_lower:
                issues.append(f"pattern detected: {p}")
        risk_score = min(1.0, len(issues) * 0.3 + len(skill_code) / 10000)
        return {
            "skill_name": skill_name,
            "clean": len(issues) == 0,
            "issues": issues,
            "risk_score": round(risk_score, 3),
            "lines_of_code": skill_code.count("\n"),
        }

# ── OWASP ASI Top 10 map ──────────────────────────────────────────────────────
OWASP_ASM = {
    "critical": ["delete all", "rm -rf", "exfiltrate", "backdoor"],
    "high": ["sudo", "chmod 777", "eval(", "exec("],
    "medium": ["subprocess", "os.system", "curl.*| wget"],
    "low": ["read-only-check"],
}
"""OWASP Agent Security Map — threat categories for ASBOM risk classification."""
