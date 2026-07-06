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
from dataclasses import dataclass, field, replace
from typing import Any, Dict, List, Optional, Tuple

from nexus_os.relay.circuit_breaker import ProviderCircuitBreaker
from nexus_os.relay.quota import SlidingWindowRPMTracker, max_completion_budget

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
        circuit_breaker: Optional[ProviderCircuitBreaker] = None,
        rpm_tracker: Optional[SlidingWindowRPMTracker] = None,
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
        self._breaker = circuit_breaker or ProviderCircuitBreaker()
        self._rpm_tracker = rpm_tracker

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    #: Longest proactive RPM pacing sleep; past this we still proceed rather
    #: than blocking the caller (exhaustion is handled by the hard-stop above).
    MAX_PACING_SLEEP_SECONDS = 5.0

    def execute(self, request: RelayRequest) -> RelayResult:
        """Execute the request through the fallback chain.

        Returns the first successful RelayResult, or an error result if all
        three tiers fail.  Enforced guards, in order:

        1. Context fit — completion budget is clamped to the model's known
           context window; if the input alone overflows it, fail immediately
           (the provider would reject the request with zero retry value).
        2. RPM quota — an exhausted sliding window returns an error result
           without dispatch; proactive backoff pacing sleeps briefly.
        3. Circuit breaker — keyed per relay tier; an OPEN tier is skipped
           instead of hammered.
        """
        model_id = request.model

        est_input_tokens = len(request.prompt.encode("utf-8")) // 4
        budget_cap = max_completion_budget(model_id, est_input_tokens)
        if budget_cap is not None and budget_cap <= 0:
            logger.warning(
                "Context overflow for %s: ~%d input tokens exceed the model window — failing over",
                model_id, est_input_tokens,
            )
            return RelayResult(
                status="error:context_overflow",
                provider="none",
                model=model_id,
                used_fallback=False,
                latency_ms=0.0,
                attempts=[],
                raw=None,
            )
        if budget_cap is not None and request.max_tokens > budget_cap:
            logger.warning(
                "Clamping completion budget for %s: %d -> %d (input ~%d tokens)",
                model_id, request.max_tokens, budget_cap, est_input_tokens,
            )
            request = replace(request, max_tokens=budget_cap)

        if self._rpm_tracker is not None:
            allowed, backoff, util = self._rpm_tracker.can_proceed()
            if not allowed:
                logger.warning("RPM exhausted (%.1f%%), retry in %.1fs", util * 100, backoff)
                return RelayResult(
                    status="error:rpm_exhausted",
                    provider="none",
                    model=model_id,
                    used_fallback=False,
                    latency_ms=0.0,
                    attempts=[{
                        "tier": "rpm_guard",
                        "url": "",
                        "status": "error:rpm_exhausted",
                        "provider": "none",
                        "latency_ms": 0.0,
                        "used_fallback": False,
                        "retry_after_seconds": round(backoff, 1),
                        "utilization_pct": round(util * 100, 1),
                    }],
                    raw=None,
                )
            if backoff > 0:
                pause = min(backoff, self.MAX_PACING_SLEEP_SECONDS)
                logger.info("RPM pacing sleep %.1fs at %.1f%% utilization", pause, util * 100)
                time.sleep(pause)
            # Count the request when it is dispatched, not on success —
            # a failed upstream call still consumed provider quota.
            self._rpm_tracker.record_request()

        tiers: List[Tuple[str, str, bool]] = [
            ("primary", self.primary_url, False),
            ("godmode", self.godmode_url, False),
            ("fallback", self.fallback_url, True),
        ]
        attempts: List[Dict[str, Any]] = []

        for tier_name, base_url, is_fallback in tiers:
            tier_key = f"relay:{tier_name}"
            if not self._breaker.can_execute(tier_key):
                logger.warning("Circuit OPEN for relay tier %s — skipping", tier_name)
                attempts.append(
                    {
                        "tier": tier_name,
                        "url": base_url,
                        "status": "error:circuit_open",
                        "provider": "none",
                        "latency_ms": 0.0,
                        "used_fallback": is_fallback,
                    }
                )
                continue
            t0 = time.time()
            try:
                status, provider, raw_text = self._call_chat(request, base_url, tier_name)
            except Exception as exc:
                status = f"error:{exc.__class__.__name__}"
                provider = "unknown"
                raw_text = None
                logger.warning("Adapter tier %s raised %s: %s", tier_name, exc.__class__.__name__, exc)
            latency_ms = round((time.time() - t0) * 1000.0, 2)

            if status == "ok":
                self._breaker.record_success(tier_key)
            else:
                self._breaker.record_failure(tier_key)

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

    def _call_chat(self, request: RelayRequest, base_url: str,
                   tier_name: str = "") -> Tuple[str, str, Optional[str]]:
        """OpenAI-compatible POST.  Returns (status, provider, response_text).

        An HTTP 200 with an unparseable body, no choices, or empty content is
        an error status (not "ok"), so the tier fallback chain continues
        instead of short-circuiting on a garbage response.
        """
        url = f"{base_url.rstrip('/')}/v1/chat/completions"
        request_payload = {
            "model": request.model,
            "messages": [{"role": "user", "content": request.prompt}],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        payload = json.dumps(request_payload).encode("utf-8")
        headers = {
            "content-type": "application/json",
            "accept": "application/json",
        }
        t0 = time.time()
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
        try:
            data = json.loads(body)
        except ValueError:
            logger.warning("Relay %s returned unparseable body (%d bytes)", base_url, len(body))
            return "error:malformed_response", "unknown", None
        if not isinstance(data, dict) or not data.get("choices"):
            logger.warning("Relay %s returned no choices: %s", base_url, str(data)[:200])
            return "error:malformed_response", "unknown", None
        provider = str(data.get("model", request.model))
        try:
            text = data["choices"][0].get("message", {}).get("content")
        except (AttributeError, IndexError, TypeError):
            text = None
        if not text:
            return "error:empty_response", provider, None
        # FI-T1 exactly-once: only the PRIMARY tier (Node relay :7350
        # direct) is captured here — godmode and fallback tiers are
        # captured server-side by god_mode_proxy / model_relay.
        if tier_name == "primary":
            self._capture_trace(request_payload, data,
                                latency_ms=int((time.time() - t0) * 1000))
        return "ok", provider, text

    _trace_fail_warned = False

    def _capture_trace(self, request_payload: dict, data: dict, latency_ms: int) -> None:
        """NEXUS-REASONS-DB capture for Node-relay-direct traffic. Never raises."""
        try:
            from nexus_os.relay.tracing.capture import record_response, split_provider_model
            provider, model_id = split_provider_model(str(data.get("model") or ""))
            record_response(
                provider=provider,
                model_id=model_id,
                request_payload=request_payload,
                response_payload=data,
                latency_ms=latency_ms,
                temperature=request_payload.get("temperature"),
                tags=["adapter-primary"],
            )
        except Exception:
            if not ModelRelayAdapter._trace_fail_warned:
                logger.warning("adapter trace capture failed — REASONS-DB not recording", exc_info=True)
                ModelRelayAdapter._trace_fail_warned = True


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
