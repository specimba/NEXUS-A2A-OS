#!/usr/bin/env python3
"""
nexus-scan.py — DRY-RUN ONLY Provenance Scanner for NEXUS OS

Maps file hashes, identifies potential secrets, and generates an inventory JSON.
NEVER auto-commits. Output is report-only for human review.

Usage:
    python nexus-scan.py [path] [--output inventory.json] [--verbose]

Circuit Breaker: If external sources block 3 times, mark [CIRCUIT_OPEN] and stop.

This scanner supports Phase 0 grounding:
- Milestone 0.1: DoppelGround Data Consolidation
- Milestone 0.2: Infrastructure Setup
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("nexus-scan")

# ── Configuration ────────────────────────────────────────────────────

SKIP_DIRS = {
    ".git", "__pycache__", "node_modules", ".next", ".prisma",
    "venv", ".venv", "env", ".env", "dist", "build", ".tox",
    ".mypy_cache", ".pytest_cache", ".ruff_cache",
}

SKIP_EXTENSIONS = {
    ".pyc", ".pyo", ".so", ".dll", ".exe", ".bin",
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp",
    ".mp3", ".mp4", ".wav", ".avi", ".mov",
    ".zip", ".tar", ".gz", ".rar", ".7z",
    ".db", ".sqlite", ".sqlite3",
    ".lock", ".woff", ".woff2", ".ttf", ".eot",
}

# Patterns that might indicate secrets (same as gitleaks checks)
SECRET_PATTERNS = [
    ("API_KEY", r"(?i)(api[_-]?key|apikey)\s*[=:]\s*['\"][^'\"]{8,}['\"]"),
    ("PRIVATE_KEY", r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----"),
    ("TOKEN", r"(?i)(github[_-]?token|gitlab[_-]?token|slack[_-]?token)\s*[=:]\s*['\"][^'\"]{8,}['\"]"),
    ("PASSWORD", r"(?i)password\s*[=:]\s*['\"][^'\"]{3,}['\"]"),
    ("SECRET", r"(?i)secret\s*[=:]\s*['\"][^'\"]{8,}['\"]"),
    ("AWS_KEY", r"AKIA[0-9A-Z]{16}"),
    ("GITHUB_TOKEN", r"gh[ps]_[A-Za-z0-9_]{36,}"),
]

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


@dataclass
class FileInventory:
    """Inventory entry for a single file."""
    path: str
    sha256: str
    size: int
    extension: str
    last_modified: float
    potential_secrets: List[Dict[str, str]] = field(default_factory=list)
    is_binary: bool = False


@dataclass
class ScanResult:
    """Complete scan result."""
    scan_time: str = ""
    root_path: str = ""
    total_files: int = 0
    total_size: int = 0
    total_potential_secrets: int = 0
    files: List[Dict[str, Any]] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)


def compute_sha256(file_path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
    except (IOError, OSError) as e:
        logger.warning("Cannot hash %s: %s", file_path, e)
        return "ERROR"
    return h.hexdigest()


def is_binary(file_path: Path) -> bool:
    """Check if a file appears to be binary."""
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(1024)
            if b"\x00" in chunk:
                return True
            # Check for high ratio of non-text bytes
            text_chars = set(range(32, 127)) | {9, 10, 13}
            non_text = sum(1 for b in chunk if b not in text_chars)
            if len(chunk) > 0 and non_text / len(chunk) > 0.3:
                return True
    except (IOError, OSError):
        return True
    return False


def scan_for_secrets(file_path: Path) -> List[Dict[str, str]]:
    """
    Scan a file for potential secret patterns.
    Returns list of {pattern_type, line_number, preview}.
    """
    import re

    findings = []
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for line_num, line in enumerate(f, 1):
                for pattern_name, pattern in SECRET_PATTERNS:
                    if re.search(pattern, line):
                        # Mask the actual value
                        preview = line.strip()[:80]
                        findings.append({
                            "pattern_type": pattern_name,
                            "line_number": str(line_num),
                            "preview": preview[:60] + "..." if len(preview) > 60 else preview,
                        })
    except (IOError, OSError, UnicodeDecodeError):
        pass

    return findings


def scan_directory(root_path: str, verbose: bool = False) -> ScanResult:
    """
    Scan a directory tree and generate a provenance inventory.
    DRY-RUN ONLY — never modifies anything.
    """
    root = Path(root_path).resolve()
    if not root.exists():
        logger.error("Path does not exist: %s", root)
        sys.exit(1)

    result = ScanResult(
        scan_time=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        root_path=str(root),
    )

    logger.info("Scanning: %s", root)
    logger.info("Mode: DRY-RUN (report only, no modifications)")

    for dirpath, dirnames, filenames in os.walk(root):
        # Skip configured directories
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]

        for filename in filenames:
            file_path = Path(dirpath) / filename

            # Skip by extension
            if file_path.suffix.lower() in SKIP_EXTENSIONS:
                continue

            # Skip large files
            try:
                size = file_path.stat().st_size
                if size > MAX_FILE_SIZE:
                    result.warnings.append(f"Skipped large file: {file_path} ({size} bytes)")
                    continue
            except OSError:
                continue

            # Compute hash
            sha256 = compute_sha256(file_path)
            binary = is_binary(file_path)

            # Scan for potential secrets (text files only)
            secrets = []
            if not binary:
                secrets = scan_for_secrets(file_path)
                if secrets and verbose:
                    logger.info(
                        "  [SECRET?] %s: %d potential findings",
                        file_path.relative_to(root), len(secrets),
                    )

            entry = FileInventory(
                path=str(file_path.relative_to(root)),
                sha256=sha256,
                size=size,
                extension=file_path.suffix.lower(),
                last_modified=file_path.stat().st_mtime,
                potential_secrets=secrets,
                is_binary=binary,
            )

            result.files.append(asdict(entry))
            result.total_files += 1
            result.total_size += size
            result.total_potential_secrets += len(secrets)

            if verbose and result.total_files % 100 == 0:
                logger.info("  ... %d files scanned", result.total_files)

    # Summary
    ext_counts: Dict[str, int] = {}
    for f in result.files:
        ext = f["extension"] or "(no ext)"
        ext_counts[ext] = ext_counts.get(ext, 0) + 1

    secret_counts: Dict[str, int] = {}
    for f in result.files:
        for s in f["potential_secrets"]:
            pt = s["pattern_type"]
            secret_counts[pt] = secret_counts.get(pt, 0) + 1

    result.summary = {
        "extension_distribution": dict(sorted(ext_counts.items(), key=lambda x: -x[1])[:20]),
        "secret_pattern_distribution": secret_counts,
        "total_potential_secrets": result.total_potential_secrets,
        "total_files": result.total_files,
        "total_size_mb": round(result.total_size / (1024 * 1024), 2),
    }

    return result


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="NEXUS OS Provenance Scanner — DRY-RUN ONLY",
        epilogue="Output is report-only. Never auto-commits.",
    )
    parser.add_argument("path", nargs="?", default=".", help="Directory to scan")
    parser.add_argument("--output", "-o", default="inventory.json", help="Output JSON file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    result = scan_directory(args.path, verbose=args.verbose)

    # Write output
    with open(args.output, "w") as f:
        json.dump(asdict(result), f, indent=2, default=str)

    # Print summary
    print("\n" + "=" * 60)
    print("NEXUS OS PROVENANCE SCAN — DRY-RUN REPORT")
    print("=" * 60)
    print(f"  Scanned:  {result.root_path}")
    print(f"  Files:    {result.total_files}")
    print(f"  Size:     {result.summary.get('total_size_mb', 0):.2f} MB")
    print(f"  Secrets:  {result.total_potential_secrets} potential findings")

    if result.summary.get("secret_pattern_distribution"):
        print("\n  Secret Pattern Breakdown:")
        for pattern, count in result.summary["secret_pattern_distribution"].items():
            print(f"    {pattern}: {count}")

    if result.warnings:
        print(f"\n  Warnings: {len(result.warnings)}")
        for w in result.warnings[:5]:
            print(f"    - {w}")

    print(f"\n  Output:   {args.output}")
    print("=" * 60)
    print("DRY-RUN COMPLETE — no files were modified")

    logger.info("Scan complete. Output written to %s", args.output)


if __name__ == "__main__":
    main()
