#!/usr/bin/env python3
# CANARY: 572c390f3d6e1b75d03507bd72748157
"""Ollama cleanup v2 — simplified, no caching issues."""
import json, os, shutil, sys
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
    "Bonsai-1.7B-gguf:Q1_0", "IBM-Grok4-Ultra.Fast.Coder-1B-GGUF:F16",
    "Qwen3Guard-Gen-0.6B-GGUF:Q4_K_M", "Darwin-2B-Opus-GGUF:Q6_K",
    "Qwen3.5-0.8B-heretic-ara-v2-GGUF:Q8_0", "functiongemma",
    "Bonsai-8B-requantized", "nemotron-3-nano", "Trinity-Nano-Preview-GGUF",
    "LFM2-12B-A1B-SpeedDemon", "Qwen3.6-27B-DFlash", "Omega-Evolution-9B",
    "DR-Venus-4B-RL-GGUF", "Carnice-9b-GGUF", "qwopus3.5-9B",
    "Darwin-9B-Opus-GGUF", "Huihui-granite-4.1-8b-abliterated-GGUF",
    "L3.1-Dark-Reasoning-LewdPlay", "MiniCPM-V-4.6-Abliterated",
    "Albert_Wesker-1B", "Alexia.FinalEvolution-1B", "Alexia.v2-1B",
    "Hunter.Beta-1B", "Joy-3.2-1B", "Neptune.3.2-1B", "PG67A-W-Serum-3.2-1B",
    "T-Polyphalus_RP-3.2-1B", "T-Veronica-PROTO-1B", "T-Virus_Zeta.VirginKiller-3.2-1B",
    "Neo_T-Virus-3.2-1B", "The_Croupier-3.2-1B-i1", "Prototype-Virus-1B",
    "E-Cameron-3.2-1B", "Omni-Reasoner-2B-GGUF", "GRaPE-2-Mini-GGUF",
    "Gemma4-E2B-SFT-Claude-Opus-Reasoning-Unsloth-GGUF",
    "Granite-4.1-3B-SFT-Claude-Opus-Reasoning-Unsloth-i1-GGUF",
    "Huihui-granite-4.1-3b-abliterated-i1-GGUF",
    "granite-4.1-8b-Abliterated-AND-Disinhibited-GGUF",
    "ibm-research/granite-guardian-3.2-3b", "geoffmunn/Qwen3Guard-Gen-4B",
    "hauhaucs/Gemma-4-E2B-Uncensored", "obliteratus/gemma-4-E4B-it-OBLITERATED",
    "arcee-ai/Trinity-Nano-Preview-GGUF", "bartowski/arcee-ai_Trinity-Nano-Preview-GGUF",
    "jaahas/qwen3.5-uncensored", "frob/locooperator", "model/latest",
    "deepseek-r1/8b", "qwen2.5-coder/7b", "qwen2.5-1.5b-linear-fixed",
    "qwen2.5-1.5b-linear-merged", "qwen2.5-1.5b-slerp-manual",
    "qwen2.5-1.5b-ties-merged",
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
            if digest.startswith("sha256-"):
                blob = BLOBS_DIR / digest.replace(":", "-")
                if blob.exists():
                    total += blob.stat().st_size
        return total
    except Exception:
        return 0


def get_referenced_blobs():
    refs = set()
    for root, _, files in os.walk(MANIFESTS_DIR):
        for fn in files:
            try:
                with open(Path(root) / fn, "r") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    for layer in data.get("layers", []):
                        d = layer.get("digest", "")
                        if d.startswith("sha256-"):
                            refs.add(d.replace(":", "-"))
            except Exception:
                pass
    return refs


def fmt(n):
    for u in ["B", "KB", "MB", "GB"]:
        if n < 1024:
            return f"{n:.1f}{u}"
        n /= 1024
    return f"{n:.1f}TB"


def main():
    execute = "--execute" in sys.argv

    print("=" * 70)
    print("NEXUS Ollama Emergency Cleanup v2")
    print("=" * 70)

    models = []
    for root, _, files in os.walk(MANIFESTS_DIR):
        for fn in files:
            p = Path(root) / fn
            rel = str(p.relative_to(MANIFESTS_DIR))
            sz = manifest_size(p)
            models.append((p, rel, sz))

    models.sort(key=lambda x: x[2], reverse=True)

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

    print(f"\n📊 INVENTORY ({len(models)} models)")
    print(f"   KEEP:      {len(keep):3d}  {fmt(sk)}")
    print(f"   REMOVE:    {len(remove):3d}  {fmt(sr)}")
    print(f"   UNCERTAIN: {len(uncertain):3d}  {fmt(su)}")

    if remove:
        print(f"\n🗑️  REMOVE ({len(remove)} models):")
        for _, n, s in remove[:50]:
            print(f"   - {n:65s} {fmt(s):>10s}")
        if len(remove) > 50:
            print(f"   ... and {len(remove)-50} more")

    if uncertain:
        print(f"\n❓ UNCERTAIN ({len(uncertain)} models):")
        for _, n, s in uncertain:
            print(f"   - {n:65s} {fmt(s):>10s}")

    print(f"\n✅ KEEP ({len(keep)} models):")
    for _, n, s in keep:
        print(f"   - {n:65s} {fmt(s):>10s}")

    if not execute:
        print(f"\n⚠️  DRY RUN — no changes. Use --execute to clean.")
        print(f"   Reclaimable: {fmt(sr)}")
        return 0

    print(f"\n🚨 EXECUTING...")

    # Backup manifests
    if remove:
        bp = BACKUP_DIR / "manifests"
        bp.mkdir(parents=True, exist_ok=True)
        for p, rel, _ in remove:
            dest = bp / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dest)
        print(f"   Backed up {len(remove)} manifests to {bp}")

    # Delete manifests
    for p, _, _ in remove:
        try:
            p.unlink()
        except OSError as e:
            print(f"   WARN: could not delete {p}: {e}")
    print(f"   Deleted {len(remove)} manifests")

    # Delete unreferenced blobs
    refs = get_referenced_blobs()
    deleted = 0
    recl = 0
    for blob in BLOBS_DIR.iterdir():
        if blob.is_file() and blob.name not in refs:
            try:
                recl += blob.stat().st_size
                blob.unlink()
                deleted += 1
            except OSError:
                pass
    print(f"   Deleted {deleted} unreferenced blobs ({fmt(recl)})")
    print(f"\n✅ DONE — reclaimed ~{fmt(sr + recl)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
