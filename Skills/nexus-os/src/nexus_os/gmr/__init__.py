"""NEXUS OS — GMR module: Model rotation and sub-agent routing.
Routes intents to specialized sub-agents via /zo/ask API.
Primary: MiniMax 2.7 (this instance, orchestrator).
Workers: Free-tier API endpoints (OpenRouter, Groq, Cerebras).
"""
from nexus_os.engine import Hermes, Domain

class Model:
    def __init__(self, name: str, tier: int, domains: list, endpoint: str = "", cost: float = 0):
        self.name = name
        self.tier = tier
        self.domains = domains
        self.endpoint = endpoint
        self.cost = cost

# Zo's actual model stack. Primary is the orchestrator (this instance).
# Sub-agents are spawned via /zo/ask API — not local processes.
_MODELS = [
    Model("minimax-m2.7",  95, ["reason", "code", "research", "fast", "sec"], "vercel:minimax/minimax-m2.7", 0),
    Model("openrouter",    75, ["code", "reason"],                                 "vercel:openrouter/*",        0),
    Model("groq",          70, ["code", "fast"],                                   "vercel:groq/*",              0),
    Model("cerebras",      65, ["fast", "research"],                               "vercel:cerebras/*",          0),
    Model("claude-code",   90, ["reason", "sec", "code"],                         "vercel:claude/claude-code",   0),
]

class GMR:
    """Global Model Router — routes intents to sub-agents via /zo/ask API."""
    def __init__(self):
        self.hermes = Hermes()

    def classify(self, prompt: str) -> str:
        return self.hermes.classify(prompt).value

    def route(self, prompt: str, domain: str) -> list:
        return [m for m in _MODELS if domain in m.domains]

    def select(self, prompt: str) -> Model:
        domain = self.classify(prompt)
        candidates = [m for m in _MODELS if domain in m.domains]
        if not candidates:
            candidates = _MODELS
        return max(candidates, key=lambda m: m.tier)

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
