"""Append one Browser-AI director outro to the durable grounding ledger."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from nexus_os.grounding.models import GroundingEvent
from nexus_os.grounding.store import GroundingStore


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--memory", type=Path, required=True)
    parser.add_argument("--grounding-root", type=Path, required=True)
    args = parser.parse_args()

    lines = [
        line for line in args.memory.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not lines:
        return 2
    record = json.loads(lines[-1])
    encoded = json.dumps(record, ensure_ascii=True, sort_keys=True).encode("utf-8")
    run_id = str(record["run_id"])
    GroundingStore(args.grounding_root).append(
        GroundingEvent(
            source_id="browser_ai.grok",
            path=f"browser-ai://grok/{run_id}",
            size=len(encoded),
            mtime_ns=0,
            content_hash=hashlib.sha256(encoded).hexdigest(),
            source_kind="browser_ai_cycle",
            evidence_grade="E1",
            lifecycle_state="classified",
            trace_id=run_id,
            metadata={
                "action": record.get("action"),
                "visible_fingerprint": record.get("visible_fingerprint"),
                "bridge_tools": record.get("bridge_tools", []),
                "provider": record.get("provider", "none"),
                "provider_calls": record.get("provider_calls", 0),
                "blocker": record.get("blocker"),
                "next_action": record.get("next_action"),
            },
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
