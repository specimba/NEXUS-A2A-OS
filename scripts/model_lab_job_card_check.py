"""Validate governed NEXUS model-lab job cards."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "nexus-model-lab-job-card-v1"
HASH_RE = re.compile(r"^[0-9a-fA-F]{64}$")
SECRET_RE = re.compile(
    r"(sk-[A-Za-z0-9_-]{8,}|AIza[0-9A-Za-z_-]{10,}|xox[baprs]-|ghp_[A-Za-z0-9_]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)"
)


def _walk_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        out: list[str] = []
        for child in value.values():
            out.extend(_walk_strings(child))
        return out
    if isinstance(value, list):
        out = []
        for child in value:
            out.extend(_walk_strings(child))
        return out
    return []


def _require_dict(card: dict[str, Any], key: str, errors: list[str]) -> dict[str, Any]:
    value = card.get(key)
    if not isinstance(value, dict):
        errors.append(f"{key} must be an object")
        return {}
    return value


def validate_card(card: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if card.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    operation = card.get("operation")
    if operation not in {"eval_only", "fine_tune", "merge", "compression"}:
        errors.append("operation must be eval_only, fine_tune, merge, or compression")

    for key in ("job_id", "created_at", "status", "objective"):
        if not card.get(key):
            errors.append(f"{key} is required")

    dataset = _require_dict(card, "dataset", errors)
    recipe = _require_dict(card, "recipe", errors)
    resource_policy = _require_dict(card, "resource_policy", errors)
    safety_gates = _require_dict(card, "safety_gates", errors)
    outputs = _require_dict(card, "outputs", errors)
    _require_dict(card, "approvals", errors)

    for path, value in (
        ("dataset.hash_sha256", dataset.get("hash_sha256")),
        ("recipe.hash_sha256", recipe.get("hash_sha256")),
    ):
        if not isinstance(value, str) or not HASH_RE.match(value):
            errors.append(f"{path} must be a 64-character sha256 hex string")

    if not outputs.get("target_dir"):
        errors.append("outputs.target_dir is required")
    if outputs.get("registry_action") not in {"evidence_only", "register_candidate"}:
        errors.append("outputs.registry_action must be evidence_only or register_candidate")

    if operation in {"fine_tune", "merge", "compression"}:
        if resource_policy.get("protected_workloads_ack") is not True:
            errors.append("resource_policy.protected_workloads_ack must be true")
        for gate in ("guard_eval_required", "rollback_required", "human_approval_required"):
            if safety_gates.get(gate) is not True:
                errors.append(f"safety_gates.{gate} must be true")

    for text in _walk_strings(card):
        if SECRET_RE.search(text):
            errors.append("card contains secret-shaped value")
            break

    return {
        "schema_version": SCHEMA_VERSION,
        "passed": not errors,
        "operation": operation,
        "errors": errors,
    }


def validate_file(path: str | Path) -> dict[str, Any]:
    card_path = Path(path)
    data = json.loads(card_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("job card must be a JSON object")
    report = validate_card(data)
    report["path"] = str(card_path)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--card", required=True)
    parser.add_argument("--out")
    args = parser.parse_args()
    report = validate_file(args.card)
    payload = json.dumps(report, indent=2, sort_keys=True)
    if args.out:
        Path(args.out).write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
