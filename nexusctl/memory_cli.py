"""Memory operator commands for the canonical nexusctl entry point.

Thin wrapper over `nexus_os.vault.memory_channels` that exposes the 8 vault
channels, the canonical TrustKernel snapshot, and the in-memory record list.
Read-only by default; `--allow-write` is required for `append` so the operator
cannot accidentally drop new intel into a channel.
"""

from __future__ import annotations

import json
import sys
from typing import Any

from nexus_os.vault.memory_channels import (
    ChannelRecord,
    ConsolidationStats,
    FailurePattern,
    MemoryChannel,
    MemoryChannelManager,
    get_manager,
)


# Channel-level write-gate min trust. Must match the values enforced inside
# MemoryChannelManager._check_write_access. Kept here for operator-facing display.
CHANNEL_MIN_TRUST: dict[str, int] = {
    MemoryChannel.SENSORY.value: 0,
    MemoryChannel.WORKING.value: 30,
    MemoryChannel.EPISODIC.value: 50,
    MemoryChannel.SEMANTIC.value: 65,
    MemoryChannel.PROCEDURAL.value: 80,
    MemoryChannel.TRUST.value: 90,
    MemoryChannel.TASK.value: 50,
    MemoryChannel.META.value: 70,
}


def _channel(value: str) -> MemoryChannel:
    """Resolve a CLI-provided channel name into the MemoryChannel enum."""
    try:
        return MemoryChannel(value)
    except ValueError as exc:
        valid = ", ".join(c.value for c in MemoryChannel)
        raise ValueError(f"unknown channel {value!r}; expected one of: {valid}") from exc


def _resolve_agent(agent_id: str | None) -> str:
    """Resolve agent_id, falling back to the active session if unset."""
    if agent_id:
        return agent_id
    return "opencode-operator"


def _record_to_dict(record: ChannelRecord) -> dict[str, Any]:
    """JSON-safe projection of one ChannelRecord."""
    return {
        "record_id": record.record_id,
        "channel": record.channel.value if hasattr(record.channel, "value") else str(record.channel),
        "agent_id": record.agent_id,
        "lane": record.lane,
        "content": record.content,
        "topic_tags": list(record.topic_tags or []),
        "skill_tags": list(record.skill_tags or []),
        "outcome": record.outcome,
        "failure_type": record.failure_type,
        "duration_ms": record.duration_ms,
        "token_count": record.token_count,
        "trust_score": record.trust_score,
        "evidence_count": record.evidence_count,
        "rule_violated": record.rule_violated,
        "severity": record.severity,
        "confidence": record.confidence,
        "task_id": record.task_id,
        "task_status": record.task_status,
        "meta_type": record.meta_type,
        "meta_value": record.meta_value,
        "trace_id": record.trace_id,
        "timestamp": record.timestamp,
        "origin": record.origin,
        "tainted": record.tainted,
        "persistence_score": record.persistence_score,
        "access_count": record.access_count,
        "last_access": record.last_access,
    }


def _stat_to_dict(stats: ConsolidationStats) -> dict[str, Any]:
    return {
        "channel": stats.channel.value if hasattr(stats.channel, "value") else str(stats.channel),
        "total_records": stats.total_records,
        "consolidated_records": stats.consolidated_records,
        "deduplicated_records": stats.deduplicated_records,
        "last_consolidation": stats.last_consolidation,
        "avg_retrieval_time_ms": stats.avg_retrieval_time_ms,
        "retrieval_hit_rate": stats.retrieval_hit_rate,
    }


def _failure_to_dict(fp: FailurePattern) -> dict[str, Any]:
    return {
        "failure_type": fp.failure_type,
        "frequency": fp.frequency,
        "severity": fp.severity,
        "last_occurrence": fp.last_occurrence,
        "lanes_affected": list(fp.lanes_affected or []),
    }


def _print(code: int, payload: dict[str, Any]) -> tuple[int, dict]:
    """Print payload as JSON to stdout and return (code, payload)."""
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False))
    sys.stdout.write("\n")
    return code, payload


def run_memory(args: Any) -> tuple[int, dict]:
    """Top-level dispatcher for `nexusctl memory` subcommands."""
    manager = get_manager()
    subcommand = getattr(args, "memory_command", None)

    if subcommand == "channels":
        return _print(0, _list_channels())

    if subcommand == "trust":
        return _trust_snapshot(manager, args)

    if subcommand == "show":
        return _show(manager, args)

    if subcommand == "stats":
        return _stats(manager, args)

    if subcommand == "failures":
        return _failures(manager, args)

    if subcommand == "append":
        return _append(manager, args)

    return 2, {"error": f"unknown memory command: {subcommand}"}


def _list_channels() -> dict[str, Any]:
    return {
        "channels": [
            {
                "name": ch.value,
                "min_trust": CHANNEL_MIN_TRUST.get(ch.value, 0),
            }
            for ch in MemoryChannel
        ]
    }


