"""Read-only live health projection for the governed ModelRelay plane.

The command deliberately reads only three loopback GET endpoints:

* ModelRelay ``/api/health-sampler`` for the bounded-canary budget;
* ModelRelay ``/api/models`` for aggregate raw offer status counts; and
* Model Arena ``/api/model-cards`` for the evidence-aware health projection.

It never calls a provider endpoint, completion endpoint, ping endpoint, log
endpoint, or local configuration file.  The resulting JSON is intentionally
small and excludes errors, tokens, keys, and other provider configuration.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
import math
import re
import socket
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


DEFAULT_RELAY_URL = "http://127.0.0.1:7350"
DEFAULT_ARENA_URL = "http://127.0.0.1:7356"
MAX_RESPONSE_BYTES = 4 * 1024 * 1024
LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}
SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,199}$")
SAFE_EVENT_WORD = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
KNOWN_OFFER_STATES = {
    "up",
    "pending",
    "down",
    "timeout",
    "error",
    "rate_limited",
    "noauth",
    "unauthorized",
    "banned",
    "disabled",
    "excluded",
}
ARENA_SUMMARY_STATES = {"healthy", "stale", "unverified", "unavailable", "rate_limited"}
ARENA_OBSERVED_UNHEALTHY_STATES = {"unavailable", "rate_limited", "auth_required"}
MAX_RATE_LIMIT_EVIDENCE = 25


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _loopback_base_url(value: str) -> str | None:
    """Accept a plain loopback HTTP base URL and reject all other targets."""
    try:
        parsed = urlparse(str(value).strip())
    except (TypeError, ValueError):
        return None
    if (
        parsed.scheme != "http"
        or parsed.hostname not in LOOPBACK_HOSTS
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        return None
    try:
        _ = parsed.port
    except ValueError:
        return None
    return parsed.geturl().rstrip("/")


def _safe_identifier(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    candidate = value.strip()
    return candidate if SAFE_IDENTIFIER.fullmatch(candidate) else None


def _safe_event_word(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    candidate = value.strip().lower()
    return candidate if SAFE_EVENT_WORD.fullmatch(candidate) else None


def _safe_number(value: object, *, lower: float = 0, upper: float = 3_600_000) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number) or number < lower or number > upper:
        return None
    return int(number)


def _safe_timestamp(value: object) -> str | None:
    """Convert epoch milliseconds/seconds or ISO timestamps to UTC ISO safely."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        if not math.isfinite(number) or number <= 0:
            return None
        seconds = number / 1_000 if number > 100_000_000_000 else number
        try:
            return datetime.fromtimestamp(seconds, timezone.utc).isoformat()
        except (OverflowError, OSError, ValueError):
            return None
    if not isinstance(value, str) or len(value) > 64:
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc).isoformat()


def _get_json(base_url: str, path: str, timeout: float) -> tuple[dict[str, Any] | None, str | None]:
    """Fetch a single bounded JSON document without credentials or side effects."""
    try:
        request = Request(
            f"{base_url}{path}",
            method="GET",
            headers={"Accept": "application/json"},
        )
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - base URL is loopback-validated
            if not 200 <= int(response.status) < 300:
                return None, f"http_{int(response.status)}"
            body = response.read(MAX_RESPONSE_BYTES + 1)
    except HTTPError as exc:
        return None, f"http_{exc.code}"
    except (socket.timeout, TimeoutError):
        return None, "timeout"
    except URLError:
        return None, "url_unreachable"
    except OSError:
        return None, "url_unreachable"

    if len(body) > MAX_RESPONSE_BYTES:
        return None, "response_too_large"
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None, "invalid_json"
    return (payload, None) if isinstance(payload, dict) else (None, "invalid_payload")


def _sampler_projection(payload: Mapping[str, Any]) -> dict[str, Any]:
    latest_event = payload.get("lastEvent")
    event: dict[str, Any] | None = None
    if isinstance(latest_event, Mapping):
        event = {
            "at": _safe_timestamp(latest_event.get("at")),
            "provider_key": _safe_identifier(latest_event.get("providerKey")),
            "model_id": _safe_identifier(latest_event.get("modelId")),
            "source": _safe_event_word(latest_event.get("source")),
            "outcome": _safe_event_word(latest_event.get("outcome")),
            "http_status": _safe_number(latest_event.get("status"), lower=100, upper=599),
            "latency_ms": _safe_number(latest_event.get("latencyMs")),
        }
    last_sampler_observation_at = _safe_timestamp(payload.get("lastObservedAt"))
    return {
        "policy": _safe_event_word(payload.get("policy")),
        "global_limit_per_window": _safe_number(payload.get("globalLimitPerWindow"), upper=10_000),
        "window_seconds": _safe_number(payload.get("windowSeconds"), upper=86_400),
        "minimum_spacing_seconds": _safe_number(payload.get("minimumSpacingSeconds"), upper=86_400),
        "used_in_window": _safe_number(payload.get("usedInWindow"), upper=10_000),
        "remaining_in_window": _safe_number(payload.get("remainingInWindow"), upper=10_000),
        "persisted_observations": _safe_number(payload.get("persistedObservations"), upper=1_000_000),
        "active_persisted_cooldowns": _safe_number(payload.get("activePersistedCooldowns"), upper=1_000_000),
        "active_persisted_access_blocks": _safe_number(payload.get("activePersistedAccessBlocks"), upper=1_000_000),
        # Retained as a compatibility alias.  This is sampler activity, not
        # evidence that any particular route is currently healthy.
        "last_observed_at": last_sampler_observation_at,
        "last_sampler_observation_at": last_sampler_observation_at,
        "next_eligible_at": _safe_timestamp(payload.get("nextEligibleAt")),
        "latest_event": event,
        # A manually triggered event must not be misrepresented as a canary.
        "latest_scheduled_canary_event": event if event and event["source"] == "scheduled" else None,
    }


