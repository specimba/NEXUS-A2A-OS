#!/usr/bin/env python3
"""
NEXUS Image Guard Backend — onnxruntime detector wrapper (VISION GUARD MVP).

Serves the image lane of the guard plane (guard_plane_service.py v1.5.0):
  - OnnxDetector: lazy onnxruntime InferenceSession + letterbox preprocessing
    in pure numpy. YOLO26 exports are NMS-free end-to-end, so postprocessing
    is a confidence filter only.
  - load_manifest: sha256-verified weight loading (supply-chain rule — a
    hash mismatch is a hard failure, never a warning).
  - resolve_providers: execution-provider chain from NEXUS_IMAGE_GUARD_EP
    ("dml" default on the RTX 4070 via onnxruntime-directml).

IMPORTANT: onnxruntime is imported lazily inside OnnxDetector._ensure_session()
so this module (and the guard plane service) imports cleanly on hosts where
onnxruntime is not installed. Real weights + runtime are operator steps.
"""
import hashlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Sequence

import numpy as np

DEFAULT_INPUT_SIZE = 640
DEFAULT_CONF_THRESHOLD = 0.25


class ManifestError(RuntimeError):
    """Raised when the vision manifest is invalid or a weight fails verification."""


@dataclass
class Detection:
    """One detector hit. bbox_xywh_norm = [x, y, w, h], all in 0-1 of the
    ORIGINAL image (x, y = top-left corner)."""
    label: str
    score: float
    bbox_xywh_norm: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0, 0.0])


def resolve_providers(ep: Optional[str] = None) -> List[str]:
    """Map NEXUS_IMAGE_GUARD_EP to an onnxruntime provider chain.

    "dml" (default) -> DirectML with CPU fallback (RTX 4070 target)
    "cuda"          -> CUDA with CPU fallback
    "cpu"           -> CPU only
    """
    choice = (ep or os.getenv("NEXUS_IMAGE_GUARD_EP", "dml")).strip().lower()
    if choice == "cuda":
        return ["CUDAExecutionProvider", "CPUExecutionProvider"]
    if choice == "cpu":
        return ["CPUExecutionProvider"]
    return ["DmlExecutionProvider", "CPUExecutionProvider"]


