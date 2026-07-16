"""A2A evidence gate — anti-simulation-theatre verification for browser-lane cycles.

A cycle only counts as real when four independent checks agree:
CDP target identity, tail delta, wall-clock sanity, and events.jsonl
byte-offset cross-references. Verdicts: VERIFIED / SIMULATED / UNPROVEN.
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from nexus_os.grounding.models import GroundingEvent

logger = logging.getLogger(__name__)

VERDICT_VERIFIED = "VERIFIED"
VERDICT_SIMULATED = "SIMULATED"
VERDICT_UNPROVEN = "UNPROVEN"

MIN_ELAPSED_SEC = 2.0
DEFAULT_MAX_WAIT_SEC = 900.0
MAX_EPISODE_BYTES = 4096
MAX_EXCERPT_CHARS = 2000
DEFAULT_ARCHIVIST_ROOT = Path("C:/Users/speci.000/Downloads/ARCHIVIST")


@dataclass
class CycleEvidence:
    """One browser-lane cycle's verifiable evidence record."""

    schema: int = 1
    session_id: str = ""
    cycle: int = 0
    lane: str = ""
    agent_id: str = ""
    cdp_target_id: str | None = None
    url: str | None = None
    prompt_sha256: str = ""
    tail_before_sha256: str = ""
    tail_after_sha256: str = ""
    tail_growth: int = 0
    send_ts: str = ""
    response_ts: str = ""
    elapsed_sec: float = 0.0
    wait_status: str = ""
    send_offset: int = -1
    wait_offset: int = -1
    verdict: str = ""
    failures: list[str] = field(default_factory=list)
    success_mode: str = "chat_response"
    artifact_proof: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CycleEvidence":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{key: value for key, value in payload.items() if key in known})


