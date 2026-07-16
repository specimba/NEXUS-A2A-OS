#!/usr/bin/env python3
r"""
NEXUS OCR -> Continuity writer (local, no GPU, stdlib only)
===========================================================
Reads workspace OCR facts / agent_brief and writes durable continuity files
for Intern / multi-agent handoff.

Outputs (repo-local, resource-light):
  scratch/continuity/OCR_FACTS_LATEST.json
  scratch/continuity/SESSION_PROGRESS_LATEST.md
  scratch/continuity/MISSION_STATUS.md
  scratch/continuity/history/ocr_facts_YYYYMMDDTHHMMSS.json

Optional: copy pointers under Downloads/NEXUSlogs/_runs/GROK/YYYYMMDD/ if present.

Usage:
  python scripts/ocr/ocr_to_continuity.py
  python scripts/ocr/ocr_to_continuity.py --from-json path\to\result.ocr.json
  python scripts/ocr/ocr_to_continuity.py --source-image C:\...\shot.png
"""

from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(r"C:\Users\speci.000\Documents\NEXUS")
SCREENSHOTS = REPO / "scratch" / "screenshots"
CONTINUITY = REPO / "scratch" / "continuity"
HISTORY = CONTINUITY / "history"
LATEST_JSON = SCREENSHOTS / "OCR_RESULT_LATEST.json"
NEXUSLOGS = Path(r"C:\Users\speci.000\Downloads\NEXUSlogs")


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _local_now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def load_ocr_payload(path: Path | None = None) -> dict[str, Any]:
    p = path or LATEST_JSON
    if not p.exists():
        raise FileNotFoundError(f"No OCR payload at {p}")
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("OCR payload must be a JSON object")
    return data


def _clean_fact_str(v: Any) -> str:
    s = re.sub(r"\s+", " ", str(v or "").replace("\r", " ")).strip()
    return s[:200]


def extract_facts_bundle(payload: dict[str, Any], source_image: str | None = None) -> dict[str, Any]:
    r = payload.get("result") if isinstance(payload.get("result"), dict) else {}
    facts = payload.get("facts") or r.get("facts") or {}
    brief = (payload.get("agent_brief") or r.get("agent_brief") or "").strip()
    if not isinstance(facts, dict):
        facts = {}

    cleaned_facts = {k: _clean_fact_str(v) for k, v in facts.items() if _clean_fact_str(v)}
    # Prefer A100 line over corrupted desktop gpu
    gpu = cleaned_facts.get("a100_line") or cleaned_facts.get("gpu") or ""
    if re.match(r'^[\d"\\]+$', gpu):
        gpu = cleaned_facts.get("a100_line") or cleaned_facts.get("device") or gpu
    if gpu:
        cleaned_facts["gpu_primary"] = gpu
        cleaned_facts["gpu"] = gpu
    # disk canonical
    disk = cleaned_facts.get("disk") or cleaned_facts.get("juicefs") or ""
    disk = disk.replace("disk: ", "").strip()
    if disk:
        cleaned_facts["disk"] = disk
        if "JuiceFS" in disk:
            cleaned_facts["juicefs"] = disk

    # Quality: how many core keys present
    core = ("machine", "notebook_id", "gpu_primary", "torch", "disk", "session_title")
    present = sum(1 for k in core if cleaned_facts.get(k))
    quality = "high" if present >= 5 else ("medium" if present >= 3 else "low")

    # Cap + scrub brief: only lines useful for Intern grounding
    _BRIEF_ALLOW = re.compile(
        r"(?i)("
        r"^machine:|^venue:|^GPU:|^torch:|^disk:|^CPU:|"
        r"A100 M0|nb-[a-f0-9]+|JuiceFS|NVIDIA A100|Nvidia A100|"
        r"内存[：:]|显存[：:]|VERIFY|YOLO ok|cuda=True|"
        r"NEXUS_PERSISTENCE|NEXUS_GPU_SMOKE|session state"
        r")"
    )

    def _keep_brief_line(ln: str) -> bool:
        t = ln.strip()
        if len(t) < 10:
            return False
        if not _BRIEF_ALLOW.search(t):
            return False
        if t.endswith(("-", "...", " are", " for", " discovery-")):
            return False
        if any(
            x in t
            for x in (
                "insid...",
                "Full st",
                "ideall",
                "stamp: $(",
                "Loaded extra",
                "New Session",
                "SESSION PROGRESS",
                "MISSION",
                "but need to verify",
                "CLINE_A100_VERIFY_END",
                "TIMELINE ",
            )
        ):
            return False
        if t.startswith("fe758e") or t.endswith("VERIFY_END"):
            return False
        if t in ("session4", "CLINE", "Kilo Code", "Jupyter"):
            return False
        return True

    brief_lines = [ln.strip() for ln in brief.splitlines() if _keep_brief_line(ln)]

    def _brief_rank(t: str) -> int:
        if re.match(r"(?i)^(machine:|venue:|GPU:|torch:|disk:|CPU:)", t):
            return 0
        if re.search(r"(?i)(A100 M0|nb-|JuiceFS|内存|显存|VERIFY)", t):
            return 1
        return 2

    # stable unique preserve best rank
    ranked = sorted(set(brief_lines), key=lambda t: (_brief_rank(t), -len(t)))
    brief_cap = "\n".join(ranked[:14])

    prep = payload.get("preprocess") if isinstance(payload.get("preprocess"), dict) else {}
    src = source_image or payload.get("image_saved") or prep.get("source")
    return {
        "schema": "nexus.ocr.continuity.v1",
        "ts_utc": _utc_stamp(),
        "ts_local": _local_now(),
        "source_image": src,
        "mode": payload.get("mode"),
        "elapsed_s": payload.get("elapsed_s"),
        "facts": cleaned_facts,
        "agent_brief": brief_cap,
        "quality": quality,
        "core_keys_present": present,
        "line_count": (r.get("line_count") if r else None),
        "avg_confidence": (r.get("avg_confidence") if r else None),
        "ocr_result_file": payload.get("result_file"),
    }


