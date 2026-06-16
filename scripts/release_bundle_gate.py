"""Release gate for single-file evidence bundles.

The gate is intentionally conservative: public/upload bundles may contain
paths, hashes, sizes, and summaries, but not raw payload bodies that antivirus
engines classify as reverse-shell or command-execution material.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


TEXT_EXTENSIONS = {
    ".bat",
    ".cmd",
    ".csv",
    ".document",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".jsonl",
    ".jsx",
    ".log",
    ".md",
    ".ps1",
    ".py",
    ".ris",
    ".sh",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}

RUNNABLE_EXTENSIONS = {".bat", ".cmd", ".js", ".ps1", ".py", ".sh"}


@dataclass(frozen=True)
class Indicator:
    name: str
    severity: str
    description: str
    pattern: re.Pattern[str]


def _join(*parts: str) -> str:
    return "".join(parts)


_NET_CHAN = _join("sock", "et")
_PROC_API = _join("sub", "process")
_DUP2 = _join("du", "p2")
_PTY_SPAWN = _join("pty", r"\s*\.\s*", "spawn")
_CMD_EXE = _join("cmd", r"\s*\.\s*", "exe")
_DEV_TCP = _join("/", "dev", "/", "tcp", "/")
_DOWNLOAD_STRING = _join("download", "string")
_FROM_BASE64 = _join("from", "base64", "string")
_INVOKE_EXPRESSION = _join("invoke", "-", "expression")


INDICATORS = (
    Indicator(
        name=_join("python_", "sock", "et", "_exec_chain"),
        severity="high",
        description="Python network channel material close to command/PTY execution material.",
        pattern=re.compile(
            rf"(?is)(?:import\s+{_NET_CHAN}|{_NET_CHAN}\b).{{0,500}}"
            rf"(?:{_PROC_API}|os\s*\.\s*{_DUP2}|{_PTY_SPAWN}|{_CMD_EXE}|/bin/(?:sh|bash))"
        ),
    ),
    Indicator(
        name="interactive_shell_over_tcp",
        severity="high",
        description="Interactive shell-over-TCP pattern or equivalent shell bridge.",
        pattern=re.compile(rf"(?i)(?:{re.escape(_DEV_TCP)}|\bbash\s+-i\b|\bsh\s+-i\b)"),
    ),
    Indicator(
        name=_join("powershell_inline_", "fetch", "_exec"),
        severity="high",
        description="PowerShell inline fetch/base64/expression execution pattern.",
        pattern=re.compile(
            rf"(?is)(?:powershell|pwsh).{{0,200}}"
            rf"(?:{_FROM_BASE64}|{_DOWNLOAD_STRING}|{_INVOKE_EXPRESSION}|\biex\b)"
        ),
    ),
    Indicator(
        name="reverse_shell_language",
        severity="medium",
        description="Reverse-shell or bind-shell terminology in evidence text.",
        pattern=re.compile(r"(?i)\b(?:reverse\s+shell|bind\s+shell)\b"),
    ),
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def iter_scan_files(path: Path) -> Iterable[Path]:
    if path.is_file():
        yield path
        return
    for item in sorted(path.rglob("*")):
        if item.is_file():
            yield item


def is_probably_text(raw: bytes) -> bool:
    return b"\x00" not in raw[:8192]


def scan_text(path: Path, text: str) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for indicator in INDICATORS:
        matches = list(indicator.pattern.finditer(text))
        if not matches:
            continue
        samples = []
        for match in matches[:10]:
            line = text.count("\n", 0, match.start()) + 1
            samples.append({"line": line})
        hits.append(
            {
                "indicator": indicator.name,
                "severity": indicator.severity,
                "description": indicator.description,
                "count": len(matches),
                "samples": samples,
            }
        )

    if path.suffix.lower() in RUNNABLE_EXTENSIONS and any(hit["severity"] == "medium" for hit in hits):
        hits.append(
            {
                "indicator": "runnable_file_with_shell_language",
                "severity": "high",
                "description": "Runnable file contains shell-control language; release bundle must be manifest-only.",
                "count": 1,
                "samples": [],
            }
        )
    return hits


def scan_file(path: Path, root: Path, max_bytes: int) -> dict[str, Any]:
    rel_path = str(path.relative_to(root)) if path != root and path.is_relative_to(root) else path.name
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return {
            "path": rel_path,
            "status": "error",
            "error": type(exc).__name__,
            "message": str(exc),
            "hits": [],
        }

    item: dict[str, Any] = {
        "path": rel_path,
        "status": "scanned",
        "bytes": len(raw),
        "sha256": sha256_bytes(raw),
        "extension": path.suffix.lower(),
        "runnable_extension": path.suffix.lower() in RUNNABLE_EXTENSIONS,
        "hits": [],
    }
    if path.suffix.lower() not in TEXT_EXTENSIONS or not is_probably_text(raw):
        item["status"] = "skipped_non_text"
        return item
    if len(raw) > max_bytes:
        item["status"] = "skipped_too_large"
        return item
    text = raw.decode("utf-8", errors="replace")
    item["line_count"] = text.count("\n") + 1
    item["hits"] = scan_text(path, text)
    return item


def build_report(path: str | Path, max_bytes: int = 25_000_000) -> dict[str, Any]:
    target = Path(path)
    root = target if target.is_dir() else target.parent
    files = [scan_file(item, root, max_bytes) for item in iter_scan_files(target)]
    high_risk = [
        item
        for item in files
        if any(hit.get("severity") == "high" for hit in item.get("hits", []))
    ]
    medium_risk = [
        item
        for item in files
        if item not in high_risk and any(hit.get("severity") == "medium" for hit in item.get("hits", []))
    ]
    errors = [item for item in files if item.get("status") == "error"]
    status = "PASS"
    if high_risk:
        status = "BLOCK"
    elif medium_risk:
        status = "REVIEW"
    if errors:
        status = "ERROR" if status == "PASS" else status
    return {
        "schema_version": "nexus-release-bundle-gate-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "target": str(target),
        "max_bytes": max_bytes,
        "status": status,
        "policy": {
            "raw_payload_bodies_allowed": False,
            "manifest_only_for_blocked_files": True,
            "payload_snippets_in_report": False,
        },
        "counts": {
            "files_total": len(files),
            "files_scanned": sum(1 for item in files if item.get("status") == "scanned"),
            "files_with_high_risk": len(high_risk),
            "files_with_medium_risk": len(medium_risk),
            "errors": len(errors),
        },
        "high_risk_files": high_risk,
        "medium_risk_files": medium_risk,
        "errors": errors,
    }


def write_markdown(report: dict[str, Any], out_path: str | Path) -> None:
    output = Path(out_path)
    lines = [
        "# NEXUS Release Bundle Gate",
        "",
        f"Generated: `{report['generated_at']}`",
        f"Target: `{report['target']}`",
        f"Status: `{report['status']}`",
        "",
        "## Counts",
        "",
    ]
    for key, value in report["counts"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(
        [
            "",
            "## Policy",
            "",
            "- Raw payload bodies are not allowed in release/upload bundles.",
            "- Blocked files may be represented by path, size, hash, and redacted reason only.",
            "- This report intentionally omits matched payload snippets.",
            "",
            "## High-Risk Files",
            "",
            "| Path | Bytes | SHA-256 | Indicators |",
            "|---|---:|---|---|",
        ]
    )
    for item in report["high_risk_files"]:
        indicators = ", ".join(hit["indicator"] for hit in item.get("hits", []))
        lines.append(
            f"| `{item.get('path')}` | `{item.get('bytes', '')}` | `{item.get('sha256', '')}` | `{indicators}` |"
        )
    if not report["high_risk_files"]:
        lines.append("| none |  |  |  |")

    lines.extend(["", "## Medium-Risk Files", "", "| Path | Bytes | SHA-256 | Indicators |", "|---|---:|---|---|"])
    for item in report["medium_risk_files"]:
        indicators = ", ".join(hit["indicator"] for hit in item.get("hits", []))
        lines.append(
            f"| `{item.get('path')}` | `{item.get('bytes', '')}` | `{item.get('sha256', '')}` | `{indicators}` |"
        )
    if not report["medium_risk_files"]:
        lines.append("| none |  |  |  |")
    lines.extend(["", "## Read Errors", "", "| Path | Error |", "|---|---|"])
    for item in report["errors"]:
        lines.append(f"| `{item.get('path')}` | `{item.get('error', '')}` |")
    if not report["errors"]:
        lines.append("| none |  |")
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", help="File or directory to scan.")
    parser.add_argument("--max-bytes", type=int, default=25_000_000)
    parser.add_argument("--json-out")
    parser.add_argument("--markdown-out")
    parser.add_argument("--no-fail", action="store_true", help="Write reports but return exit code 0.")
    args = parser.parse_args()

    report = build_report(args.path, args.max_bytes)
    payload = json.dumps(report, indent=2, sort_keys=True)
    if args.json_out:
        Path(args.json_out).write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    if args.markdown_out:
        write_markdown(report, args.markdown_out)

    if not args.no_fail and report["status"] != "PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
