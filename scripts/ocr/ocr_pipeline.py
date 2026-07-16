#!/usr/bin/env python3
"""
NEXUS OCR Pipeline Connector
=============================
Connects CDP screenshots to PaddleOCR service for text extraction.

Usage:
    # Screenshot a lane and OCR it
    python scripts/ocr/ocr_pipeline.py --port 9224 --required grok.com
    
    # OCR an existing image
    python scripts/ocr/ocr_pipeline.py --image C:\screenshots\test.png
    
    # Use specific mode (fast/struct/vl)
    python scripts/ocr/ocr_pipeline.py --image C:\screenshots\test.png --mode struct

Output: JSON with extracted text printed to stdout
"""

import argparse
import base64
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

REPO = Path(r"C:\Users\speci.000\Documents\NEXUS")
SCRATCH = REPO / "scratch" / "screenshots"
SCRATCH.mkdir(parents=True, exist_ok=True)
OCR_SERVICE = "http://127.0.0.1:7360"


def screenshot_lane(port: int, required: str) -> Path:
    """Use screenshot_lane.mjs to capture a lane tab."""
    script = REPO / "tools" / "browser_ai_supervisor" / "screenshot_lane.mjs"
    if not script.exists():
        print(f"ERROR: screenshot script not found at {script}", file=sys.stderr)
        sys.exit(1)
    
    result = subprocess.run(
        ["node", str(script), "--port", str(port), "--required", required],
        capture_output=True, text=True, timeout=30,
    )
    
    if result.returncode != 0:
        print(f"Screenshot failed: {result.stderr}", file=sys.stderr)
        sys.exit(2)
    
    try:
        data = json.loads(result.stdout.strip())
        return Path(data["path"])
    except Exception as e:
        print(f"Parse error: {e}\nOutput: {result.stdout}", file=sys.stderr)
        sys.exit(3)


def ocr_image(image_path: Path, mode: str = "fast") -> dict:
    """Send image to PaddleOCR service."""
    if not image_path.exists():
        print(f"ERROR: image not found: {image_path}", file=sys.stderr)
        sys.exit(1)
    
    img_b64 = base64.b64encode(image_path.read_bytes()).decode()
    payload = json.dumps({"image": img_b64, "mode": mode}).encode()
    
    req = urllib.request.Request(
        f"{OCR_SERVICE}/ocr",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"OCR service error: {e}", file=sys.stderr)
        sys.exit(4)


def check_service() -> bool:
    """Check if OCR service is running."""
    try:
        req = urllib.request.Request(f"{OCR_SERVICE}/health")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            return data.get("status") == "ok"
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser(description="NEXUS OCR Pipeline")
    parser.add_argument("--port", type=int, default=9224, help="CDP port")
    parser.add_argument("--required", help="Lane host to screenshot (e.g., grok.com)")
    parser.add_argument("--image", help="Path to existing image file")
    parser.add_argument("--mode", default="fast", choices=["fast", "struct", "vl"])
    parser.add_argument("--serve", action="store_true", help="Start OCR service first")
    args = parser.parse_args()

    # Optionally start the service
    if args.serve:
        svc = REPO / "scripts" / "ocr" / "paddle_ocr_service.py"
        subprocess.Popen([sys.executable, str(svc), "--port", "7360"])
        import time
        time.sleep(3)

    # Check service health
    if not check_service():
        print("OCR service not running. Start with:", file=sys.stderr)
        print(f"  python scripts/ocr/paddle_ocr_service.py --port 7360", file=sys.stderr)
        sys.exit(1)

    # Get image
    if args.image:
        img_path = Path(args.image)
    elif args.required:
        img_path = screenshot_lane(args.port, args.required)
    else:
        print("Specify --image or --required", file=sys.stderr)
        sys.exit(1)

    # OCR it
    result = ocr_image(img_path, args.mode)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
