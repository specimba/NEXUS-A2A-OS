"""Persistent entry point for the NEXUS grounding supervisor."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from nexus_os.grounding import GroundingService, GroundingStore
from nexus_os.grounding.native_watcher import watch_grounding


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path)
    parser.add_argument("--poll-seconds", type=int, default=30)
    parser.add_argument("--reconcile-seconds", type=int, default=3600)
    args = parser.parse_args()

    root = args.root or (
        Path(os.environ["LOCALAPPDATA"]) / "NEXUS" / "grounding"
    )
    service = GroundingService(store=GroundingStore(root))
    watch_grounding(
        service,
        fallback_poll_seconds=args.poll_seconds,
        reconcile_seconds=args.reconcile_seconds,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
