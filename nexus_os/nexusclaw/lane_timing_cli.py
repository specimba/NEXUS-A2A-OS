"""CLI for lane timing store."""
from __future__ import annotations

import argparse
import json
import sys

from nexus_os.nexusclaw.lane_timing import (
    median_elapsed,
    record_from_wait_json,
    suggest_max_wait_sec,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    rec = sub.add_parser("record")
    rec.add_argument("--task-class", default="general")
    rec.add_argument("--json", required=True)

    sug = sub.add_parser("suggest-wait")
    sug.add_argument("agent_id")
    sug.add_argument("task_class")

    med = sub.add_parser("median")
    med.add_argument("agent_id")
    med.add_argument("task_class")

    args = parser.parse_args(argv)
    if args.cmd == "record":
        payload = json.loads(args.json)
        record_from_wait_json(payload, task_class=args.task_class)
        return 0
    if args.cmd == "suggest-wait":
        print(int(suggest_max_wait_sec(args.agent_id, args.task_class)))
        return 0
    if args.cmd == "median":
        m = median_elapsed(args.agent_id, args.task_class)
        print(m if m is not None else "")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())