"""Record one prompted Browser-AI collaboration in the grounding ledger."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from nexus_os.grounding.models import GroundingEvent
from nexus_os.grounding.store import GroundingStore


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", type=Path, required=True)
    parser.add_argument("--response-probe", type=Path, required=True)
    parser.add_argument("--grounding-root", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--bridge-state", default="ok")
    args = parser.parse_args()

    prompt = args.prompt.read_bytes()
    response = args.response_probe.read_bytes()
    payload = json.loads(response.decode("utf-8-sig"))
    artifact_names = payload.get("artifactNames", [])
    GroundingStore(args.grounding_root).append(
        GroundingEvent(
            source_id="browser_ai.grok",
            path=f"browser-ai://grok/collaboration/{args.run_id}",
            size=len(prompt) + len(response),
            mtime_ns=0,
            content_hash=digest(prompt + b"\0" + response),
            source_kind="browser_ai_collaboration",
            evidence_grade="E1",
            lifecycle_state="classified",
            trace_id=args.run_id,
            metadata={
                "prompt_hash": f"sha256:{digest(prompt)}",
                "response_fingerprint": f"sha256:{digest(response)}",
                "bridge_state": args.bridge_state,
                "provider": "grok-browser",
                "artifact_names": artifact_names,
                "next_action": "local_review_and_test",
            },
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
