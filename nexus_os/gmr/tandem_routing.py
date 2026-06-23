"""gmr/tandem_routing.py — Tandem Routing (LLM-SLM Collaboration)

Implements the Tandem framework (arXiv:2407.01234) where a large coordinator model
generates strategic reasoning insights (a blueprint) to guide a smaller local executor
model (e.g. VibeThinker-3B) in completing the full reasoning trace.
"""

from __future__ import annotations

import json
import logging
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

COORDINATOR_SYSTEM_PROMPT = (
    "You are a strategic reasoning coordinator. Given the user's prompt, provide "
    "a concise list of key reasoning steps, subgoals, or logical insights (max 3-5 bullets) "
    "that will guide a smaller model in solving the task. Do NOT solve the task or write the "
    "final answer. Only output the guiding insights."
)

EXECUTOR_SYSTEM_PROMPT = (
    "You are a reasoning model. You will solve the user's prompt step-by-step. "
    "Use the strategic reasoning insights provided by the coordinator model to guide "
    "your thinking and ensure accuracy."
)


class TandemRouter:
    """Orchestrates collaborative reasoning between Large (coordinator) and Small (executor) models."""

    def __init__(
        self,
        relay_url: Optional[str] = None,
        timeout: float = 30.0,
    ) -> None:
        import os
        port = int(os.environ.get("NODERELAY_PORT", "7350"))
        self._relay_url = (relay_url or f"http://127.0.0.1:{port}").rstrip("/")
        self._timeout = timeout

    def _call_model(self, model: str, system_prompt: str, user_content: str, max_tokens: int = 512) -> str:
        """Call ModelRelay for chat completions."""
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0.1,
            "max_tokens": max_tokens,
        }
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                f"{self._relay_url}/v1/chat/completions",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            choices = result.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "").strip()
        except Exception as e:
            logger.debug("TandemRouter: Failed to call model %s: %s", model, e)
        return ""

    def generate_blueprint(self, query: str, coordinator_model: str) -> str:
        """Query coordinator model to generate a strategic reasoning blueprint."""
        logger.info("TandemRouter: Generating strategic blueprint using %s", coordinator_model)
        blueprint = self._call_model(
            model=coordinator_model,
            system_prompt=COORDINATOR_SYSTEM_PROMPT,
            user_content=query,
            max_tokens=256
        )
        return blueprint

    def execute_blueprint(self, query: str, blueprint: str, executor_model: str) -> str:
        """Query executor model using the blueprint as context."""
        logger.info("TandemRouter: Executing blueprint using %s", executor_model)
        user_content = (
            f"User Prompt: {query}\n\n"
            f"Strategic Reasoning Insights (use these to guide your solution):\n"
            f"{blueprint}\n"
        )
        result = self._call_model(
            model=executor_model,
            system_prompt=EXECUTOR_SYSTEM_PROMPT,
            user_content=user_content,
            max_tokens=1024
        )
        return result

    def route(
        self,
        query: str,
        coordinator_model: str = "fugu-ultra",
        executor_model: str = "VibeThinker-3B",
    ) -> str:
        """Run the full Tandem routing pipeline: plan with Large, execute with Small."""
        # Generate blueprint (insights)
        blueprint = self.generate_blueprint(query, coordinator_model)
        if not blueprint:
            logger.warning("TandemRouter: Blueprint generation failed, falling back to direct executor call")
            return self._call_model(
                model=executor_model,
                system_prompt="You are a reasoning model. Solve the prompt step-by-step.",
                user_content=query,
                max_tokens=1024
            )
        
        # Execute blueprint
        return self.execute_blueprint(query, blueprint, executor_model)
