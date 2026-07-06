"""Live REASONS-DB feed for the reasoning engine (FI-T → W1 wiring).

Bridges the trace capture pipeline into pattern extraction: reads the
TRAINABLE partition of ~/.nexus/reasons_db and yields records in the
CoT-entry shape PatternExtractor.parse_trajectory expects
({uid, source_file, session, model, context}).

Hard gates (belt-and-braces on top of the write-time partition):
- a base path that points inside a reference partition raises;
- any record whose license_class is not "permissive" is skipped even if
  found inside the trainable directory;
- records carrying credential-class redaction flags are skipped — a
  redacted key means the surrounding reasoning context is tainted for
  training (email/IP fingerprints are anonymous and pass).

The static fable5_cot_merged.jsonl corpus is REFERENCE/EVAL-ONLY per the
FI plan and must never be merged with output of this module.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Iterator

#: redaction flags that taint a record for training. Fingerprinted
#: emails/IPs are anonymous and acceptable.
_TAINTING_FLAG_MARKERS = ("KEY", "PAT", "TOKEN", "JWT")

_ALLOWED_FLAGS = {"REDACTED_EMAIL", "REDACTED_IP"}


def _default_base() -> Path:
    return Path(os.environ.get(
        "NEXUS_REASONS_DB", Path.home() / ".nexus" / "reasons_db"
    ))


def _is_tainted(flags: list[str]) -> bool:
    for flag in flags:
        if flag in _ALLOWED_FLAGS:
            continue
        if any(marker in flag for marker in _TAINTING_FLAG_MARKERS):
            return True
        # unrecognized flag → fail safe
        return True
    return False


def iter_trainable_records(base_dir: Path | None = None) -> Iterator[Dict[str, Any]]:
    """Yield CoT-shaped dicts from the trainable partition ONLY."""
    from nexus_os.relay.tracing.record import TraceWriter

    base = Path(base_dir) if base_dir is not None else _default_base()
    if "reference" in {p.lower() for p in base.parts}:
        raise ValueError(
            "trace_source refuses reference-partition paths — "
            "restricted/unknown-license traces never train"
        )
    trainable = base / "trainable"
    if not trainable.exists():
        return
    writer = TraceWriter(base_dir=trainable)
    try:
        for rec in writer.iter_all():
            if rec.license_class != "permissive":
                continue  # belt-and-braces: partition alone is not trusted
            if _is_tainted(rec.redaction_flags):
                continue  # FI-T3 preview: dirty records don't train
            for attempt in rec.models_tried:
                if attempt.outcome not in ("ok",):
                    continue
                context_parts = [f"USER: {rec.request_subject}"]
                assistant = ""
                if attempt.reasoning_content:
                    assistant += attempt.reasoning_content
                if attempt.message_content:
                    assistant += ("\n" if assistant else "") + attempt.message_content
                if not assistant.strip():
                    continue
                context_parts.append(f"ASSISTANT: {assistant}")
                yield {
                    "uid": rec.trace_id,
                    "source_file": "reasons_db/trainable",
                    "session": rec.session_id or "",
                    "model": f"{attempt.provider}/{attempt.model_id}",
                    "context": "\n".join(context_parts),
                }
    finally:
        writer.close()


def extract_patterns_from_traces(
    base_dir: Path | None = None, limit: int = 500
):
    """ReasoningPatterns extracted from live trainable traces."""
    from nexus_os.reasoning.pattern_extractor import PatternExtractor

    extractor = PatternExtractor(cot_file_path="")  # string ops only
    patterns = []
    for i, entry in enumerate(iter_trainable_records(base_dir)):
        if i >= limit:
            break
        trajectory = extractor.parse_trajectory(entry["context"])
        for p in extractor.extract_patterns(trajectory):
            p.source_uid = entry["uid"]
            patterns.append(p)
    return patterns
