#!/usr/bin/env python3
"""
NEXUS PaddleOCR HTTP Service
=============================
Runs a local HTTP server that accepts screenshot images and returns
structured text extraction results.

Port: 7360
Endpoints:
  POST /ocr          - General OCR (PP-OCRv6 fast mode)
  POST /ocr/struct   - Structured document parsing (PP-StructureV3)
  POST /ocr/vl       - Vision-language model parsing (PaddleOCR-VL)
  GET  /health       - Service health check

Usage:
    python scripts/ocr/paddle_ocr_service.py --port 7360
    
Then from PowerShell:
    # Screenshot OCR
    $b64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes("C:\screenshot.png"))
    $body = @{ image = $b64; mode = "fast" } | ConvertTo-Json
    Invoke-RestMethod -Uri "http://127.0.0.1:7360/ocr" -Method POST -Body $body -ContentType "application/json"
"""

import argparse
import base64
import gc
import io
import json
import logging
import os
import re
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# Windows + paddleocr 3.x: OneDNN/PIR path often throws
# NotImplementedError ConvertPirAttribute2RuntimeAttribute — disable MKLDNN/PIR early.
os.environ.setdefault("FLAGS_use_mkldnn", "0")
os.environ.setdefault("FLAGS_onednn", "0")
os.environ.setdefault("FLAGS_enable_pir_api", "0")
os.environ.setdefault("FLAGS_enable_pir_in_executor", "0")
os.environ.setdefault("FLAGS_pir_apply_inplace_pass", "0")
# GPU OCR: single card, limited VRAM (default ~3GB of laptop GPU — not whole 8GB)
os.environ.setdefault("CUDA_VISIBLE_DEVICES", os.environ.get("CUDA_VISIBLE_DEVICES", "0"))
# Paddle pre-alloc fraction. Overridden precisely in _configure_device() once we know total VRAM.
os.environ.setdefault("FLAGS_fraction_of_gpu_memory_to_use", os.environ.get("NEXUS_OCR_GPU_FRAC", "0.35"))
os.environ.setdefault("FLAGS_allocator_strategy", "auto_growth")

# Paths
REPO = Path(r"C:\Users\speci.000\Documents\NEXUS")
SCRATCH = REPO / "scratch"
SCREENSHOTS = SCRATCH / "screenshots"
SCREENSHOTS.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [OCR] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(SCRATCH / "ocr_service.log", encoding="utf-8"),
    ],
)
log = logging.getLogger("ocr_service")

# Lazy-loaded OCR engines
_OCR_FAST = None  # PP-OCRv6
_OCR_STRUCT = None  # PP-StructureV3
_OCR_VL = None  # PaddleOCR-VL
_DEVICE_INFO = {"configured": False}

# Explicit PP-OCRv6 pins: continuous=small (or medium if budget high), detailed=medium
PP_OCRV6_TIERS = {
    "tiny": ("PP-OCRv6_tiny_det", "PP-OCRv6_tiny_rec"),
    "small": ("PP-OCRv6_small_det", "PP-OCRv6_small_rec"),
    "medium": ("PP-OCRv6_medium_det", "PP-OCRv6_medium_rec"),
}

# Idle auto-shutdown: free GPU after no OCR work for N seconds (default 30).
# CRITICAL: do NOT idle-kill before first OCR (boot grace) — users type commands slowly.
# Set NEXUS_OCR_IDLE_SEC=0 to keep process alive until killed.
_STATE = {
    "idle_sec": 30.0,
    "boot_grace_sec": 120.0,
    "last_activity": time.monotonic(),
    "started_at": time.monotonic(),
    "inflight": 0,
    "jobs_done": 0,
    "shutdown": False,
}
_activity_lock = threading.Lock()


def _idle_sec_from_env() -> float:
    try:
        v = float(os.environ.get("NEXUS_OCR_IDLE_SEC", "30"))
    except ValueError:
        v = 30.0
    return max(0.0, v)


def _boot_grace_from_env() -> float:
    """Seconds after start before idle can kill if zero OCR jobs yet."""
    try:
        v = float(os.environ.get("NEXUS_OCR_BOOT_GRACE_SEC", "120"))
    except ValueError:
        v = 120.0
    return max(30.0, v)


def _touch_activity() -> None:
    """Mark usage so idle timer resets (OCR jobs only)."""
    with _activity_lock:
        _STATE["last_activity"] = time.monotonic()


def _begin_job() -> None:
    with _activity_lock:
        _STATE["inflight"] = int(_STATE["inflight"]) + 1
        _STATE["last_activity"] = time.monotonic()


def _end_job() -> None:
    with _activity_lock:
        _STATE["inflight"] = max(0, int(_STATE["inflight"]) - 1)
        _STATE["last_activity"] = time.monotonic()
        _STATE["jobs_done"] = int(_STATE["jobs_done"]) + 1


def _activity_snapshot() -> dict:
    with _activity_lock:
        now = time.monotonic()
        idle_for = now - float(_STATE["last_activity"])
        inflight = int(_STATE["inflight"])
        idle_sec = float(_STATE["idle_sec"])
        jobs_done = int(_STATE["jobs_done"])
        boot_age = now - float(_STATE["started_at"])
        boot_grace = float(_STATE["boot_grace_sec"])
    return {
        "idle_timeout_s": idle_sec,
        "idle_for_s": round(idle_for, 1),
        "inflight": inflight,
        "jobs_done": jobs_done,
        "boot_grace_s": boot_grace,
        "boot_age_s": round(boot_age, 1),
        "auto_shutdown": idle_sec > 0,
        # Idle kill only after at least one OCR completed (or boot grace elapsed)
        "idle_armed": jobs_done > 0 or boot_age >= boot_grace,
    }


def _release_engines() -> None:
    """Drop model refs and try to free GPU memory."""
    global _OCR_FAST, _OCR_STRUCT, _OCR_VL
    loaded = {
        "fast": _OCR_FAST is not None,
        "struct": _OCR_STRUCT is not None,
        "vl": _OCR_VL is not None,
    }
    _OCR_FAST = None
    _OCR_STRUCT = None
    _OCR_VL = None
    gc.collect()
    try:
        import paddle

        if hasattr(paddle, "device") and hasattr(paddle.device, "cuda"):
            empty = getattr(paddle.device.cuda, "empty_cache", None)
            if callable(empty):
                empty()
    except Exception as e:
        log.warning("GPU cache clear skipped: %s", e)
    log.info("Engines released (were %s)", loaded)


