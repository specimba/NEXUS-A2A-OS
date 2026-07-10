"""nexusctl continuity commands."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from nexus_os.continuity.records import (
    ContinuityRunRecord,
    EVIDENCE_GRADE_E0,
    EVIDENCE_GRADE_E1,
    ProgressClass,
    VERIFICATION_UNVERIFIED,
    VERIFICATION_VERIFIED,
    append_record,
    classify_progress,
    default_ledger_path,
    legacy_state_refs,
    read_records,
    records_since,
    stable_fingerprint,
    summarize_records,
    utc_now,
)


def _repo_root() -> Path:
    current = Path.cwd().resolve()
    for path in (current, *current.parents):
        if (path / ".git").exists():
            return path
    return current


def _split_values(values: list[str] | None) -> tuple[str, ...]:
    return tuple(v for v in (values or []) if v)


def run_continuity(args: Any) -> tuple[int, dict[str, Any]]:
    command = args.continuity_command
    ledger = default_ledger_path()

    if command == "status":
        records, meta = read_records(ledger)
        payload = {
            "status": "ok" if not meta["corrupt_tail"] else "degraded",
            "command": "continuity status",
            "ledger": meta,
            "summary": summarize_records(records),
            "legacy_refs": legacy_state_refs(_repo_root()),
        }
        return 0 if not meta["corrupt_tail"] else 2, payload

    if command == "coverage":
        records, meta = read_records(ledger)
        window_records = records_since(records, hours=args.hours)
        payload = {
            "status": "ok" if window_records else "degraded",
            "command": "continuity coverage",
            "hours": args.hours,
            "ledger": meta,
            "summary": summarize_records(window_records),
            "required_progress_classes": [item.value for item in ProgressClass],
        }
        return 0 if window_records else 2, payload

    if command == "open":
        now = utc_now()
        fingerprint = args.input_fingerprint or stable_fingerprint(args.agent_id, args.source_lane, now)
        record = ContinuityRunRecord(
            run_id=args.run_id,
            agent_id=args.agent_id,
            source_lane=args.source_lane,
            input_fingerprint=fingerprint,
            output_fingerprint=fingerprint,
            progress_class=ProgressClass.NOOP_RECAP.value,
            next_action=args.next_action or "run_opened",
            started_at=now,
            completed_at=None,
            memory_routes=("TASK", "META"),
        )
        path = append_record(record, ledger, origin=getattr(args, "origin", None))
        return 0, {"status": "ok", "command": "continuity open", "ledger": str(path), "record": record.to_dict()}

    if command == "close":
        artifacts = _split_values(args.artifact)
        tests_run = _split_values(args.test)
        progress = classify_progress(
            input_fingerprint=args.input_fingerprint,
            output_fingerprint=args.output_fingerprint,
            artifact_paths=artifacts,
            tests=tests_run,
            provider_calls=args.provider_calls,
            blocker=args.blocker,
            implemented=args.implemented,
            advisory_only=args.advisory_only,
        )
        verification = (
            VERIFICATION_VERIFIED
            if progress is ProgressClass.VERIFIED_DELTA
            else VERIFICATION_UNVERIFIED
        )
        evidence_grade = EVIDENCE_GRADE_E1 if (artifacts or tests_run) else EVIDENCE_GRADE_E0
        record = ContinuityRunRecord(
            run_id=args.run_id,
            agent_id=args.agent_id,
            source_lane=args.source_lane,
            input_fingerprint=args.input_fingerprint,
            output_fingerprint=args.output_fingerprint,
            progress_class=progress.value,
            artifact_paths=artifacts,
            tests=tests_run,
            provider_calls=args.provider_calls,
            quota_reserved=args.quota_reserved,
            blocker=args.blocker,
            next_action=args.next_action,
            started_at=args.started_at or utc_now(),
            completed_at=utc_now(),
            verification=verification,
            evidence_grade=evidence_grade,
            proof_path=getattr(args, "proof_path", None),
        )
        path = append_record(record, ledger, origin=getattr(args, "origin", None))
        return 0, {"status": "ok", "command": "continuity close", "ledger": str(path), "record": record.to_dict()}

    if command == "resume-plan":
        records, meta = read_records(ledger, limit=20)
        latest = records[-1] if records else None
        payload = {
            "status": "ok" if latest else "blocked",
            "command": "continuity resume-plan",
            "ledger": meta,
            "latest": latest.to_dict() if latest else None,
            "resume_plan": {
                "source_lane": latest.source_lane if latest else None,
                "next_action": latest.next_action if latest else "no continuity records found",
                "blocker": latest.blocker if latest else "missing_ledger",
                "provider_calls_allowed": False if latest and latest.progress_class == ProgressClass.NOOP_RECAP.value else None,
            },
        }
        return 0 if latest else 2, payload

    return 2, {"status": "blocked", "error": f"unknown continuity command: {command}"}

