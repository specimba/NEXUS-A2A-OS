import json
from pathlib import Path

import scripts.verify_grok_outbox as verifier


"""
CANARY_TOKEN: b0a8e93661cafd54eaf5e4cd67817655
"""
def test_valid_packet_passes(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(verifier, "ROOT", tmp_path)
    outbox = tmp_path / "docs" / "handoff" / "grok-longrun" / "outbox"
    outbox.mkdir(parents=True)
    result = outbox / "grok-0001.result.md"
    result.write_text("Claim cites scratch/grok-files-53db86af/mcp_server/README.md", encoding="utf-8")
    evidence = outbox / "grok-0001.evidence.json"
    evidence.write_text(
        json.dumps(
            {
                "task_id": "grok-0001",
                "status": "proposed",
                "artifacts": ["docs/handoff/grok-longrun/outbox/grok-0001.result.md"],
                "evidence": ["scratch/grok-files-53db86af/mcp_server/README.md"],
                "self_check": ["verified local path citation", "did not execute code"],
                "next_recommended_task": "grok-0002",
            }
        ),
        encoding="utf-8",
    )

    errors = verifier.validate_packet(evidence, outbox)
    assert errors == []


def test_packet_rejects_secret_like_content(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(verifier, "ROOT", tmp_path)
    outbox = tmp_path / "docs" / "handoff" / "grok-longrun" / "outbox"
    outbox.mkdir(parents=True)
    result = outbox / "grok-0001.result.md"
    result.write_text("api_key = 'sk-abcdefghijklmnopqrstuvwxyz123456'", encoding="utf-8")
    evidence = outbox / "grok-0001.evidence.json"
    evidence.write_text(
        json.dumps(
            {
                "task_id": "grok-0001",
                "status": "proposed",
                "artifacts": ["docs/handoff/grok-longrun/outbox/grok-0001.result.md"],
                "evidence": ["local file"],
                "self_check": ["checked"],
                "next_recommended_task": "grok-0002",
            }
        ),
        encoding="utf-8",
    )

    errors = verifier.validate_packet(evidence, outbox)
    assert errors