def _idle_watchdog(server: ThreadingHTTPServer) -> None:
    """Exit process after idle timeout with no in-flight OCR work.

    Race fixed: never kill during boot grace before first OCR, and never while inflight>0.
    """
    with _activity_lock:
        idle_sec = float(_STATE["idle_sec"])
        boot_grace = float(_STATE["boot_grace_sec"])
        _STATE["last_activity"] = time.monotonic()
        _STATE["started_at"] = time.monotonic()
    if idle_sec <= 0:
        log.info("Idle auto-shutdown disabled (NEXUS_OCR_IDLE_SEC=0)")
        return
    log.info(
        "Idle auto-shutdown: %.0fs after last OCR; boot grace %.0fs before any OCR",
        idle_sec,
        boot_grace,
    )
    while True:
        time.sleep(0.5)
        with _activity_lock:
            if _STATE["shutdown"]:
                return
            now = time.monotonic()
            idle_for = now - float(_STATE["last_activity"])
            busy = int(_STATE["inflight"]) > 0
            idle_sec = float(_STATE["idle_sec"])
            jobs_done = int(_STATE["jobs_done"])
            boot_age = now - float(_STATE["started_at"])
            boot_grace = float(_STATE["boot_grace_sec"])
        if busy or idle_sec <= 0:
            continue
        # Before first job: only exit after long boot grace (not 30s — kills first desktop run)
        if jobs_done == 0:
            if boot_age < boot_grace:
                continue
            # still no work after grace — free GPU
            pass
        elif idle_for < idle_sec:
            continue
        else:
            # jobs_done > 0 and idle_for >= idle_sec
            pass

        # Unified exit condition
        should_stop = False
        if jobs_done == 0 and boot_age >= boot_grace:
            should_stop = True
            reason = f"boot grace {boot_age:.0f}s exceeded with zero OCR jobs"
        elif jobs_done > 0 and idle_for >= idle_sec:
            should_stop = True
            reason = f"idle {idle_for:.1f}s >= {idle_sec:.0f}s after last OCR"
        if not should_stop:
            continue

        with _activity_lock:
            if _STATE["shutdown"] or int(_STATE["inflight"]) > 0:
                continue
            _STATE["shutdown"] = True
        log.info("%s - releasing engines and shutting down", reason)
        try:
            _release_engines()
        except Exception:
            log.exception("engine release failed")

        def _stop():
            try:
                server.shutdown()
            except Exception:
                pass

        threading.Thread(target=_stop, name="ocr-idle-shutdown", daemon=True).start()
        return


def _target_gpu_mem_gb() -> float:
    """Desired OCR VRAM budget (GB). Default 5.0 on 8GB laptop — models were underusing 3GB.

    Env NEXUS_OCR_GPU_MEM_GB, clamp 2-6.5 (leave headroom for desktop).
    """
    try:
        v = float(os.environ.get("NEXUS_OCR_GPU_MEM_GB", "5.0"))
    except ValueError:
        v = 5.0
    return max(2.0, min(6.5, v))


def _configure_device() -> dict:
    """Pick GPU if paddle CUDA build is present; cap allocator to ~2-4GB. Else CPU."""
    global _DEVICE_INFO
    if _DEVICE_INFO.get("configured"):
        return _DEVICE_INFO
    # Planned pins advertised on /health before first OCR (lazy load)
    small_det, small_rec = PP_OCRV6_TIERS["small"]
    info = {
        "configured": True,
        "device": "cpu",
        "cuda_compiled": False,
        "gpu_name": None,
        "mem_total_gb": None,
        "mem_budget_gb": None,
        "frac": None,
        "ocr_tier": "small",
        "det_model": small_det,
        "rec_model": small_rec,
        "fast_tier": "small",
        "detailed_tier": "medium",
        "lang": _ocr_lang(),
        "tile_policy": os.environ.get("NEXUS_OCR_TILE", "auto"),
    }
    try:
        import paddle

        info["paddle_version"] = getattr(paddle, "__version__", "?")
        info["cuda_compiled"] = bool(
            hasattr(paddle, "is_compiled_with_cuda") and paddle.is_compiled_with_cuda()
        )
        if info["cuda_compiled"]:
            try:
                paddle.device.set_device("gpu:0")
                info["device"] = "gpu:0"
            except Exception as e:
                log.warning("set_device gpu failed (%s); staying CPU", e)
                info["device"] = "cpu"
            # Cap VRAM: fraction of total, targeting 2–4 GB
            budget = _target_gpu_mem_gb()
            total_gb = None
            try:
                # paddle may expose props; fall back to 8GB laptop default
                import subprocess

                out = subprocess.check_output(
                    [
                        "nvidia-smi",
                        "--query-gpu=memory.total,name",
                        "--format=csv,noheader,nounits",
                    ],
                    text=True,
                    timeout=10,
                ).strip().split("\n")[0]
                # e.g. "8188, NVIDIA GeForce..."
                parts = [p.strip() for p in out.split(",")]
                total_mb = float(parts[0])
                total_gb = total_mb / 1024.0
                info["gpu_name"] = parts[1] if len(parts) > 1 else None
            except Exception:
                total_gb = 8.0
            info["mem_total_gb"] = round(total_gb, 2)
            info["mem_budget_gb"] = budget
            # Use more of the card: up to ~70% when budget asks for it (was capped 50%/3GB)
            frac = min(0.70, max(0.20, budget / max(total_gb, 0.1)))
            info["frac"] = round(frac, 3)
            os.environ["FLAGS_fraction_of_gpu_memory_to_use"] = str(frac)
            os.environ["FLAGS_allocator_strategy"] = "auto_growth"
            try:
                paddle.set_flags({"FLAGS_fraction_of_gpu_memory_to_use": frac})
            except Exception as e:
                log.warning("paddle.set_flags mem frac failed: %s", e)
            # Live used memory (helps confirm we are not leaving budget idle)
            try:
                used = subprocess.check_output(
                    [
                        "nvidia-smi",
                        "--query-gpu=memory.used",
                        "--format=csv,noheader,nounits",
                    ],
                    text=True,
                    timeout=5,
                ).strip().split("\n")[0]
                info["mem_used_gb"] = round(float(used) / 1024.0, 2)
            except Exception:
                info["mem_used_gb"] = None
            log.info(
                "OCR device=%s budget=%.1fGB / total=%.1fGB frac=%.3f name=%s",
                info["device"],
                budget,
                total_gb,
                frac,
                info.get("gpu_name"),
            )
        else:
            log.warning(
                "paddle compiled WITHOUT CUDA (CPU wheel). Install paddlepaddle-gpu "
                "from cu126 index for GPU OCR. Running on CPU."
            )
    except Exception as e:
        log.exception("device configure failed: %s", e)
    _DEVICE_INFO = info
    return info


def _resolve_tier(tier: str | None) -> str:
    """Map continuous/detailed policy → tiny|small|medium."""
    t = (tier or os.environ.get("NEXUS_OCR_V6_TIER", "small")).lower().strip()
    if t in ("fast", "continuous", "default", ""):
        t = "small"
    if t in ("detailed", "detail", "struct", "hires"):
        t = "medium"
    if t not in PP_OCRV6_TIERS:
        log.warning("unknown tier %s; using small", t)
        t = "small"
    # If budget <2.2GB prefer tiny for continuous
    try:
        budget = float(os.environ.get("NEXUS_OCR_GPU_MEM_GB", "5.0"))
        if budget < 2.2 and t == "small":
            t = "tiny"
    except ValueError:
        pass
    return t


