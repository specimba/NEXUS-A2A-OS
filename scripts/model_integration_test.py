"""Unified NEXUS model integration tester.

Tests Intern AI and LongCat provider readiness, lane resolution,
dry-run config, and optional live probe surface.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from typing import Any, Iterable

# Ensure local repo import paths are available when run from scripts/
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _sub in ["upload", "nexus_os/bridge/provider_adapters"]:
    _p = os.path.join(REPO_ROOT, _sub)
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from intern_ai_lanes import get_intern_ai_lane_report as _intern_report
except Exception as exc:  # pragma: no cover
    _intern_report = None

try:
    from longcat_lanes import get_longcat_lane_report as _longcat_report
except Exception as exc:  # pragma: no cover
    _longcat_report = None


@dataclass(frozen=True)
class SurfaceCheck:
    provider: str
    lane: str
    surface: str
    key_env: str
    key_found: bool
    default_model: str
    ready: bool


def _iter_env_vars(order: Iterable[str]) -> list[str]:
    return list(order)


def _key_found(env_order: Iterable[str]) -> tuple[bool, str | None]:
    for name in env_order:
        if os.environ.get(name):
            return True, name
    return False, None


def intern_surface_checks() -> list[SurfaceCheck]:
    checks: list[SurfaceCheck] = []
    if _intern_report is None:
        return checks
    report = _intern_report()
    for lane_name, data in report.items():
        checks.append(
            SurfaceCheck(
                provider="internai",
                lane=lane_name,
                surface=str(data.get("surface") or ""),
                key_env=str(data.get("active_env") or ""),
                key_found=bool(data.get("ready")),
                default_model=str(data.get("default_model") or ""),
                ready=bool(data.get("ready")),
            )
        )
    return checks


def longcat_surface_checks() -> list[SurfaceCheck]:
    checks: list[SurfaceCheck] = []
    if _longcat_report is None:
        return checks
    report = _longcat_report()
    for lane_name, data in report.items():
        checks.append(
            SurfaceCheck(
                provider="longcat",
                lane=lane_name,
                surface=str(data.get("surface") or ""),
                key_env=str(data.get("active_env") or ""),
                key_found=bool(data.get("ready")),
                default_model=str(data.get("default_model") or ""),
                ready=bool(data.get("ready")),
            )
        )
    return checks


def provider_report() -> dict[str, Any]:
    return {
        "internai": {
            "lanes": [_lane_summary(c) for c in intern_surface_checks()],
            "models": [
                {"id": "intern-s2-preview", "thinking_mode_default": True},
                {"id": "intern-latest", "thinking_mode_default": False},
                {"id": "internvl2.5-latest", "vision": True},
            ],
        },
        "longcat": {
            "lanes": [_lane_summary(c) for c in longcat_surface_checks()],
            "models": [{"id": "LongCat-2.0-Preview", "context": 1_000_000}],
        },
    }


def _lane_summary(c: SurfaceCheck) -> dict[str, Any]:
    return {
        "provider": c.provider,
        "lane": c.lane,
        "surface": c.surface,
        "key_env": c.key_env,
        "key_found": c.key_found,
        "default_model": c.default_model,
        "ready": c.ready,
    }


def pretty_report() -> str:
    data = provider_report()
    lines: list[str] = []
    for provider, meta in data.items():
        lines.append(f"[{provider}]")
        for lane in meta.get("lanes", []):
            status = "READY" if lane["ready"] else "MISSING"
            lines.append(
                f"  {lane['lane']:10} | {lane['surface']:28} | "
                f"env={lane['key_env'] or '(none)':28} | {status}"
            )
        lines.append("  models:")
        for m in meta.get("models", []):
            lines.append(f"    - {m['id']}")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="NEXUS provider integration checker")
    parser.add_argument("--json", action="store_true", help="Emit JSON report")
    parser.add_argument("--live", action="store_true", help="Include live HTTP probe")
    parser.add_argument("--model", default="", help="Override model name for live probe")
    args = parser.parse_args()

    if args.json:
        print(json.dumps(provider_report(), indent=2, sort_keys=True))
        return 0

    print(pretty_report())
    if args.live:
        print("Live HTTP probe is not implemented in this minimal surface.")
        print("Use scripts/intern_ai_provider_check.py --live when available.")
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