def sha256_file(path: Path, chunk_size: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def read_manifest(manifest_path) -> dict:
    """Parse the vision manifest WITHOUT touching weight files (health checks)."""
    manifest_path = Path(manifest_path)
    if not manifest_path.exists():
        raise ManifestError(f"Vision manifest not found: {manifest_path}")
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    models = manifest.get("models")
    if not isinstance(models, list) or not models:
        raise ManifestError(f"Vision manifest has no 'models' list: {manifest_path}")
    for m in models:
        for key in ("id", "file", "sha256"):
            if not m.get(key):
                raise ManifestError(f"Manifest entry missing '{key}': {m}")
    return manifest


def load_manifest(manifest_path) -> dict:
    """Read the vision manifest and verify the sha256 of every .onnx weight.

    Supply-chain rule: any digest mismatch raises ManifestError — the weight
    must never be loaded. Missing files and OPERATOR_FILL placeholders raise
    clear "not acquired yet" errors so the operator knows what to do.

    Returns the manifest dict with each model entry augmented with:
      "path" (absolute Path as str) and "verified": True.
    """
    manifest_path = Path(manifest_path)
    manifest = read_manifest(manifest_path)
    base_dir = manifest_path.parent
    for m in manifest["models"]:
        weight_path = base_dir / m["file"]
        expected = str(m["sha256"]).strip().lower()
        if expected in ("", "operator_fill"):
            raise ManifestError(
                f"Weight '{m['id']}' not acquired yet: manifest sha256 is a placeholder "
                f"(OPERATOR_FILL). Operator must download {m['file']} "
                f"(source: {m.get('source', 'unknown')}) and fill the real digest."
            )
        if not weight_path.exists():
            raise ManifestError(
                f"Weight '{m['id']}' not acquired yet: file missing at {weight_path} "
                f"(source: {m.get('source', 'unknown')}). Download is an operator step."
            )
        actual = sha256_file(weight_path)
        if actual != expected:
            raise ManifestError(
                f"sha256 MISMATCH for '{m['id']}' ({weight_path}): "
                f"expected {expected}, got {actual}. Refusing to load (supply-chain rule)."
            )
        m["path"] = str(weight_path.resolve())
        m["verified"] = True
    return manifest


def letterbox(img: np.ndarray, size: int = DEFAULT_INPUT_SIZE, pad_value: int = 114):
    """Resize HWC uint8 RGB image to (size, size) preserving aspect ratio,
    padding with gray. Pure numpy (nearest-neighbor). Returns
    (letterboxed_img, gain, pad_x, pad_y)."""
    h, w = img.shape[:2]
    gain = min(size / h, size / w)
    new_h, new_w = max(1, int(round(h * gain))), max(1, int(round(w * gain)))
    # Nearest-neighbor resize via index maps (no PIL/cv2 dependency).
    row_idx = (np.arange(new_h) / gain).astype(np.int64).clip(0, h - 1)
    col_idx = (np.arange(new_w) / gain).astype(np.int64).clip(0, w - 1)
    resized = img[row_idx[:, None], col_idx[None, :]]
    canvas = np.full((size, size, img.shape[2]), pad_value, dtype=img.dtype)
    pad_y = (size - new_h) // 2
    pad_x = (size - new_w) // 2
    canvas[pad_y:pad_y + new_h, pad_x:pad_x + new_w] = resized
    return canvas, gain, pad_x, pad_y


class OnnxDetector:
    """Thin onnxruntime wrapper for NMS-free end-to-end detectors (YOLO26-n,
    NudeNet-v3-class). The InferenceSession is created lazily on first infer()
    so construction never requires onnxruntime to be installed."""

    def __init__(self, model_path, providers_chain: Sequence[str],
                 class_names: Optional[Sequence[str]] = None,
                 conf_threshold: float = DEFAULT_CONF_THRESHOLD,
                 input_size: int = DEFAULT_INPUT_SIZE):
        self.model_path = str(model_path)
        self.providers_chain = list(providers_chain)
        self.class_names = list(class_names) if class_names else None
        self.conf_threshold = float(conf_threshold)
        self.input_size = int(input_size)
        self._session = None
        self._input_name = None

    def _ensure_session(self):
        if self._session is not None:
            return self._session
        # Lazy import: keeps the guard plane importable without onnxruntime.
        import onnxruntime as ort
        self._session = ort.InferenceSession(self.model_path, providers=self.providers_chain)
        self._input_name = self._session.get_inputs()[0].name
        return self._session

    @property
    def active_provider(self) -> Optional[str]:
        if self._session is None:
            return None
        providers = self._session.get_providers()
        return providers[0] if providers else None

    def _preprocess(self, np_img: np.ndarray):
        boxed, gain, pad_x, pad_y = letterbox(np_img, self.input_size)
        blob = boxed.astype(np.float32) / 255.0
        blob = np.transpose(blob, (2, 0, 1))[None]  # HWC -> NCHW
        return np.ascontiguousarray(blob), gain, pad_x, pad_y

    def _label_for(self, class_id: int) -> str:
        if self.class_names and 0 <= class_id < len(self.class_names):
            return self.class_names[class_id]
        return f"class_{class_id}"

    def _postprocess(self, output: np.ndarray, gain: float, pad_x: int, pad_y: int,
                     orig_h: int, orig_w: int) -> List[Detection]:
        """YOLO26 end-to-end output: (1, N, 6) rows [x1, y1, x2, y2, score, class]
        in letterboxed-pixel space. NMS-free, so postprocess = confidence filter."""
        rows = np.asarray(output)
        rows = rows.reshape(-1, rows.shape[-1]) if rows.ndim >= 2 else rows[None]
        detections: List[Detection] = []
        for row in rows:
            if row.shape[0] < 6:
                continue
            x1, y1, x2, y2, score, cls = (float(v) for v in row[:6])
            if score < self.conf_threshold:
                continue
            # Undo letterbox -> original pixel space -> normalized xywh.
            ox1 = min(max((x1 - pad_x) / gain, 0.0), orig_w)
            oy1 = min(max((y1 - pad_y) / gain, 0.0), orig_h)
            ox2 = min(max((x2 - pad_x) / gain, 0.0), orig_w)
            oy2 = min(max((y2 - pad_y) / gain, 0.0), orig_h)
            bbox = [ox1 / orig_w, oy1 / orig_h,
                    max(0.0, ox2 - ox1) / orig_w, max(0.0, oy2 - oy1) / orig_h]
            detections.append(Detection(
                label=self._label_for(int(cls)),
                score=round(score, 4),
                bbox_xywh_norm=[round(v, 4) for v in bbox],
            ))
        return detections

    def infer(self, np_img: np.ndarray) -> List[Detection]:
        """Run detection on an HWC uint8 RGB numpy image."""
        session = self._ensure_session()
        orig_h, orig_w = np_img.shape[:2]
        blob, gain, pad_x, pad_y = self._preprocess(np_img)
        outputs = session.run(None, {self._input_name: blob})
        return self._postprocess(outputs[0], gain, pad_x, pad_y, orig_h, orig_w)
