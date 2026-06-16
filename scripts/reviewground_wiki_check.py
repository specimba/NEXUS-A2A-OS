#!/usr/bin/env python3
"""Validate the local ReviewGround wiki workspace.

CANARY_TOKEN: 2e3dae25e109bff3daed3210cffe3a8f
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REQUIRED_PUBLISHED_FIELDS = {
    "id",
    "title",
    "truth_layer",
    "source_sha256",
    "evidence_quality",
    "review_status",
}
WIKI_LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


def parse_frontmatter(text: str) -> dict[str, str] | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end == -1:
        return None
    fields: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" not in line or line.strip().startswith("#"):
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip().strip('"')
    return fields


def check_wiki(root: Path) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    markdown_files = sorted(root.rglob("*.md")) if root.exists() else []
    existing_stems = {path.stem for path in markdown_files}

    required_dirs = ["raw", "briefs", "drafts", "published", "graph", "obsidian"]
    for rel in required_dirs:
        if not (root / rel).exists():
            issues.append({"severity": "error", "file": rel, "issue": "missing required wiki directory"})

    for path in markdown_files:
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        frontmatter = parse_frontmatter(text)

        if rel.startswith("published/"):
            if frontmatter is None:
                issues.append({"severity": "error", "file": rel, "issue": "published page missing frontmatter"})
            else:
                missing = sorted(REQUIRED_PUBLISHED_FIELDS - set(frontmatter))
                if missing:
                    issues.append(
                        {
                            "severity": "error",
                            "file": rel,
                            "issue": "published page missing required frontmatter",
                            "fields": missing,
                        }
                    )

        for target in WIKI_LINK_RE.findall(text):
            target_stem = target.split("|", 1)[0].split("#", 1)[0].strip()
            if target_stem and target_stem not in existing_stems:
                issues.append(
                    {
                        "severity": "warning",
                        "file": rel,
                        "issue": "unresolved wiki link",
                        "target": target_stem,
                    }
                )

    passed = sum(1 for issue in issues if issue["severity"] != "error") == len(issues)
    return {
        "schema_version": "reviewground-wiki-check-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "passed": passed,
        "total_markdown": len(markdown_files),
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", required=True, type=Path, help="docs/wiki workspace path")
    parser.add_argument("--out", type=Path, help="Optional JSON report path")
    args = parser.parse_args()

    report = check_wiki(args.dir)
    payload = json.dumps(report, indent=2, sort_keys=True)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload, encoding="utf-8")
        print(f"wrote wiki check: {args.out} passed={report['passed']} issues={len(report['issues'])}")
    else:
        print(payload)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
