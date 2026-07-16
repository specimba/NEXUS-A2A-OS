#!/usr/bin/env python3
r"""
NEXUS Local OCR Client
========================
Sends a local image file to the PaddleOCR service on port 7360
and prints the extracted text.

Usage:
    python scripts/ocr/ocr_client.py <image_path> --mode desktop
    python scripts/ocr/ocr_client.py C:\path\to\screenshot.png --mode detailed
"""

import argparse
import base64
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

OCR_SERVICE = "http://127.0.0.1:7360"
REPO = Path(r"C:\Users\speci.000\Documents\NEXUS")
LATEST = REPO / "scratch" / "screenshots" / "OCR_RESULT_LATEST.json"
START_PS1 = REPO / "scripts" / "ocr" / "start_ocr_gpu.ps1"

DEFAULT_TIMEOUT = {
    "fast": 180,
    "struct": 420,
    "detailed": 420,
    "desktop": 600,
    "workspace": 420,
    "vl": 600,
}


def _health(timeout: float = 3.0) -> dict | None:
    try:
        req = urllib.request.Request(f"{OCR_SERVICE}/health", method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def ensure_service(auto_start: bool = True) -> dict | None:
    """Return health dict; optionally start GPU service if down."""
    h = _health()
    if h and h.get("status") == "ok":
        return h
    if not auto_start:
        return None
    if not START_PS1.exists():
        print(f"ERROR: OCR service down and missing {START_PS1}")
        return None
    print("OCR service not running — starting start_ocr_gpu.ps1 ...")
    try:
        subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(START_PS1),
            ],
            cwd=str(REPO),
            timeout=90,
            check=False,
        )
    except Exception as e:
        print(f"ERROR: failed to start OCR service: {e}")
        return None
    for _ in range(20):
        time.sleep(1.5)
        h = _health(5.0)
        if h and h.get("status") == "ok":
            print(f"OCR service up pid={h.get('pid')} budget={((h.get('device') or {}).get('mem_budget_gb'))}")
            return h
    print("ERROR: OCR service still down after start")
    return None


def _load_durable(note: str) -> dict | None:
    if LATEST.exists() and (LATEST.stat().st_mtime > time.time() - 120):
        try:
            data = json.loads(LATEST.read_text(encoding="utf-8"))
            if data.get("status") == "ok":
                data["note"] = note
                return data
        except Exception:
            pass
    return None


def ocr_image(
    image_path: str,
    mode: str = "fast",
    timeout: float | None = None,
    tile: bool = False,
) -> dict:
    """Send image to OCR service and return result."""
    img_bytes = Path(image_path).read_bytes()
    b64 = base64.b64encode(img_bytes).decode()
    mode_send = "struct" if mode in ("detailed", "detail", "hires") else mode
    if mode in ("workspace", "ws", "nexus"):
        mode_send = "workspace"
    body = {"image": b64, "mode": mode_send}
    if tile or mode in ("desktop", "multi", "full"):
        body["tile"] = True
        if mode_send not in ("struct", "desktop", "vl", "workspace"):
            body["mode"] = "desktop"
        elif mode_send == "fast":
            body["mode"] = "desktop"
    if mode in ("workspace", "ws", "nexus") and not tile:
        body["tile"] = False  # single-frame medium for clean IDE shots
    payload = json.dumps(body).encode()
    t = timeout if timeout is not None else DEFAULT_TIMEOUT.get(mode, 300)

    req = urllib.request.Request(
        f"{OCR_SERVICE}/ocr",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=t) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        # Brief wait: server may still be writing durable result while connection drops
        time.sleep(1.5)
        durable = _load_durable(f"socket failed ({e}); loaded durable OCR_RESULT_LATEST.json")
        if durable:
            return durable
        # One retry if connection refused (idle killed service mid-flight previously)
        if "10061" in str(e) or "10054" in str(e) or "refused" in str(e).lower():
            h = ensure_service(auto_start=True)
            if h:
                try:
                    with urllib.request.urlopen(req, timeout=t) as resp:
                        return json.loads(resp.read().decode())
                except Exception as e2:
                    durable = _load_durable(f"retry failed ({e2}); durable if any")
                    if durable:
                        return durable
                    raise e2 from e
        raise


