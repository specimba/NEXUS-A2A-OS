"""Build a redacted DoppelGround gitleaks false-positive ledger."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

RUN_TOKEN_RE = re.compile(r"DR-\d{2}_\d{8}_\d{6}_\d+_[0-9a-fA-F]+")


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _redact_run_tokens(value: str, replacement: str) -> str:
    return RUN_TOKEN_RE.sub(replacement, value)


def _classify(finding: dict[str, Any]) -> str:
    path = str(finding.get("File", ""))
    secret = str(finding.get("Secret", ""))
    if "drill_runs" in path.replace("\\", "/") and RUN_TOKEN_RE.search(secret):
        return "likely_false_positive"
    return "needs_review"


def build_ledger(report_path: str | Path, source: str = "gitleaks") -> dict[str, Any]:
    """Return a secret-redacted ledger for a gitleaks JSON report."""
    report_file = Path(report_path)
    findings = json.loads(report_file.read_text(encoding="utf-8"))
    if not isinstance(findings, list):
        raise ValueError("gitleaks report must be a JSON list")

    entries: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        secret = str(finding.get("Secret", ""))
        file_path = str(finding.get("File", ""))
        match = str(finding.get("Match", ""))
        classification = _classify(finding)
        counts[classification] = counts.get(classification, 0) + 1
        entries.append(
            {
                "rule_id": finding.get("RuleID"),
                "classification": classification,
                "source": source,
                "commit": finding.get("Commit"),
                "start_line": finding.get("StartLine"),
                "secret_sha256": _sha256_text(secret) if secret else "",
                "file_sha256": _sha256_text(file_path) if file_path else "",
                "file_redacted": _redact_run_tokens(file_path, "[RUN_TOKEN_REDACTED]"),
                "redacted_match": _redact_run_tokens(match.replace(secret, "[REDACTED]"), "[REDACTED]"),
            }
        )

    return {
        "schema_version": "nexus-doppelground-false-positive-ledger-v1",
        "source": source,
        "report": str(report_file),
        "classification_counts": counts,
        "entries": entries,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report")
    parser.add_argument("--source", default="gitleaks")
    parser.add_argument("--out")
    args = parser.parse_args()

    ledger = build_ledger(args.report, args.source)
    payload = json.dumps(ledger, indent=2, sort_keys=True)
    if args.out:
        Path(args.out).write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)


if __name__ == "__main__":
    main()
