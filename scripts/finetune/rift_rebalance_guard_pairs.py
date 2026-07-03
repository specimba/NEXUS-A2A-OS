"""RIFT rebalance of the guard DPO pair set (Track F / papers09).

Reads the deduplicated guard DPO pairs (247 SAFE / 128 UNSAFE — imbalanced)
and emits a reward-weighted RIFT SFT dataset: every chosen completion with
a positive reward, every rejected completion REPURPOSED with a graded
negative reward, both scaled by inverse-frequency class weights so SAFE and
UNSAFE carry equal effective training mass. No pair is discarded and no new
labels are needed — see nexus_os/finetune/rift.py.

Usage:
    python scripts/finetune/rift_rebalance_guard_pairs.py
    python scripts/finetune/rift_rebalance_guard_pairs.py --in PATH --out PATH
    python scripts/finetune/rift_rebalance_guard_pairs.py --check   # dry stats
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from nexus_os.finetune.rift import RIFTConfig, rebalance_pairs  # noqa: E402

DEFAULT_IN = REPO / "datasets" / "finetune" / "guard_dpo_v1_dedup.jsonl"
DEFAULT_OUT = REPO / "datasets" / "finetune" / "guard_rift_v1.jsonl"


def _load_pairs(path: Path) -> list[dict]:
    pairs = []
    with path.open(encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            pair = json.loads(line)
            missing = {"prompt", "chosen", "rejected"} - set(pair)
            if missing:
                raise ValueError(f"{path}:{lineno} missing fields {sorted(missing)}")
            pairs.append(pair)
    return pairs


def _summarize(records: list[dict]) -> str:
    by_label_mass: Counter[str] = Counter()
    by_role: Counter[str] = Counter()
    for r in records:
        by_label_mass[r["meta"].get("label", "?")] += abs(r["reward"])
        by_role[r["meta"]["role"]] += 1
    lines = [f"records: {len(records)} ({dict(by_role)})"]
    lines.append(
        "effective |reward| mass by label: "
        + ", ".join(f"{k}={v:.1f}" for k, v in sorted(by_label_mass.items()))
    )
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--in", dest="src", type=Path, default=DEFAULT_IN)
    ap.add_argument("--out", dest="out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--pos-reward", type=float, default=1.0)
    ap.add_argument("--neg-reward", type=float, default=-0.2)
    ap.add_argument("--no-balance", action="store_true",
                    help="skip inverse-frequency class weighting")
    ap.add_argument("--check", action="store_true",
                    help="print stats only, write nothing")
    args = ap.parse_args()

    if not args.src.exists():
        print(f"ERROR: input not found: {args.src}", file=sys.stderr)
        return 1

    cfg = RIFTConfig(
        pos_reward=args.pos_reward,
        neg_reward=args.neg_reward,
        balance_classes=not args.no_balance,
    )
    pairs = _load_pairs(args.src)
    records = list(rebalance_pairs(pairs, cfg))
    print(f"input pairs: {len(pairs)} "
          f"({dict(Counter((p.get('meta') or {}).get('label', '?') for p in pairs))})")
    print(_summarize(records))

    if args.check:
        return 0

    args.out.parent.mkdir(parents=True, exist_ok=True)
    tmp = args.out.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    tmp.replace(args.out)
    print(f"wrote {len(records)} RIFT records -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
