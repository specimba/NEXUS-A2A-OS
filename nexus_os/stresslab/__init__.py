"""NEXUS OS Stress Lab package with lazy exports."""

from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORTS: dict[str, tuple[str, str]] = {
    "ChainIntegrityError": (".cloud_report_bee", "ChainIntegrityError"),
    "CloudAttackBeeV2": (".cloud_attack_bee_v2", "CloudAttackBeeV2"),
    "CloudReportBee": (".cloud_report_bee", "CloudReportBee"),
    "CloudSwarmOrchestrator": (".cloud_swarm_orchestrator", "CloudSwarmOrchestrator"),
    "ISCRunner": (".isc_runner", "ISCRunner"),
    "ISCTemplate": (".isc_runner", "ISCTemplate"),
    "ISCResult": (".isc_runner", "ISCResult"),
    "TokenBudgetGuard": (".cloud_swarm_orchestrator", "TokenBudgetGuard"),
}

__all__ = list(_EXPORTS)


def __getattr__(name: str) -> Any:
    try:
        module_name, attr_name = _EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc
    module = import_module(module_name, __name__)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
