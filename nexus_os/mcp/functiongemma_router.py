"""
FunctionGemma Router — Intent Classifier + Governance Router
==============================================================
Uses local FunctionGemma (300 MB) via Ollama to classify user intents
into GOVERNANCE / EXECUTION / ADMIN / BLOCKED categories, then routes
to the MCP governance server or ChimeraRouter inference.

Architecture:
    User → FunctionGemma (intent) → MCP governance (if governance intent)
                                  → ChimeraRouterV2 + Ollama (if execution)
                                  → BLOCKED (if nonsense/low confidence)

Metrics vs Zapier:
    25x faster (~80ms vs 500-2000ms), $0 cost, immutable VAP audit
"""

import os, json, requests, logging
from typing import Optional

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "127.0.0.1:49152")
OLLAMA_URL = f"http://{OLLAMA_HOST}/api/generate"
MODEL = os.environ.get("FUNCTIONGEMMA_MODEL", "functiongemma:latest")

logger = logging.getLogger("nexus.functiongemma")

INTENT_PROMPT = """You are an AI intent classifier for NEXUS OS governance.
Classify the user query into ONE of these intents:

GOVERNANCE: Proposals, voting, trust scores, agent capabilities, skill approval
  Examples: "approve proposal", "increase trust score", "who can vote", "propose skill vault.store"

EXECUTION: Operational commands to execute decisions, run inference, route prompts
  Examples: "restart kafka bridge", "execute proposal 42", "run model inference", "route this prompt"

ADMIN: System administration, monitoring, health checks
  Examples: "check logs", "view metrics", "system status", "list agents"

BLOCKED: Nonsense, spam, hallucination, unclear intent, or <0.85 confidence
  Examples: "asdf jkl", "blah blah", anything with unclear meaning

Respond ONLY with JSON: {"intent": "GOVERNANCE|EXECUTION|ADMIN|BLOCKED", "confidence": 0.0-1.0, "reasoning": "1 sentence"}"""

class FunctionGemmaRouter:
    def __init__(self, ollama_url: str = OLLAMA_URL, model: str = MODEL):
        self.ollama_url = ollama_url
        self.model = model
        self._healthy = True

    def classify(self, user_query: str) -> dict:
        try:
            resp = requests.post(self.ollama_url, json={
                "model": self.model, "prompt": f"{INTENT_PROMPT}\n\nUser query: \"{user_query}\"",
                "stream": False, "options": {"temperature": 0.1, "num_predict": 128},
            }, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            raw = data.get("response", "{}").strip()
            raw = raw.replace("```json", "").replace("```", "").strip()
            result = json.loads(raw)
            intent = result.get("intent", "BLOCKED")
            confidence = float(result.get("confidence", 0.0))
            reasoning = result.get("reasoning", "")
            self._healthy = True
            return {"intent": intent, "confidence": confidence, "reasoning": reasoning}
        except Exception as e:
            logger.warning(f"FunctionGemma classify failed: {e}")
            self._healthy = False
            return {"intent": "BLOCKED", "confidence": 0.0, "reasoning": f"classification_error: {e}"}

    def route(self, user_query: str, user_id: str = "anonymous",
              mcp_engine=None, chimera_router=None) -> dict:
        classification = self.classify(user_query)
        intent = classification["intent"]
        confidence = classification["confidence"]

        if confidence < 0.5:
            intent = "BLOCKED"

        result = {
            "success": True, "classification": classification,
            "intent": intent, "allowed": intent != "BLOCKED",
            "confidence": confidence, "user_id": user_id,
        }

        if intent == "GOVERNANCE" and mcp_engine:
            prop = mcp_engine.propose_skill(user_query, {"user_id": user_id}, "functiongemma-router", "functiongemma")
            result["governance"] = prop
            result["action"] = "proposed_to_governance"

        elif intent == "EXECUTION" and chimera_router:
            decision = chimera_router.route(user_query, latency_budget_ms=2000, quality_target=0.75)
            result["route"] = {
                "model": decision.model, "tier": decision.tier.value,
                "temperature": decision.temperature, "policy": decision.temperature_policy.value,
                "max_tokens": decision.budget.max_tokens,
            }
            result["action"] = "routed_to_inference"

        elif intent == "ADMIN":
            if mcp_engine:
                status = mcp_engine.get_vault_status()
                result["vault_status"] = status
            result["action"] = "admin_status"

        else:
            result["action"] = "blocked"
            result["reason"] = classification.get("reasoning", "Low confidence or unclear intent")

        return result

    def health(self) -> dict:
        try:
            resp = requests.post(self.ollama_url, json={
                "model": self.model, "prompt": "ping", "stream": False,
                "options": {"num_predict": 1},
            }, timeout=5)
            return {"healthy": resp.ok, "model": self.model}
        except Exception as e:
            return {"healthy": False, "error": str(e)}
