"""Install or print secret-free LongCat adapter configs.

Default mode is a dry run. It never reads any boot token file and never writes
secret values. Use --write-local to copy templates into repo-local agent config
folders for manual review before any tool consumes them.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from upload.longcat_lanes import DEFAULT_BASE_URL, get_longcat_lane_report


TEMPLATE_DIR = REPO_ROOT / "nexus_os" / "bridge" / "provider_adapters" / "longcat"
LOCAL_TARGETS = {
    "opencode": (TEMPLATE_DIR / "opencode-provider.json", REPO_ROOT / ".opencode" / "providers" / "longcat.json"),
    "kilocode": (TEMPLATE_DIR / "kilocode-provider.json", REPO_ROOT / ".kilo" / "providers" / "longcat.json"),
    "openclaw": (TEMPLATE_DIR / "openclaw-provider.json", REPO_ROOT / ".openclaw" / "providers" / "longcat.json"),
    "hermes": (TEMPLATE_DIR / "hermes-modelrelay-routing.json", REPO_ROOT / ".nexus" / "modelrelay" / "longcat-routing.json"),
    "lanes": (TEMPLATE_DIR / "agent-lanes.json", REPO_ROOT / ".nexus" / "providers" / "longcat-lanes.json"),
}


def copy_template(source: Path, target: Path, write: bool) -> dict[str, Any]:
    target = target.resolve()
    if not str(target).startswith(str(REPO_ROOT.resolve())):
        raise RuntimeError(f"Refusing to write outside repo: {target}")

    action = "would_write"
    if write:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        action = "wrote"

    return {
        "action": action,
        "source": str(source),
        "target": str(target),
    }


def zo_secret_plan() -> dict[str, Any]:
    return {
        "base_url": DEFAULT_BASE_URL,
        "required": ["NEXUS_LONGCAT_API_KEY"],
        "recommended_key_layout": {
            "primary_local_or_modelrelay": "LONGCAT_API_KEY",
            "shared_external_agents": "NEXUS_LONGCAT_API_KEY",
            "dedicated_opencode": "LONGCAT_OPENCODE_API_KEY",
            "dedicated_kilocode": "LONGCAT_KILOCODE_API_KEY",
            "dedicated_hermes": "LONGCAT_HERMES_API_KEY",
            "dedicated_openclaw": "LONGCAT_CLAW_API_KEY",
            "dedicated_zo_cloud": "LONGCAT_ZO_API_KEY",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Install or print LongCat adapter configs")
    parser.add_argument(
        "--surface",
        choices=["all", *LOCAL_TARGETS.keys()],
        default="all",
        help="Adapter surface to process",
    )
    parser.add_argument("--write-local", action="store_true", help="Write repo-local adapter copies")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    args = parser.parse_args()

    selected = LOCAL_TARGETS if args.surface == "all" else {args.surface: LOCAL_TARGETS[args.surface]}
    install_plan = {
        name: copy_template(source, target, write=args.write_local)
        for name, (source, target) in selected.items()
    }

    report = {
        "provider": "longcat",
        "dry_run": not args.write_local,
        "templates_dir": str(TEMPLATE_DIR),
        "install_plan": install_plan,
        "lane_readiness": get_longcat_lane_report(),
        "zo_secret_plan": zo_secret_plan(),
        "secret_policy": "No token values are read, printed, or written by this script.",
    }

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=True))
        return 0

    print(f"LongCat adapter install plan ({'dry-run' if report['dry_run'] else 'write-local'})")
    for name, item in install_plan.items():
        print(f"- {name}: {item['action']} {item['target']}")
    print("- secrets: set env vars in local .env or Zo secrets; this script does not write them")
    print("- Zo/OpenClaw: onboard as custom OpenAI-compatible, base URL "
          f"{DEFAULT_BASE_URL}, model LongCat-2.0-Preview")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
