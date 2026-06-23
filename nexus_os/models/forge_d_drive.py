"""D:Drive Forge Pipeline — Convert downloaded HF datasets to NEXUS training data.

Usage:
    python nexus_os/models/forge_d_drive.py --all
    python nexus_os/models/forge_d_drive.py --dataset nemotron-safety-guard-v3
"""

import json
import sys
from pathlib import Path

D_ROOT = Path("D:/NEXUS_MODELS")
FORGE_OUT = Path("C:/Users/speci.000/Documents/NEXUS/datasets/forge")

def forge_nemotron_safety(path: Path, output: Path) -> int:
    """Convert NVIDIA Nemotron Safety Guard v3 → NEXUS guard_safe + guard_adversarial."""
    records = []
    for f in sorted(path.glob("*.jsonl")):
        for line in open(f, encoding="utf-8"):
            try:
                obj = json.loads(line)
                text = obj.get("prompt") or obj.get("text") or ""
                label = obj.get("label") or obj.get("safety") or ""
                if not text:
                    continue
                is_unsafe = str(label).lower() in {"unsafe", "harmful", "1", "true", "yes"}
                records.append(json.dumps({
                    "text": text,
                    "label": "unsafe" if is_unsafe else "safe",
                    "category": "nemotron_safety_v3",
                    "source": "nvidia/Nemotron-Safety-Guard-Dataset-v3",
                    "quality": "S2_eval",
                }))
            except json.JSONDecodeError:
                continue

    out_file = output / "nexus_guard_nemotron_v3.jsonl"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text("\n".join(records), encoding="utf-8")
    return len(records)


def forge_aegis_safety(path: Path, output: Path) -> int:
    """Convert NVIDIA Aegis Safety v2 → NEXUS safety classification records."""
    records = []
    for f in sorted(path.glob("*.jsonl")):
        for line in open(f, encoding="utf-8"):
            try:
                obj = json.loads(line)
                text = obj.get("prompt") or obj.get("text") or obj.get("input") or ""
                label = obj.get("label") or obj.get("safety_label") or ""
                if not text:
                    continue
                is_unsafe = str(label).lower() in {"unsafe", "harmful", "1", "true", "yes"}
                records.append(json.dumps({
                    "text": text,
                    "label": "unsafe" if is_unsafe else "safe",
                    "category": "aegis_safety_v2",
                    "source": "nvidia/Aegis-AI-Content-Safety-Dataset-2.0",
                    "quality": "S2_eval",
                }))
            except json.JSONDecodeError:
                continue

    out_file = output / "nexus_guard_aegis_v2.jsonl"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text("\n".join(records), encoding="utf-8")
    return len(records)


def merge_all_guard_datasets(output: Path) -> int:
    """Merge all guard datasets into single training file."""
    all_records = []
    for f in sorted(output.glob("nexus_guard_*.jsonl")):
        for line in open(f, encoding="utf-8"):
            all_records.append(line.strip())

    merged = output / "nexus_guard_cascade_train.jsonl"
    merged.write_text("\n".join(all_records), encoding="utf-8")

    safe = sum(1 for r in all_records if '"safe"' in r)
    unsafe = sum(1 for r in all_records if '"unsafe"' in r)
    print(f"  Merged: {len(all_records)} total ({safe} safe / {unsafe} unsafe)")
    return len(all_records)


def main():
    datasets = {
        "nemotron-safety-guard-v3": (D_ROOT / "datasets" / "nemotron-safety-guard-v3", forge_nemotron_safety),
        "nvidia-aegis-safety-v2": (D_ROOT / "datasets" / "nvidia-aegis-safety-v2", forge_aegis_safety),
    }

    target = sys.argv[1] if len(sys.argv) > 1 else "--all"
    total = 0

    for name, (path, func) in datasets.items():
        if target not in (name, "--all"):
            continue
        if not path.exists():
            print(f"[SKIP] {name} — not downloaded yet (run download_models.ps1 first)")
            continue
        count = func(path, FORGE_OUT)
        print(f"[FORGE] {name} → {count} records")
        total += count

    if total > 0:
        print(f"\n[FORGE] Total: {total} records across {len(datasets)} datasets")
        merge_all_guard_datasets(FORGE_OUT)

    print(f"[DONE] Output: {FORGE_OUT}")


if __name__ == "__main__":
    main()