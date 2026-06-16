"""Research intake manifest, VAP record, and Lane B summary helpers."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _components(text: str) -> list[str]:
    lowered = text.lower()
    components: list[str] = []
    if "guard plane" in lowered or "adversarial" in lowered or "guard" in lowered:
        components.append("guard_plane")
    if "trust" in lowered or "governance" in lowered:
        components.append("trust_kernel")
    if "mcp" in lowered:
        components.append("mcp")
    if not components:
        components.append("research_intake")
    return components


def _proposal(components: list[str]) -> dict[str, str]:
    if "guard_plane" in components:
        return {"type": "guard_plane_candidate", "lane": "Lane B - Active Diagnosis"}
    return {"type": "research_evidence", "lane": "Lane A - Reconcile"}


def build_manifest(base_dir: str | Path, artifacts: list[str]) -> dict[str, Any]:
    base = Path(base_dir)
    items: list[dict[str, Any]] = []
    missing: list[str] = []
    for rel in artifacts:
        path = base / rel
        if not path.exists() or not path.is_file():
            missing.append(rel)
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        comps = _components(text)
        items.append(
            {
                "path": rel,
                "size": path.stat().st_size,
                "sha256": _sha256(path),
                "components": comps,
                "proposal": _proposal(comps),
            }
        )
    return {
        "schema_version": "nexus-research-intake-manifest-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_dir": str(base),
        "artifact_count": len(items),
        "missing_artifacts": missing,
        "artifacts": items,
    }


def validate_manifest(manifest: dict[str, Any], base_dir: str | Path) -> dict[str, Any]:
    errors: list[str] = []
    if manifest.get("schema_version") != "nexus-research-intake-manifest-v1":
        errors.append("invalid schema_version")
    for missing in manifest.get("missing_artifacts", []):
        errors.append(f"missing artifact: {missing}")
    base = Path(base_dir)
    for item in manifest.get("artifacts", []):
        path = base / item.get("path", "")
        if not path.exists():
            errors.append(f"artifact vanished: {item.get('path')}")
        elif _sha256(path) != item.get("sha256"):
            errors.append(f"sha256 mismatch: {item.get('path')}")
    return {"passed": not errors, "errors": errors, "artifact_count": manifest.get("artifact_count", 0)}


def write_vap_records(manifest: dict[str, Any], out_path: str | Path) -> dict[str, Any]:
    output = Path(out_path)
    previous = "0" * 64
    lines: list[str] = []
    for item in manifest.get("artifacts", []):
        record = {
            "record_type": "research_intake_vap",
            "path": item["path"],
            "sha256": item["sha256"],
            "components": item["components"],
            "previous_hash": previous,
        }
        record_payload = json.dumps(record, sort_keys=True)
        current = hashlib.sha256(record_payload.encode("utf-8")).hexdigest()
        record["record_hash"] = current
        previous = current
        lines.append(json.dumps(record, sort_keys=True))
    output.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return {"record_count": len(lines), "chain_integrity": True, "path": str(output)}


def write_lane_b_summary(manifest: dict[str, Any], vap_report: dict[str, Any], out_path: str | Path) -> dict[str, Any]:
    output = Path(out_path)
    lines = [
        "# Lane B - Active Diagnosis",
        "",
        f"Artifacts: {manifest.get('artifact_count', 0)}",
        f"VAP records: {vap_report.get('record_count', 0)}",
        "",
    ]
    for item in manifest.get("artifacts", []):
        lines.append(f"- `{item['path']}` -> {', '.join(item['components'])}")
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"artifact_count": manifest.get("artifact_count", 0), "path": str(output)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_dir")
    parser.add_argument("artifacts", nargs="+")
    parser.add_argument("--manifest-out")
    args = parser.parse_args()
    manifest = build_manifest(args.base_dir, args.artifacts)
    payload = json.dumps(manifest, indent=2, sort_keys=True)
    if args.manifest_out:
        Path(args.manifest_out).write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)


if __name__ == "__main__":
    main()