def _make_paddle_ocr(tier: str = "small", **kwargs):
    """Create PaddleOCR pinned to PP-OCRv6 tier on GPU when available.

    Policy (NEXUS research):
      continuous/fast → PP-OCRv6_small (or tiny if VRAM budget <2.2GB)
      detailed/struct  → PP-OCRv6_medium
    Never pass show_log. Prefer device=gpu:0 when CUDA build present.
    """
    _configure_device()
    from paddleocr import PaddleOCR

    lang = kwargs.get("lang") or _ocr_lang()
    use_gpu = _DEVICE_INFO.get("device", "cpu").startswith("gpu")
    tier = _resolve_tier(tier)
    det_name, rec_name = PP_OCRV6_TIERS[tier]
    _DEVICE_INFO["ocr_tier"] = tier
    _DEVICE_INFO["det_model"] = det_name
    _DEVICE_INFO["rec_model"] = rec_name
    _DEVICE_INFO["lang"] = lang

    # Shared base: pin v6 models; disable heavy doc preprocess for UI screenshots
    # lang=ch uses Chinese+English dictionary path (fixes taskbar 内存/显存 + mixed UI)
    base = dict(
        lang=lang,
        text_detection_model_name=det_name,
        text_recognition_model_name=rec_name,
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=True,
    )

    attempts = []
    if use_gpu:
        attempts.extend(
            [
                {**base, "device": "gpu:0"},
                {**base, "device": "gpu"},
                {**base, "use_gpu": True},
            ]
        )
    attempts.extend(
        [
            dict(base),
            # fallback without orientation flag
            dict(
                lang=lang,
                text_detection_model_name=det_name,
                text_recognition_model_name=rec_name,
                device="gpu:0" if use_gpu else "cpu",
            ),
            # last resort: unpinned defaults (still GPU if possible)
            dict(lang=lang, device="gpu:0") if use_gpu else dict(lang=lang),
            dict(lang=lang),
            {},
        ]
    )
    last_err = None
    for params in attempts:
        try:
            log.info("PaddleOCR init tier=%s try keys=%s", tier, sorted(params.keys()))
            eng = PaddleOCR(**params)
            log.info(
                "PaddleOCR init OK tier=%s det=%s rec=%s device_info=%s",
                tier,
                det_name,
                rec_name,
                _DEVICE_INFO,
            )
            return eng
        except (TypeError, ValueError) as e:
            last_err = e
            log.warning("PaddleOCR init rejected params=%s err=%s", params, e)
            continue
        except Exception as e:
            last_err = e
            log.warning("PaddleOCR init failed params=%s err=%s", params, e)
            continue
    raise RuntimeError(f"Unable to construct PaddleOCR tier={tier}: {last_err}")


def _run_ocr(engine, img_path: str):
    """Run OCR supporting both .ocr() (2.x) and .predict() (3.x)."""
    if hasattr(engine, "ocr"):
        try:
            return engine.ocr(str(img_path), cls=True)
        except TypeError:
            try:
                return engine.ocr(str(img_path))
            except Exception:
                pass
    if hasattr(engine, "predict"):
        return engine.predict(str(img_path))
    raise RuntimeError("OCR engine has neither ocr() nor predict()")


def _ocr_lang() -> str:
    """PP-OCRv6 rec supports 50 langs; `ch` is best for mixed CN+EN Windows chrome.

    Override with NEXUS_OCR_LANG=en|ch|japan|...
    """
    return (os.environ.get("NEXUS_OCR_LANG") or "ch").strip() or "ch"


def get_fast_ocr():
    """Continuous/fast: small by default; medium when VRAM budget >= 4.5GB (use the GPU)."""
    global _OCR_FAST
    if _OCR_FAST is None:
        budget = _target_gpu_mem_gb()
        # Prefer quality when user allocates enough VRAM (was leaving 3GB mostly idle)
        use_med = os.environ.get("NEXUS_OCR_FAST_TIER", "").lower() in ("medium", "med", "detailed")
        if not use_med and budget >= 4.5:
            use_med = os.environ.get("NEXUS_OCR_FAST_TIER", "auto").lower() != "small"
        tier = "medium" if use_med else "small"
        log.info(
            "Loading PP-OCRv6_%s (fast path, budget=%.1fGB) - first run may download weights...",
            tier,
            budget,
        )
        _OCR_FAST = _make_paddle_ocr(tier=tier, lang=_ocr_lang())
        log.info("PP-OCRv6_%s ready (fast path)", tier)
    return _OCR_FAST


def get_struct_ocr():
    """Detailed/struct: PP-OCRv6_medium (preserve more UI detail)."""
    global _OCR_STRUCT
    if _OCR_STRUCT is None:
        log.info("Loading PP-OCRv6_medium (detailed) - first run may download weights...")
        _OCR_STRUCT = _make_paddle_ocr(tier="medium", lang=_ocr_lang())
        log.info("PP-OCRv6_medium ready")
    return _OCR_STRUCT


def get_vl_ocr():
    """PaddleOCR-VL when available; else fall back to medium classical OCR."""
    global _OCR_VL
    if _OCR_VL is None:
        log.info("Loading PaddleOCR-VL if available (optional hard-doc path)...")
        try:
            from paddleocr import PaddleOCRVL

            try:
                _OCR_VL = PaddleOCRVL()
            except TypeError:
                _OCR_VL = PaddleOCRVL()
            except ValueError:
                _OCR_VL = get_struct_ocr()
                return _OCR_VL
        except Exception as e:
            log.warning("PaddleOCR-VL unavailable (%s); falling back to PP-OCRv6_medium", e)
            _OCR_VL = get_struct_ocr()
        log.info("PaddleOCR-VL path ready")
    return _OCR_VL


def decode_image(b64_data: str) -> bytes:
    """Decode base64 image data, handling data URIs."""
    if "," in b64_data:
        b64_data = b64_data.split(",", 1)[1]
    return base64.b64decode(b64_data)


def save_screenshot(img_bytes: bytes, prefix: str = "cap") -> Path:
    """Save screenshot to scratch/screenshots with timestamp."""
    ts = time.strftime("%Y%m%dT%H%M%SZ")
    path = SCREENSHOTS / f"{prefix}_{ts}.png"
    path.write_bytes(img_bytes)
    return path


def _max_edge_for_mode(mode: str) -> int:
    """Higher edges preserve small IDE fonts (research: 960px kills UI OCR).

    With ~5GB VRAM budget we can keep near-native UI resolution.
    Env overrides:
      NEXUS_OCR_MAX_EDGE_FAST (default 1920)
      NEXUS_OCR_MAX_EDGE_DETAILED (default 2560)
    """
    is_fast = mode in ("fast", "default", "")
    env_key = "NEXUS_OCR_MAX_EDGE_FAST" if is_fast else "NEXUS_OCR_MAX_EDGE_DETAILED"
    default = "1920" if is_fast else "2560"
    try:
        return max(640, int(os.environ.get(env_key, default)))
    except ValueError:
        return 1920 if is_fast else 2560


def _maybe_enhance_contrast(im, meta: dict):
    """Light CLAHE-style boost only for very flat / low-contrast dark UIs.

    Blind binarize/CLAHE often *hurts* clean screenshots (research 2025-2026).
    """
    try:
        from PIL import ImageEnhance, ImageOps, ImageStat
    except Exception:
        return im
    try:
        gray = ImageOps.grayscale(im)
        st = ImageStat.Stat(gray)
        mean = float(st.mean[0]) if st.mean else 128.0
        # stddev approx from rms
        rms = float(st.stddev[0]) if st.stddev else 40.0
        meta["luma_mean"] = round(mean, 1)
        meta["luma_std"] = round(rms, 1)
        # Dark VSCode-like panels: low mean + moderate std -> mild contrast only
        if mean < 90 and rms < 55:
            im2 = ImageEnhance.Contrast(im).enhance(1.25)
            im2 = ImageEnhance.Sharpness(im2).enhance(1.15)
            meta["contrast_boost"] = True
            return im2
        meta["contrast_boost"] = False
        return im
    except Exception as e:
        meta["contrast_boost_err"] = str(e)
        return im


