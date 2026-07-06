"""CLI for the A2A evidence gate."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from nexus_os.grounding.store import GroundingStore
from nexus_os.nexusclaw.a2a_evidence import (
    DEFAULT_MAX_WAIT_SEC,
    VERDICT_VERIFIED,
    CycleEvidence,
    to_grounding_event,
    validate,
    write_episode,
)

DEFAULT_REGISTRY_PATH = Path(__file__).resolve().parent / "browser_lane_registry.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    ver = sub.add_parser("verify")
    ver.add_argument("--json", required=True)
    ver.add_argument("--events", required=True)
    ver.add_argument("--registry", default=None)
    ver.add_argument("--grounding-root", default=None)
    ver.add_argument("--archivist-root", default=None)
    ver.add_argument("--tail-excerpt", default="")
    ver.add_argument("--max-wait-sec", type=float, default=DEFAULT_MAX_WAIT_SEC)

    args = parser.parse_args(argv)
    if args.cmd == "verify":
        evidence = CycleEvidence.from_dict(json.loads(args.json))
        registry = None
        registry_path = Path(args.registry) if args.registry else DEFAULT_REGISTRY_PATH
        if registry_path.is_file():
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
        verdict, failures = validate(
            evidence,
            Path(args.events),
            registry,
            max_wait_sec=args.max_wait_sec,
        )
        evidence.verdict = verdict
        evidence.failures = failures
        if verdict == VERDICT_VERIFIED:
            grounding_root = Path(args.grounding_root) if args.grounding_root else None
            GroundingStore(grounding_root).append(to_grounding_event(evidence))
            archivist_root = Path(args.archivist_root) if args.archivist_root else None
            write_episode(evidence, args.tail_excerpt, archivist_root)
        print(json.dumps({"verdict": verdict, "failures": failures}))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