def _show(manager: MemoryChannelManager, args: Any) -> tuple[int, dict]:
    try:
        channel = _channel(args.channel)
    except ValueError as exc:
        return _print(2, {"error": str(exc)})
    agent_id = _resolve_agent(args.agent)
    try:
        limit = max(1, min(int(args.limit), 500))
    except (TypeError, ValueError):
        limit = 50
    records = manager.get_records(agent_id, channel, limit=limit)
    return _print(0, {
        "channel": channel.value,
        "agent_id": agent_id,
        "count": len(records),
        "records": [_record_to_dict(r) for r in records],
    })


def _stats(manager: MemoryChannelManager, args: Any) -> tuple[int, dict]:
    out: dict[str, Any] = {"per_channel": []}
    for ch in MemoryChannel:
        stats = manager.get_consolidation_stats(ch)
        out["per_channel"].append(_stat_to_dict(stats))
    if getattr(args, "agent", None):
        out["buffer_summary"] = {
            "agent_id": args.agent,
            "buffers": dict(manager.get_buffer_summary(args.agent)),
        }
    return _print(0, out)


def _failures(manager: MemoryChannelManager, args: Any) -> tuple[int, dict]:
    agent_id = _resolve_agent(args.agent)
    failures = manager.get_failures(agent_id)
    return _print(0, {
        "agent_id": agent_id,
        "failure_count": len(failures),
        "failures": [_failure_to_dict(fp) for fp in failures.values()],
    })


def _trust_snapshot(manager: MemoryChannelManager, args: Any) -> tuple[int, dict]:
    """Print TrustKernel.get_snapshot(agent_id, lane) -- preferred over
    MemoryChannelManager for canonical trust but kept here for ergonomic
    operator access."""
    try:
        from nexus_os.governor.trust_kernel import get_trust_kernel
    except ImportError as exc:  # pragma: no cover
        return _print(2, {"error": f"trust kernel unavailable: {exc}"})
    kernel = get_trust_kernel()
    agent_id = _resolve_agent(args.agent)
    lane = getattr(args, "lane", None) or "general"
    snapshot = kernel.get_snapshot(agent_id, lane)
    return _print(0, {"snapshot": snapshot.to_dict()})


def _append(manager: MemoryChannelManager, args: Any) -> tuple[int, dict]:
    if not getattr(args, "allow_write", False):
        return _print(2, {
            "error": "append requires --allow-write",
            "advice": "this gates accidental channel writes; pass --allow-write on intent",
        })
    try:
        channel = _channel(args.channel)
    except ValueError as exc:
        return _print(2, {"error": str(exc)})
    agent_id = _resolve_agent(args.agent)
    content = (args.content or "").strip()
    if not content:
        return _print(2, {"error": "content is required"})
    min_trust = CHANNEL_MIN_TRUST.get(channel.value, 0)

    method_name = f"append_{channel.value}"
    method = getattr(manager, method_name, None)
    if method is None:
        return _print(2, {"error": f"manager has no {method_name}()"})

    try:
        record = method(agent_id=agent_id, content=content)
    except Exception as exc:
        return _print(2, {"error": f"append failed: {exc}"})

    return _print(0, {
        "appended": True,
        "channel": channel.value,
        "agent_id": agent_id,
        "min_trust": min_trust,
        "record": _record_to_dict(record) if record is not None else None,
    })


def cli_main(argv: list[str] | None = None) -> int:
    """Standalone `python -m nexusctl.memory_cli` entry point."""
    import argparse

    p = argparse.ArgumentParser(prog="nexusctl memory", description=__doc__)
    sub = p.add_subparsers(dest="memory_command", required=True)

    sub.add_parser("channels", help="List 8 vault channels + min-trust gates")

    p_show = sub.add_parser("show", help="Show records in one channel")
    p_show.add_argument("channel", help="channel name (sensory, working, episodic, semantic, procedural, trust, task, meta)")
    p_show.add_argument("--agent", default=None, help="agent id (defaults to 'opencode-operator')")
    p_show.add_argument("--limit", type=int, default=50, help="max records to return")

    p_trust = sub.add_parser("trust", help="Print canonical trust snapshot for an agent/lane")
    p_trust.add_argument("--agent", default=None)
    p_trust.add_argument("--lane", default="general")

    sub.add_parser("stats", help="List consolidation stats per channel")

    p_fail = sub.add_parser("failures", help="List failure patterns recorded for an agent")
    p_fail.add_argument("--agent", default=None)

    p_app = sub.add_parser("append", help="Append one record to a channel (requires --allow-write)")
    p_app.add_argument("channel")
    p_app.add_argument("--content", required=True)
    p_app.add_argument("--agent", default=None)
    p_app.add_argument("--allow-write", action="store_true",
                      help="explicit gate; without it append refuses to run")

    args = p.parse_args(argv)
    code, payload = run_memory(args)
    if getattr(args, "json", True):
        sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False))
        sys.stdout.write("\n")
    return code


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(cli_main())