def prepare_image_for_ocr(img_path: Path, mode: str) -> tuple[Path, dict]:
    """Prepare UI screenshot for OCR: smart resize + optional mild contrast.

    History: 960 max-edge made continuous OCR fast but destroyed small UI text.
    GPU path can keep more resolution. Never upscale huge frames.

    Policy:
      fast:     max_edge default 1400 (was 960)
      detailed: max_edge default 1920 (was 1400)
      LANCZOS resize for sharper glyphs than BILINEAR
      optional mild contrast only when image is dark+flat
    """
    meta = {"source": str(img_path), "resized": False, "max_edge": None, "contrast_boost": False}
    try:
        from PIL import Image
    except Exception as e:
        log.warning("PIL unavailable (%s); OCR on original size", e)
        return img_path, meta

    max_edge = _max_edge_for_mode(mode)
    meta["max_edge"] = max_edge
    try:
        with Image.open(img_path) as im0:
            im = im0.convert("RGB")
            w, h = im.size
            meta["orig_size"] = [w, h]
            im = _maybe_enhance_contrast(im, meta)
            scale = min(1.0, float(max_edge) / float(max(w, h)))
            # Tiny crops: slight upscale helps det on small text panels
            if max(w, h) < 700:
                scale = min(1.5, 900.0 / float(max(w, h)))
                meta["upscaled"] = True
            if 0.98 <= scale <= 1.02 and not meta.get("contrast_boost"):
                return img_path, meta
            nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
            out = img_path.with_name(img_path.stem + f"_r{nw}x{nh}" + img_path.suffix)
            resample = getattr(Image, "Resampling", Image).LANCZOS
            im.resize((nw, nh), resample).save(out, format="PNG", optimize=True)
            meta.update({"resized": True, "new_size": [nw, nh], "path": str(out), "scale": round(scale, 3)})
            log.info(
                "OCR preprocess %sx%s -> %sx%s mode=%s boost=%s",
                w, h, nw, nh, mode, meta.get("contrast_boost"),
            )
            return out, meta
    except Exception as e:
        log.warning("preprocess failed (%s); using original", e)
        return img_path, meta


class OCRHandler(BaseHTTPRequestHandler):
    # Avoid hanging half-dead clients forever
    timeout = 30

    def log_message(self, fmt, *args):
        log.info("%s - %s", self.address_string(), fmt % args)

    def _send_json(self, data: dict, status: int = 200):
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError) as e:
            # Client already timed out; result should still be on disk
            log.warning("client gone while sending response: %s", e)

    def _send_error(self, message: str, status: int = 400):
        self._send_json({"error": message, "status": "error"}, status)

    def _persist_result(self, img_path: Path, payload: dict) -> Path:
        out = img_path.with_suffix(".ocr.json")
        try:
            out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            # latest pointer for continuous support without waiting on socket
            latest = SCREENSHOTS / "OCR_RESULT_LATEST.json"
            latest.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            txt = SCREENSHOTS / "OCR_RESULT_LATEST.txt"
            res = payload.get("result") or {}
            # Agent-first: brief + facts, then optional sections/clean dump
            brief = (res.get("agent_brief") or "").strip()
            facts = res.get("facts") or {}
            rest = (
                res.get("full_text_sections")
                or res.get("full_text_clean")
                or res.get("full_text")
                or ""
            )
            parts = []
            if brief:
                parts.append("=== AGENT_BRIEF ===\n" + brief)
            if facts:
                parts.append("=== FACTS ===\n" + json.dumps(facts, ensure_ascii=False, indent=2))
            if rest:
                parts.append("=== RAW_CLEAN ===\n" + rest)
            txt.write_text("\n\n".join(parts) if parts else "", encoding="utf-8")
        except Exception as e:
            log.warning("persist OCR result failed: %s", e)
        return out

    def do_GET(self):
        # Health does NOT reset idle timer (avoids keep-alive via probes).
        if self.path == "/health" or self.path.startswith("/health?"):
            snap = _activity_snapshot()
            self._send_json({
                "status": "ok",
                "service": "nexus-ocr",
                "models": {
                    "fast": _OCR_FAST is not None,
                    "struct": _OCR_STRUCT is not None,
                    "vl": _OCR_VL is not None,
                },
                "device": _DEVICE_INFO if _DEVICE_INFO.get("configured") else _configure_device(),
                "idle": snap,
                "pid": os.getpid(),
            })
        elif self.path == "/shutdown":
            # Browser-friendly stop (also POST /shutdown).
            self._request_shutdown()
            self._send_json({"status": "shutting_down", "pid": os.getpid()})
        else:
            self._send_error("not found", 404)

    def _request_shutdown(self) -> None:
        """Release engines and stop HTTP server (idle watchdog or /shutdown)."""
        with _activity_lock:
            if _STATE["shutdown"]:
                return
            _STATE["shutdown"] = True
        log.info("Shutdown requested (pid=%s)", os.getpid())
        try:
            _release_engines()
        except Exception:
            log.exception("engine release on shutdown failed")
        server = self.server

        def _stop():
            try:
                server.shutdown()
            except Exception:
                pass

        threading.Thread(target=_stop, name="ocr-shutdown", daemon=True).start()

    def do_POST(self):
        if self.path == "/shutdown" or self.path.startswith("/shutdown?"):
            self._request_shutdown()
            self._send_json({"status": "shutting_down", "pid": os.getpid()})
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length)
            payload = json.loads(raw.decode("utf-8"))
        except Exception as e:
            self._send_error(f"bad request: {e}")
            return

        mode = payload.get("mode", "fast")
        b64_image = payload.get("image", "")
        if not b64_image:
            self._send_error("missing 'image' field (base64)")
            return

        # Mark busy ASAP so idle watchdog cannot kill mid-request (race with boot grace)
        _begin_job()
        try:
            img_bytes = decode_image(b64_image)
            img_path = save_screenshot(img_bytes, prefix=mode)
        except Exception as e:
            _end_job()
            self._send_error(f"image decode failed: {e}")
            return

        # Aliases
        force_tile = False
        workspace_mode = False
        if mode in ("workspace", "ws", "nexus"):
            # Agent-oriented: medium engine, prefer single-frame unless forced tile
            workspace_mode = True
            mode = "struct"
        if mode in ("detailed", "detail", "hires"):
            mode = "struct"
        if mode in ("desktop", "multi", "full"):
            force_tile = True
            mode = "struct"  # medium engine for quality

        # Client can force tiling without changing engine tier
        if payload.get("tile") in (True, 1, "1", "true", "yes", "auto"):
            force_tile = True
        if payload.get("tile") in (False, 0, "0", "false", "no") and workspace_mode:
            force_tile = False

        start = time.monotonic()
        try:
            if mode == "vl":
                engine = get_vl_ocr()
            elif mode == "struct":
                engine = get_struct_ocr()
            else:
                engine = get_fast_ocr()

            # Decide tiling from image geometry (multi-app desktop)
            tile_now = force_tile
            try:
                from PIL import Image

                with Image.open(img_path) as _im:
                    ow, oh = _im.size
                tile_now = _should_tile(mode if not force_tile else "desktop", ow, oh, force=force_tile)
            except Exception:
                ow = oh = 0

            if tile_now:
                parsed, prep_meta = ocr_with_tiles(engine, img_path, "desktop" if force_tile else mode)
                work_path = img_path
            else:
                parsed, prep_meta = _ocr_image_path(engine, img_path, mode)
                work_path = Path(prep_meta.get("path") or img_path)

            elapsed = time.monotonic() - start
            log.info(
                "OCR done mode=%s tiled=%s lines=%s elapsed=%.2fs raw_type=%s prep=%s",
                mode,
                bool(prep_meta.get("tiled")),
                parsed.get("line_count"),
                elapsed,
                parsed.get("raw_type"),
                prep_meta,
            )

            # Workspace mode always attaches agent view (also present on other modes via postprocess)
            if workspace_mode and parsed.get("agent_brief"):
                prep_meta = dict(prep_meta or {})
                prep_meta["workspace_mode"] = True

            response = {
                "status": "ok",
                "mode": "workspace" if workspace_mode else mode,
                "elapsed_s": round(elapsed, 2),
                "image_saved": str(img_path),
                "image_ocr_input": str(work_path),
                "preprocess": prep_meta,
                "result": parsed,
                "agent_brief": parsed.get("agent_brief"),
                "facts": parsed.get("facts"),
                "result_file": None,
            }
            result_file = self._persist_result(img_path, response)
            response["result_file"] = str(result_file)
            # rewrite with path
            self._persist_result(img_path, response)
            self._send_json(response)
        except Exception as e:
            log.exception("OCR failed")
            err = {"status": "error", "error": f"OCR engine error: {e}", "mode": mode, "image_saved": str(img_path)}
            try:
                self._persist_result(img_path, err)
            except Exception:
                pass
            self._send_error(f"OCR engine error: {e}", 500)
        finally:
            _end_job()


