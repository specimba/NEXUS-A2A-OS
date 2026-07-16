"""Append-only continuity ledger for agent and browser-AI runs.

The ledger is intentionally simple JSONL. It is the durable handoff substrate
for "what changed, what was verified, and what should happen next" without
rewriting canonical docs or old `.nexus_pi` state.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from enum import Enum
import hashlib
import json
import os
from pathlib import Path
import time
from contextlib import contextmanager
from typing import Any, Iterable, Mapping


SCHEMA_VERSION = "nexus.continuity.run.v1"

# --- Writer-fence vocabulary (schema v1, additive fields only) ---
VERIFICATION_VERIFIED = "VERIFIED"
VERIFICATION_UNVERIFIED = "UNVERIFIED"
EVIDENCE_GRADE_E0 = "E0"
EVIDENCE_GRADE_E1 = "E1"
PROOF_TOKEN = "NEXUS_PROOF"

ORIGIN_CORE = "core"
ORIGIN_BROWSER = "browser"
ORIGIN_MCP = "mcp"
ORIGIN_LANE = "lane"
KNOWN_ORIGINS = (ORIGIN_CORE, ORIGIN_BROWSER, ORIGIN_MCP, ORIGIN_LANE)
UNTRUSTED_ORIGINS = frozenset({ORIGIN_BROWSER, ORIGIN_MCP, ORIGIN_LANE})

# Presence of this key in a raw JSONL row marks it as written through the
# fenced Python append path; rows lacking it are legacy or foreign-writer rows.
FENCE_MARKER_FIELD = "fenced"

# Structural keys emitted only by the known non-Python ledger writers
# (send_grok_cdp.ps1, lane_stack_preflight.mjs, multi_lane_a2a_cycle.mjs,
# intern_workbench_cdp.mjs, grok_mcp_server_v2 continuity_append).
_FOREIGN_WRITER_KEYS = ("kind", "lane", "proof_token", "agent")


class ProgressClass(str, Enum):
    NOOP_RECAP = "NOOP_RECAP"
    ADVISORY_ONLY = "ADVISORY_ONLY"
    EVIDENCE_DELTA = "EVIDENCE_DELTA"
    IMPLEMENTED_DELTA = "IMPLEMENTED_DELTA"
    VERIFIED_DELTA = "VERIFIED_DELTA"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_ledger_path() -> Path:
    configured = os.environ.get("NEXUS_CONTINUITY_LEDGER")
    if configured:
        return Path(configured)
    canonical = Path.home() / "Downloads" / "NEXUSlogs" / "NEXUScontinuity_runs.jsonl"
    if canonical.exists() or canonical.parent.is_dir():
        return canonical
    local = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / ".nexus")))
    return local / "NEXUS" / "continuity" / "runs.jsonl"


def stable_fingerprint(*parts: str) -> str:
    digest = hashlib.sha256()
    for part in parts:
        digest.update(part.encode("utf-8", errors="replace"))
        digest.update(b"\0")
    return "sha256:" + digest.hexdigest()


def classify_progress(
    *,
    input_fingerprint: str | None,
    output_fingerprint: str | None,
    artifact_paths: Iterable[str] = (),
    tests: Iterable[str] = (),
    provider_calls: int = 0,
    blocker: str | None = None,
    implemented: bool = False,
    advisory_only: bool = False,
) -> ProgressClass:
    artifacts = tuple(p for p in artifact_paths if p)
    test_rows = tuple(t for t in tests if t)
    if test_rows:
        return ProgressClass.VERIFIED_DELTA
    if implemented or artifacts:
        return ProgressClass.IMPLEMENTED_DELTA
    if advisory_only or blocker:
        return ProgressClass.ADVISORY_ONLY
    if provider_calls > 0:
        return ProgressClass.EVIDENCE_DELTA
    if input_fingerprint and output_fingerprint and input_fingerprint != output_fingerprint:
        return ProgressClass.EVIDENCE_DELTA
    return ProgressClass.NOOP_RECAP


@dataclass(frozen=True)
class ContinuityRunRecord:
    run_id: str
    agent_id: str
    source_lane: str
    input_fingerprint: str | None = None
    output_fingerprint: str | None = None
    progress_class: str = ProgressClass.NOOP_RECAP.value
    artifact_paths: tuple[str, ...] = ()
    tests: tuple[str, ...] = ()
    provider_calls: int = 0
    quota_reserved: int = 0
    blocker: str | None = None
    next_action: str | None = None
    started_at: str = field(default_factory=utc_now)
    completed_at: str | None = None
    memory_routes: tuple[str, ...] = ("EPISODIC", "TASK", "META")
    origin: str = ORIGIN_CORE
    verification: str = VERIFICATION_UNVERIFIED
    evidence_grade: str = EVIDENCE_GRADE_E0
    proof_path: str | None = None
    proof: Mapping[str, Any] | None = None
    fenced: bool = False
    fence_reason: str | None = None
    schema: str = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "run_id": self.run_id,
            "agent_id": self.agent_id,
            "source_lane": self.source_lane,
            "input_fingerprint": self.input_fingerprint,
            "output_fingerprint": self.output_fingerprint,
            "progress_class": self.progress_class,
            "artifact_paths": list(self.artifact_paths),
            "tests": list(self.tests),
            "provider_calls": self.provider_calls,
            "quota_reserved": self.quota_reserved,
            "blocker": self.blocker,
            "next_action": self.next_action,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "memory_routes": list(self.memory_routes),
            "origin": self.origin,
            "verification": self.verification,
            "evidence_grade": self.evidence_grade,
            "proof_path": self.proof_path,
            "proof": dict(self.proof) if self.proof is not None else None,
            "fenced": self.fenced,
            "fence_reason": self.fence_reason,
        }

    @classmethod
    def from_mapping(cls, item: Mapping[str, Any]) -> "ContinuityRunRecord":
        run_id = str(item.get("run_id") or "")
        legacy = not run_id
        if legacy:
            # The canonical Downloads ledger predates the typed run schema and
            # contains event-shaped rows (kind/lane/ts) without a run_id. A
            # content-addressed ID makes those rows readable without mutating
            # or pretending they were authored through the governed API.
            canonical = json.dumps(item, sort_keys=True, separators=(",", ":"), default=str)
            run_id = "legacy-sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        timestamp = str(
            item.get("started_at")
            or item.get("ts")
            or item.get("timestamp")
            or "1970-01-01T00:00:00Z"
        )
        progress = item.get("progress_class")
        if not progress:
            status = str(item.get("status") or "").strip().lower()
            evidence_keys = ("evidence", "proof", "verify", "changes", "milestone", "deliverable")
            if any(key in item for key in evidence_keys):
                progress = ProgressClass.EVIDENCE_DELTA.value
            elif status in {"blocked", "error", "failed", "failure", "halted"}:
                progress = ProgressClass.ADVISORY_ONLY.value
            else:
                progress = ProgressClass.NOOP_RECAP.value
        return cls(
            run_id=run_id,
            agent_id=str(item.get("agent_id") or item.get("agent") or item.get("kind") or "legacy-writer"),
            source_lane=str(item.get("source_lane") or item.get("lane") or item.get("kind") or "legacy"),
            input_fingerprint=item.get("input_fingerprint"),
            output_fingerprint=item.get("output_fingerprint"),
            progress_class=str(progress),
            artifact_paths=tuple(str(v) for v in item.get("artifact_paths", []) or ()),
            tests=tuple(str(v) for v in item.get("tests", []) or ()),
            provider_calls=int(item.get("provider_calls", 0) or 0),
            quota_reserved=int(item.get("quota_reserved", 0) or 0),
            blocker=item.get("blocker"),
            next_action=item.get("next_action") or (str(item.get("kind")) if item.get("kind") else None),
            started_at=timestamp,
            completed_at=item.get("completed_at"),
            memory_routes=tuple(str(v) for v in item.get("memory_routes", []) or ("EPISODIC", "TASK", "META")),
            origin=classify_origin(item),
            verification=str(item.get("verification") or VERIFICATION_UNVERIFIED),
            evidence_grade=str(item.get("evidence_grade") or EVIDENCE_GRADE_E0),
            proof_path=str(item.get("proof_path")) if item.get("proof_path") else None,
            proof=(item.get("proof") if isinstance(item.get("proof"), Mapping) else None),
            fenced=bool(item.get("fenced", False)),
            fence_reason=item.get("fence_reason"),
            schema=str(item.get("schema") or ("nexus.continuity.legacy.v0" if legacy else SCHEMA_VERSION)),
        )


def classify_writer_identity(agent_id: str | None) -> str:
    """Classify writer origin from the writer identity (agent_id).

    Governed core writers (codex/claude/nexusctl operators) stay ``core``.
    Identities that name browser lanes, CDP bridges, or MCP servers are
    untrusted for verification claims.
    """
    ident = (agent_id or "").strip().lower()
    if not ident:
        return ORIGIN_CORE
    if "mcp" in ident:
        return ORIGIN_MCP
    if "a2a" in ident or "lane" in ident:
        return ORIGIN_LANE
    if any(tok in ident for tok in ("browser", "cdp", "grok", "gemini", "qwen", "chatgpt")):
        return ORIGIN_BROWSER
    return ORIGIN_CORE


def classify_origin(item: Mapping[str, Any]) -> str:
    """Classify the origin of a raw ledger mapping (read side).

    An explicit ``origin`` field wins. Otherwise structural keys used only by
    the non-Python browser/MCP/lane writers mark the row untrusted, then the
    writer-identity heuristic applies.
    """
    explicit = str(item.get("origin") or "").strip().lower()
    if explicit in KNOWN_ORIGINS:
        return explicit
    if explicit:
        return ORIGIN_BROWSER
    if any(key in item for key in _FOREIGN_WRITER_KEYS):
        ident = str(item.get("agent") or item.get("kind") or "").lower()
        if "mcp" in ident:
            return ORIGIN_MCP
        if "a2a" in ident or ident.startswith("lane"):
            return ORIGIN_LANE
        return ORIGIN_BROWSER
    return classify_writer_identity(str(item.get("agent_id") or ""))


def proof_attached(record: "ContinuityRunRecord") -> bool:
    """True when the record carries a real proof artifact.

    Accepted proofs: a ``proof_path`` that exists on disk, a ``proof`` payload
    containing a NEXUS_PROOF token string, a nested existing ``proof_path``,
    or a sha256-bearing evidence dict. A bare boolean claim (e.g. the
    ``proof_token: true`` flag some lane writers emit) is not proof.
    """
    if record.proof_path:
        try:
            if Path(record.proof_path).exists():
                return True
        except OSError:
            pass
    proof = record.proof
    if isinstance(proof, Mapping) and proof:
        nested = proof.get("proof_path")
        if nested:
            try:
                if Path(str(nested)).exists():
                    return True
            except OSError:
                pass
        for value in proof.values():
            if isinstance(value, str) and PROOF_TOKEN in value:
                return True
        if any(key in proof for key in ("sha256", "artifact_sha256")):
            return True
    return False


def fence_record(record: "ContinuityRunRecord", *, marker_present: bool = True) -> "ContinuityRunRecord":
    """Apply the continuity writer fence (schema v1, additive).

    Rows originating from browser/MCP/lane writers are structurally capped at
    UNVERIFIED/E0 unless a proof artifact is attached, in which case they are
    eligible for E1. Downgrades are never silent: the returned record carries
    ``fenced=True`` and a ``fence_reason``. On the read side, rows lacking the
    fence marker (legacy or foreign writers) receive the same cap; rows that
    claim nothing above the floor pass through unchanged (legacy tolerance).
    """
    untrusted = record.origin in UNTRUSTED_ORIGINS
    if not untrusted and marker_present:
        return record

    claims_verification = record.verification not in ("", VERIFICATION_UNVERIFIED)
    claims_grade = record.evidence_grade not in ("", EVIDENCE_GRADE_E0)
    claims_delta = record.progress_class == ProgressClass.VERIFIED_DELTA.value

    if proof_attached(record):
        eligible = (
            claims_verification
            or claims_grade
            or claims_delta
            or record.evidence_grade == EVIDENCE_GRADE_E1
        )
        target_grade = EVIDENCE_GRADE_E1 if eligible else EVIDENCE_GRADE_E0
        if record.evidence_grade == target_grade:
            return record
        if record.evidence_grade in (EVIDENCE_GRADE_E0, EVIDENCE_GRADE_E1):
            return replace(record, evidence_grade=target_grade)
        return replace(
            record,
            evidence_grade=EVIDENCE_GRADE_E1,
            fenced=True,
            fence_reason=(
                f"writer fence: origin={record.origin} claimed evidence_grade="
                f"{record.evidence_grade}; capped to E1 (proof attached)"
            ),
        )

    if not (claims_verification or claims_grade or claims_delta):
        return record  # already at the UNVERIFIED/E0 floor; the cap is identity

    reasons = []
    if claims_verification:
        reasons.append(f"verification={record.verification}")
    if claims_delta:
        reasons.append(f"progress_class={record.progress_class}")
    if claims_grade:
        reasons.append(f"evidence_grade={record.evidence_grade}")
    cause = (
        f"untrusted origin {record.origin}"
        if untrusted
        else "missing fence marker (legacy/foreign row)"
    )
    return replace(
        record,
        verification=VERIFICATION_UNVERIFIED,
        evidence_grade=EVIDENCE_GRADE_E0,
        progress_class=(
            ProgressClass.EVIDENCE_DELTA.value if claims_delta else record.progress_class
        ),
        fenced=True,
        fence_reason=(
            "writer fence: " + ", ".join(reasons)
            + f" claimed without proof ({cause}); capped to UNVERIFIED/E0"
        ),
    )


def prepare_record(
    record: ContinuityRunRecord,
    *,
    origin: str | None = None,
) -> ContinuityRunRecord:
    """Normalize writer identity and apply the proof fence before append.

    Kept public so CLI and other callers can return the exact persisted row
    instead of an optimistic pre-fence representation.
    """
    if origin is not None:
        normalized = str(origin).strip().lower()
        if normalized not in KNOWN_ORIGINS:
            normalized = ORIGIN_BROWSER
        if normalized != record.origin:
            record = replace(record, origin=normalized)
    elif record.origin == ORIGIN_CORE:
        inferred = classify_writer_identity(record.agent_id)
        if inferred != record.origin:
            record = replace(record, origin=inferred)
    return fence_record(record)


@contextmanager
def _ledger_lock(ledger: Path, *, timeout_seconds: float = 10.0):
    """Cross-process advisory lock using a stable sibling lock file."""
    lock_path = ledger.with_name(ledger.name + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = lock_path.open("a+b")
    handle.seek(0, os.SEEK_END)
    if handle.tell() == 0:
        handle.write(b"\0")
        handle.flush()
    handle.seek(0)
    deadline = time.monotonic() + timeout_seconds
    acquired = False
    try:
        if os.name == "nt":
            import msvcrt

            while not acquired:
                try:
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    acquired = True
                except OSError:
                    if time.monotonic() >= deadline:
                        raise TimeoutError(f"timed out locking continuity ledger: {ledger}")
                    time.sleep(0.025)
        else:  # pragma: no cover - exercised by Linux CI
            import fcntl

            while not acquired:
                try:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    acquired = True
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        raise TimeoutError(f"timed out locking continuity ledger: {ledger}")
                    time.sleep(0.025)
        yield
    finally:
        if acquired:
            if os.name == "nt":
                import msvcrt

                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:  # pragma: no cover - exercised by Linux CI
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


def append_record(
    record: ContinuityRunRecord,
    path: str | Path | None = None,
    *,
    origin: str | None = None,
) -> Path:
    record = prepare_record(record, origin=origin)
    ledger = Path(path) if path else default_ledger_path()
    ledger.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(record.to_dict(), sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    with _ledger_lock(ledger):
        with ledger.open("ab") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    return ledger


def read_records(path: str | Path | None = None, *, limit: int | None = None) -> tuple[list[ContinuityRunRecord], dict[str, Any]]:
    ledger = Path(path) if path else default_ledger_path()
    meta: dict[str, Any] = {"path": str(ledger), "exists": ledger.exists(), "corrupt_tail": False, "errors": []}
    if not ledger.exists():
        return [], meta
    records: list[ContinuityRunRecord] = []
    with ledger.open("r", encoding="utf-8") as handle:
        if limit is not None:
            from collections import deque
            line_iter: Iterable = deque(handle, maxlen=limit)
        else:
            line_iter = handle
        for index, line in enumerate(line_iter, start=1):
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
                if not isinstance(raw, Mapping):
                    raise ValueError("continuity row must be a JSON object")
                record = ContinuityRunRecord.from_mapping(raw)
                records.append(fence_record(record, marker_present=FENCE_MARKER_FIELD in raw))
            except (json.JSONDecodeError, ValueError) as exc:
                meta["corrupt_tail"] = True
                meta["errors"].append({"line": index, "error": str(exc)})
    return records, meta


def summarize_records(records: Iterable[ContinuityRunRecord]) -> dict[str, Any]:
    rows = list(records)
    progress_counts: dict[str, int] = {}
    provider_calls = 0
    fenced_records = 0
    blockers: dict[str, int] = {}
    for record in rows:
        progress_counts[record.progress_class] = progress_counts.get(record.progress_class, 0) + 1
        provider_calls += record.provider_calls
        if record.fenced:
            fenced_records += 1
        if record.blocker:
            blockers[record.blocker] = blockers.get(record.blocker, 0) + 1
    return {
        "record_count": len(rows),
        "progress_counts": progress_counts,
        "provider_calls": provider_calls,
        "fenced_records": fenced_records,
        "blockers": blockers,
        "last_record": rows[-1].to_dict() if rows else None,
    }


def records_since(records: Iterable[ContinuityRunRecord], *, hours: float) -> list[ContinuityRunRecord]:
    threshold = datetime.now(timezone.utc) - timedelta(hours=hours)
    selected: list[ContinuityRunRecord] = []
    for record in records:
        stamp = record.completed_at or record.started_at
        try:
            parsed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        except ValueError:
            continue
        if parsed >= threshold:
            selected.append(record)
    return selected


def legacy_state_refs(repo_root: Path | None = None) -> list[dict[str, Any]]:
    roots = []
    if repo_root:
        roots.append(repo_root / ".nexus_pi" / "state")
    roots.append(Path.home() / ".nexus_pi" / "state")
    refs: list[dict[str, Any]] = []
    seen: set[str] = set()
    for root in roots:
        if str(root) in seen:
            continue
        seen.add(str(root))
        if not root.exists():
            refs.append({"path": str(root), "exists": False, "files": []})
            continue
        files = [
            {
                "path": str(path),
                "size": path.stat().st_size,
                "mtime": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat().replace("+00:00", "Z"),
            }
            for path in sorted(root.glob("*.json"))
        ]
        refs.append({"path": str(root), "exists": True, "files": files})
    return refs
