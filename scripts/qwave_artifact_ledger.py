"""Summarize QWAVE/TWAVE artifact files as evidence records."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _json_summary(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"json_ok": False, "error": str(exc)}
    if not isinstance(data, dict):
        return {"json_ok": True, "type": type(data).__name__}

    summary: dict[str, Any] = {"json_ok": True}
    for key in ("status", "model", "chi", "score", "passed", "failed", "total"):
        if key in data:
            summary[key] = data[key]
    summary["key_count"] = len(data)
    return summary


def build_ledger(root: str | Path) -> dict[str, Any]:
    base = Path(root)
    artifacts: list[dict[str, Any]] = []
    for path in sorted(base.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(base).as_posix()
        item: dict[str, Any] = {
            "path": rel,
            "size": path.stat().st_size,
            "sha256": _sha256(path),
        }
        if path.suffix.lower() == ".json":
            item["json_summary"] = _json_summary(path)
        artifacts.append(item)
    return {
        "schema_version": "nexus-qwave-artifact-ledger-v1",
        "root": str(base),
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root")
    parser.add_argument("--out")
    args = parser.parse_args()
    ledger = build_ledger(args.root)
    payload = json.dumps(ledger, indent=2, sort_keys=True)
    if args.out:
        Path(args.out).write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)


if __name__ == "__main__":
    main()
