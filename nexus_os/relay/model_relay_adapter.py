#!/usr/bin/env python3
"""
ModelRelay Adapter — ChimeraRouter ⇄ ModelRelay execution bridge.

This is the owned integration surface that turns a ChimeraRouter RoutingDecision
into an actual LLM call.  ChimeraRouter stays secret/config-agnostic — the adapter
reads relay endpoints from environment variables and executes OpenAI-compatible
/v1/chat/completions calls with a 3-tier fallback chain:

    1. Node ModelRelay  (port 7350, primary)
    2. God Mode Proxy   (port 7357, intelligent routing with provider diversity)
    3. Python Relay     (port 7355, last resort)

References:
    - Hermes log-04 ChimeraRouter⇄ModelRelay mission (2026-06-23)
    - Port ownership: docs/handbook/08_PORT_OWNERSHIP_RULESET.md

Architecture invariant:
    ChimeraRouter = decision layer  (which model? which policy? which tier?)
    Adapter       = execution layer (call the relay, return the text)
"""
from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("nexus.relay.adapter")

# ---------------------------------------------------------------------------
# Data surface
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RelayRequest:
    """A single chat-completion request destined for a relay endpoint."""

    model: str
    prompt: str
    temperature: float = 0.7
    max_tokens: int = 512
    relay_url: str = ""
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class RelayResult:
    """Result of executing a RelayRequest against the relay chain."""

    status: str  # "ok" | "error:primary" | "error:god" | "error:fallback" | "error:both_failed" | "error:exception"
    provider: str  # the actual model string returned by the endpoint
    model: str
    used_fallback: bool
    latency_ms: float
    attempts: List[Dict[str, Any]] = field(default_factory=list)
    raw: Optional[str] = None


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class ModelRelayAdapter:
    """OpenAI-compatible relay adapter with 3-tier fallback.

    Tier order (first success wins):
        1. Node ModelRelay  (7350)  — primary, widest model palette
        2. God Mode Proxy   (7357)  — intelligent routing, provider diversity
        3. Python Relay     (7355)  — minimal fallback

    All URLs can be overridden via constructor args or environment variables:
        NODERELAY_URL / NODERELAY_PORT  (default 7350)
        GODMODE_URL   / GODMODE_PORT    (default 7357)
        PYTHONRELAY_URL / PYTHONRELAY_PORT (default 7355)
    """

    def __init__(
        self,
        primary_url: Optional[str] = None,
        fallback_url: Optional[str] = None,
        godmode_url: Optional[str] = None,
        timeout_seconds: int = 30,
    ) -> None:
        self.primary_url = (
            primary_url
            or os.environ.get("NODERELAY_URL")
            or f"http://127.0.0.1:{os.environ.get('NODERELAY_PORT', '7350')}"
        )
        self.godmode_url = (
            godmode_url
            or os.environ.get("GODMODE_URL")
            or f"http://127.0.0.1:{os.environ.get('GODMODE_PORT', '7357')}"
        )
        self.fallback_url = (
            fallback_url
            or os.environ.get("PYTHONRELAY_URL")
            or f"http://127.0.0.1:{os.environ.get('PYTHONRELAY_PORT', '7355')}"
        )
        self.timeout_seconds = timeout_seconds

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute(self, request: RelayRequest) -> RelayResult:
        """Execute the request through the fallback chain.

        Returns the first successful RelayResult, or an error result if all
        three tiers fail.
        """
        tiers: List[Tuple[str, str, bool]] = [
            ("primary", self.primary_url, False),
            ("godmode", self.godmode_url, False),
            ("fallback", self.fallback_url, True),
        ]
        attempts: List[Dict[str, Any]] = []

        for tier_name, base_url, is_fallback in tiers:
            t0 = time.time()
            try:
                status, provider, raw_text = self._call_chat(request, base_url)
            except Exception as exc:
                status = f"error:{exc.__class__.__name__}"
                provider = "unknown"
                raw_text = None
                logger.warning("Adapter tier %s raised %s: %s", tier_name, exc.__class__.__name__, exc)
            latency_ms = round((time.time() - t0) * 1000.0, 2)

            attempts.append(
                {
                    "tier": tier_name,
                    "url": base_url,
                    "status": status,
                    "provider": provider,
                    "latency_ms": latency_ms,
                    "used_fallback": is_fallback,
                }
            )

            if status == "ok":
                return RelayResult(
                    status=status,
                    provider=provider,
                    model=request.model,
                    used_fallback=is_fallback,
                    latency_ms=latency_ms,
                    attempts=attempts,
                    raw=raw_text,
                )

        all_failed = all(a["status"] != "ok" for a in attempts)
        return RelayResult(
            status="error:both_failed" if all_failed else "error:partial",
            provider="none",
            model=request.model,
            used_fallback=True,
            latency_ms=sum(a["latency_ms"] for a in attempts),
            attempts=attempts,
            raw=None,
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _call_chat(self, request: RelayRequest, base_url: str) -> Tuple[str, str, str]:
        """OpenAI-compatible POST.  Returns (status, provider, response_text)."""
        url = f"{base_url.rstrip('/')}/v1/chat/completions"
        payload = json.dumps(
            {
                "model": request.model,
                "messages": [{"role": "user", "content": request.prompt}],
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
            }
        ).encode("utf-8")
        headers = {
            "content-type": "application/json",
            "accept": "application/json",
        }
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
        try:
            data = json.loads(body)
            text = (
                data.get("choices", [{}])[0].get("message", {}).get("content", "")
            )
        except Exception:
            data = {}
            text = ""
        provider = data.get("model", request.model) if isinstance(data, dict) else request.model
        return "ok", str(provider), text


# ---------------------------------------------------------------------------
# Convenience: decision → request → execute
# ---------------------------------------------------------------------------


def execute_decision(
    decision: Any,
    prompt: str,
    adapter: Optional[ModelRelayAdapter] = None,
) -> RelayResult:
    """Convert a ChimeraRouter RoutingDecision into a RelayRequest and execute it.

    ``decision`` is expected to have attributes ``model``, ``temperature``, and
    ``budget.max_tokens`` as defined in nexus_os.twave.chimera_router_v2.RoutingDecision.
    """
    if adapter is None:
        adapter = ModelRelayAdapter()

    max_tokens = getattr(getattr(decision, "budget", None), "max_tokens", 512)
    policy = getattr(getattr(decision, "temperature_policy", None), "value", "auto")

    request = RelayRequest(
        model=decision.model,
        prompt=prompt,
        temperature=decision.temperature,
        max_tokens=max_tokens,
        metadata={"policy": policy},
    )
    return adapter.execute(request)
