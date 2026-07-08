"""calibrate_tc_v7_suggest.py — F.2: Threshold sweep per category.

For each of 20 categories, sweep thresholds in [0.30, 0.90] step 0.05
and pick the threshold that maximizes F1 on the 10-scenario subset.

Output: benchmarks/stress_lab/calibrate_tc_v7_suggest_<date>.json
with suggested CATEGORY_THRESHOLDS dict + provenance.
"""
import json
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from nexus_os.security.meta_attack_detector import MetaAttackDetector

MISSION = Path(r"D:\GROSS\phase3\ERNIE_Tc_RECALIBRATION_MISSION.md")
ATTACK_LABELS = {
    "REFUSE_ILLEGAL", "REFUSE_UNSAFE_ACTION", "REDIRECT_TO_SAFE", "REFUSE",
    "REFUSE_AND_REDIRECT",
}
CATEGORY_RE = re.compile(r"^### (\w+)\s+\((\d+)\)")
SCENARIO_RE = re.compile(
    r"^(\w+)\s*\|\s*(.+?)\s*\|\s*(REFUSE[A-Z_]*|REDIRECT[A-Z_]*|SAFE)\s*$"
)


def parse_scenarios(md_text: str) -> list[tuple[str, str, str]]:
    out = []
    current = None
    expected = 0
    seen = 0
    for line in md_text.splitlines():
        m = CATEGORY_RE.match(line.rstrip())
        if m:
            current = m.group(1); expected = int(m.group(2)); seen = 0
            continue
        if not current or seen >= expected:
            continue
        m = SCENARIO_RE.match(line)
        if m and m.group(1) == current:
            out.append((current, m.group(2).strip(), m.group(3).strip()))
            seen += 1
    return out


def f1(tp, fp, fn):
    p = tp / max(1, tp + fp)
    r = tp / max(1, tp + fn)
    return 0.0 if (p + r) == 0 else 2 * p * r / (p + r)


def main():
    scenarios = parse_scenarios(MISSION.read_text(encoding="utf-8"))
    print(f"Parsed {len(scenarios)} scenarios")

    detector = MetaAttackDetector()
    # Per-scenario raw detection: is_threat + confidence (regardless of category match)
    raw: dict[tuple[str, int], tuple[bool, float, str]] = {}
    for i, (cat, qry, lbl) in enumerate(scenarios):
        res = detector.scan(qry)
        raw[(cat, i)] = (res.is_threat, res.confidence, res.category or "")

    # For category-specific threshold tuning, we use scenarios labeled with
    # that category. Treat each as positive; out-of-category is not a true
    # negative (it's just unknown).
    by_category: dict[str, list[float]] = defaultdict(list)
    for i, (cat, qry, lbl) in enumerate(scenarios):
        is_attack = lbl in ATTACK_LABELS
        flagged, conf, _ = raw[(cat, i)]
        by_category[cat].append((is_attack, conf, flagged))

    sweep = [round(t * 0.05 + 0.30, 2) for t in range(0, 13)]  # 0.30..0.90
    suggestions: dict[str, dict] = {}
    for cat in sorted(by_category):
        data = by_category[cat]
        best_t = 0.50
        best_f1 = -1.0
        best_metrics = None
        for thr in sweep:
            tp = sum(1 for atk, _, _ in data if atk and _ >= thr)
            # We don't have a true negative set per category, so we approximate
            # recall at the threshold and use F1 against the "positive" set only.
            # The full positive set for cat is sum(atk) = 10.
            pos = sum(1 for atk, _, _ in data if atk)
            fn = pos - tp
            fp_approx = 0  # no clean negative signal per category
            f = f1(tp, fp_approx, fn)
            if f > best_f1:
                best_f1 = f
                best_t = thr
                best_metrics = {"tp": tp, "fn": fn, "pos": pos, "thr": thr, "f1": round(f, 3)}
        suggestions[cat] = {
            "current_threshold": detector.CATEGORY_THRESHOLDS.get(cat, 0.50),
            "suggested_threshold": best_t,
            "metrics": best_metrics,
        }

    out = {
        "date": time.strftime("%Y-%m-%d"),
        "n_scenarios": len(scenarios),
        "sweep_range": [0.30, 0.90],
        "methodology": (
            "Per-category threshold sweep on 10-scenario subset. "
            "Optimizes F1 against the positive set; no per-category negatives "
            "in the corpus, so F1 reduces to recall."
        ),
        "suggestions": suggestions,
        "summary": {
            "raised": [
                c for c, s in suggestions.items()
                if s["suggested_threshold"] > s["current_threshold"]
            ],
            "lowered": [
                c for c, s in suggestions.items()
                if s["suggested_threshold"] < s["current_threshold"]
            ],
            "unchanged": [
                c for c, s in suggestions.items()
                if s["suggested_threshold"] == s["current_threshold"]
            ],
        },
    }
    out_dir = Path(r"C:\Users\speci.000\Documents\NEXUS\benchmarks\stress_lab")
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"calibrate_tc_v7_suggest_{stamp}.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\nSaved -> {out_path}")
    print("\n=== SUGGESTED THRESHOLD CHANGES ===")
    for cat, s in sorted(suggestions.items()):
        cur = s["current_threshold"]; sug = s["suggested_threshold"]
        m = s["metrics"]
        delta = "↑" if sug > cur else ("↓" if sug < cur else "=")
        print(f"  {delta} {cat:35s} {cur:.2f} -> {sug:.2f}  (tp={m['tp']}/{m['pos']} fn={m['fn']})")


if __name__ == "__main__":
    main()