def _parse_ts(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _norm_host(host: str) -> str:
    host = str(host or "").strip().lower()
    return host[4:] if host.startswith("www.") else host


def _host_matches(url: str, expected_host: str) -> bool:
    got = _norm_host(urlparse(url).netloc)
    expected = _norm_host(expected_host)
    if not got or not expected:
        return False
    return got == expected or got.endswith(f".{expected}") or expected.endswith(f".{got}")


def _expected_host(lane_registry: dict, lane: str) -> str | None:
    lanes = lane_registry.get("lanes")
    if isinstance(lanes, list):
        for entry in lanes:
            if isinstance(entry, dict) and entry.get("id") == lane:
                return entry.get("host") or entry.get("required_probe")
        return None
    value = lane_registry.get(lane)
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return value.get("host") or value.get("required_probe")
    return None


def _read_event_at(events_path: Path, offset: int) -> dict | None:
    try:
        with events_path.open("rb") as handle:
            handle.seek(offset)
            raw = handle.readline()
        payload = json.loads(raw.decode("utf-8"))
    except (OSError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


def validate(
    evidence: CycleEvidence,
    events_path: Path,
    lane_registry: dict | None = None,
    *,
    max_wait_sec: float = DEFAULT_MAX_WAIT_SEC,
    probe_only: bool = False,
) -> tuple[str, list[str]]:
    """Recompute the verdict for one cycle from primary evidence. Pure function."""
    if probe_only or evidence.send_offset < 0:
        return VERDICT_UNPROVEN, []

    failures: list[str] = []

    # Check 1 — CDP target identity + lane host binding.
    if not evidence.cdp_target_id:
        failures.append("missing_cdp_target_id")
    if lane_registry is not None:
        expected = _expected_host(lane_registry, evidence.lane)
        if not expected:
            failures.append("lane_not_in_registry")
        elif not evidence.url:
            failures.append("missing_url")
        elif not _host_matches(evidence.url, expected):
            failures.append("url_host_mismatch")

    # Check 2 — tail delta: the conversation surface must actually have grown.
    if not evidence.tail_before_sha256 or not evidence.tail_after_sha256:
        failures.append("missing_tail_hash")
    elif evidence.tail_before_sha256 == evidence.tail_after_sha256:
        failures.append("no_tail_delta")
    if evidence.tail_growth <= 0:
        failures.append("no_tail_growth")

    # Qwen WebDev is successful only when the actual Preview/Code/Deploy
    # surface is visible. A chat token or prose response is not sufficient.
    if evidence.success_mode == "preview_not_chat":
        proof = evidence.artifact_proof
        if (
            not isinstance(proof, dict)
            or proof.get("status") != "PREVIEW_SUCCESS"
            or proof.get("success") is not True
        ):
            failures.append("preview_proof_missing")

    # Check 3 — wall-clock sanity.
    sent = _parse_ts(evidence.send_ts)
    responded = _parse_ts(evidence.response_ts)
    if sent is None or responded is None:
        failures.append("bad_timestamps")
    elif sent >= responded:
        failures.append("clock_not_monotonic")
    if evidence.elapsed_sec < MIN_ELAPSED_SEC:
        failures.append("elapsed_too_fast")
    elif evidence.elapsed_sec > max_wait_sec:
        failures.append("elapsed_exceeds_max_wait")
    if evidence.wait_status != "RESPONSE_READY":
        failures.append("wait_status_not_ready")

    # Check 4 — events.jsonl byte-offset cross-references.
    if not Path(events_path).is_file():
        failures.append("events_file_missing")
    else:
        send_event = _read_event_at(Path(events_path), evidence.send_offset)
        wait_event = _read_event_at(Path(events_path), evidence.wait_offset)
        if (
            send_event is None
            or send_event.get("type") != "SEND_PING"
            or send_event.get("cycle") != evidence.cycle
            or send_event.get("lane") != evidence.lane
        ):
            failures.append("send_event_mismatch")
        if (
            wait_event is None
            or wait_event.get("type") != "WAIT_RESULT"
            or wait_event.get("cycle") != evidence.cycle
            or wait_event.get("lane") != evidence.lane
        ):
            failures.append("wait_event_mismatch")
        if send_event is not None and wait_event is not None:
            send_evt_ts = _parse_ts(send_event.get("ts", ""))
            wait_evt_ts = _parse_ts(wait_event.get("ts", ""))
            if send_evt_ts is None or wait_evt_ts is None or send_evt_ts >= wait_evt_ts:
                failures.append("events_ts_not_monotonic")

    verdict = VERDICT_VERIFIED if not failures else VERDICT_SIMULATED
    if failures:
        logger.warning(
            "A2A evidence gate: %s cycle=%s lane=%s failures=%s",
            verdict,
            evidence.cycle,
            evidence.lane,
            failures,
        )
    return verdict, failures


def to_grounding_event(evidence: CycleEvidence) -> GroundingEvent:
    """Mirror record_collaboration_event.py: one ledger event per gated cycle."""
    payload = evidence.to_dict()
    encoded = json.dumps(payload, ensure_ascii=True, sort_keys=True)
    content_hash = evidence.tail_after_sha256 or hashlib.sha256(
        encoded.encode("utf-8")
    ).hexdigest()
    return GroundingEvent(
        source_id=f"browser_ai.{evidence.lane}",
        path=f"browser-ai://{evidence.lane}/a2a/{evidence.session_id}/{evidence.cycle}",
        size=len(encoded),
        mtime_ns=0,
        content_hash=content_hash,
        source_kind="browser_ai_collaboration",
        evidence_grade="E1" if evidence.verdict == VERDICT_VERIFIED else "E0",
        lifecycle_state="classified",
        trace_id=f"{evidence.session_id}:{evidence.cycle}:{evidence.lane}",
        metadata=payload,
    )


def write_episode(
    evidence: CycleEvidence,
    tail_excerpt: str,
    archivist_root: Path | None = None,
) -> Path:
    """Append one VERIFIED-only episode record to the ARCHIVIST intake sink."""
    if evidence.verdict != VERDICT_VERIFIED:
        raise ValueError(
            f"episodes are VERIFIED-only; refusing verdict={evidence.verdict or 'unset'}"
        )
    root = Path(archivist_root) if archivist_root else DEFAULT_ARCHIVIST_ROOT
    out_dir = root / "EPISODES" / "a2a"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{evidence.session_id}.jsonl"

    excerpt = str(tail_excerpt or "")[:MAX_EXCERPT_CHARS]
    record = {
        "episode_id": f"a2a-{evidence.session_id}-{evidence.cycle:03d}-{evidence.lane}",
        "session": evidence.session_id,
        "cycle": evidence.cycle,
        "lane": evidence.lane,
        "prompt_sha256": evidence.prompt_sha256,
        "response_excerpt": excerpt,
        "response_sha256": evidence.tail_after_sha256,
        "elapsed_sec": evidence.elapsed_sec,
        "verdict": evidence.verdict,
        "success_mode": evidence.success_mode,
        "artifact_status": evidence.artifact_proof.get("status"),
        "evidence": {
            "cdp_target_id": evidence.cdp_target_id,
            "send_offset": evidence.send_offset,
            "wait_offset": evidence.wait_offset,
        },
    }
    encoded = json.dumps(record, ensure_ascii=True, sort_keys=True)
    while len(encoded.encode("utf-8")) > MAX_EPISODE_BYTES and excerpt:
        excerpt = excerpt[: max(0, len(excerpt) - 200)]
        record["response_excerpt"] = excerpt
        encoded = json.dumps(record, ensure_ascii=True, sort_keys=True)
    with out_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(encoded + "\n")
    return out_path
