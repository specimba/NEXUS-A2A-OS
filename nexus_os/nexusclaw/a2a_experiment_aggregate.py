"""Aggregate A2A long-run experiment logs into actionable report."""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

try:
    from nexus_os.nexusclaw.a2a_evidence import (
        VERDICT_SIMULATED,
        VERDICT_UNPROVEN,
        VERDICT_VERIFIED,
        CycleEvidence,
        validate,
    )
except ImportError:  # direct script execution: python a2a_experiment_aggregate.py
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from nexus_os.nexusclaw.a2a_evidence import (
        VERDICT_SIMULATED,
        VERDICT_UNPROVEN,
        VERDICT_VERIFIED,
        CycleEvidence,
        validate,
    )

EVIDENCE_GATE_VERSION = "v1"
DEFAULT_REGISTRY_PATH = Path(__file__).resolve().parent / "browser_lane_registry.json"


def load_events(session_dir: Path) -> list[dict]:
    path = session_dir / "events.jsonl"
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def load_registry(registry_path: Path) -> dict | None:
    if not registry_path.is_file():
        return None
    try:
        return json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--session-dir", required=True)
    ap.add_argument("--registry", default=str(DEFAULT_REGISTRY_PATH))
    args = ap.parse_args(argv)
    session_dir = Path(args.session_dir)
    events_path = session_dir / "events.jsonl"
    events = load_events(session_dir)
    registry = load_registry(Path(args.registry))

    probes_by_lane: dict[str, list[dict]] = defaultdict(list)
    waits: list[dict] = []
    evidence_rows: list[dict] = []
    generating_hits = 0
    send_events = 0
    cycles = set()

    for ev in events:
        if ev.get("type") == "CYCLE_START":
            cycles.add(ev.get("cycle"))
        if ev.get("type") == "SEND_PING":
            send_events += 1
        if ev.get("type") == "PROBE":
            probes_by_lane[ev.get("lane", "?")].append(ev)
            if ev.get("generating"):
                generating_hits += 1
        if ev.get("type") == "WAIT_RESULT":
            w = ev.get("wait") or {}
            waits.append(
                {
                    "lane": ev.get("lane"),
                    "elapsedSec": w.get("elapsedSec"),
                    "status": w.get("status"),
                    "cycle": ev.get("cycle"),
                }
            )
        if ev.get("type") == "CYCLE_EVIDENCE":
            payload = ev.get("evidence") or {}
            try:
                evidence = CycleEvidence.from_dict(payload)
            except TypeError:
                evidence = CycleEvidence(cycle=ev.get("cycle") or 0, lane=ev.get("lane") or "?")
            # NEVER trust the inline verdict — recompute from primary evidence.
            verdict, failures = validate(evidence, events_path, registry)
            evidence_rows.append(
                {
                    "cycle": evidence.cycle,
                    "lane": evidence.lane,
                    "verdict": verdict,
                    "failures": failures,
                    "claimed_verdict": ev.get("verdict"),
                }
            )

    verified_rows = [r for r in evidence_rows if r["verdict"] == VERDICT_VERIFIED]
    simulated_rows = [r for r in evidence_rows if r["verdict"] == VERDICT_SIMULATED]
    unproven_rows = [r for r in evidence_rows if r["verdict"] == VERDICT_UNPROVEN]
    verified_pairs = {(r["cycle"], r["lane"]) for r in verified_rows}
    simulation_suspected = not verified_rows and send_events > 0

    # Median-wait tables come from VERIFIED cycles only.
    wait_by_lane: dict[str, list[float]] = defaultdict(list)
    for w in waits:
        if (w.get("cycle"), w.get("lane")) not in verified_pairs:
            continue
        el = w.get("elapsedSec")
        if isinstance(el, (int, float)) and el > 0:
            wait_by_lane[w.get("lane", "?")].append(float(el))

    lines = []
    if simulation_suspected:
        lines.extend(["STATUS: SIMULATION_SUSPECTED", ""])
    lines.extend(
        [
            "# A2A browser experiment — combined report",
            "",
            f"Generated: {datetime.now(timezone.utc).isoformat()}",
            f"Session: `{session_dir}`",
            f"Cycles observed: {len(cycles)}",
            f"Cycle evidence: total={len(evidence_rows)} verified={len(verified_rows)} "
            f"simulated={len(simulated_rows)} unproven={len(unproven_rows)}",
            f"Generating-state probes: {generating_hits}",
            "",
            "## Median wait (VERIFIED a2a_ping sends only)",
            "",
        ]
    )
    for lane, vals in sorted(wait_by_lane.items()):
        med = statistics.median(vals) if vals else 0
        lines.append(f"- **{lane}**: n={len(vals)} median={med:.0f}s")

    lines.extend(["", f"## Evidence gate ({EVIDENCE_GATE_VERSION})", ""])
    if not evidence_rows:
        lines.append("- No CYCLE_EVIDENCE records found (pre-gate session — treat as unverified).")
    for r in simulated_rows:
        lines.append(
            f"- SIMULATED cycle={r['cycle']} lane={r['lane']} failures={','.join(r['failures']) or '?'}"
        )
    if evidence_rows and not simulated_rows:
        lines.append("- No simulated cycles detected.")

    lines.extend(["", "## Lane reachability (last probe per lane)", ""])
    for lane, plist in sorted(probes_by_lane.items()):
        last = plist[-1] if plist else {}
        u = last.get("url") or last.get("pickUrl") or "?"
        lines.append(
            f"- **{lane}**: url={str(u)[:80]} generating={last.get('generating')} tailLen={last.get('tailLen')}"
        )

    lines.extend(
        [
            "",
            "## Optimization hints",
            "",
            "- Increase `cycleMin` when lanes show `generating=true` often (avoid ping during thought).",
            "- Use `task_class` medians in `lane_timing` for adaptive MaxWaitSec per agent.",
            "- A2A chain: Grok plan tag -> ChatGPT audit -> Zo execute (paste tags; do not blind-nudge).",
            "- GLM: cancel downgrade dialog; retry 5–10s (registry send_policy).",
            "",
        ]
    )

    md = "\n".join(lines)
    out_md = session_dir / "FINAL_REPORT.md"
    out_json = session_dir / "FINAL_REPORT.json"
    out_md.write_text(md, encoding="utf-8")
    out_json.write_text(
        json.dumps(
            {
                "wait_by_lane": {k: statistics.median(v) if v else 0 for k, v in wait_by_lane.items()},
                "generating_hits": generating_hits,
                "cycles": len(cycles),
                "verified_cycles": len(verified_rows),
                "simulated_cycles": len(simulated_rows),
                "unproven_cycles": len(unproven_rows),
                "simulation_suspected": simulation_suspected,
                "evidence_gate": EVIDENCE_GATE_VERSION,
                "simulated": [
                    {"cycle": r["cycle"], "lane": r["lane"], "failures": r["failures"]}
                    for r in simulated_rows
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(md.encode("ascii", errors="replace").decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
