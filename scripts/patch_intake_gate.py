"""Read-only gate for externally generated patch artifacts.

This script verifies local patch provenance before any agent runs
``git apply``. It intentionally does not apply or mutate files.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any


SHA256_RE = re.compile(r"\b[a-fA-F0-9]{64}\b")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_sha256_file(path: Path) -> str | None:
    text = path.read_text(encoding="utf-8", errors="replace")
    match = SHA256_RE.search(text)
    return match.group(0).lower() if match else None


def run_git_apply_check(repo: Path, patch: Path) -> dict[str, Any]:
    proc = subprocess.run(
        ["git", "apply", "--check", str(patch)],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    patch = Path(args.patch).resolve()
    repo = Path(args.repo).resolve()
    report: dict[str, Any] = {
        "patch_path": str(patch),
        "repo": str(repo),
        "exists": patch.exists(),
        "checks": {},
        "ok": False,
    }

    errors: list[str] = []
    if not patch.exists():
        errors.append("patch file does not exist")
        report["errors"] = errors
        return report
    if not patch.is_file():
        errors.append("patch path is not a file")
        report["errors"] = errors
        return report

    actual_sha = sha256_file(patch)
    actual_bytes = patch.stat().st_size
    report["sha256"] = actual_sha
    report["bytes"] = actual_bytes

    if args.expected_sha256 and actual_sha != args.expected_sha256.lower():
        errors.append("expected sha256 mismatch")
    if args.expected_bytes is not None and actual_bytes != args.expected_bytes:
        errors.append("expected byte count mismatch")

    if args.sha256_file:
        sha_path = Path(args.sha256_file).resolve()
        report["sha256_file"] = str(sha_path)
        if not sha_path.exists():
            errors.append("sha256 sidecar file does not exist")
        else:
            sidecar_sha = parse_sha256_file(sha_path)
            report["sidecar_sha256"] = sidecar_sha
            if sidecar_sha != actual_sha:
                errors.append("sha256 sidecar mismatch")

    if args.apply_check:
        report["checks"]["git_apply_check"] = run_git_apply_check(repo, patch)
        if not report["checks"]["git_apply_check"]["ok"]:
            errors.append("git apply --check failed")

    report["errors"] = errors
    report["ok"] = not errors
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify patch artifact before application.")
    parser.add_argument("patch", help="Patch file path to verify.")
    parser.add_argument("--repo", default=".", help="Repository root for git apply --check.")
    parser.add_argument("--sha256-file", help="Optional .sha256 sidecar file.")
    parser.add_argument("--expected-sha256", help="Expected SHA256 hex digest.")
    parser.add_argument("--expected-bytes", type=int, help="Expected byte count.")
    parser.add_argument("--apply-check", action="store_true", help="Run git apply --check.")
    args = parser.parse_args()

    report = build_report(args)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
