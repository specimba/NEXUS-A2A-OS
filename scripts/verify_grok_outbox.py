#!/usr/bin/env python3
# CANARY: 5b8ef49aa086c508f5950d3928a09fc2
"""Validate Grok burst-harness outbox artifacts.

This verifier is intentionally structural. It accepts proposal packets only
when they stay inside the outbox, include evidence, and avoid obvious secret
patterns. It does not approve the underlying technical content.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTBOX = ROOT / "docs" / "handoff" / "grok-longrun" / "outbox"

SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"sk-or-v1-[A-Za-z0-9_-]{20,}"),
    re.compile(r"ghp_[A-Za-z0-9_]{20,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{20,}"),
    re.compile(r"(?i)(api[_-]?key|auth[_-]?token|secret)\s*[:=]\s*['\"]?[A-Za-z0-9_.-]{16,}"),
]

REQUIRED_KEYS = {
    "task_id",
    "status",
    "artifacts",
    "evidence",
    "self_check",
    "next_recommended_task",
}

ALLOWED_STATUS = {"proposed", "blocked", "needs_review"}


def _is_relative_to(path: Path, base: Path) -> bool:
    try:
        path.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False


def _contains_secret(text: str) -> bool:
    return any(pattern.search(text) for pattern in SECRET_PATTERNS)


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("evidence JSON must be an object")
    return payload


def validate_packet(evidence_path: Path, outbox: Path) -> list[str]:
    errors: list[str] = []

    try:
        payload = _load_json(evidence_path)
    except Exception as exc:
        return [f"{evidence_path}: invalid JSON: {exc}"]

    missing = REQUIRED_KEYS - set(payload)
    if missing:
        errors.append(f"{evidence_path}: missing keys {sorted(missing)}")

    status = payload.get("status")
    if status not in ALLOWED_STATUS:
        errors.append(f"{evidence_path}: invalid status {status!r}")

    task_id = payload.get("task_id")
    if not isinstance(task_id, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+", task_id):
        errors.append(f"{evidence_path}: invalid task_id")

    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        errors.append(f"{evidence_path}: artifacts must be a non-empty list")
        artifacts = []

    evidence = payload.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        errors.append(f"{evidence_path}: evidence must be a non-empty list")

    self_check = payload.get("self_check")
    if not isinstance(self_check, list) or not self_check:
        errors.append(f"{evidence_path}: self_check must be a non-empty list")

    packet_files = [evidence_path]
    for artifact in artifacts:
        if not isinstance(artifact, str):
            errors.append(f"{evidence_path}: artifact path must be a string")
            continue
        artifact_path = (ROOT / artifact).resolve()
        if not _is_relative_to(artifact_path, outbox):
            errors.append(f"{evidence_path}: artifact outside outbox: {artifact}")
            continue
        if not artifact_path.exists():
            errors.append(f"{evidence_path}: missing artifact: {artifact}")
            continue
        packet_files.append(artifact_path)

    for packet_file in packet_files:
        try:
            text = packet_file.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            errors.append(f"{packet_file}: unreadable: {exc}")
            continue
        if _contains_secret(text):
            errors.append(f"{packet_file}: possible raw secret pattern")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Grok long-run outbox packets.")
    parser.add_argument("--outbox", default=str(DEFAULT_OUTBOX), help="Outbox directory to scan.")
    args = parser.parse_args(argv)

    outbox = Path(args.outbox).resolve()
    if not outbox.exists():
        print(json.dumps({"status": "ok", "checked": 0, "errors": []}, indent=2))
        return 0

    evidence_files = sorted(outbox.glob("*.evidence.json"))
    errors: list[str] = []
    for evidence_path in evidence_files:
        errors.extend(validate_packet(evidence_path.resolve(), outbox))

    payload = {
        "status": "ok" if not errors else "failed",
        "checked": len(evidence_files),
        "errors": errors,
    }
    print(json.dumps(payload, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
