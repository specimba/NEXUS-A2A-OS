#!/usr/bin/env python3
r"""
scripts/cold_storage_backup.py — NEXUS Cold Storage Backup Tool

Backs up confidential NEXUS IP to D:\NEXUS_COLD (offline storage).
These files must NEVER be committed to GitHub or any public repository.

Usage:
    python scripts/cold_storage_backup.py [--dry-run] [--verify]

Policy:
    - Source: C:\Users\speci.000\Documents\NEXUS
    - Destination: D:\NEXUS_COLD\level{auto}_{YYYYMMDD}\NEXUS
    - Files backed up: datasets/, models/, research/, benchmarks/, logs/, upload/, vault/
    - Backups are FULL (not incremental) for forensic integrity
    - Pruning: keeps last 3 backups by default

Rationale:
    NEXUS contains proprietary model weights, adversarial datasets,
    red-team research, and encrypted credentials. These are valuable
    intellectual property that must remain air-gapped from public repos.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ── Configuration ────────────────────────────────────────────────────

SOURCE_ROOT = Path(r"C:/Users/speci.000/Documents/NEXUS")
COLD_ROOT = Path(r"D:/NEXUS_COLD")
RECOVERY_ROOT = Path(r"D:/NEXUS_RECOVERY")

# Directories that MUST be backed up to cold storage (never GitHub)
BACKUP_DIRS = [
    "datasets",
    "models",
    "research",
    "benchmarks",
    "logs",
    "upload",
    "vault",
]

# Large file extensions that should be tracked separately
LARGE_EXTENSIONS = {".gguf", ".safetensors", ".bin", ".pt", ".pth", ".onnx", ".h5", ".ckpt", ".npy", ".npz", ".zip", ".tar", ".tar.gz", ".rar", ".7z"}

# Max file size for inline manifest (larger files get hash-only)
MANIFEST_SIZE_LIMIT = 10 * 1024 * 1024  # 10 MB

# Pruning: keep last N backups
KEEP_BACKUPS = 3

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("nexus.cold_storage")


# ── Data Classes ──────────────────────────────────────────────────────

class BackupManifest:
    """Manifest for a single backup operation."""

    def __init__(self, backup_path: Path, source_root: Path):
        self.backup_path = backup_path
        self.source_root = source_root
        self.timestamp = datetime.now().isoformat()
        self.files: List[Dict[str, any]] = []
        self.total_files = 0
        self.total_bytes = 0
        self.large_files = 0
        self.large_bytes = 0
        self.errors: List[str] = []

    def add_file(self, rel_path: str, src_path: Path, dst_path: Path) -> None:
        """Add a file to the manifest."""
        size = src_path.stat().st_size
        self.total_files += 1
        self.total_bytes += size

        is_large = size > MANIFEST_SIZE_LIMIT or src_path.suffix.lower() in LARGE_EXTENSIONS
        if is_large:
            self.large_files += 1
            self.large_bytes += size

        # Compute hash for integrity verification
        file_hash = hash_file(src_path) if is_large or size < MANIFEST_SIZE_LIMIT else "<large>"

        entry = {
            "rel_path": rel_path,
            "size": size,
            "hash": file_hash,
            "mtime": src_path.stat().st_mtime,
            "is_large": is_large,
        }
        self.files.append(entry)

    def add_error(self, rel_path: str, error: str) -> None:
        """Record a backup error."""
        self.errors.append(f"{rel_path}: {error}")

    def to_dict(self) -> Dict[str, any]:
        return {
            "backup_path": str(self.backup_path),
            "source_root": str(self.source_root),
            "timestamp": self.timestamp,
            "total_files": self.total_files,
            "total_bytes": self.total_bytes,
            "total_gb": round(self.total_bytes / (1024**3), 2),
            "large_files": self.large_files,
            "large_bytes": self.large_bytes,
            "large_gb": round(self.large_bytes / (1024**3), 2),
            "errors": self.errors,
            "files": self.files,
        }

    def save(self) -> Path:
        """Save manifest to backup directory."""
        manifest_path = self.backup_path / "_manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        return manifest_path


# ── Helper Functions ─────────────────────────────────────────────────

def hash_file(path: Path, algorithm: str = "blake3") -> str:
    """Compute file hash for integrity verification."""
    try:
        if algorithm == "blake3":
            try:
                import blake3
                h = blake3.blake3()
                with open(path, "rb") as f:
                    while chunk := f.read(65536):
                        h.update(chunk)
                return h.hexdigest()[:32]
            except ImportError:
                pass  # Fall through to SHA-256

        # SHA-256 fallback
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()[:32]
    except Exception as e:
        return f"<hash_error: {e}>"


def get_next_level() -> int:
    """Determine next backup level number by scanning existing directories."""
    if not COLD_ROOT.exists():
        return 7  # Start at 7 (after existing 5 and 6)

    levels = []
    for entry in COLD_ROOT.iterdir():
        if entry.is_dir() and entry.name.startswith("level"):
            try:
                level_num = int(entry.name.split("_")[0].replace("level", ""))
                levels.append(level_num)
            except (ValueError, IndexError):
                pass

    return max(levels, default=6) + 1


def create_backup_dir() -> Path:
    """Create a new backup directory with timestamp."""
    level = get_next_level()
    date_str = datetime.now().strftime("%Y%m%d")
    backup_name = f"level{level}_backup_{date_str}"
    backup_path = COLD_ROOT / backup_name / "NEXUS"
    backup_path.mkdir(parents=True, exist_ok=True)
    return backup_path


def copy_with_progress(src: Path, dst: Path, manifest: BackupManifest, rel_path: str) -> bool:
    """Copy a file and update manifest. Returns True on success."""
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        manifest.add_file(rel_path, src, dst)
        return True
    except Exception as e:
        manifest.add_error(rel_path, str(e))
        logger.warning("Failed to copy %s: %s", rel_path, e)
        return False


def backup_directory(src_dir: Path, dst_dir: Path, manifest: BackupManifest, root: Path = SOURCE_ROOT) -> None:
    """Recursively backup a directory."""
    if not src_dir.exists():
        logger.warning("Source directory does not exist: %s", src_dir)
        return

    for item in src_dir.rglob("*"):
        if item.is_file():
            rel_path = item.relative_to(root).as_posix()
            dst_path = dst_dir / rel_path
            copy_with_progress(item, dst_path, manifest, rel_path)


def verify_backup(manifest: BackupManifest) -> bool:
    """Verify backup integrity by re-hashing files."""
    logger.info("Verifying backup integrity...")
    verified = 0
    failed = 0

    for entry in manifest.files:
        if entry["hash"].startswith("<"):
            continue  # Skip large files without hashes

        dst_path = manifest.backup_path / entry["rel_path"]
        if not dst_path.exists():
            failed += 1
            continue

        current_hash = hash_file(dst_path)
        if current_hash == entry["hash"]:
            verified += 1
        else:
            failed += 1
            logger.error("Hash mismatch: %s", entry["rel_path"])

    logger.info("Verification: %d passed, %d failed", verified, failed)
    return failed == 0


def prune_old_backups() -> None:
    """Remove old backups, keeping only the last N."""
    if not COLD_ROOT.exists():
        return

    backups = []
    for entry in COLD_ROOT.iterdir():
        if entry.is_dir() and entry.name.startswith("level"):
            try:
                # Extract level number for sorting
                level_num = int(entry.name.split("_")[0].replace("level", ""))
                backups.append((level_num, entry))
            except (ValueError, IndexError):
                pass

    backups.sort(key=lambda x: x[0], reverse=True)

    to_remove = backups[KEEP_BACKUPS:]
    for level_num, path in to_remove:
        logger.info("Pruning old backup: %s", path.name)
        try:
            shutil.rmtree(path)
        except Exception as e:
            logger.warning("Failed to prune %s: %s", path.name, e)


def print_summary(manifest: BackupManifest) -> None:
    """Print backup summary."""
    print()
    print("=" * 60)
    print("NEXUS COLD STORAGE BACKUP COMPLETE")
    print("=" * 60)
    print(f"Backup path:     {manifest.backup_path}")
    print(f"Timestamp:       {manifest.timestamp}")
    print(f"Total files:     {manifest.total_files:,}")
    print(f"Total size:      {manifest.total_bytes / (1024**3):.2f} GB")
    print(f"Large files:     {manifest.large_files:,} ({manifest.large_gb:.2f} GB)")
    print(f"Errors:          {len(manifest.errors)}")
    print()

    if manifest.errors:
        print("ERRORS:")
        for error in manifest.errors[:10]:
            print(f"  - {error}")
        if len(manifest.errors) > 10:
            print(f"  ... and {len(manifest.errors) - 10} more")
        print()

    print("Directories backed up:")
    for d in BACKUP_DIRS:
        src = SOURCE_ROOT / d
        if src.exists():
            count = sum(1 for _ in src.rglob("*") if _.is_file())
            size = sum(f.stat().st_size for f in src.rglob("*") if f.is_file())
            print(f"  {d:15s} {count:6,} files  {size/(1024**3):6.2f} GB")
        else:
            print(f"  {d:15s} (not found)")
    print()


# ── Main ───────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="NEXUS Cold Storage Backup")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be backed up without copying")
    parser.add_argument("--verify", action="store_true", help="Verify backup integrity after completion")
    parser.add_argument("--prune", action="store_true", help="Prune old backups after completion")
    args = parser.parse_args()

    # Check source exists
    if not SOURCE_ROOT.exists():
        logger.error("Source root does not exist: %s", SOURCE_ROOT)
        return 1

    # Check destination exists
    if not COLD_ROOT.exists():
        if args.dry_run:
            logger.info("Would create: %s", COLD_ROOT)
        else:
            COLD_ROOT.mkdir(parents=True, exist_ok=True)
            logger.info("Created cold storage root: %s", COLD_ROOT)

    # Create backup directory
    if args.dry_run:
        backup_path = COLD_ROOT / f"level{get_next_level()}_backup_{datetime.now().strftime('%Y%m%d')}" / "NEXUS"
        logger.info("[DRY-RUN] Would create backup: %s", backup_path)
    else:
        backup_path = create_backup_dir()
        logger.info("Created backup directory: %s", backup_path)

    # Initialize manifest
    manifest = BackupManifest(backup_path, SOURCE_ROOT)

    # Backup each directory
    for dir_name in BACKUP_DIRS:
        src_dir = SOURCE_ROOT / dir_name
        if not src_dir.exists():
            logger.info("Skipping (not found): %s", src_dir)
            continue

        dst_dir = backup_path / dir_name
        logger.info("Backing up: %s", dir_name)

        if args.dry_run:
            # Count files and sizes without copying
            file_count = 0
            total_size = 0
            for item in src_dir.rglob("*"):
                if item.is_file():
                    file_count += 1
                    total_size += item.stat().st_size
            logger.info("  [DRY-RUN] %s: %d files, %.2f GB", dir_name, file_count, total_size / (1024**3))
        else:
            backup_directory(src_dir, backup_path, manifest)
            logger.info("  %s: %d files, %.2f GB", dir_name, manifest.total_files, manifest.total_bytes / (1024**3))

    # Save manifest
    if not args.dry_run:
        manifest_path = manifest.save()
        logger.info("Manifest saved: %s", manifest_path)

    # Verify
    if args.verify and not args.dry_run:
        if verify_backup(manifest):
            logger.info("Backup verification PASSED")
        else:
            logger.error("Backup verification FAILED")
            return 1

    # Prune
    if args.prune and not args.dry_run:
        prune_old_backups()

    # Print summary
    if not args.dry_run:
        print_summary(manifest)
    else:
        print()
        print("[DRY-RUN] No files were copied.")
        print("Run without --dry-run to perform the backup.")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