def main():
    parser = argparse.ArgumentParser(description="NEXUS Local OCR Client")
    parser.add_argument("image", help="Path to image file (not shot.png placeholder)")
    parser.add_argument(
        "--mode",
        default="workspace",
        choices=["fast", "struct", "detailed", "desktop", "workspace", "vl"],
        help="workspace=agent brief+facts (default)|detailed|desktop(tile)|fast|vl",
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Print full cleaned OCR dump (default for workspace is brief+facts only)",
    )
    parser.add_argument("--timeout", type=float, default=None, help="override client timeout seconds")
    parser.add_argument(
        "--tile",
        action="store_true",
        help="Force multi-region tiling (wide multi-app desktops)",
    )
    parser.add_argument(
        "--no-start",
        action="store_true",
        help="Do not auto-start OCR service if down",
    )
    parser.add_argument(
        "--no-continuity",
        action="store_true",
        help="Skip writing scratch/continuity SESSION_PROGRESS + MISSION_STATUS",
    )
    args = parser.parse_args()

    img_path = Path(args.image)
    if args.image.lower() in ("shot.png", "shot.jpg", "./shot.png"):
        print("ERROR: shot.png is a placeholder name, not a real file.")
        print("Use a ShareX path, e.g.:")
        print(r'  python .\scripts\ocr\ocr_client.py "C:\Users\speci.000\Documents\ShareX\Screenshots\2026-07\chrome_xwrSTTQOab.png" --mode detailed')
        print(r'  powershell -ExecutionPolicy Bypass -File .\scripts\ocr\test_sharex_latest.ps1')
        sys.exit(1)
    if not img_path.exists():
        print(f"ERROR: file not found: {args.image}")
        sys.exit(1)
    img_exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff"}
    if img_path.suffix.lower() not in img_exts:
        print(f"ERROR: not an image file (got {img_path.suffix!r}): {args.image}")
        print("Hint: pass a real screenshot (.png/.jpg/...), not .ocr.json sidecars")
        sys.exit(1)

    if not args.no_start:
        ensure_service(auto_start=True)

    tile_req = bool(args.tile or args.mode in ("desktop", "multi", "full"))
    print(f"OCR-ing {args.image} (mode={args.mode}, tile={tile_req})...")
    try:
        result = ocr_image(args.image, args.mode, timeout=args.timeout, tile=args.tile)
    except Exception as e:
        print(f"ERROR: {e}")
        print("Hint: service may have been idle-stopped — re-run start_ocr_gpu.ps1")
        print("      or check scratch/screenshots/OCR_RESULT_LATEST.txt")
        sys.exit(2)

    if result.get("status") != "ok":
        print(f"ERROR: {result.get('error', 'unknown')}")
        sys.exit(3)

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    r = result["result"] if isinstance(result.get("result"), dict) else {}
    brief = (result.get("agent_brief") or r.get("agent_brief") or "").strip()
    facts = result.get("facts") or r.get("facts") or {}
    raw_text = r.get("full_text_sections") or r.get("full_text_clean") or r.get("full_text") or ""
    prep = result.get("preprocess") or {}
    dev = {}
    try:
        h = _health(2.0) or {}
        dev = h.get("device") or {}
    except Exception:
        pass
    print(
        f"\n=== OCR RESULT (elapsed={result.get('elapsed_s')}s, "
        f"lines={r.get('line_count')}"
        f"{('/' + str(r['line_count_raw'])) if r.get('line_count_raw') is not None else ''}"
        f", avg_conf={r.get('avg_confidence')}, dropped={r.get('dropped_noise')}"
        f", tiled={bool(prep.get('tiled'))}, mode={result.get('mode')}) ===\n"
    )
    if dev:
        print(
            f"device: {dev.get('device')} budget={dev.get('mem_budget_gb')}GB "
            f"used={dev.get('mem_used_gb')}GB frac={dev.get('frac')} "
            f"tier={dev.get('ocr_tier')} lang={dev.get('lang')}"
        )
    if prep and args.raw:
        compact = {k: prep[k] for k in prep if k != "tiles"}
        if prep.get("tiles"):
            compact["tiles"] = [
                {k: t.get(k) for k in ("name", "box", "lines", "error") if k in t or t.get("error")}
                for t in prep["tiles"]
            ]
        print(f"preprocess: {compact}")
    if result.get("note"):
        print(f"note: {result.get('note')}")

    # Agent-usable view first (this is what workspace mode is for)
    if brief:
        print("=== AGENT_BRIEF (use this for grounding) ===")
        print(brief)
        print()
    if facts:
        print("=== FACTS ===")
        print(json.dumps(facts, ensure_ascii=False, indent=2))
        print()
    if args.raw or (not brief and raw_text):
        print("=== RAW_CLEAN ===")
        print(raw_text or "(no text)")
    elif not brief:
        print(raw_text or "(no text)")

    text = brief or raw_text or "(no text)"
    if facts:
        text = (
            "=== AGENT_BRIEF ===\n"
            + (brief or "")
            + "\n\n=== FACTS ===\n"
            + json.dumps(facts, ensure_ascii=False, indent=2)
            + ("\n\n=== RAW_CLEAN ===\n" + raw_text if args.raw and raw_text else "")
        )
    scratch = REPO / "scratch" / "screenshots"
    scratch.mkdir(parents=True, exist_ok=True)
    stem = img_path.stem
    out_txt = scratch / f"{stem}.ocr.txt"
    out_json = scratch / f"{stem}.ocr.json"
    try:
        out_txt.write_text(text, encoding="utf-8")
        out_json.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nWrote {out_txt}")
        print(f"Wrote {out_json}")
    except Exception as e:
        print(f"(sidecar write failed: {e})")

    # Continuity: facts -> SESSION_PROGRESS / MISSION_STATUS (stdlib, no extra GPU)
    if not getattr(args, "no_continuity", False) and (facts or brief):
        try:
            cont = REPO / "scripts" / "ocr" / "ocr_to_continuity.py"
            if cont.exists():
                import subprocess as _sp

                _sp.run(
                    [
                        sys.executable,
                        str(cont),
                        "--from-json",
                        str(out_json if out_json.exists() else LATEST),
                        "--source-image",
                        str(img_path),
                    ],
                    cwd=str(REPO),
                    timeout=30,
                    check=False,
                )
        except Exception as e:
            print(f"(continuity write skipped: {e})")

    print(f"\n=== JSON (truncated) ===")
    print(json.dumps({k: result[k] for k in result if k != "result"}, indent=2, ensure_ascii=False))
    print("full_text_lines:", r.get("line_count"))


if __name__ == "__main__":
    main()
