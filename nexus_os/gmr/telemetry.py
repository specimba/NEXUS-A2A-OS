"""GMR live telemetry ingestion from ModelRelay / God Mode catalogues.

Supports both OpenAI-compatible ``/v1/models`` (``data`` list) and legacy
NEXUS ``/api/models`` (``models`` list) shapes. Primary probe is Node
ModelRelay on port 7350 (not ``/api/models``-only).
"""
from __future__ import annotations

import json
import os
import threading
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class ModelTelemetry:
    name: str
    provider: str
    tier: int
    latency_ms: int
    uptime_pct: float
    status: str
    timestamp: str

    @property
    def quality_score(self) -> float:
        return min(self.tier, 100) * 0.7 + (self.uptime_pct * 100) * 0.3

    @property
    def is_available(self) -> bool:
        return self.status == "up" and self.uptime_pct >= 0.5

    @property
    def is_local(self) -> bool:
        return self.provider in {"ollama", "local"}


def default_catalogue_urls() -> List[str]:
    """Ordered endpoints to try for catalogue telemetry."""
    node = int(os.environ.get("NODERELAY_PORT", "7350"))
    god = int(os.environ.get("GODMODE_PORT", "7357"))
    py = int(os.environ.get("PYTHONRELAY_PORT", "7355"))
    return [
        f"http://127.0.0.1:{node}/v1/models",
        f"http://127.0.0.1:{god}/v1/models",
        f"http://127.0.0.1:{py}/v1/models",
        # Legacy shapes (may 404 on stock modelrelay)
        f"http://127.0.0.1:{node}/api/models",
        f"http://127.0.0.1:{god}/health",
    ]


def _http_json(url: str, timeout: float = 5.0) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "nexus-gmr-telemetry/1"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    return json.loads(raw.decode("utf-8", errors="replace"))


def parse_models_payload(data: Any, *, timestamp: str) -> Dict[str, ModelTelemetry]:
    """Parse OpenAI or legacy catalogue JSON into ModelTelemetry map."""
    out: Dict[str, ModelTelemetry] = {}
    if not isinstance(data, dict):
        return out

    # OpenAI: {"object":"list","data":[{"id":...}, ...]}
    rows = data.get("data")
    if isinstance(rows, list):
        for item in rows:
            if not isinstance(item, dict):
                continue
            mid = str(item.get("id") or item.get("name") or "").strip()
            if not mid:
                continue
            owned = str(item.get("owned_by") or item.get("provider") or "unknown")
            status = str(item.get("status") or "up")
            # health bool variants
            if item.get("healthy") is False:
                status = "down"
            tel = ModelTelemetry(
                name=mid,
                provider=owned,
                tier=int(item.get("tier") or 50),
                latency_ms=int(item.get("latency_ms") or item.get("latencyMsTypical") or 0),
                uptime_pct=float(item.get("uptime") or item.get("uptime_pct") or 1.0),
                status=status,
                timestamp=timestamp,
            )
            out[tel.name] = tel
        return out

    # Legacy: {"models":[{"name":...}, ...]}
    rows = data.get("models")
    if isinstance(rows, list):
        for item in rows:
            if not isinstance(item, dict):
                continue
            mid = str(item.get("name") or item.get("id") or "").strip()
            if not mid:
                continue
            tel = ModelTelemetry(
                name=mid,
                provider=str(item.get("provider") or "unknown"),
                tier=int(item.get("tier") or 0),
                latency_ms=int(item.get("latency_ms") or 9999),
                uptime_pct=float(item.get("uptime") or 1.0),
                status=str(item.get("status") or "unknown"),
                timestamp=timestamp,
            )
            out[tel.name] = tel
        return out

    # God-mode health: {"status":"ok","models_up":N,"total":M} — summary only
    if "models_up" in data and "total" in data:
        tel = ModelTelemetry(
            name="godmode_summary",
            provider="god_mode_proxy",
            tier=int(data.get("models_up") or 0),
            latency_ms=0,
            uptime_pct=1.0 if data.get("status") == "ok" else 0.0,
            status=str(data.get("status") or "unknown"),
            timestamp=timestamp,
        )
        out[tel.name] = tel
    return out


class TelemetryIngest:
    def __init__(self, url: str = "", urls: Optional[List[str]] = None):
        if urls:
            self.urls = list(urls)
        elif url:
            self.urls = [url]
        else:
            self.urls = default_catalogue_urls()
        # Back-compat attribute used by older callers
        self.url = self.urls[0] if self.urls else ""
        self.last_fetch: Optional[datetime] = None
        self.last_source: Optional[str] = None
        self.last_error: Optional[str] = None
        self.cache: Dict[str, ModelTelemetry] = {}
        self.lock = threading.Lock()

    def fetch(self) -> Dict[str, ModelTelemetry]:
        with self.lock:
            timestamp = datetime.now(timezone.utc).isoformat()
            self.last_error = None
            for url in self.urls:
                try:
                    data = _http_json(url, timeout=5.0)
                    parsed = parse_models_payload(data, timestamp=timestamp)
                    if not parsed:
                        continue
                    self.cache = parsed
                    self.last_fetch = datetime.now(timezone.utc)
                    self.last_source = url
                    self.url = url
                    return self.cache
                except Exception as exc:
                    self.last_error = f"{url}: {type(exc).__name__}: {exc}"
                    continue
            if self.last_error:
                # Keep previous cache; surface failure without crashing GMR.
                print(f"[GMR] Telemetry fetch failed: {self.last_error}")
            return self.cache
