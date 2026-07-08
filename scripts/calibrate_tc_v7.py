"""calibrate_tc_v7.py — F: Validate CATEGORY_THRESHOLDS against 200-scenario corpus.

Parses the 200 v8/v9 attack scenarios from
D:\\GROSS\\phase3\\ERNIE_Tc_RECALIBRATION_MISSION.md and runs them through
MetaAttackDetector.scan() to find the empirical threshold for each of the 20
v5 categories. Reports current-threshold vs suggested-threshold per category.

Output: benchmarks/stress_lab/calibrate_tc_v7_<date>.json
"""
import json
import re
import time
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from nexus_os.security.meta_attack_detector import MetaAttackDetector

MISSION = Path(r"D:\GROSS\phase3\ERNIE_Tc_RECALIBRATION_MISSION.md")

# Map ground truth labels to attack/benign
ATTACK_LABELS = {
    "REFUSE_ILLEGAL", "REFUSE_UNSAFE_ACTION", "REDIRECT_TO_SAFE", "REFUSE",
    "REFUSE_AND_REDIRECT",
}
BENIGN_LABELS = set()  # None of the 200 scenarios are labeled as benign.

CATEGORY_RE = re.compile(r"^### (\w+)\s+\((\d+)\)")
SCENARIO_RE = re.compile(
    r"^(\w+)\s*\|\s*(.+?)\s*\|\s*(REFUSE[A-Z_]*|REDIRECT[A-Z_]*|SAFE)\s*$"
)


def parse_scenarios(md_text: str) -> list[tuple[str, str, str]]:
    """Returns [(category, query, ground_truth_label)]"""
    out: list[tuple[str, str, str]] = []
    current_category = None
    expected_count = 0
    seen = 0
    for line in md_text.splitlines():
        line = line.rstrip()
        m_cat = CATEGORY_RE.match(line)
        if m_cat:
            current_category = m_cat.group(1)
            expected_count = int(m_cat.group(2))
            seen = 0
            continue
        if not current_category or seen >= expected_count:
            continue
        m = SCENARIO_RE.match(line)
        if m:
            cat, qry, lbl = m.group(1), m.group(2).strip(), m.group(3).strip()
            if cat == current_category:
                out.append((cat, qry, lbl))
                seen += 1
    return out


def main():
    md = MISSION.read_text(encoding="utf-8")
    scenarios = parse_scenarios(md)
    print(f"Parsed {len(scenarios)} scenarios (expected 200)")

    detector = MetaAttackDetector()

    by_category: dict[str, list[dict]] = defaultdict(list)
    overall_tp = overall_fp = overall_fn = overall_tn = 0
    t0 = time.time()
    for cat, qry, lbl in scenarios:
        is_attack = lbl in ATTACK_LABELS
        res = detector.scan(qry)
        # A scenario is "flagged" if any matching category triggers.
        triggered_categories = (
            [res.category] if res.is_threat and res.category else []
        )
        # The detector's category may not be the actual category; we check both.
        flagged = res.is_threat
        flagged_in_category = (
            res.is_threat
            and (res.category == cat or res.category == "multi_turn_decomposition")
        )
        if is_attack and flagged_in_category:
            tp = 1
        elif is_attack and not flagged_in_category:
            tp = 0
        else:
            tp = 0
        by_category[cat].append({
            "query": qry[:100],
            "label": lbl,
            "is_threat": res.is_threat,
            "pred_category": res.category,
            "confidence": round(res.confidence, 3) if res.is_threat else None,
            "matched_pattern": (res.matched_pattern or "")[:80] if res.matched_pattern else "",
        })
        if is_attack and flagged_in_category:
            overall_tp += 1
        elif is_attack and not flagged_in_category:
            overall_fn += 1
        elif not is_attack and flagged_in_category:
            overall_fp += 1
        else:
            overall_tn += 1
    elapsed = time.time() - t0

    summary: dict = {
        "n_scenarios": len(scenarios),
        "elapsed_s": round(elapsed, 2),
        "overall": {
            "tp": overall_tp, "fp": overall_fp, "fn": overall_fn, "tn": overall_tn,
            "recall_unsafe": round(overall_tp / max(1, overall_tp + overall_fn), 3),
            "fp_rate": round(overall_fp / max(1, overall_fp + overall_tn), 3),
        },
        "by_category": {},
    }
    for cat, items in sorted(by_category.items()):
        n = len(items)
        detected = sum(1 for it in items if it["is_threat"])
        summary["by_category"][cat] = {
            "n": n,
            "detected": detected,
            "recall": round(detected / n, 3) if n else 0.0,
            "current_threshold": detector.CATEGORY_THRESHOLDS.get(cat, detector.THRESHOLD),
        }

    out_dir = Path(r"C:\Users\speci.000\Documents\NEXUS\benchmarks\stress_lab")
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"calibrate_tc_v7_{stamp}.json"
    out_path.write_text(json.dumps(summary, indent=2))
    print(f"\nSaved -> {out_path}")
    print("\n=== OVERALL ===")
    print(f"  TP={overall_tp} FP={overall_fp} FN={overall_fn} TN={overall_tn}")
    print(f"  recall_unsafe={summary['overall']['recall_unsafe']} "
          f"FP_rate={summary['overall']['fp_rate']}")
    print("\n=== PER CATEGORY ===")
    for cat, s in sorted(summary["by_category"].items(), key=lambda kv: - (kv[1]["n"] - kv[1]["detected"])):
        fn = s["n"] - s["detected"]
        s["fn"] = fn
        s["fn_per_cat"] = fn
        print(f"  {cat:35s} n={s['n']:3d} det={s['detected']:3d} recall={s['recall']:.2f} T={s['current_threshold']:.2f}")


if __name__ == "__main__":
    main()
