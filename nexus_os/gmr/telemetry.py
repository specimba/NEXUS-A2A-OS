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


# ─────────────────────────────────────────────────────────────────────────
# Seam 2: routing-decision telemetry sink (schema v1, append-only JSONL)
#
# Chimera/CogER/LG produce routing decisions and stability data that nothing
# used to persist. record_routing_decision() is the single fail-safe sink:
# every event becomes one JSON line in $NEXUS_GMR_TELEMETRY (default
# ~/.nexus/gmr_telemetry.jsonl). The sink must NEVER raise into the routing
# path — failures degrade to a warn-once log line. A simple size guard
# rotates the file to <name>.1 above ROTATE_MAX_BYTES so growth is bounded.
# ─────────────────────────────────────────────────────────────────────────

import logging
from pathlib import Path

_routing_logger = logging.getLogger("nexus.gmr.telemetry")

ROUTING_SCHEMA_VERSION = 1

#: Schema v1 field order. Missing fields are recorded as null so every line
#: has the same shape for downstream consumers (jq / pandas / archivist).
ROUTING_SCHEMA_FIELDS = (
    "ts",                    # ISO-8601 UTC write timestamp
    "task_id",               # request/task correlation id, if the caller had one
    "coger_level",           # CogER complexity level L1-L4
    "quality_target",        # Chimera quality target (0..1)
    "latency_budget_ms",     # Chimera latency budget
    "chosen_model",          # model the decision landed on
    "candidate_count",       # how many candidates survived filtering
    "chimera_quality_score", # expected_quality of the chosen profile
    "lg_verdict",            # relay_info.hallucination verdict dict, if any
    "outcome",               # success | error | fallback (null pre-outcome)
    "source",                # relay-auto-gmr | coger | chimera
)

DEFAULT_ROUTING_TELEMETRY_PATH = Path.home() / ".nexus" / "gmr_telemetry.jsonl"

#: Size guard: rotate to <name>.1 (replacing any previous .1) above this.
ROTATE_MAX_BYTES = 50 * 1024 * 1024

_ROUTING_DISABLED_VALUES = {"0", "off", "false", "disabled", "none"}
_routing_write_lock = threading.Lock()
_routing_warned = False


def _routing_telemetry_path() -> Optional[Path]:
    """Resolve the sink path; None disables.

    Precedence mirrors persistent_trust_memory.default_trust_memory_path():
    NEXUS_GMR_TELEMETRY (explicit / disable), then NEXUS_HOME (tests/CI
    isolation), then ~/.nexus/gmr_telemetry.jsonl.
    """
    raw = os.environ.get("NEXUS_GMR_TELEMETRY", "").strip()
    if raw.lower() in _ROUTING_DISABLED_VALUES:
        return None
    if raw:
        return Path(raw).expanduser()
    nexus_home = os.environ.get("NEXUS_HOME")
    if nexus_home:
        return Path(nexus_home) / "gmr_telemetry.jsonl"
    return DEFAULT_ROUTING_TELEMETRY_PATH


def _rotate_if_oversized(path: Path, max_bytes: int) -> None:
    """Best-effort size guard; rotation failure must not block the write."""
    try:
        if path.exists() and path.stat().st_size > max_bytes:
            os.replace(path, path.with_name(path.name + ".1"))
    except OSError:
        pass


def _warn_routing_sink_once(exc: Exception) -> None:
    global _routing_warned
    if not _routing_warned:
        _routing_warned = True
        _routing_logger.warning(
            "GMR routing telemetry sink failed (%s: %s) — routing decisions "
            "are NOT being persisted",
            type(exc).__name__, exc,
        )


def record_routing_decision(event: dict) -> None:
    """Append one schema-v1 routing-decision record as a JSONL line.

    Fail-safe by contract: this function NEVER raises into the routing
    path. Any sink failure (bad path, permissions, disk full, non-dict
    event) is swallowed and reported once via a warning log.

    Unknown keys in *event* are passed through after the schema fields so
    call sites can attach extra context (phase, strategy, latency_ms, ...).
    """
    try:
        path = _routing_telemetry_path()
        if path is None:
            return
        record: Dict[str, Any] = {
            "schema_version": ROUTING_SCHEMA_VERSION,
            "ts": event.get("ts") or datetime.now(timezone.utc).isoformat(),
        }
        for field_name in ROUTING_SCHEMA_FIELDS:
            if field_name == "ts":
                continue
            record[field_name] = event.get(field_name)
        for key, value in event.items():
            if key not in record:
                record[key] = value
        line = json.dumps(record, ensure_ascii=False, default=str)
        with _routing_write_lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            _rotate_if_oversized(path, ROTATE_MAX_BYTES)
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")
    except Exception as exc:
        _warn_routing_sink_once(exc)
