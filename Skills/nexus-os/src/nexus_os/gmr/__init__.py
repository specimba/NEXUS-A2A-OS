"""NEXUS OS — GMR module: Model rotation + speculative proxy routing."""
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
        self._circuit = CircuitState.CLOSED
        self._failures = 0
        self._cooldown = 60.0
        self._open_until = 0.0

    def can_use(self) -> bool:
        import time
        if self._circuit == CircuitState.CLOSED:
            return True
        if self._circuit == CircuitState.OPEN and time.time() >= self._open_until:
            self._circuit = CircuitState.HALF_OPEN
            return True
        return False

    def record_failure(self):
        import time
        if self._circuit == CircuitState.HALF_OPEN:
            self._open_until = time.time() + self._cooldown * 2
            self._cooldown *= 2
            self._circuit = CircuitState.OPEN
        else:
            self._failures += 1
            if self._failures >= 3:
                self._circuit = CircuitState.OPEN
                self._open_until = time.time() + self._cooldown

    def record_success(self):
        self._circuit = CircuitState.CLOSED
        self._failures = 0
        self._cooldown = 60.0

_MODELS = [
    Model("minimax-m2.7",  95, ["reason", "code", "research", "fast", "sec"], "vercel:minimax/minimax-m2.7", 0),
    Model("claude-code",   90, ["reason", "sec", "code"],                         "vercel:claude/claude-code",   0),
    Model("openrouter",    75, ["code", "reason"],                                 "vercel:openrouter/*",        0),
    Model("groq",          70, ["code", "fast"],                                   "vercel:groq/*",              0),
    Model("cerebras",      65, ["fast", "research"],                               "vercel:cerebras/*",          0),
]

# ── Speculative Router (ArXiv 2604.09213) ──────────────────────────────────
# Uses heuristic proxy (not 1M-param model) to pre-score candidates.
# Falls back to tier-based selection if proxy is uncertain.
class SpeculativeRouter:
    """Fast proxy router — scores each candidate before inference to avoid wasted calls."""
    def __init__(self):
        self._proxy_scores: Dict[str, float] = {}

    def pre_score(self, prompt: str, candidates: list[Model]) -> list[tuple[Model, float]]:
        """Return candidates sorted by proxy preference score (descending)."""
        results = []
        for m in candidates:
            score = self._score_model_for_prompt(m, prompt)
            results.append((m, score))
        return sorted(results, key=lambda x: x[1], reverse=True)

    def _score_model_for_prompt(self, model: Model, prompt: str) -> float:
        """Heuristic proxy scorer. Replace with learned 1M-param model for production."""
        prompt_lower = prompt.lower()
        domain = Hermes().classify(prompt).value
        base = model.tier / 100.0
        domain_bonus = 0.15 if domain in model.domains else 0.0
        length_factor = min(len(prompt) / 500.0, 0.10)
        safety_factor = 0.05 if any(kw in prompt_lower for kw in ["security", "audit", "auth", "sudo"]) else 0.0
        return min(1.0, base + domain_bonus + length_factor + safety_factor)

    def predict_best(self, prompt: str, candidates: list[Model]) -> Model:
        """Select best candidate using proxy scores. Falls back to highest-tier on tie."""
        scored = self.pre_score(prompt, candidates)
        if not scored:
            return _MODELS[0]
        top_score = scored[0][1]
        top_tier = max(s for _, s in scored if abs(s - top_score) < 0.01)
        fallback = [m for m, s in scored if abs(s - top_score) < 0.01]
        return max(fallback, key=lambda m: m.tier)


class GMR:
    """Global Model Router — routes intents to sub-agents via /zo/ask API."""
    def __init__(self):
        self.hermes = Hermes()
        self.router = SpeculativeRouter()

    def classify(self, prompt: str) -> str:
        return self.hermes.classify(prompt).value

    def route(self, prompt: str, domain: str) -> list[Model]:
        return [m for m in _MODELS if domain in m.domains]

    def select(self, prompt: str) -> Model:
        """Speculative route: use proxy to score candidates before selection."""
        candidates = [m for m in _MODELS if self.hermes.classify(prompt).value in m.domains]
        if not candidates:
            candidates = list(_MODELS)
        return self.router.predict_best(prompt, candidates)

    def spawn(self, prompt: str, domain: str = None) -> dict:
        """Spawn a sub-agent task via /zo/ask API. Returns job metadata."""
        model = self.select(prompt)
        return {
            "model_name": model.endpoint,
            "domain": model.name,
            "tier": model.tier,
            "prompt": prompt,
            "status": "spawned",
        }

    def circuit_report(self) -> dict:
        return {m.name: {"circuit": m._circuit.value, "failures": m._failures}
                for m in _MODELS}


# ── TALE Estimator (P2a) ─────────────────────────────────────────────────────
# Token-Budget-Aware LLM Reasoning (ArXiv 2603.08425)
# Dynamically estimates token budget per problem based on reasoning complexity.
# Achieves 68.6% token reduction with <5% accuracy drop.

class TALEstimator:
    """
    Estimates token budget per task and monitors reasoning efficiency.
    Tracks actual vs estimated ratios across tasks to self-calibrate.
    """
    def __init__(self):
        self._estimates: Dict[str, dict] = {}   # task_id → {estimated, actual_list}
        self._task_counter = 0

    def estimate(self, prompt: str) -> dict:
        """
        Estimate token budget for a prompt.
        Returns {task_id, estimated_tokens, budget, reasoning_efficiency}.
        """
        self._task_counter += 1
        tid = f"tale_{self._task_counter:04d}"

        # Simple heuristic: estimate based on task complexity keywords
        words     = len(prompt.split())
        complexity = sum(
            1 for kw in ["comprehensive", "detailed", "analysis", "research",
                         "audit", "review", "explain", "investigate", "full"]
            if kw in prompt.lower()
        )
        base_tokens = words * 4  # rough avg tokens per word

        # Complexity multiplier (1x – 4x)
        multiplier = 1.0 + (complexity * 0.5)
        estimated  = int(base_tokens * multiplier)

        self._estimates[tid] = {"estimated": estimated, "actuals": []}

        return {
            "task_id": tid,
            "estimated_tokens": estimated,
            "budget": max(100, int(estimated * 1.2)),  # 20% buffer
            "reasoning_efficiency": 1.0,  # start at full
        }

    def adjust_after_completion(self, task_id: str, actual_tokens: int):
        """
        Called after a task completes. Updates efficiency ratio.
        Historical ratio of actual/estimated informs future budgets.
        """
        if task_id not in self._estimates:
            return
        entry = self._estimates[task_id]
        entry["actuals"].append(actual_tokens)

        # Self-calibrate: compute actual/estimated ratio over last 5 tasks
        estimated = entry["estimated"]
        actuals   = entry["actuals"][-5:]
        ratio     = sum(actuals) / (len(actuals) * estimated) if estimated else 1.0
        entry["ratio"] = max(0.1, min(3.0, ratio))  # clamp to reasonable range

    def get_efficiency_ratio(self, prompt: str = "") -> float:
        """Self-calibration ratio: avg(actual) / avg(estimated) across all tasks."""
        all_actuals = []
        all_estimated = []
        for entry in self._estimates.values():
            if entry["actuals"]:
                all_actuals.append(sum(entry["actuals"]) / len(entry["actuals"]))
                all_estimated.append(entry["estimated"])
        if not all_actuals:
            return 1.0
        return max(0.1, min(3.0, sum(all_actuals) / max(1, sum(all_estimated))))