def render_session_progress(bundle: dict[str, Any]) -> str:
    f = bundle.get("facts") or {}
    brief = bundle.get("agent_brief") or ""
    lines = [
        f"# SESSION_PROGRESS_LATEST",
        f"",
        f"- **Updated (local):** {bundle.get('ts_local')}",
        f"- **Updated (UTC):** {bundle.get('ts_utc')}",
        f"- **Source shot:** `{bundle.get('source_image') or 'n/a'}`",
        f"- **OCR mode:** `{bundle.get('mode')}` | elapsed `{bundle.get('elapsed_s')}s`",
        f"- **Quality:** `{bundle.get('quality')}` ({bundle.get('core_keys_present')}/6 core keys)",
        f"- **Lines / conf:** {bundle.get('line_count')} / {bundle.get('avg_confidence')}",
        f"",
        f"## Intern / A100 grounding (from OCR facts)",
        f"",
        f"| Key | Value |",
        f"|---|---|",
    ]
    order = [
        "session_title",
        "machine",
        "notebook_id",
        "venue",
        "gpu_primary",
        "a100_line",
        "gpu",
        "device",
        "torch",
        "disk",
        "juicefs",
        "cpu_line",
        "sys_mem",
        "cuda_mem",
        "mem_budget_gb",
        "verify_banner",
    ]
    seen = set()
    for k in order:
        if k in f and k not in seen:
            seen.add(k)
            lines.append(f"| `{k}` | {str(f[k]).replace('|', '/')} |")
    for k, v in f.items():
        if k not in seen:
            lines.append(f"| `{k}` | {str(v).replace('|', '/')} |")

    lines.extend(
        [
            f"",
            f"## Agent brief (high-signal OCR)",
            f"",
            f"```",
            brief[:4000] if brief else "(empty)",
            f"```",
            f"",
            f"## Next actions (template)",
            f"",
            f"1. Confirm notebook_id / machine match Intern UI",
            f"2. Sync this block to remote `/data/NEXUS/SESSION_PROGRESS_LATEST.md` when online",
            f"3. Prefer `--mode workspace` on single IDE shots (not multi-app desktop tiles)",
            f"",
            f"_Generated by `scripts/ocr/ocr_to_continuity.py` — no VLM; classical OCR facts only._",
            f"",
        ]
    )
    return "\n".join(lines)