def _as_dict(obj):
    """Best-effort convert paddlex OCRResult / mapping-like objects to dict."""
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    for attr in ("json", "to_dict", "dict"):
        if hasattr(obj, attr):
            try:
                val = getattr(obj, attr)
                val = val() if callable(val) else val
                if isinstance(val, dict):
                    return val
                # paddlex sometimes nests under res
                if hasattr(val, "keys"):
                    return dict(val)
            except Exception:
                pass
    # attribute bag
    out = {}
    for k in (
        "rec_text", "rec_texts", "rec_score", "rec_scores",
        "dt_polys", "dt_boxes", "texts", "text", "scores",
        "res",
    ):
        if hasattr(obj, k):
            try:
                out[k] = getattr(obj, k)
            except Exception:
                pass
    if out:
        return out
    try:
        return dict(obj)
    except Exception:
        return {"_raw": repr(obj)[:500]}


def _parse_fast_result(result, clean: bool = True) -> dict:
    """Parse classic list-of-lines OCR output and newer dict/list predict payloads."""
    lines = []
    raw_type = type(result).__name__
    log.info("OCR raw result type=%s", raw_type)

    # Unwrap single-item list of result objects (paddleocr 3.x predict)
    items = result
    if isinstance(result, (list, tuple)):
        items = list(result)
    else:
        items = [result]

    for item in items:
        # Classic paddleocr 2.x page: list of [box, (text, conf)]
        if isinstance(item, list) and item and isinstance(item[0], (list, tuple)) and len(item[0]) >= 2:
            # could be classic lines OR nested page
            sample = item[0]
            if isinstance(sample[0], (list, tuple)) or (
                hasattr(sample[0], "__iter__") and not isinstance(sample[0], (str, bytes))
            ):
                for line in item:
                    try:
                        if not line or len(line) < 2:
                            continue
                        box = line[0]
                        text_info = line[1]
                        if isinstance(text_info, (list, tuple)):
                            text = text_info[0] if text_info else ""
                            conf = float(text_info[1]) if len(text_info) > 1 else 0.0
                        elif isinstance(text_info, dict):
                            text = text_info.get("text") or text_info.get("transcription") or ""
                            conf = float(text_info.get("score") or text_info.get("confidence") or 0)
                        else:
                            text = str(text_info)
                            conf = 0.0
                        if text:
                            box_pts = []
                            try:
                                box_pts = [[int(p[0]), int(p[1])] for p in box] if box else []
                            except Exception:
                                box_pts = []
                            lines.append({
                                "text": str(text),
                                "confidence": round(float(conf), 3),
                                "box": box_pts,
                            })
                    except Exception:
                        continue
                continue

        d = _as_dict(item)
        if "res" in d and isinstance(d["res"], dict):
            d = {**d, **d["res"]}

        # paddlex / paddleocr 3.x keys
        recs = (
            d.get("rec_texts")
            or d.get("rec_text")
            or d.get("texts")
            or d.get("text")
        )
        scores = d.get("rec_scores") or d.get("rec_score") or d.get("scores") or []
        if isinstance(recs, str):
            recs = [recs]
        if recs is None:
            recs = []
        if not isinstance(recs, (list, tuple)):
            recs = [recs]
        if not isinstance(scores, (list, tuple)):
            scores = [scores] if scores not in (None, "") else []

        # Optional boxes for reading-order sort
        polys = d.get("dt_polys") or d.get("rec_polys") or d.get("dt_boxes") or d.get("boxes") or []
        if not isinstance(polys, (list, tuple)):
            polys = []

        for i, t in enumerate(recs):
            if t is None or str(t).strip() == "":
                continue
            conf = 0.0
            try:
                if i < len(scores):
                    conf = float(scores[i])
            except Exception:
                conf = 0.0
            box_pts = []
            try:
                if i < len(polys):
                    poly = polys[i]
                    # numpy arrays / nested lists
                    if hasattr(poly, "tolist"):
                        poly = poly.tolist()
                    if isinstance(poly, (list, tuple)) and poly:
                        if isinstance(poly[0], (list, tuple)):
                            box_pts = [[int(p[0]), int(p[1])] for p in poly]
                        elif len(poly) >= 4 and not isinstance(poly[0], (list, tuple)):
                            # flat [x1,y1,x2,y2,...] or bbox
                            box_pts = [[int(poly[0]), int(poly[1])], [int(poly[2]), int(poly[3])]]
            except Exception:
                box_pts = []
            lines.append({"text": str(t), "confidence": round(conf, 3), "box": box_pts})

    if not lines:
        # last-ditch: stringify for debug
        log.warning("OCR parse produced 0 lines; raw_type=%s sample=%s", raw_type, repr(result)[:400])

    if not clean:
        return {
            "lines": lines,
            "line_count": len(lines),
            "full_text": "\n".join(l["text"] for l in lines),
            "raw_type": raw_type,
        }
    return _postprocess_lines(lines, raw_type)


def _tile_policy() -> str:
    """auto | always | never — multi-region OCR for multi-app desktops."""
    return (os.environ.get("NEXUS_OCR_TILE") or "auto").strip().lower()


