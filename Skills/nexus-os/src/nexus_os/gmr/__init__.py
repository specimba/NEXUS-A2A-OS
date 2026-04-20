"""NEXUS OS — GMR module: Model rotation and sub-agent routing.
Routes intents to specialized sub-agents via /zo/ask API.
Primary: MiniMax 2.7 (this instance, orchestrator).
Workers: Free-tier API endpoints (OpenRouter, Groq, Cerebras).

P0d upgrade: Half-open circuit breaker per Model.
  CLOSED  → (3 failures)        → OPEN  (cooldown seconds, doubles on repeated trips)
  OPEN    → (cooldown expires)  → HALF_OPEN
  HALF_OPEN → (1 test request):
    → success  → CLOSED (cooldown resets)
    → fail     → OPEN  (cooldown doubles, max 10 min)
"""
import time
from enum import Enum
from nexus_os.engine import Hermes, Domain


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class Model:
    def __init__(self, name: str, tier: int, domains: list, endpoint: str = "", cost: float = 0):
        self.name = name
        self.tier = tier
        self.domains = domains
        self.endpoint = endpoint
        self.cost = cost

        # --- P0d: Half-open circuit breaker ---
        self._circuit = CircuitState.CLOSED
        self._failures = 0
        self._cooldown = 60.0          # seconds; doubles on re-trip
        self._open_until = 0.0          # unix timestamp
        self._max_cooldown = 600.0     # 10 minute cap

    def _check_circuit(self) -> bool:
        """Return True if requests are allowed through."""
        now = time.time()
        if self._circuit == CircuitState.CLOSED:
            return True
        if self._circuit == CircuitState.OPEN:
            if now >= self._open_until:
                self._circuit = CircuitState.HALF_OPEN
                return True
            return False
        # HALF_OPEN: allow exactly one test request through
        return True

    def record_failure(self):
        """Call after every failed API call."""
        if self._circuit == CircuitState.HALF_OPEN:
            # Failed during probe → go back to OPEN with doubled cooldown
            self._cooldown = min(self._cooldown * 2, self._max_cooldown)
            self._open_until = time.time() + self._cooldown
            self._circuit = CircuitState.OPEN
        else:
            self._failures += 1
            if self._failures >= 3:
                self._open_until = time.time() + self._cooldown
                self._circuit = CircuitState.OPEN

    def record_success(self):
        """Call after every successful API call."""
        self._circuit = CircuitState.CLOSED
        self._failures = 0
        self._cooldown = 60.0

    def can_use(self) -> bool:
        """True if model is not tripped."""
        return self._check_circuit()

    def circuit_status(self) -> dict:
        return {
            "model": self.name,
            "state": self._circuit.value,
            "failures": self._failures,
            "cooldown_s": round(self._cooldown, 1),
            "open_until": round(self._open_until, 2),
        }


# Zo's actual model stack. Primary is the orchestrator (this instance).
# Sub-agents are spawned via /zo/ask API — not local processes.
_MODELS = [
    Model("minimax-m2.7",  95, ["reason", "code", "research", "fast", "sec"], "vercel:minimax/minimax-m2.7", 0),
    Model("openrouter",     75, ["code", "reason"],                                  "vercel:openrouter/*",         0),
    Model("groq",           70, ["code", "fast"],                                    "vercel:groq/*",               0),
    Model("cerebras",       65, ["fast", "research"],                                "vercel:cerebras/*",           0),
    Model("claude-code",    90, ["reason", "sec", "code"],                           "vercel:claude/claude-code",   0),
]


class GMR:
    """Global Model Router — routes intents to sub-agents via /zo/ask API."""
    def __init__(self):
        self.hermes = Hermes()

    def classify(self, prompt: str) -> str:
        return self.hermes.classify(prompt).value

    def route(self, prompt: str, domain: str) -> list:
        return [m for m in _MODELS if domain in m.domains]

    def _available(self, candidates: list) -> list:
        """Filter to only models that aren't tripped."""
        return [m for m in candidates if m.can_use()]

    def select(self, prompt: str) -> Model:
        domain = self.classify(prompt)
        candidates = [m for m in _MODELS if domain in m.domains]
        if not candidates:
            candidates = _MODELS
        available = self._available(candidates)
        return max(available if available else candidates, key=lambda m: m.tier)

    def spawn(self, prompt: str, domain: str = None) -> dict:
        """Spawn a sub-agent task via /zo/ask API. Returns job metadata."""
        model = self.select(prompt)
        return {
            "model_name": model.endpoint,
            "domain": model.name,
            "tier": model.tier,
            "prompt": prompt,
            "circuit": model.circuit_status(),
            "status": "spawned",
        }

    def circuit_report(self) -> list:
        """Full circuit status for all models."""
        return [m.circuit_status() for m in _MODELS]
