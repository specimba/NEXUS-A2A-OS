"""Top-level NEXUS OS exports with lazy loading for optional subsystems."""

from __future__ import annotations

from importlib import import_module
from typing import Any

__version__ = "1.0.0"

_EXPORTS = {
    "TokenGuard": (".monitoring.token_guard", "TokenGuard"),
    "LocalCounter": (".monitoring.counters", "LocalCounter"),
    "NativeCounter": (".monitoring.counters", "NativeCounter"),
    "TokscaleCounter": (".monitoring.counters", "TokscaleCounter"),
    "SemanticCache": (".monitoring.strategies", "SemanticCache"),
    "hot_path": (".monitoring.strategies", "hot_path"),
    "warm_path": (".monitoring.strategies", "warm_path"),
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
