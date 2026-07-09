#!/usr/bin/env python3
"""Allocate / write NEXUSbuildubuntuGROK45logs-NN.txt under the NEXUSlogs vault.

Hard rule: NEXUSLOGS-GB-001 (docs/policies/NEXUSLOGS_GROK45_LOGGING.md).
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

DEFAULT_VAULT = Path(r"C:\Users\speci.000\Downloads\NEXUSlogs")
WSL_VAULT = Path("/mnt/c/Users/speci.000/Downloads/NEXUSlogs")
PREFIX = "NEXUSbuildubuntuGROK45logs-"
PATTERN = re.compile(r"^NEXUSbuildubuntuGROK45logs-(\d+)\.txt$")
SOFT_MAX = 1500
HARD_MAX = 3000


def vault_path() -> Path:
    if WSL_VAULT.is_dir():
        return WSL_VAULT
    return DEFAULT_VAULT


def next_index(vault: Path) -> int:
    highest = 0
    for p in vault.glob(f"{PREFIX}*.txt"):
        m = PATTERN.match(p.name)
        if m:
            highest = max(highest, int(m.group(1)))
    return highest + 1


def part_path(vault: Path, index: int) -> Path:
    return vault / f"{PREFIX}{index:02d}.txt"


def count_lines(text: str) -> int:
    if not text:
        return 0
    return text.count("\n") + (0 if text.endswith("\n") else 1)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--vault", type=Path, default=None)
    ap.add_argument("--status", action="store_true", help="Print next free index and exit")
    ap.add_argument("--write", type=Path, help="Copy draft file into next log part")
    ap.add_argument("--stdin", action="store_true", help="Read draft from stdin")
    ap.add_argument("--force-index", type=int, default=None, help="Write specific index (must not exist)")
    args = ap.parse_args(argv)

    vault = args.vault or vault_path()
    vault.mkdir(parents=True, exist_ok=True)

    if args.status:
        n = next_index(vault)
        print(f"vault={vault}")
        print(f"next_index={n:02d}")
        print(f"next_path={part_path(vault, n)}")
        print(f"soft_max_lines={SOFT_MAX}")
        print(f"hard_max_lines={HARD_MAX}")
        return 0

    if not args.write and not args.stdin:
        ap.error("provide --status, --write PATH, or --stdin")

    if args.stdin:
        draft = sys.stdin.read()
    else:
        draft = args.write.read_text(encoding="utf-8", errors="replace")

    lines = count_lines(draft)
    if lines > HARD_MAX:
        print(
            f"ERROR: draft has {lines} lines > hard max {HARD_MAX}. "
            "Split into multiple parts before writing.",
            file=sys.stderr,
        )
        return 2
    if lines > SOFT_MAX:
        print(
            f"WARNING: draft has {lines} lines > soft max {SOFT_MAX}. "
            "Prefer splitting for reviewability.",
            file=sys.stderr,
        )

    idx = args.force_index if args.force_index is not None else next_index(vault)
    dest = part_path(vault, idx)
    if dest.exists():
        print(f"ERROR: refuses overwrite of existing {dest}", file=sys.stderr)
        return 3

    dest.write_text(draft if draft.endswith("\n") else draft + "\n", encoding="utf-8")
    print(f"wrote {dest} lines={count_lines(dest.read_text(encoding='utf-8'))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
