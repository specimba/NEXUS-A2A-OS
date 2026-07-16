"""Quota-aware model-team planning commands."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any

from nexus_os.model_relay.provider_budget import DEFAULT_POLICIES, ProviderBudgetLedger


@dataclass(frozen=True)
class ModelTeamPlan:
    role: str
    preferred_provider: str
    preferred_model: str
    fallback_provider: str
    fallback_model: str
    rpm_limit: int
    context_limit: int
    max_tokens: int
    evidence_output: str
    verification_command: str
    promotion_gate: str


ROLE_TEMPLATES: dict[str, dict[str, Any]] = {
    "Planner": {
        "preferred_provider": "longcat",
        "preferred_model": "LongCat-2.0",
        "fallback_provider": "internai",
        "fallback_model": "intern-s2-preview",
        "context_limit": 1_000_000,
        "max_tokens": 16_384,
        "evidence_output": "architecture delta with artifact paths and tests",
        "verification_command": "python -m pytest tests/nexusctl tests/tools -q --tb=short",
        "promotion_gate": "verified delta plus no quota cooldown",
    },
    "Researcher": {
        "preferred_provider": "internai",
        "preferred_model": "intern-s2-preview",
        "fallback_provider": "longcat",
        "fallback_model": "LongCat-2.0",
        "context_limit": 256_000,
        "max_tokens": 8_192,
        "evidence_output": "E1 source card with hash, lane, claim, contradiction status",
        "verification_command": "python -m pytest tests/research -q --tb=short",
        "promotion_gate": "body-derived claim and source-card test",
    },
    "Executor": {
        "preferred_provider": "longcat",
        "preferred_model": "LongCat-2.0",
        "fallback_provider": "internai",
        "fallback_model": "intern-s2-preview",
        "context_limit": 1_000_000,
        "max_tokens": 12_288,
        "evidence_output": "patch proposal with focused test command",
        "verification_command": "python -m pytest tests/bridge tests/nexusclaw -q --tb=short",
        "promotion_gate": "local tests pass before adoption",
    },
    "Verifier": {
        "preferred_provider": "internai",
        "preferred_model": "intern-latest",
        "fallback_provider": "longcat",
        "fallback_model": "LongCat-2.0",
        "context_limit": 256_000,
        "max_tokens": 4_096,
        "evidence_output": "verification matrix with exact commands and failures",
        "verification_command": "python -m pytest tests/ -v --tb=short",
        "promotion_gate": "no done claim without reproduced evidence",
    },
    "Archivist": {
        "preferred_provider": "internai",
        "preferred_model": "intern-s2-preview",
        "fallback_provider": "longcat",
        "fallback_model": "LongCat-2.0",
        "context_limit": 256_000,
        "max_tokens": 8_192,
        "evidence_output": "grounding ledger event and ARCHIVIST source card proposal",
        "verification_command": "python -m pytest tests/grounding -q --tb=short",
        "promotion_gate": "SEMANTIC only for reviewed E1+ cards",
    },
}


def _registry_path() -> Path:
    current = Path.cwd().resolve()
    for path in (current, *current.parents):
        candidate = path / "config" / "models.registry.json"
        if candidate.exists():
            return candidate
    return Path("config/models.registry.json")


def _load_registry() -> dict[str, Any]:
    return json.loads(_registry_path().read_text(encoding="utf-8"))


def _models(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(item.get("id")): item for item in registry.get("models", []) if isinstance(item, dict)}


def _providers(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    providers = registry.get("providers", {})
    if isinstance(providers, dict):
        return {str(key): value for key, value in providers.items() if isinstance(value, dict)}
    return {str(item.get("id")): item for item in providers if isinstance(item, dict)}


def _policy_quota(provider: str, error: str | None = None) -> dict[str, Any]:
    policy = DEFAULT_POLICIES.get(provider, {})
    return {
        "provider": provider,
        "balance_verified": False,
        "enabled": False if error else True,
        "disabled_reason": error,
        "current_rpm": int(policy.get("initial_rpm") or 1),
        "max_rpm": int(policy.get("max_rpm") or policy.get("initial_rpm") or 1),
        "concurrency_limit": int(policy.get("concurrency_limit") or 1),
        "cooldown_remaining_seconds": 0,
        "target_remaining_tokens": policy.get("target_tokens"),
        "daily_budget_tokens": None,
        "fallback_source": "DEFAULT_POLICIES",
    }


def _safe_ledger() -> tuple[ProviderBudgetLedger | None, str | None]:
    try:
        return ProviderBudgetLedger(), None
    except Exception as exc:  # pragma: no cover - host DB permission/debt path
        return None, str(exc)


def _quota_status(ledger: ProviderBudgetLedger | None, provider: str, ledger_error: str | None) -> dict[str, Any]:
    if ledger is None:
        return _policy_quota(provider, ledger_error)
    try:
        return ledger.status(provider)
    except Exception as exc:  # pragma: no cover - host DB permission/debt path
        return _policy_quota(provider, str(exc))


def _plan_for_role(role: str, ledger: ProviderBudgetLedger | None, registry: dict[str, Any], ledger_error: str | None) -> ModelTeamPlan:
    template = ROLE_TEMPLATES[role]
    provider = template["preferred_provider"]
    quota = _quota_status(ledger, provider, ledger_error)
    rpm = min(int(template.get("rpm_limit") or quota["current_rpm"]), int(quota["current_rpm"]))
    return ModelTeamPlan(role=role, rpm_limit=rpm, **template)


def run_model_team(args: Any) -> tuple[int, dict[str, Any]]:
    registry = _load_registry()
    models = _models(registry)
    providers = _providers(registry)
    ledger, ledger_error = _safe_ledger()
    command = args.model_team_command

    if command == "list":
        plans = [_plan_for_role(role, ledger, registry, ledger_error) for role in ROLE_TEMPLATES]
        return 0, {
            "status": "ok",
            "command": "model-team list",
            "roles": [asdict(plan) for plan in plans],
            "active_models": {
                "LongCat-2.0": "LongCat-2.0" in models and models["LongCat-2.0"].get("status") == "active",
                "LongCat-2.0-Preview": "LongCat-2.0-Preview" in models,
                "intern-s2-preview": "intern-s2-preview" in models,
                "intern-latest": "intern-latest" in models,
                "internvl3.5-latest": "internvl3.5-latest" in models,
            },
        }

    if command == "plan":
        role = args.role
        if role not in ROLE_TEMPLATES:
            return 2, {"status": "blocked", "reason": "unknown_role", "role": role}
        plan = _plan_for_role(role, ledger, registry, ledger_error)
        quota = _quota_status(ledger, plan.preferred_provider, ledger_error)
        return 0, {
            "status": "ok",
            "command": "model-team plan",
            "plan": asdict(plan),
            "quota": quota,
            "dispatch_allowed": quota["enabled"] and quota["cooldown_remaining_seconds"] == 0,
        }

    if command == "probe":
        provider = args.provider
        model = args.model
        exists = provider in providers and model in models
        quota = _quota_status(ledger, provider, ledger_error) if provider in providers else None
        return 0 if exists else 2, {
            "status": "ok" if exists else "blocked",
            "command": "model-team probe",
            "dry_run": not args.live,
            "provider": provider,
            "model": model,
            "provider_known": provider in providers,
            "model_known": model in models,
            "live_probe_performed": False,
            "quota": quota,
            "note": "live probes are intentionally operator-gated; this command validates registry and quota route only",
        }

    if command == "swap":
        role = args.role
        if role not in ROLE_TEMPLATES:
            return 2, {"status": "blocked", "reason": "unknown_role", "role": role}
        exists = args.provider in providers and args.model in models
        return 0 if exists else 2, {
            "status": "dry_run" if exists else "blocked",
            "command": "model-team swap",
            "role": role,
            "provider": args.provider,
            "model": args.model,
            "changed": False,
            "operator_review_required": True,
            "reason": None if exists else "provider_or_model_not_registered",
        }

    return 2, {"status": "blocked", "error": f"unknown model-team command: {command}"}




