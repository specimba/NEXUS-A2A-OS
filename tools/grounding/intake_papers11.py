"""Deterministic Papers11 E0 inventory and E1 source-card intake."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from nexus_os.grounding import GroundingService, GroundingStore


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("papers11", type=Path)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()

    service = GroundingService(
        store=GroundingStore(args.root),
        roots={"papers11": args.papers11},
    )
    result = service.reconcile(stability_delay_seconds=0.0)
    cards = []
    if service.store.cards_path.exists():
        cards = [
            json.loads(line)
            for line in service.store.cards_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    result["papers11"] = {
        "files": len([path for path in args.papers11.iterdir() if path.is_file()]),
        "cards": len(cards),
        "e0": sum(card["evidence_grade"] == "E0" for card in cards),
        "e1_plus": sum(card["evidence_grade"] != "E0" for card in cards),
    }
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
