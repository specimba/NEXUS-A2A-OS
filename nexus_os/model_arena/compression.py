"""HQQ Compression Integration for VRAM-Constrained Models.

Wraps PrunaAI HQQ for 8-bit quantization with fallback to local cache.
"""

import json
import os
import time
import hashlib
from pathlib import Path
from typing import Dict, Optional, Any


COMPRESSED_CACHE_PATH = Path(os.path.expanduser("~/.nexus_os/compressed"))


class HQQQuantizer:
    """Half-Quadratic Quantization wrapper for model compression."""

    def __init__(self, cache_dir: Optional[str] = None):
        self.cache_dir = Path(cache_dir or COMPRESSED_CACHE_PATH)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def compress(
        self,
        model_name: str,
        bits: int = 8,
        group_size: int = 128,
    ) -> Dict[str, Any]:
        """Compress model using HQQ quantization."""
        cache_key = self._cache_key(model_name, bits, group_size)
        cached = self._check_cache(cache_key)
        if cached:
            return cached

        try:
            from pruna_hqq import compress_model
            start = time.time()
            compressed_path = compress_model(
                model_name=model_name,
                bits=bits,
                group_size=group_size,
            )
            elapsed = time.time() - start

            result = {
                "model": model_name,
                "bits": bits,
                "group_size": group_size,
                "compressed_path": str(compressed_path),
                "compression_ratio": self._estimate_ratio(model_name, bits),
                "timestamp": time.time(),
                "elapsed_s": elapsed,
            }
            self._write_cache(cache_key, result)
            return result

        except ImportError:
            return self._fallback_compress(model_name, bits, group_size)

    def _cache_key(self, model: str, bits: int, group_size: int) -> str:
        raw = f"{model}:{bits}:{group_size}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def _check_cache(self, key: str) -> Optional[Dict[str, Any]]:
        cache_file = self.cache_dir / f"{key}.json"
        if cache_file.exists():
            with open(cache_file, "r") as f:
                return json.load(f)
        return None

    def _write_cache(self, key: str, data: Dict[str, Any]) -> None:
        cache_file = self.cache_dir / f"{key}.json"
        with open(cache_file, "w") as f:
            json.dump(data, f, indent=2)

    def _estimate_ratio(self, model: str, bits: int) -> float:
        base_bits = 16
        return base_bits / bits

    def _fallback_compress(
        self, model_name: str, bits: int, group_size: int
    ) -> Dict[str, Any]:
        """Return stub for environments without pruna_hqq."""
        return {
            "model": model_name,
            "bits": bits,
            "group_size": group_size,
            "compressed_path": f"[fallback] {model_name}",
            "compression_ratio": self._estimate_ratio(model_name, bits),
            "timestamp": time.time(),
            "elapsed_s": 0.0,
            "status": "fallback_no_pruna",
        }