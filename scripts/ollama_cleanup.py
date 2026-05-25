#!/usr/bin/env python3
"""
ollama_cleanup.py — Hardened Ollama model cleanup.

NEVER delete manifests before computing the reference set.
ALWAYS verify refs is non-empty before deleting blobs.
DRY RUN by default. Use --execute to actually clean.
"""
import argparse, json, os, shutil, sys
from pathlib import Path

OLLAMA_DIR = Path("/mnt/c/Users/speci.000/.ollama/models")
MANIFESTS_DIR = OLLAMA_DIR / "manifests"
BLOBS_DIR = OLLAMA_DIR / "blobs"
BACKUP_DIR = Path("/mnt/d/Ollama_Backup")

# ── Classification patterns ─────────────────────────────────────────
KEEP_PATTERNS = ["special-virus", "llama-guard3", "gemma3", "e-cameron", "qwen2.5"]
REMOVE_PATTERNS = [
    "deepseek-v4-flash", "deepseek-v4-pro", "glm-5.1", "kimi-k2.6",
    "minimax-m2.7", "qwen3-coder-next", "gemma4/31b-cloud",
]


def classify(name):
    nl = name.lower()
    for k in KEEP_PATTERNS:
        if k.lower() in nl:
            return "KEEP"
    for r in REMOVE_PATTERNS:
        if r.lower() in nl:
            return "REMOVE"
    return "UNCERTAIN"


def manifest_size(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return 0
        total = 0
        for layer in data.get("layers", []):
            digest = layer.get("digest", "")
            blob = BLOBS_DIR / digest.replace(":", "-")
            if blob.exists():
                total += blob.stat().st_size
        return total
    except (json.JSONDecodeError, OSError):
        return 0


def get_all_referenced_blobs() -> set[str]:
    """Walk ALL existing manifests and collect referenced blob names.
    MUST be called BEFORE deleting any manifests."""
    refs = set()
    for root, _, files in os.walk(MANIFESTS_DIR):
        for fn in files:
            p = Path(root) / fn
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if not isinstance(data, dict):
                    continue
                for layer in data.get("layers", []):
                    digest = layer.get("digest", "")
                    if digest.startswith("sha256-"):
                        refs.add(digest.replace(":", "-"))
            except (json.JSONDecodeError, OSError, UnicodeDecodeError):
                continue
    return refs


def fmt(n):
    for u in ["B", "KB", "MB", "GB"]:
        if n < 1024:
            return f"{n:.1f}{u}"
        n /= 1024
    return f"{n:.1f}TB"


def main():
    parser = argparse.ArgumentParser(description="Ollama model cleanup")
    parser.add_argument("--execute", action="store_true", help="Actually delete models")
    parser.add_argument("--backup-dir", type=Path, default=BACKUP_DIR)
    args = parser.parse_args()

    print("=" * 70)
    print("NEXUS Ollama Cleanup (Hardened v2)")
    print("=" * 70)

    models = []
    for root, _, files in os.walk(MANIFESTS_DIR):
        for fn in files:
            p = Path(root) / fn
            rel = str(p.relative_to(MANIFESTS_DIR))
            sz = manifest_size(p)
            models.append((p, rel, sz))

    keep, remove, uncertain = [], [], []
    for p, rel, sz in models:
        cat = classify(rel)
        if cat == "KEEP":
            keep.append((p, rel, sz))
        elif cat == "REMOVE":
            remove.append((p, rel, sz))
        else:
            uncertain.append((p, rel, sz))

    sk = sum(s for _, _, s in keep)
    sr = sum(s for _, _, s in remove)
    su = sum(s for _, _, s in uncertain)

    print(f"\n📊 INVENTORY: {len(models)} models")
    print(f"   KEEP:      {len(keep):3d}  {fmt(sk)}")
    print(f"   REMOVE:    {len(remove):3d}  {fmt(sr)}")
    print(f"   UNCERTAIN: {len(uncertain):3d}  {fmt(su)}")

    if remove:
        print(f"\n🗑️  TOP REMOVE:")
        for _, n, s in remove[:20]:
            print(f"   {fmt(s):>10s}  {n}")

    if uncertain:
        print(f"\n❓ UNCERTAIN:")
        for _, n, s in uncertain:
            print(f"   {fmt(s):>10s}  {n}")

    if not args.execute:
        print(f"\n⚠️  DRY RUN — no changes. Reclaimable: {fmt(sr)}")
        print(f"   Use --execute to clean.")
        return 0

    # ── EXECUTE: compute refs FIRST, before any deletions ────────────
    print(f"\n🚨 EXECUTING...")

    refs = get_all_referenced_blobs()
    print(f"   Referenced blobs: {len(refs)}")

    if not refs:
        print("   ❌ ABORT: refs set is empty. Something is wrong.")
        return 1

    # 1. Backup manifests for removed models
    if remove:
        bp = args.backup_dir / "manifests"
        bp.mkdir(parents=True, exist_ok=True)
        for p, rel, _ in remove:
            dest = bp / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dest)
        print(f"   Backed up {len(remove)} manifests to {bp}")

    # 2. Delete removed manifests
    for p, _, _ in remove:
        try:
            p.unlink()
        except OSError as e:
            print(f"   WARN: could not delete {p}: {e}")
    print(f"   Deleted {len(remove)} manifests")

    # 3. Re-compute refs after manifest deletion
    refs_after = get_all_referenced_blobs()
    print(f"   Remaining referenced blobs: {len(refs_after)}")

    # 4. Delete only blobs NOT in refs_after
    deleted = 0
    recl = 0
    for blob in BLOBS_DIR.iterdir():
        if blob.is_file() and blob.name not in refs_after:
            try:
                recl += blob.stat().st_size
                blob.unlink()
                deleted += 1
            except OSError:
                pass
    print(f"   Deleted {deleted} unreferenced blobs ({fmt(recl)})")

    # 5. Verify remaining models still have their blobs
    verify_ok = True
    for p, rel, _ in keep:
        sz = manifest_size(p)
        if sz == 0:
            print(f"   ❌ VERIFY FAIL: {rel} has 0 bytes after cleanup")
            verify_ok = False
    if verify_ok:
        print(f"   ✅ All kept models verified intact")

    print(f"\n✅ DONE — reclaimed ~{fmt(sr + recl)}")
    print(f"   Remaining models: {len(keep) + len(uncertain)}")
    return 0 if verify_ok else 1


if __name__ == "__main__":
    sys.exit(main())
