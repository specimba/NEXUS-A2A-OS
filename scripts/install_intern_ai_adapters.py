"""Install or print secret-free Intern AI adapter configs.

Default mode is a dry run. It never reads the boot token file and never writes
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

from upload.intern_ai_lanes import DEFAULT_BASE_URL, get_intern_ai_lane_report


TEMPLATE_DIR = REPO_ROOT / "nexus_os" / "bridge" / "provider_adapters" / "internai"
LOCAL_TARGETS = {
    "opencode": (TEMPLATE_DIR / "opencode-provider.json", REPO_ROOT / ".opencode" / "providers" / "internai.json"),
    "kilocode": (TEMPLATE_DIR / "kilocode-provider.json", REPO_ROOT / ".kilo" / "providers" / "internai.json"),
    "openclaw": (TEMPLATE_DIR / "openclaw-provider.json", REPO_ROOT / ".openclaw" / "providers" / "internai.json"),
    "hermes": (TEMPLATE_DIR / "hermes-modelrelay-routing.json", REPO_ROOT / ".nexus" / "modelrelay" / "internai-routing.json"),
    "lanes": (TEMPLATE_DIR / "agent-lanes.json", REPO_ROOT / ".nexus" / "providers" / "internai-lanes.json"),
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
        "required": ["INTERN_BASE_URL"],
        "recommended_key_layout": {
            "primary_local_or_modelrelay": "INTERN_API_KEY",
            "shared_external_agents_if_only_one_extra_key": "INTERN_API_KEY_2",
            "dedicated_opencode": "INTERN_OPENCODE_API_KEY",
            "dedicated_kilocode": "INTERN_KILOCODE_API_KEY",
            "dedicated_hermes": "INTERN_HERMES_API_KEY",
            "dedicated_openclaw": "INTERN_CLAW_API_KEY",
            "dedicated_zo_cloud": "INTERN_ZO_API_KEY",
        },
        "openclaw_onboard": {
            "provider_type": "custom-openai-compatible",
            "base_url": DEFAULT_BASE_URL,
            "model": "intern-s2-preview",
            "api_key_env_preference": ["INTERN_CLAW_API_KEY", "INTERN_ZO_API_KEY", "INTERN_API_KEY_2"],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Install or print Intern AI adapter configs")
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
        "provider": "internai",
        "dry_run": not args.write_local,
        "templates_dir": str(TEMPLATE_DIR),
        "install_plan": install_plan,
        "lane_readiness": get_intern_ai_lane_report(),
        "zo_secret_plan": zo_secret_plan(),
        "secret_policy": "No token values are read, printed, or written by this script.",
    }

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=True))
        return 0

    print(f"Intern AI adapter install plan ({'dry-run' if report['dry_run'] else 'write-local'})")
    for name, item in install_plan.items():
        print(f"- {name}: {item['action']} {item['target']}")
    print("- secrets: set env vars in local .env or Zo secrets; this script does not write them")
    print("- Zo/OpenClaw: onboard as custom OpenAI-compatible, base URL "
          f"{DEFAULT_BASE_URL}, model intern-s2-preview")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