def _should_tile(mode: str, width: int, height: int, force: bool = False) -> bool:
    if force or mode in ("desktop", "multi", "full"):
        return True
    pol = _tile_policy()
    if pol in ("never", "0", "off", "false"):
        return False
    if pol in ("always", "1", "on", "true"):
        return True
    # auto: only true multi-app desktops (avoid tiling clean single IDE frames)
    # e.g. 1826x1049 multi-window yes; 1584x859 single A100 workspace no
    if width >= 1700 and width / max(height, 1) >= 1.55:
        return True
    if width * height >= 2_200_000:  # ~1920x1150+
        return True
    return False


def _build_tiles(width: int, height: int) -> list[tuple[int, int, int, int, str]]:
    """Column tiles + taskbar strip. Overlap reduces edge-cut words."""
    tiles: list[tuple[int, int, int, int, str]] = []
    # 3 vertical panels (left nav | center | right) with ~4% overlap
    cols = 3 if width >= 1400 else 2
    base = width // cols
    overlap = max(24, int(width * 0.04))
    for i in range(cols):
        x0 = max(0, i * base - (overlap if i else 0))
        x1 = width if i == cols - 1 else min(width, (i + 1) * base + overlap)
        tiles.append((x0, 0, x1, height, f"col{i}"))
    # Taskbar / status strip (bottom ~7%)
    y0 = max(0, int(height * 0.93))
    if height - y0 >= 20:
        tiles.append((0, y0, width, height, "taskbar"))
    # Top chrome strip (tabs/URL) when tall enough
    y1 = min(height, max(40, int(height * 0.08)))
    if y1 >= 36:
        tiles.append((0, 0, width, y1, "topchrome"))
    return tiles


def _offset_boxes(lines: list, dx: int, dy: int, tile: str) -> list:
    out = []
    for ln in lines:
        box = ln.get("box") or []
        nbox = []
        try:
            nbox = [[int(p[0]) + dx, int(p[1]) + dy] for p in box] if box else []
        except Exception:
            nbox = []
        out.append({
            "text": ln.get("text"),
            "confidence": ln.get("confidence", 0),
            "box": nbox,
            "tile": tile,
        })
    return out


def _ocr_image_path(engine, img_path: Path, mode: str) -> tuple[dict, dict]:
    """Single-shot OCR with preprocess. Returns (parsed, prep_meta)."""
    work_path, prep_meta = prepare_image_for_ocr(img_path, mode)
    raw = _run_ocr(engine, str(work_path))
    if mode in ("struct", "vl"):
        parsed = _parse_struct_result(raw)
    else:
        parsed = _parse_fast_result(raw)
    return parsed, prep_meta


def ocr_with_tiles(engine, img_path: Path, mode: str) -> tuple[dict, dict]:
    """Multi-region OCR: tile wide desktops so each panel keeps native resolution.

    Classical OCR cannot invent icon glyphs; tiling maximizes text recovery across
    multi-app layouts (browser + IDE + chat).
    """
    try:
        from PIL import Image
    except Exception as e:
        log.warning("tile OCR needs PIL (%s); falling back single", e)
        return _ocr_image_path(engine, img_path, mode if mode != "desktop" else "struct")

    with Image.open(img_path) as im0:
        im = im0.convert("RGB")
        w, h = im.size

    tiles = _build_tiles(w, h)
    merged_raw: list = []
    tile_info = []
    # Per-tile: keep near-native resolution (cap edge so VRAM stays in budget)
    tile_mode = "struct" if mode in ("desktop", "multi", "full", "struct", "detailed") else "fast"

    for x0, y0, x1, y1, name in tiles:
        crop = im.crop((x0, y0, x1, y1))
        tw, th = crop.size
        if tw < 32 or th < 16:
            continue
        tile_path = SCREENSHOTS / f"tile_{name}_{x0}_{y0}_{img_path.stem}.png"
        crop.save(tile_path, format="PNG", optimize=True)
        work, prep = prepare_image_for_ocr(tile_path, tile_mode)
        try:
            raw = _run_ocr(engine, str(work))
            part = _parse_fast_result(raw, clean=False)
            lines = _offset_boxes(part.get("lines") or [], x0, y0, name)
            merged_raw.extend(lines)
            tile_info.append({
                "name": name,
                "box": [x0, y0, x1, y1],
                "lines": len(lines),
                "prep": prep,
            })
            log.info("tile %s %sx%s lines=%s", name, tw, th, len(lines))
        except Exception as e:
            log.warning("tile %s failed: %s", name, e)
            tile_info.append({"name": name, "box": [x0, y0, x1, y1], "error": str(e)})

    parsed = _postprocess_lines(merged_raw, "tiled")
    # Spatial section headers for agents (preserve tile labels through postprocess)
    # Re-attach tile labels lost if postprocess dropped the field - use merged_raw order
    by_tile: dict[str, list] = {}
    for ln in merged_raw:
        tname = ln.get("tile") or "?"
        text = str(ln.get("text") or "").strip()
        conf = float(ln.get("confidence") or 0)
        if _is_noise_text(text, conf, float(parsed.get("min_conf") or 0.55)):
            continue
        by_tile.setdefault(tname, []).append(text)
    # de-dupe within section
    sections = {}
    for k, vals in by_tile.items():
        seen = set()
        out_v = []
        for v in vals:
            if v in seen:
                continue
            seen.add(v)
            out_v.append(v)
        sections[k] = "\n".join(out_v)
    parsed["sections"] = sections
    order = [t[4] for t in tiles]
    parts = []
    for name in order:
        body = sections.get(name)
        if body:
            parts.append(f"=== {name} ===\n{body}")
    if parts:
        parsed["full_text_sections"] = "\n\n".join(parts)
    meta = {
        "tiled": True,
        "tile_count": len(tiles),
        "tiles": tile_info,
        "orig_size": [w, h],
        "policy": _tile_policy(),
    }
    return parsed, meta


def _box_sort_key(line: dict):
    """Top-to-bottom, left-to-right using box top-left."""
    box = line.get("box") or []
    if not box:
        return (10**9, 10**9)
    try:
        ys = [p[1] for p in box]
        xs = [p[0] for p in box]
        return (min(ys), min(xs))
    except Exception:
        return (10**9, 10**9)


def _has_cjk(text: str) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" for ch in text)


def _is_noise_text(text: str, conf: float, min_conf: float) -> bool:
    """Drop low-value fragments common on dense multi-window UIs / icon chrome."""
    t = (text or "").strip()
    if not t:
        return True
    if conf > 0 and conf < min_conf:
        return True
    # Icon-like pure symbols (not CJK, not alnum)
    if all(not (ch.isalnum() or _has_cjk(ch)) for ch in t) and len(t) <= 3:
        return True
    # Single latin letter alone is usually a tab/icon OCR ghost (keep CJK singles + digits)
    if len(t) == 1:
        if t.isdigit() or _has_cjk(t):
            return False
        if t.isalpha() and conf < 0.92:
            return True
        if not t.isalnum():
            return True
    # Classic UTF-8 mojibake fragments from wrong CJK decoding / en-only path
    if any(s in t for s in ("Γÿ", "σô", "Σ╕", "τ¢", "µù", "Γæ", "τö", "Γé", "â€", "Ã")):
        return True
    # Repeated same character
    if len(t) >= 3 and len(set(t.replace(" ", ""))) == 1:
        return True
    return False


