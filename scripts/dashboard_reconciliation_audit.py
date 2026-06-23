"""Read-only dashboard reconciliation audit.

Compares high-value sandbox claims against the local checkout without applying
patches or starting services.
"""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

EXPECTED_FILES = {
    "panel_status_component": "src/components/nexus/panel-status.tsx",
    "panel_status_hook": "src/hooks/use-panel-status.ts",
    "brain_api_contract": "src/lib/brain-api/contract.ts",
    "brain_api_client": "src/lib/brain-api/client.ts",
    "brain_status_tab": "src/components/nexus/tabs/brain-status-tab.tsx",
    "panel_status_route": "src/app/api/panel-status/route.ts",
}

STALE_PATTERNS = {
    "glm_47": re.compile(r"glm-4\.7|glm-4-7", re.IGNORECASE),
    "7352_modelrelay": re.compile(r"(7352[^\n]{0,80}ModelRelay|ModelRelay[^\n]{0,80}7352)", re.IGNORECASE),
}


def scan_text_files(paths: list[Path]) -> dict[str, list[dict[str, object]]]:
    hits: dict[str, list[dict[str, object]]] = {key: [] for key in STALE_PATTERNS}
    for path in paths:
        if not path.exists() or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for idx, line in enumerate(text.splitlines(), start=1):
            for key, pattern in STALE_PATTERNS.items():
                if pattern.search(line):
                    hits[key].append({
                        "path": str(path.relative_to(ROOT)),
                        "line": idx,
                        "text": line.strip()[:180],
                    })
    return hits


def main() -> int:
    expected = {
        key: {
            "path": value,
            "exists": (ROOT / value).exists(),
        }
        for key, value in EXPECTED_FILES.items()
    }

    scan_roots = [
        ROOT / "AGENTS.md",
        ROOT / "01_PROJECT_STATE.md",
        ROOT / "knowledge.md",
        *list((ROOT / "src").rglob("*.ts")),
        *list((ROOT / "src").rglob("*.tsx")),
        *list((ROOT / "nexus_os").rglob("*.py")),
        *list((ROOT / "docs").glob("*.md")),
        *list((ROOT / "docs" / "handbook").glob("*.md")),
    ]
    stale_hits = scan_text_files(scan_roots)
    missing = [key for key, item in expected.items() if not item["exists"]]
    stale_count = sum(len(v) for v in stale_hits.values())

    report = {
        "repo": str(ROOT),
        "expected_files": expected,
        "missing_expected_files": missing,
        "stale_hits": stale_hits,
        "ok": not missing and stale_count == 0,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
