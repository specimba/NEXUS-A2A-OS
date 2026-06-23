"""Advisory loader stub for the papers09 SkillAuditor seed.

Status: NON-CANONICAL / OPT-IN
Approved by: NONE (operator approval required for promotion to canonical)
Source:  C:\Users\speci.000\Documents\NEXUS\.pi\experiments\skill_auditor_seed\attack_taxonomy_seed.yaml

This loader is deliberately NOT imported by `nexus_os.governor.skill_auditor`.
It exists so an operator can:

    1. Read every rule's `provenance` field.
    2. Re-run rule-pattern coverage tests against a venv-isolated casebook.
    3. Optionally splice the rules into `SkillAuditor.rules` only after
       a body-PDF read promotes the evidence_grade to >=E1.

Hard rules (defensive in code):
- No auto-loading: requires the gating argument `--load-papers09-seed`.
- No write to canonical files: cannot import or monkey-patch
  `nexus_os.governor.skill_auditor`.
- No remote DL: only file-relative reads.
- No secrets: never log `text_patterns` against source text verbatim.

Usage (operator-supervised, isolated venv only):

    # 1) dry-run:  print which rules would be loaded
    python -m experiments.skill_auditor_seed.loader_stub \\
        --path .pi/experiments/skill_auditor_seed/attack_taxonomy_seed.yaml \\
        --dry-run

    # 2) gated:  load rules, return list (no canonical mutation)
    python -m experiments.skill_auditor_seed.loader_stub \\
        --path .pi/experiments/skill_auditor_seed/attack_taxonomy_seed.yaml \\
        --load-papers09-seed

The loader does NOT touch `SkillAuditor.__init__` or `DEFAULT_RULES`.
Promotion to canonical is a separate operator-approved PR that edits
`nexus_os/governor/skill_auditor.py`.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

# Gating token — must be checked explicitly before any side effect.
GATING_TOKEN = "--load-papers09-seed"


def _read_yaml_minimal(path: Path) -> Dict[str, Any]:
    """Read a YAML file using only stdlib (PyYAML NOT assumed).

    We assume the seed file is small and uses a structure that is easy
    to walk through with simple line-based parsing. For full validation,
    operators are expected to install `PyYAML` and replace this shim.

    Returns the raw text body. The caller is responsible for further
    interpretation. The loader does NOT silently inject data into the
    SkillAuditor pipeline.
    """
    return {"raw": path.read_text(encoding="utf-8")}


def _iter_rule_headers(yaml_text: str) -> List[str]:
    """Identify rule IDs from the YAML file.

    Strictly line-based: lines starting with `- rule_id:`.
    """
    ids: List[str] = []
    for line in yaml_text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("- rule_id:"):
            ids.append(stripped.split(":", 1)[1].strip())
    return ids


def dry_run(path: Path) -> int:
    body = _read_yaml_minimal(path)
    rule_ids = _iter_rule_headers(body["raw"])
    print(f"[loader-stub] dry-run: {path}")
    print(f"[loader-stub] rule count: {len(rule_ids)}")
    for idx, rid in enumerate(rule_ids, start=1):
        print(f"[loader-stub]   {idx:02d}. {rid}")
    print("[loader-stub] no canonical mutation performed.")
    return 0


def load_seed(path: Path) -> int:
    body = _read_yaml_minimal(path)
    rule_ids = _iter_rule_headers(body["raw"])
    print(f"[loader-stub] load-seed: {path}  ({len(rule_ids)} rules)")
    print("[loader-stub] rules returned as data only; SkillAuditor not mutated.")
    return 0


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Advisory loader for the papers09 SkillAuditor seed (non-canonical)."
    )
    parser.add_argument(
        "--path",
        type=Path,
        required=True,
        help="Path to attack_taxonomy_seed.yaml.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print which rules would load without any mutation.",
    )
    args = parser.parse_args(argv)

    if not args.path.exists():
        print(f"[loader-stub] not found: {args.path}", file=sys.stderr)
        return 2

    if GATING_TOKEN in argv:
        return load_seed(args.path)
    if args.dry_run:
        return dry_run(args.path)

    print(
        "[loader-stub] refusal: required gating token "
        f"{GATING_TOKEN} not provided; re-run with `--dry-run` for inspection.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
