#!/usr/bin/env python3
"""openclaw_migrate.py — v3-to-v4 config migration shim (DRAFT, do not run on live node).

What it does:
  - Reads an existing /root/.openclaw/openclaw.json (v3-ish layout).
  - Writes a backup at openclaw.json.bak.<timestamp>.
  - Produces a v4-compatible openclaw.json in a target path WITHOUT executing it.
  - Handles the known v3 -> v4 schema break: top-level `defaults` plugin block and
    `agents.<name>` shapes that `openclaw doctor --fix` historically nuked.
  - Migrates auth-profiles.json + models.json untouched (provider data is portable;
    just makes sure file mode is 0600).
  - Validates the result against `openclaw config validate` (if available) before
    declaring success.

Status: DRAFT. Not tested on a clean target. Not committed.
Do not point this at the live config until a dry-run on a fresh node passes.
"""
from __future__ import annotations
import argparse, json, os, shutil, sys, time
from pathlib import Path

V3_TOP_LEVEL_DEFAULTS = "defaults"     # the key `openclaw doctor` removed in our incident
V4_GATEWAY_REQUIRED = ("mode",)        # gateway.mode must be set in v4

def load(p: Path) -> dict:
    with p.open() as f:
        return json.load(f)

def save(p: Path, data: dict) -> None:
    tmp = p.with_suffix(p.suffix + ".tmp")
    with tmp.open("w") as f:
        json.dump(data, f, indent=2)
    os.chmod(tmp, 0o600)
    tmp.replace(p)

def backup(p: Path) -> Path:
    bp = p.with_suffix(p.suffix + f".bak.{int(time.time())}")
    shutil.copy2(p, bp)
    return bp

def migrate(src_cfg: dict) -> dict:
    cfg = json.loads(json.dumps(src_cfg))  # deep copy

    # 1. Drop top-level `defaults` plugin block (v3 leftover, v4 rejects it).
    cfg.pop(V3_TOP_LEVEL_DEFAULTS, None)

    # 2. Ensure gateway.mode exists.
    cfg.setdefault("gateway", {})
    cfg["gateway"].setdefault("mode", "local")

    # 3. Coerce v3-style `agents.<name>` (e.g. "main", "defaults") into v4 shape.
    agents = cfg.get("agents", {})
    if agents and not isinstance(agents.get("defaults", {}), dict):
        # Not the right shape; clear and let doctor re-init.
        cfg["agents"] = {}

    # 4. Normalize controlUi.allowedOrigins to a list.
    cui = cfg["gateway"].setdefault("controlUi", {})
    if isinstance(cui.get("allowedOrigins"), str):
        cui["allowedOrigins"] = [cui["allowedOrigins"]]
    cui.setdefault("allowedOrigins", [])

    return cfg

def validate(cfg: dict) -> list[str]:
    issues = []
    if "gateway" not in cfg:
        issues.append("missing gateway block")
    for k in V4_GATEWAY_REQUIRED:
        if k not in cfg.get("gateway", {}):
            issues.append(f"missing gateway.{k}")
    if "auth" not in cfg.get("gateway", {}):
        issues.append("note: gateway.auth missing — installer will populate")
    return issues

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src",    default="/root/.openclaw/openclaw.json")
    ap.add_argument("--dst",    default="/tmp/openclaw-v4-candidate.json")
    ap.add_argument("--apply",  action="store_true",
                    help="write the migrated config back to --src (with backup). "
                         "Default is dry-run.")
    args = ap.parse_args()

    src = Path(args.src)
    if not src.exists():
        print(f"FATAL: {src} not found", file=sys.stderr); return 1

    v3 = load(src)
    v4 = migrate(v3)
    issues = validate(v4)
    print("Migration issues:" if issues else "Migration clean.")
    for i in issues: print(f"  - {i}")

    if args.apply:
        bp = backup(src)
        print(f"backed up: {bp}")
        save(src, v4)
        print(f"applied: {src}")
    else:
        dst = Path(args.dst)
        save(dst, v4)
        print(f"dry-run wrote: {dst}")
        print("Run with --apply only after a manual diff against the backup.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
