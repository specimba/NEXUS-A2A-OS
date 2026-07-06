"""NEXUS Frontier Scanner — orchestrator."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from tools.frontier_scanner.signals.catalog_puller import (
    PROVIDER_PROFILES,
    pull_all_catalogs,
    catalog_summary_text,
)
from tools.frontier_scanner.delta.detect_new import (
    run_delta_pass,
    delta_summary_text,
)
from tools.frontier_scanner.validate.probe import (
    run_probe,
    NIM_HEAVY_COOLDOWN,
)
from tools.frontier_scanner.watchlist.maintain import (
    add_to_watchlist,
    probe_watchlist,
    list_watchlist,
)


def cmd_pull(args) -> int:
    cats = pull_all_catalogs(args.providers, state_dir=Path(args.state_dir))
    print(catalog_summary_text(cats))
    return 0


def cmd_delta(args) -> int:
    reps = run_delta_pass(Path(args.state_dir), args.providers)
    print(delta_summary_text(reps))
    new_ids = []
    for name, r in reps.items():
        for mid in r.new_ids:
            new_ids.append((name, mid, r))
    if args.emit_json:
        out = [
            {"provider": p, "model_id": m, "reason": r.reason}
            for (p, m, r) in new_ids
        ]
        Path(args.emit_json).write_text(json.dumps(out, indent=2, sort_keys=True), encoding="utf-8")
    if new_ids and args.add_to_watchlist:
        for (name, mid, _) in new_ids:
            add_to_watchlist(Path(args.state_dir), name, mid)
        print(f"-- {len(new_ids)} candidates added to watchlist")
    return 0


def cmd_probe(args) -> int:
    res = run_probe(args.provider, args.model, Path(args.state_dir), mode=args.mode)
    print(json.dumps(res.to_json(), indent=2, sort_keys=True))
    return 0


def cmd_watchlist_tick(args) -> int:
    if args.cooldown_provider_nim_heavy:
        last = _last_heavy_timestamp(Path(args.state_dir))
        wait = NIM_HEAVY_COOLDOWN - (time.time() - last)
        if wait > 0:
            print(f"-- rate-limited: waiting {wait:.0f}s for NIM heavy cooldown")
            time.sleep(wait)
    results = probe_watchlist(Path(args.state_dir), providers=args.providers)
    print(f"-- {len(results)} watchlist entries probed")
    return 0


def _last_heavy_timestamp(state_dir: Path) -> float:
    last = 0.0
    for path in state_dir.glob("probe__nvidia__*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            ts = data.get("finished_at", 0.0)
            if ts > last and data.get("latency_ms", 0) > 60_000:
                last = ts
        except (OSError, json.JSONDecodeError):
            continue
    return last


def cmd_show(args) -> int:
    entries = list_watchlist(Path(args.state_dir))
    if not entries:
        print("-- watchlist empty")
        return 0
    for entry in entries:
        status = "GRAD" if entry.graduated else f"p{entry.passes}/f{entry.failures}"
        print(f"{entry.provider}/{entry.model_id} probes={entry.probes} status={status}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="NEXUS Frontier Scanner orchestrator.")
    p.add_argument(
        "--state-dir",
        default=str(Path.home() / ".nexus" / "frontier_scanner"),
        help="Runtime state dir (snapshots/watchlist). Never inside the repo.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sp_pull = sub.add_parser("pull", help="Pull /v1/models from each provider.")
    sp_pull.add_argument("--providers", nargs="*", default=None)
    sp_pull.set_defaults(func=cmd_pull)

    sp_delta = sub.add_parser("delta", help="Diff current vs baseline catalog.")
    sp_delta.add_argument("--providers", nargs="*", default=None)
    sp_delta.add_argument("--emit-json", default=None)
    sp_delta.add_argument("--add-to-watchlist", action="store_true")
    sp_delta.set_defaults(func=cmd_delta)

    sp_probe = sub.add_parser("probe", help="Single-call validation probe.")
    sp_probe.add_argument("--provider", required=True)
    sp_probe.add_argument("--model", required=True)
    sp_probe.add_argument("--mode", choices=("light", "heavy"), default="light")
    sp_probe.set_defaults(func=cmd_probe)

    sp_tick = sub.add_parser("watchlist-tick", help="Run watchlist daily probes.")
    sp_tick.add_argument("--providers", nargs="*", default=None)
    sp_tick.add_argument("--cooldown-provider-nim-heavy", action="store_true")
    sp_tick.set_defaults(func=cmd_watchlist_tick)

    sp_show = sub.add_parser("show-watchlist", help="List watchlist entries.")
    sp_show.set_defaults(func=cmd_show)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args) or 0


if __name__ == "__main__":
    sys.exit(main())