# High-value tokens for NEXUS / Intern / IDE workspace screenshots
_WORKSPACE_SIGNAL = re.compile(
    r"(?i)("
    r"A100|GPU|CUDA|torch|JuiceFS|/data|nb-[a-f0-9]+|"
    r"NEXUS|machine:|venue:|disk:|device|mem_budget|gpu:\d|"
    r"session|VERIFY|YOLO|Kilo|CLINE|VSCode|Jupyter|"
    r"PP-OCR|paddle|VRAM|显存|内存|vCPU|SXM|"
    r"MISSION|SESSION_PROGRESS|PERSISTENCE|HF_|token|"
    r"4000m|80Gi|80GB|cu124|FSDP|hermes|Intern"
    r")"
)
_KV_LINE = re.compile(
    r"(?i)^\s*([A-Za-z_\u4e00-\u9fff][\w\u4e00-\u9fff ./-]{1,40})\s*[:=：]\s*(.+)$"
)
_FACT_PATTERNS = [
    ("machine", re.compile(r"(?i)\bmachine\s*[:=]\s*(.+)")),
    ("venue", re.compile(r"(?i)\bvenue\s*[:=]\s*(.+)")),
    ("gpu", re.compile(r"(?i)\bGPU\s*[:=]\s*((?:NVIDIA|Nvidia)[^\n]{0,60})")),
    ("torch", re.compile(r"(?i)\btorch\s*[:=]\s*([0-9][^\n]{0,50})")),
    ("disk", re.compile(r"(?i)\bdisk\s*[:=]\s*(.+)")),
    ("device", re.compile(r'(?i)"device"\s*:\s*"(gpu:\d)"')),
    ("mem_budget_gb", re.compile(r'(?i)"mem_budget_gb"\s*:\s*([0-9.]+)')),
    ("notebook_id", re.compile(r"\b(nb-[a-f0-9]{6,})\b", re.I)),
    ("a100_line", re.compile(r"(?i)(?:GPU:\s*)?(NVIDIA\s+A100[^\n]{0,40}|Nvidia A100[^\n]{0,20})")),
    ("cuda_mem", re.compile(r"(?i)显存[：:]\s*[^\n]{0,20}")),
    ("sys_mem", re.compile(r"(?i)内存[：:]\s*[^\n]{0,20}")),
    ("cpu_line", re.compile(r"(?i)^CPU\s*[：:].+")),
    ("juicefs", re.compile(r"(?i)disk:\s*JuiceFS[^\n]{0,40}")),
]


def _normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").replace("\r", "\n")).strip()


def _looks_truncated(text: str) -> bool:
    """Heuristic: cut mid-word / incomplete OCR fragments for brief."""
    t = text.strip()
    if not t:
        return True
    if t.endswith(("-", "—", "…", "...", " wit", " and", " for", " the", " d", " c")):
        return True
    if re.search(r"(?i)(Modu1e|ideall|Bypa|setF|toro|war$|st\.\.\.|insid\.\.\.)", t):
        return True
    if t.endswith("...") and len(t) < 40:
        return True
    # lone label without value
    if t in ("内存", "显存", "CLINE", "INTERN", "Jupyter", "Kilo Code", "session4", "New Session"):
        return True
    if t.startswith("stamp: $(") or t.startswith("Loaded extra CLI"):
        return True
    return False


def _signal_score(text: str, conf: float) -> float:
    """Higher = more useful for agent workspace grounding."""
    t = _normalize_ws(text)
    if not t:
        return 0.0
    if _looks_truncated(t):
        return 0.0
    score = 0.0
    if _WORKSPACE_SIGNAL.search(t):
        score += 3.0
    if _KV_LINE.match(t):
        score += 2.5
    if re.search(r"(?i)(machine:|venue:|disk:|torch:|GPU:|nb-[a-f0-9]+|JuiceFS|A100 M0)", t):
        score += 2.0
    if len(t) >= 24:
        score += 1.0
    elif len(t) >= 14:
        score += 0.5
    if conf >= 0.9:
        score += 0.5
    elif conf >= 0.75:
        score += 0.25
    if len(t) <= 4 and not _has_cjk(t) and not t.isdigit():
        score -= 2.0
    if t.lower() in ("plan", "act", "normal", "code", "new", "menu", "spaces", "workspace", "intern"):
        score -= 2.0
    # Prefer complete kv / metric lines over chat noise
    if re.search(r"(?i)(Type a message|How to use|Let me know|Recommendation)", t):
        score -= 2.0
    return score


def _normalize_fact_value(key: str, val: str) -> str:
    v = _normalize_ws(val)
    v = re.split(r"\s+Type a message|\s+Let me know|\s+YOLO mode", v)[0].strip(" .;|")
    if key == "torch":
        # Prefer version core: 2.4.0+cu124
        m = re.search(r"([0-9]+\.[0-9]+\.[0-9]+(?:\+cu\d+)?)", v)
        if m:
            rest = ""
            if "cuda=True" in v or "cuda=true" in v.lower():
                rest = " cuda=True"
            name = re.search(r"name=([A-Za-z0-9_\-]+)", v)
            if name:
                rest += f" name={name.group(1)}"
            v = m.group(1) + rest
    if key in ("cuda_mem", "sys_mem", "cpu_line", "gpu", "a100_line"):
        v = v.replace("：", ": ")
    if key in ("gpu", "a100_line") and "A100" in v.upper():
        # Prefer full NVIDIA A100-SXM4-80GB when substring present in same line
        m = re.search(r"(NVIDIA\s+A100[-\w]*|Nvidia\s+A100[^\n,]{0,30})", v, re.I)
        if m:
            v = _normalize_ws(m.group(1))
    if key == "disk" and "JuiceFS" in v:
        v = re.sub(r"\s+", " ", v)
        if "/data" in v and not v.startswith("JuiceFS") and "disk:" not in v.lower():
            pass
        v = v.replace("disk: ", "")
        if not v.lower().startswith("juicefs"):
            v = "JuiceFS " + v if "JuiceFS" not in v else v
    return v[:180]


def _extract_workspace_facts(texts: list[str]) -> dict:
    """Pull structured NEXUS/Intern facts from OCR lines."""
    facts: dict = {}
    # Prefer longer GPU / A100 strings when multiple matches exist
    candidates: dict[str, list[str]] = {}
    blob = "\n".join(texts)
    for key, pat in _FACT_PATTERNS:
        for m in pat.finditer(blob):
            val = m.group(1).strip() if m.lastindex else m.group(0).strip()
            val = _normalize_fact_value(key, val)
            if val:
                candidates.setdefault(key, []).append(val)
    for key, vals in candidates.items():
        # longest non-truncated value wins
        vals = [v for v in vals if not _looks_truncated(v) or key in ("verify_banner", "session_title")]
        if not vals:
            continue
        facts[key] = max(vals, key=len)[:200]
    for t in texts:
        tn = _normalize_ws(t)
        if re.search(r"(?i)A100\s*M0\s*session", tn):
            facts.setdefault("session_title", tn[:120])
        if re.search(r"(?i)NEXUS.*VERIFY", tn) and "Full st" not in tn:
            facts.setdefault("verify_banner", tn[:160])
    # Canonical aliases for agents
    if facts.get("a100_line") and (
        not facts.get("gpu") or len(facts.get("a100_line", "")) >= len(facts.get("gpu", ""))
    ):
        facts["gpu"] = facts["a100_line"]
    if facts.get("disk") and "juicefs" not in facts:
        if "JuiceFS" in facts["disk"]:
            facts["juicefs"] = facts["disk"]
    return facts