def render_mission_status(bundle: dict[str, Any]) -> str:
    f = bundle.get("facts") or {}
    machine = f.get("machine") or "unknown"
    nb = f.get("notebook_id") or "unknown"
    gpu = f.get("gpu_primary") or f.get("a100_line") or f.get("gpu") or "unknown"
    torch = f.get("torch") or "unknown"
    disk = f.get("disk") or f.get("juicefs") or "unknown"
    session = f.get("session_title") or "unknown"
    verify = f.get("verify_banner") or ""

    # Compact status for agents
    ok_bits = []
    if "A100" in str(gpu).upper() or "A100" in str(session).upper():
        ok_bits.append("A100_visible")
    if nb and nb != "unknown":
        ok_bits.append("notebook_id")
    if "JuiceFS" in str(disk) or "/data" in str(disk):
        ok_bits.append("juicefs_data")
    if "2.4" in str(torch) or "cu124" in str(torch):
        ok_bits.append("torch_stack")

    q = bundle.get("quality") or "low"
    status = "GREEN" if len(ok_bits) >= 3 and q != "low" else ("YELLOW" if ok_bits else "RED")

    return "\n".join(
        [
            f"# MISSION_STATUS",
            f"",
            f"- **Status:** {status}",
            f"- **Quality:** {q}",
            f"- **Updated:** {bundle.get('ts_local')} (local) / {bundle.get('ts_utc')} (UTC)",
            f"- **Signals:** {', '.join(ok_bits) if ok_bits else 'none'}",
            f"",
            f"## Live OCR snapshot",
            f"",
            f"- **session:** {session}",
            f"- **machine:** {machine}",
            f"- **notebook_id:** {nb}",
            f"- **gpu:** {gpu}",
            f"- **torch:** {torch}",
            f"- **disk:** {disk}",
            f"- **verify:** {verify}",
            f"- **source:** `{bundle.get('source_image') or 'n/a'}`",
            f"",
            f"## Ops",
            f"",
            f"- Pipeline: ShareX -> `ocr_client --mode workspace` -> `scratch/continuity/`",
            f"- Stack: PP-OCRv6, ~5GB VRAM budget, idle 30s post-job, boot grace 120s",
            f"- No VLM (by design). Re-run: `sharex_to_continuity.ps1`",
            f"",
            f"_Auto-written from workspace OCR. Overwrites each successful run._",
            f"",
        ]
    )


def write_continuity(bundle: dict[str, Any]) -> dict[str, str]:
    CONTINUITY.mkdir(parents=True, exist_ok=True)
    HISTORY.mkdir(parents=True, exist_ok=True)

    facts_path = CONTINUITY / "OCR_FACTS_LATEST.json"
    session_path = CONTINUITY / "SESSION_PROGRESS_LATEST.md"
    mission_path = CONTINUITY / "MISSION_STATUS.md"
    hist_path = HISTORY / f"ocr_facts_{bundle['ts_utc']}.json"

    facts_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
    hist_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
    session_path.write_text(render_session_progress(bundle), encoding="utf-8")
    mission_path.write_text(render_mission_status(bundle), encoding="utf-8")

    written = {
        "facts": str(facts_path),
        "session": str(session_path),
        "mission": str(mission_path),
        "history": str(hist_path),
    }

    # Optional NEXUSlogs mirror (hygiene: under _runs only)
    try:
        day = datetime.now().strftime("%Y%m%d")
        run_dir = NEXUSLOGS / "_runs" / "GROK" / day
        if NEXUSLOGS.exists():
            run_dir.mkdir(parents=True, exist_ok=True)
            (run_dir / "OCR_FACTS_LATEST.json").write_text(
                json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            (run_dir / "SESSION_PROGRESS_LATEST.md").write_text(
                render_session_progress(bundle), encoding="utf-8"
            )
            (run_dir / "MISSION_STATUS.md").write_text(
                render_mission_status(bundle), encoding="utf-8"
            )
            written["nexuslogs"] = str(run_dir)
    except Exception:
        pass

    return written


def main() -> int:
    parser = argparse.ArgumentParser(description="OCR facts -> NEXUS continuity files")
    parser.add_argument("--from-json", type=str, default=None, help="OCR result JSON path")
    parser.add_argument("--source-image", type=str, default=None, help="Original screenshot path")
    args = parser.parse_args()

    path = Path(args.from_json) if args.from_json else None
    try:
        payload = load_ocr_payload(path)
    except Exception as e:
        print(f"ERROR: {e}")
        return 2

    bundle = extract_facts_bundle(payload, source_image=args.source_image)
    if not bundle.get("facts") and not bundle.get("agent_brief"):
        print("WARN: no facts/agent_brief in OCR payload — writing empty-ish continuity anyway")

    written = write_continuity(bundle)
    print("Continuity written:")
    for k, v in written.items():
        print(f"  {k}: {v}")
    f = bundle.get("facts") or {}
    print(
        f"status snapshot: quality={bundle.get('quality')} "
        f"machine={f.get('machine')} nb={f.get('notebook_id')} "
        f"gpu={f.get('gpu_primary') or f.get('a100_line') or f.get('gpu')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
