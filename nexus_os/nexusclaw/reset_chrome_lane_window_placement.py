"""Reset Chrome lane profile window_placement (fixes slim-line / off-screen restore)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def work_area_defaults() -> dict[str, int]:
    # Sensible primary-monitor defaults (Win10/11); overridden by CLI.
    return {
        "work_area_left": 0,
        "work_area_top": 0,
        "work_area_right": 1920,
        "work_area_bottom": 1080,
        "left": 80,
        "top": 50,
        "width": 1280,
        "height": 900,
        "maximized": True,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile-dir", required=True)
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=900)
    ap.add_argument("--left", type=int, default=80)
    ap.add_argument("--top", type=int, default=50)
    ap.add_argument("--work-right", type=int, default=1920)
    ap.add_argument("--work-bottom", type=int, default=1080)
    ap.add_argument("--no-maximized", action="store_true", help="Prefs normal window (mouse maximize works)")
    args = ap.parse_args()

    pref = Path(args.profile_dir) / "Default" / "Preferences"
    if not pref.is_file():
        print(json.dumps({"status": "NO_PREFERENCES", "path": str(pref)}))
        return 0

    raw = pref.read_text(encoding="utf-8", errors="replace")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(json.dumps({"status": "PREFERENCES_PARSE_ERROR", "error": str(e)}))
        return 1

    browser = data.setdefault("browser", {})
    wp = browser.setdefault("window_placement", {})
    left, top = args.left, args.top
    right, bottom = left + args.width, top + args.height

    maximized = not args.no_maximized

    wp.update(
        {
            "bottom": bottom,
            "left": left,
            "right": right,
            "top": top,
            "maximized": maximized,
            "work_area_left": 0,
            "work_area_top": 0,
            "work_area_right": args.work_right,
            "work_area_bottom": args.work_bottom,
        }
    )

    pref.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "WINDOW_PLACEMENT_RESET",
                "path": str(pref),
                "left": left,
                "top": top,
                "width": args.width,
                "height": args.height,
                "maximized": maximized,
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())