def _rate_limit_evidence(row: Mapping[str, Any], *, now: datetime) -> dict[str, Any] | None:
    """Project a route's explicit 429 state without deriving retry policy."""
    provider = _safe_identifier(row.get("providerKey"))
    model = _safe_identifier(row.get("modelId"))
    if not provider or not model:
        return None
    status = _safe_event_word(row.get("status"))
    http_status = _safe_number(row.get("httpCode"), lower=100, upper=599)
    is_rate_limited = (
        row.get("isRateLimited") is True
        or status in {"rate_limited", "429"}
        or http_status == 429
    )
    if not is_rate_limited:
        return None

    observed_at = max(
        (timestamp for timestamp in (
            _safe_timestamp(row.get("lastPingAt")),
            _safe_timestamp(row.get("lastModelResponseAt")),
        ) if timestamp is not None),
        default=None,
    )
    cooldown_expires_at = _safe_timestamp(row.get("cooldownUntil"))
    cooldown_active = False
    cooldown_remaining_seconds: int | None = None
    if cooldown_expires_at is not None:
        expires_at = datetime.fromisoformat(cooldown_expires_at)
        remaining_seconds = math.ceil((expires_at - now).total_seconds())
        if remaining_seconds > 0:
            cooldown_active = True
            cooldown_remaining_seconds = remaining_seconds

    return {
        "offer_id": f"{provider}/{model}",
        "provider_key": provider,
        "model_id": model,
        "failure_class": "rate_limited",
        "http_status": http_status,
        "observed_at": observed_at,
        "cooldown_active": cooldown_active,
        "cooldown_expires_at": cooldown_expires_at,
        "cooldown_remaining_seconds": cooldown_remaining_seconds,
    }


def _offer_projection(payload: Mapping[str, Any]) -> dict[str, Any] | None:
    models = payload.get("models")
    if not isinstance(models, list):
        return None
    states: Counter[str] = Counter()
    providers: set[str] = set()
    rate_limit_evidence: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc)
    for row in models:
        if not isinstance(row, Mapping):
            states["other"] += 1
            continue
        provider = _safe_identifier(row.get("providerKey"))
        if provider:
            providers.add(provider)
        raw_state = _safe_event_word(row.get("status"))
        states[raw_state if raw_state in KNOWN_OFFER_STATES else "other"] += 1
        evidence = _rate_limit_evidence(row, now=now)
        if evidence is not None:
            rate_limit_evidence.append(evidence)
    rate_limit_evidence.sort(
        key=lambda item: (item["observed_at"] or "", item["offer_id"]),
        reverse=True,
    )
    return {
        "total": len(models),
        "providers": len(providers),
        "status_counts": dict(sorted(states.items())),
        # The sampler's aggregate cooldown count is intentionally kept
        # separate: it does not expose a per-offer expiry to attribute here.
        "rate_limit_evidence_total": len(rate_limit_evidence),
        "rate_limit_evidence": rate_limit_evidence[:MAX_RATE_LIMIT_EVIDENCE],
    }


