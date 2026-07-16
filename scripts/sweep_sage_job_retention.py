"""One-shot, scheduler-safe retention sweep for NEXUS SAGE proposal jobs."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from typing import Sequence

from nexus_os.sage_gateway.jobs import (
    sage_job_database_identity,
    sage_job_database_path,
    sweep_expired_sage_jobs,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Report expired SAGE job records. Use --apply to purge only records "
            "whose expires_at timestamp has passed."
        )
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="atomically purge expired jobs and idempotency records",
    )
    return parser


def _failure_report(*, database, apply: bool) -> dict[str, object]:
    return {
        "schema": "nexus.sage-retention-sweep.v1",
        "ok": False,
        "state": "failed",
        "mode": "apply" if apply else "dry_run",
        "applied": False,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": sage_job_database_identity(database),
        "error_code": "sage_retention_sweep_failed",
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    database = sage_job_database_path()
    try:
        report = sweep_expired_sage_jobs(database, apply=args.apply)
    except Exception:
        report = _failure_report(database=database, apply=args.apply)
        print(json.dumps(report, sort_keys=True, separators=(",", ":")))
        return 2

    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