def _build_agent_brief(lines: list, max_lines: int = 22) -> str:
    """Tight high-signal dump (industry brief, not chrome dump)."""
    scored = []
    for ln in lines:
        text = _normalize_ws(str(ln.get("text") or ""))
        conf = float(ln.get("confidence") or 0)
        s = _signal_score(text, conf)
        if s >= 3.0:
            scored.append((s, conf, text))
    scored.sort(key=lambda x: (-x[0], -x[1]))
    out = []
    seen = set()
    # Priority order: machine/venue/gpu/torch/disk first if present
    priority = []
    rest = []
    for s, conf, text in scored:
        if re.search(r"(?i)^(machine:|venue:|GPU:|torch:|disk:|CPU:)", text):
            priority.append((s, conf, text))
        else:
            rest.append((s, conf, text))
    for s, conf, text in priority + rest:
        key = re.sub(r"\s+", " ", text.lower())[:90]
        # near-dupe: same prefix 40 chars
        pref = key[:40]
        if key in seen or any(pref and p.startswith(pref) or pref.startswith(p[:40]) for p in seen if len(p) > 12):
            continue
        seen.add(key)
        out.append(text)
        if len(out) >= max_lines:
            break
    return "\n".join(out)


def _postprocess_lines(lines: list, raw_type: str) -> dict:
    """Reading-order sort + confidence / noise filter + workspace agent view."""
    try:
        min_conf = float(os.environ.get("NEXUS_OCR_MIN_CONF", "0.55"))
    except ValueError:
        min_conf = 0.55
    min_conf = max(0.0, min(0.99, min_conf))

    # Sort by geometry when boxes exist
    sorted_lines = sorted(lines, key=_box_sort_key)

    cleaned = []
    dropped = 0
    for ln in sorted_lines:
        text = str(ln.get("text") or "").strip()
        conf = float(ln.get("confidence") or 0.0)
        if _is_noise_text(text, conf, min_conf):
            dropped += 1
            continue
        item = {
            "text": text,
            "confidence": round(conf, 3),
            "box": ln.get("box") or [],
            "signal": round(_signal_score(text, conf), 2),
        }
        if ln.get("tile"):
            item["tile"] = ln["tile"]
        cleaned.append(item)

    # De-dupe exact consecutive duplicates (sidebar + main echo)
    deduped = []
    for ln in cleaned:
        if deduped and deduped[-1]["text"] == ln["text"]:
            # keep higher conf
            if ln["confidence"] > deduped[-1]["confidence"]:
                deduped[-1] = ln
            continue
        deduped.append(ln)

    # Global fuzzy de-dupe (tiling overlap)
    global_dedup = []
    seen_norm = set()
    for ln in deduped:
        norm = re.sub(r"\s+", " ", ln["text"].lower()).strip()
        if len(norm) >= 8 and norm in seen_norm:
            continue
        if len(norm) >= 8:
            seen_norm.add(norm)
        global_dedup.append(ln)

    full_raw = "\n".join(l["text"] for l in sorted_lines)
    full_clean = "\n".join(l["text"] for l in global_dedup)
    avg_conf = (
        round(sum(l["confidence"] for l in global_dedup) / len(global_dedup), 3)
        if global_dedup
        else 0.0
    )
    texts = [l["text"] for l in global_dedup]
    facts = _extract_workspace_facts(texts)
    agent_brief = _build_agent_brief(global_dedup)
    return {
        "lines": global_dedup,
        "line_count": len(global_dedup),
        "line_count_raw": len(lines),
        "dropped_noise": dropped,
        "avg_confidence": avg_conf,
        "min_conf": min_conf,
        "full_text": full_clean,
        "full_text_clean": full_clean,
        "full_text_raw": full_raw,
        "agent_brief": agent_brief,
        "facts": facts,
        "raw_type": raw_type,
    }


def _parse_struct_result(result) -> dict:
    """Parse PP-StructureV3 / VL output."""
    # Structure output may include layout, tables, etc.
    parsed = _parse_fast_result(result)
    parsed["structured"] = True
    return parsed


class ThreadedOCRServer(ThreadingHTTPServer):
    """Handle health checks while a long OCR runs; daemon threads exit with process."""

    daemon_threads = True
    # Exclusive bind so a second start fails loudly instead of sharing the port with a zombie.
    allow_reuse_address = False


def main():
    parser = argparse.ArgumentParser(description="NEXUS PaddleOCR Service")
    parser.add_argument("--port", type=int, default=7360)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument(
        "--warmup",
        action="store_true",
        help="Load fast engine at startup so first request is not multi-minute cold start",
    )
    parser.add_argument(
        "--idle-sec",
        type=float,
        default=None,
        help="Seconds idle after last OCR before auto-stop (default env NEXUS_OCR_IDLE_SEC or 30; 0=never)",
    )
    args = parser.parse_args()

    if args.idle_sec is not None:
        idle_sec = max(0.0, float(args.idle_sec))
    else:
        idle_sec = _idle_sec_from_env()
    boot_grace = _boot_grace_from_env()
    os.environ["NEXUS_OCR_IDLE_SEC"] = str(idle_sec)
    os.environ["NEXUS_OCR_BOOT_GRACE_SEC"] = str(boot_grace)
    with _activity_lock:
        now = time.monotonic()
        _STATE["idle_sec"] = idle_sec
        _STATE["boot_grace_sec"] = boot_grace
        _STATE["last_activity"] = now
        _STATE["started_at"] = now
        _STATE["shutdown"] = False
        _STATE["inflight"] = 0
        _STATE["jobs_done"] = 0

    # Always probe device at boot so /health reports GPU budget immediately
    try:
        _configure_device()
    except Exception:
        log.exception("device probe failed")

    if args.warmup:
        try:
            get_fast_ocr()
            _touch_activity()
        except Exception:
            log.exception("warmup failed")

    try:
        server = ThreadedOCRServer((args.host, args.port), OCRHandler)
    except OSError as e:
        log.error("Bind failed on %s:%s - is another OCR service already running? %s", args.host, args.port, e)
        raise

    # Fresh arm right before accept loop so device-probe time does not count as idle.
    _touch_activity()
    watcher = threading.Thread(
        target=_idle_watchdog,
        args=(server,),
        name="ocr-idle-watchdog",
        daemon=True,
    )
    watcher.start()

    log.info("NEXUS OCR Service listening on http://%s:%d (threaded)", args.host, args.port)
    log.info("  device=%s", _DEVICE_INFO)
    log.info("  idle_timeout_s=%s (0=disabled)", idle_sec)
    log.info("  POST /ocr          - fast (auto-resize max_edge=960)")
    log.info("  POST /ocr mode=struct|detailed - higher-res (max_edge=1400)")
    log.info("  POST /ocr/vl       - PaddleOCR-VL / fallback")
    log.info("  GET  /health       - health check (does not reset idle timer)")
    log.info("  Results also written to scratch/screenshots/OCR_RESULT_LATEST.txt")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("Shutting down OCR service (KeyboardInterrupt)")
    finally:
        log.info("OCR service stopped - engines released")
        try:
            _release_engines()
        except Exception:
            pass
        try:
            server.server_close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
