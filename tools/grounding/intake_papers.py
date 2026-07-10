"""Deterministic E0 inventory and source-card intake for ARCHIVIST PAPERS batches."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

from nexus_os.grounding import GroundingService, GroundingStore


def discover_roots(papers_root: Path, batches: Iterable[str]) -> dict[str, Path]:
    roots: dict[str, Path] = {}
    requested = tuple(batches)
    if requested:
        for name in requested:
            path = papers_root / name
            if path.exists() and path.is_dir():
                roots[name] = path
        return roots
    for path in sorted(papers_root.glob("papers*")):
        if path.is_dir():
            roots[path.name] = path
    return roots


def summarize_batch(path: Path, cards: list[dict]) -> dict[str, int]:
    prefix = str(path)
    batch_cards = [card for card in cards if str(card.get("source_path", "")).startswith(prefix)]
    return {
        "files": len([item for item in path.iterdir() if item.is_file()]),
        "cards": len(batch_cards),
        "e0": sum(card.get("evidence_grade") == "E0" for card in batch_cards),
        "e1_plus": sum(card.get("evidence_grade") != "E0" for card in batch_cards),
    }


def run_intake(papers_root: Path, grounding_root: Path, batches: Iterable[str]) -> dict:
    roots = discover_roots(papers_root, batches)
    service = GroundingService(store=GroundingStore(grounding_root), roots=roots)
    result = service.reconcile(stability_delay_seconds=0.0)
    cards = []
    if service.store.cards_path.exists():
        cards = [
            json.loads(line)
            for line in service.store.cards_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    result["batches"] = {name: summarize_batch(path, cards) for name, path in roots.items()}
    result["promotion_rule"] = "E0 inventory is non-promotable; E1 requires body-derived claim, hash, lane, contradiction status, and adoption gate."
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("papers_root", type=Path)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--batch", action="append", default=[])
    args = parser.parse_args()

    print(json.dumps(run_intake(args.papers_root, args.root, args.batch), indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
