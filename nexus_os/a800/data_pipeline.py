#!/usr/bin/env python3
"""
CDP Trace Capture → Training Data Pipeline
============================================
Captures browser automation traces from CDP lanes,
OCRs screenshots, filters by trust, and produces training-ready datasets.
"""

import hashlib
import json
import logging
import urllib.request
from pathlib import Path
from typing import Any

from .config import REASONS_DB, TRUST_MEMORY

log = logging.getLogger("a800.data_pipeline")


class CDPTraceCapture:
    """Capture traces from Chrome DevTools Protocol lanes."""

    def __init__(self, config):
        self.config = config
        self.cdp_port = 9224
        self.cdp_base = f"http://127.0.0.1:{self.cdp_port}"

    def capture_lane(self, lane: str, n_prompts: int, timeout_s: int) -> list[dict]:
        """Capture n traces from a specific browser lane."""
        traces = []
        for i in range(n_prompts):
            trace = self._capture_single(lane, timeout_s)
            if trace:
                traces.append(trace)
        return traces

    def _capture_single(self, lane: str, timeout_s: int) -> dict | None:
        """Capture a single trace from a lane."""
        # Connect to CDP and get the target for this lane
        target = self._find_target(lane)
        if not target:
            return None

        trace = {
            "lane": lane,
            "prompt": "",
            "output": "",
            "tool_calls": [],
            "outcome_ok": False,
            "trust_score": 0.5,
            "screenshot_path": None,
        }

        # This is a placeholder — real implementation uses CDP WebSocket
        # to interact with the browser tab and capture the trace
        return trace

    def _find_target(self, lane: str) -> dict | None:
        """Find the CDP target for a lane."""
        try:
            with urllib.request.urlopen(f"{self.cdp_base}/json/list", timeout=5) as resp:
                targets = json.loads(resp.read().decode())
            lane_lower = lane.lower()
            for t in targets:
                if t.get("type") == "page" and lane_lower in t.get("url", "").lower():
                    return t
        except Exception:
            pass
        return None

    def ocr_image(self, image_path: str, ocr_url: str) -> str:
        """OCR a screenshot via the local PaddleOCR service."""
        try:
            img_bytes = Path(image_path).read_bytes()
            import base64
            b64 = base64.b64encode(img_bytes).decode()
            body = json.dumps({"image": b64, "mode": "fast"}).encode()
            req = urllib.request.Request(
                f"{ocr_url}/ocr", data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode())
            return result.get("result", {}).get("full_text", "")
        except Exception as e:
            log.error("OCR failed: %s", e)
            return ""


class DataPipeline:
    """Build training datasets from captured traces."""

    def __init__(self, config):
        self.config = config

    def build_dataset(self, traces: list[dict], output_dir: Path, fmt: str = "jsonl") -> Path:
        """Build a training dataset from traces."""
        output_dir.mkdir(parents=True, exist_ok=True)
        dataset_path = output_dir / f"dataset.{fmt}"

        if fmt == "jsonl":
            self.write_jsonl(traces, dataset_path)
        return dataset_path

    def load_jsonl(self, path: str) -> list[dict]:
        """Load a JSONL file."""
        traces = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        traces.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        return traces

    def write_jsonl(self, traces: list[dict], path: Path) -> None:
        """Write traces to JSONL."""
        with open(path, "w", encoding="utf-8") as f:
            for t in traces:
                f.write(json.dumps(t, ensure_ascii=False) + "\n")

    def deduplicate(self, traces: list[dict], strategy: str = "prompt_hash",
                    threshold: float = 0.85) -> list[dict]:
        """Deduplicate traces by prompt hash."""
        seen = set()
        result = []
        for t in traces:
            key = self._hash(t.get("prompt", ""))
            if key not in seen:
                seen.add(key)
                result.append(t)
        return result

    @staticmethod
    def _hash(text: str) -> str:
        return hashlib.md5(text.encode()).hexdigest()
