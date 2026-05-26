#!/usr/bin/env python3
r"""
NEXUS OS — DPO Preference Dataset Compiler
==========================================
Extracts chosen (safe refusal) vs rejected (harmful compliance) pairs from
ERNIE Session06 scenario corpus (1,000 adversarial prompts).

Computes synthetic reward signals for EvoMM safety loss function:
    chosen_reward = confidence / 100.0  (safe refusals get higher reward)
    rejected_reward = 0.0               (harmful compliance gets zero reward)

Outputs JSON Lines format compatible with execute_evomm_merge.py.

Run:
    python scripts/compile_dpo_dataset.py
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone

SCENARIOS_PATH = Path("/mnt/c/Users/speci.000/Downloads/ERNIEsupramacyRESEARCHpaper01/session06/scenarios_001-1000_EN.jsonl")
OUT_PATH = Path(__file__).resolve().parent.parent / "datasets" / "ernie" / "dpo_preference_dataset.jsonl"
SUMMARY_PATH = OUT_PATH.with_suffix(".summary.json")

if sys.platform == "win32":
    SCENARIOS_PATH = Path(r"C:\Users\speci.000\Downloads\ERNIEsupramacyRESEARCHpaper01\session06\scenarios_001-1000_EN.jsonl")

def safe_print(msg):
    ascii_msg = msg.encode("ascii", "replace").decode("ascii")
    print(ascii_msg)


def main():
    safe_print("=" * 70)
    safe_print("NEXUS OS — DPO Preference Dataset Compiler")
    safe_print("=" * 70)

    if not SCENARIOS_PATH.exists():
        safe_print(f"[FAIL] Scenarios file not found: {SCENARIOS_PATH}")
        sys.exit(1)

    safe_print(f"[OK] Reading scenarios from: {SCENARIOS_PATH}")

    prefs = []
    stats = {
        "total_scenarios": 0,
        "valid_pairs": 0,
        "skipped_no_chosen": 0,
        "skipped_no_rejected": 0,
        "skipped_empty_chosen": 0,
        "skipped_empty_rejected": 0,
        "unsafe_label_count": 0,
        "safe_label_count": 0,
        "avg_confidence": 0.0,
        "actors": set(),
        "targets": set(),
    }

    with open(SCENARIOS_PATH, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                scenario = json.loads(line)
            except json.JSONDecodeError:
                continue

            stats["total_scenarios"] += 1

            chosen_raw = scenario.get("dpo_chosen", "")
            rejected_raw = scenario.get("dpo_rejected", "")
            chosen = str(chosen_raw).strip() if chosen_raw is not None else ""
            rejected = str(rejected_raw).strip() if rejected_raw is not None else ""
            # Filter out boolean representations
            if chosen.lower() in ("false", "true", "none"):
                chosen = ""
            if rejected.lower() in ("false", "true", "none"):
                rejected = ""
            label = scenario.get("label", "UNKNOWN")
            confidence = scenario.get("confidence", 0.0)
            actor = scenario.get("actor", "unknown")
            target = scenario.get("target", "unknown")
            scenario_id = scenario.get("id", f"unknown_{stats['total_scenarios']}")

            stats["actors"].add(actor)
            stats["targets"].add(target)

            if label == "UNSAFE":
                stats["unsafe_label_count"] += 1
            elif label == "SAFE":
                stats["safe_label_count"] += 1

            if not chosen:
                stats["skipped_no_chosen"] += 1
                continue
            if not rejected:
                stats["skipped_no_rejected"] += 1
                continue
            if len(chosen) < 5:
                stats["skipped_empty_chosen"] += 1
                continue
            if len(rejected) < 5:
                stats["skipped_empty_rejected"] += 1
                continue

            # Compute synthetic reward signals
            # For UNSAFE scenarios: safe refusal (chosen) should be rewarded,
            # harmful compliance (rejected) should be penalized.
            # Confidence may be string like "94%" or numeric
            conf_str = str(confidence).replace("%", "").strip()
            conf_val = float(conf_str) if conf_str else 0.0
            chosen_reward = min(conf_val / 100.0, 1.0)
            rejected_reward = 0.0

            pref = {
                "scenario_id": scenario_id,
                "actor": actor,
                "target": target,
                "label": label,
                "confidence": confidence,
                "prompt": scenario.get("prompt", ""),
                "chosen": chosen,
                "rejected": rejected,
                "chosen_reward": round(chosen_reward, 4),
                "rejected_reward": round(rejected_reward, 4),
            }
            prefs.append(pref)
            stats["valid_pairs"] += 1
            stats["avg_confidence"] += conf_val

    if stats["valid_pairs"] > 0:
        stats["avg_confidence"] /= stats["valid_pairs"]

    safe_print(f"[OK] Total scenarios scanned: {stats['total_scenarios']}")
    safe_print(f"[OK] Valid DPO pairs extracted: {stats['valid_pairs']}")
    safe_print(f"[OK] UNSAFE labels: {stats['unsafe_label_count']}")
    safe_print(f"[OK] SAFE labels: {stats['safe_label_count']}")
    safe_print(f"[OK] Avg confidence of valid pairs: {stats['avg_confidence']:.2f}")
    safe_print(f"[INFO] Unique actors: {len(stats['actors'])}")
    safe_print(f"[INFO] Unique targets: {len(stats['targets'])}")

    if stats["skipped_no_chosen"] > 0:
        safe_print(f"[INFO] Skipped (no chosen): {stats['skipped_no_chosen']}")
    if stats["skipped_no_rejected"] > 0:
        safe_print(f"[INFO] Skipped (no rejected): {stats['skipped_no_rejected']}")

    # Write JSON Lines output
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        for pref in prefs:
            f.write(json.dumps(pref, ensure_ascii=False) + "\n")

    safe_print(f"[OK] DPO dataset written: {OUT_PATH}")

    # Write summary
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": str(SCENARIOS_PATH),
        "output": str(OUT_PATH),
        "total_scenarios": stats["total_scenarios"],
        "valid_pairs": stats["valid_pairs"],
        "unsafe_labels": stats["unsafe_label_count"],
        "safe_labels": stats["safe_label_count"],
        "avg_confidence": round(stats["avg_confidence"], 2),
        "unique_actors": len(stats["actors"]),
        "unique_targets": len(stats["targets"]),
        "actors": sorted(list(stats["actors"])),
    }
    with open(SUMMARY_PATH, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    safe_print(f"[OK] Summary written: {SUMMARY_PATH}")
    safe_print("=" * 70)

    # Also emit the simple JSON array format for EvoMM backward compat
    simple_json_path = OUT_PATH.with_suffix(".array.json")
    with open(simple_json_path, "w", encoding="utf-8") as f:
        json.dump(prefs, f, indent=2, ensure_ascii=False)
    safe_print(f"[OK] Array format written: {simple_json_path}")


if __name__ == "__main__":
    main()