def _arena_projection(payload: Mapping[str, Any]) -> dict[str, Any] | None:
    cards = payload.get("models")
    if not isinstance(cards, list):
        return None
    counts: Counter[str] = Counter()
    healthy_offers: list[dict[str, Any]] = []
    healthy_evidence: list[dict[str, Any]] = []
    unhealthy_evidence: list[dict[str, Any]] = []
    for card in cards:
        if not isinstance(card, Mapping):
            continue
        health = card.get("health")
        if not isinstance(health, Mapping):
            continue
        state = _safe_event_word(health.get("state"))
        provider = _safe_identifier(card.get("provider_key"))
        model = _safe_identifier(card.get("model_id"))
        observed = health.get("observed") is True
        fresh = health.get("fresh") is True
        last_checked_at = _safe_timestamp(health.get("last_checked_at"))
        latency_ms = _safe_number(health.get("latency_ms"))

        if state in ARENA_SUMMARY_STATES:
            if state != "healthy" or (observed and fresh):
                counts[state] += 1

        # A "healthy" record must be both observed and fresh.  Conversely,
        # stale and unverified cards are not evidence of an unhealthy route.
        if not provider or not model or last_checked_at is None:
            continue
        evidence = {
            "offer_id": f"{provider}/{model}",
            "provider_key": provider,
            "model_id": model,
            "state": state,
            "observed": observed,
            "fresh": fresh,
            "last_checked_at": last_checked_at,
            "latency_ms": latency_ms,
        }
        if state == "healthy" and observed and fresh:
            healthy_offers.append(
                {
                    "offer_id": evidence["offer_id"],
                    "provider_key": provider,
                    "model_id": model,
                    "last_checked_at": last_checked_at,
                    "latency_ms": latency_ms,
                }
            )
            healthy_evidence.append(evidence)
        elif state in ARENA_OBSERVED_UNHEALTHY_STATES and observed:
            unhealthy_evidence.append(evidence)
    healthy_offers.sort(key=lambda item: (item["provider_key"], item["model_id"]))
    healthy_evidence.sort(key=lambda item: (item["last_checked_at"], item["offer_id"]), reverse=True)
    unhealthy_evidence.sort(key=lambda item: (item["last_checked_at"], item["offer_id"]), reverse=True)
    return {
        "summary": {
            "catalogue_offers": len(cards),
            "fresh_healthy": counts["healthy"],
            "stale": counts["stale"],
            "unverified": counts["unverified"],
            "unavailable": counts["unavailable"],
            "rate_limited": counts["rate_limited"],
        },
        "fresh_healthy_offers": healthy_offers,
        "latest_observed_healthy_evidence": healthy_evidence[0] if healthy_evidence else None,
        "latest_observed_unhealthy_evidence": unhealthy_evidence[0] if unhealthy_evidence else None,
    }


def _modelrelay_component(base_url: str | None, timeout: float) -> dict[str, Any]:
    component: dict[str, Any] = {"reachable": False, "errors": {}}
    if base_url is None:
        component["errors"] = {"sampler": "unsafe_base_url", "models": "unsafe_base_url"}
        return component
    sampler_payload, sampler_error = _get_json(base_url, "/api/health-sampler", timeout)
    models_payload, models_error = _get_json(base_url, "/api/models", timeout)
    errors: dict[str, str] = {}
    sampler = _sampler_projection(sampler_payload) if sampler_payload is not None else None
    offers = _offer_projection(models_payload) if models_payload is not None else None
    if sampler is None:
        errors["sampler"] = sampler_error or "invalid_payload"
    if offers is None:
        errors["models"] = models_error or "invalid_payload"
    component.update({"reachable": not errors, "errors": errors, "sampler": sampler, "offers": offers})
    return component


def _model_arena_component(base_url: str | None, timeout: float) -> dict[str, Any]:
    component: dict[str, Any] = {"reachable": False, "errors": {}}
    if base_url is None:
        component["errors"] = {"model_cards": "unsafe_base_url"}
        return component
    cards_payload, cards_error = _get_json(base_url, "/api/model-cards", timeout)
    projection = _arena_projection(cards_payload) if cards_payload is not None else None
    if projection is None:
        component.update({"errors": {"model_cards": cards_error or "invalid_payload"}})
        return component
    component.update({"reachable": True, "errors": {}, **projection})
    return component


def build_report(
    *,
    relay_url: str = DEFAULT_RELAY_URL,
    arena_url: str = DEFAULT_ARENA_URL,
    timeout: float = 3.0,
) -> tuple[int, dict[str, Any]]:
    """Build the bounded health report and its command exit code.

    Exit code 0 means both contracts are reachable with at least one fresh,
    observed offer.  Code 1 means the contracts are reachable but no fresh
    healthy offer is currently proven.  Code 2 means a required contract is
    unavailable or invalid, so callers must not infer provider health.
    """
    bounded_timeout = min(10.0, max(0.1, float(timeout)))
    modelrelay = _modelrelay_component(_loopback_base_url(relay_url), bounded_timeout)
    model_arena = _model_arena_component(_loopback_base_url(arena_url), bounded_timeout)
    contracts_reachable = modelrelay["reachable"] is True and model_arena["reachable"] is True
    fresh_healthy = 0
    if contracts_reachable:
        fresh_healthy = int(model_arena["summary"]["fresh_healthy"])
    status = "ok" if contracts_reachable and fresh_healthy > 0 else (
        "degraded" if contracts_reachable else "unavailable"
    )
    exit_code = {"ok": 0, "degraded": 1, "unavailable": 2}[status]
    return exit_code, {
        "schema_version": 1,
        "command": "relay-health",
        "generated_at": _utc_now(),
        "read_only": True,
        "provider_inference": False,
        "status": status,
        "modelrelay": modelrelay,
        "model_arena": model_arena,
    }
