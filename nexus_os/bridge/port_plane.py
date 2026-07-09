"""NEXUS port plane (7350–7360 + related) — purpose, probes, pipeline roles.

Single source of truth for live service topology used by nexusctl, NexusClaw
control-center, and gateway revive scripts. Ownership IDs stay aligned with
``PortRegistry.CANONICAL_PORTS``; this module adds health paths and pipeline edges.

Hard rule: **7352 = Brain API / governance only** — never ModelRelay.
"""

from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable, Sequence


@dataclass(frozen=True)
class PortService:
    port: int
    owner: str
    title: str
    role: str  # pipeline layer label
    purpose: str
    health_paths: tuple[str, ...]  # try in order; first 2xx wins
    required: bool = True
    openapi_compatible: bool = False
    notes: str = ""
    pipeline: tuple[str, ...] = ()  # upstream/downstream tags
    bind_policy: str = "loopback_preferred"  # loopback_preferred | loopback_only


# Canonical plane for the 735x band + adjacent orchestration ports used by
# the living NEXUS organism (ctl / claw / relay / chimera / GMR / wiki).
PORT_PLANE: dict[int, PortService] = {
    7350: PortService(
        port=7350,
        owner="modelrelay_npm",
        title="Node ModelRelay (primary)",
        role="inference_gateway",
        purpose=(
            "Primary OpenAI-compatible model router (npm modelrelay). "
            "Clients: Brain API, God Mode, GMR/Chimera, Hermes base_url, OpenCode."
        ),
        health_paths=("/", "/v1/models"),  # /health is 404 on modelrelay
        required=True,
        openapi_compatible=True,
        notes="Do NOT probe /health — returns 404. Use / or /v1/models.",
        pipeline=("entry_clients", "god_mode_7357", "brain_api_7352", "gmr"),
    ),
    7351: PortService(
        port=7351,
        owner="reserved_unused",
        title="Reserved (unused)",
        role="reserved",
        purpose="Historically free; do not claim without PortRegistry update.",
        health_paths=("/health", "/"),
        required=False,
        notes="Intentionally unassigned in 2026-07 plane.",
        pipeline=(),
    ),
    7352: PortService(
        port=7352,
        owner="brain_api",
        title="NEXUS Brain API",
        role="governance",
        purpose=(
            "Governed FastAPI: agents/tasks/messages, KAIJU, relay proxy, "
            "OpenAI-compat surface for dashboard + NexusClaw."
        ),
        health_paths=("/health", "/"),
        required=True,
        openapi_compatible=True,
        notes="NEVER ModelRelay. Proxies 7350 then 7355; god profiles → 7357.",
        pipeline=("dashboard", "nexusclaw", "governor", "modelrelay"),
        bind_policy="loopback_preferred",
    ),
    7353: PortService(
        port=7353,
        owner="twave",
        title="TWAVE wrapper",
        role="execution_low_vram",
        purpose="Low-VRAM execution layer under /twave/* for external TWAVE team.",
        health_paths=("/health", "/twave/health", "/"),
        required=False,
        notes="Optional; contracts-only for external teams.",
        pipeline=("gmr_optional",),
    ),
    7354: PortService(
        port=7354,
        owner="gross_bridge",
        title="Grok / GROSS MCP Bridge",
        role="browser_mcp",
        purpose=(
            "nexus-grok-bridge-v2 MCP+A2A tools for browser CDP lanes "
            "(read-oriented control surface for Grok automation)."
        ),
        health_paths=("/health",),
        required=True,
        notes="Live server name may be nexus-grok-bridge-v2; owner id remains gross_bridge.",
        pipeline=("cdp_9224", "browser_ai_supervisor", "nexusclaw"),
        bind_policy="loopback_only",
    ),
    7355: PortService(
        port=7355,
        owner="modelrelay_python",
        title="Python ModelRelay (fallback)",
        role="inference_gateway_fallback",
        purpose="Python relay: Ollama-cloud + local discovery; Brain API fallback.",
        health_paths=("/health", "/", "/v1/models"),
        required=True,
        openapi_compatible=True,
        notes="healthy_models may be empty while still serving discovered list.",
        pipeline=("brain_api_7352", "god_mode_optional"),
    ),
    7356: PortService(
        port=7356,
        owner="static_dashboard",
        title="Static Arena / Wiki UI",
        role="operator_ui",
        purpose="HTML Quality×Health matrix + wiki static UI (outside full Brain auth).",
        health_paths=("/health", "/"),
        required=False,
        notes="Was missing /health — serve_dashboard_7356.js should expose it.",
        pipeline=("operator", "wiki_intel"),
        bind_policy="loopback_preferred",
    ),
    7357: PortService(
        port=7357,
        owner="god_mode_proxy",
        title="God Mode Proxy v3",
        role="smart_router",
        purpose="Profile-based routing (auto-fastest/smart) over ModelRelay model set.",
        health_paths=("/health", "/v1/models"),
        required=True,
        openapi_compatible=True,
        notes="Sits between clients and 7350; Brain API routes god-* profiles here.",
        pipeline=("clients", "modelrelay_7350"),
    ),
    7358: PortService(
        port=7358,
        owner="reserved_chimera",
        title="Reserved — Chimera / experimental",
        role="reserved",
        purpose="Reserved for ChimeraRouter sidecar or future LG control plane.",
        health_paths=("/health", "/"),
        required=False,
        notes="Not assigned live as of 2026-07-09.",
        pipeline=("gmr", "chimera"),
    ),
    7359: PortService(
        port=7359,
        owner="reserved_wiki_intel",
        title="Reserved — Wiki/DoppelGround intel",
        role="reserved",
        purpose="Optional dedicated wiki-intel/DoppelGround API port if split from 7352/7356.",
        health_paths=("/health", "/"),
        required=False,
        notes="Wiki currently co-located on 7356 static + Brain/docs paths.",
        pipeline=("archivist", "doppelground"),
    ),
    7360: PortService(
        port=7360,
        owner="reserved_extension",
        title="Reserved — extension band end",
        role="reserved",
        purpose="Upper bound of the 735x governance/relay band.",
        health_paths=("/health", "/"),
        required=False,
        pipeline=(),
    ),
    # Adjacent ports referenced by the living organism
    3001: PortService(
        port=3001,
        owner="next_dashboard",
        title="Next.js Command Center",
        role="operator_ui",
        purpose="Primary Next dashboard; /api/nexusclaw/status probes the plane.",
        health_paths=("/api/nexusclaw/status", "/"),
        required=False,
        notes="3000 often used as dev fallback.",
        pipeline=("operator", "nexusclaw"),
    ),
    9224: PortService(
        port=9224,
        owner="chrome_cdp",
        title="Chrome CDP (lane browser)",
        role="browser_runtime",
        purpose="Windows Chrome remote debugging for multi-lane browser agents.",
        health_paths=("/json/version", "/json/list"),
        required=False,
        notes="Not HTTP NEXUS process; CDP JSON endpoints.",
        pipeline=("browser_mcp_7354",),
        bind_policy="loopback_only",
    ),
}


PIPELINE_LAYERS: tuple[tuple[str, str, tuple[int, ...]], ...] = (
    ("1_operator_ui", "Operator / dashboard surfaces", (3001, 7356)),
    ("2_governance", "Brain API + NexusClaw governance", (7352,)),
    ("3_smart_route", "God Mode profile router", (7357,)),
    ("4_inference", "ModelRelay primary + fallback", (7350, 7355)),
    ("5_browser", "CDP + Grok MCP bridge", (9224, 7354)),
    ("6_execution", "TWAVE low-VRAM (optional)", (7353,)),
    ("7_reserved", "Chimera / wiki-intel / extension", (7358, 7359, 7360, 7351)),
)


@dataclass
class ProbeResult:
    port: int
    owner: str
    title: str
    listening: bool
    http_ok: bool
    status_code: int | None
    path_used: str | None
    latency_ms: float | None
    body_snippet: str | None
    required: bool
    error: str | None = None
    role: str = ""
    classification: str = "down"  # up | degraded | down | free_optional

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def is_listening(port: int, host: str = "127.0.0.1", timeout: float = 0.4) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _http_get(
    url: str, timeout: float = 2.0
) -> tuple[int | None, str | None, float | None, str | None]:
    import time

    started = time.perf_counter()
    try:
        req = urllib.request.Request(url, method="GET", headers={"User-Agent": "nexus-port-plane/1"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read(400)
            text = raw.decode("utf-8", errors="replace")
            ms = (time.perf_counter() - started) * 1000.0
            return int(resp.status), text, ms, None
    except urllib.error.HTTPError as exc:
        ms = (time.perf_counter() - started) * 1000.0
        try:
            body = exc.read(200).decode("utf-8", errors="replace")
        except Exception:
            body = None
        return int(exc.code), body, ms, str(exc.reason)
    except Exception as exc:
        return None, None, None, f"{type(exc).__name__}: {exc}"


def probe_service(
    service: PortService,
    *,
    host: str = "127.0.0.1",
    timeout: float = 2.0,
) -> ProbeResult:
    listening = is_listening(service.port, host=host)
    if not listening:
        return ProbeResult(
            port=service.port,
            owner=service.owner,
            title=service.title,
            listening=False,
            http_ok=False,
            status_code=None,
            path_used=None,
            latency_ms=None,
            body_snippet=None,
            required=service.required,
            error="not_listening",
            role=service.role,
            classification="down" if service.required else "free_optional",
        )

    last_err: str | None = None
    for path in service.health_paths:
        url = f"http://{host}:{service.port}{path}"
        code, body, ms, err = _http_get(url, timeout=timeout)
        if code is not None and 200 <= code < 300:
            return ProbeResult(
                port=service.port,
                owner=service.owner,
                title=service.title,
                listening=True,
                http_ok=True,
                status_code=code,
                path_used=path,
                latency_ms=ms,
                body_snippet=(body or "")[:180] if body else None,
                required=service.required,
                error=None,
                role=service.role,
                classification="up",
            )
        last_err = err or f"http_{code}"
    # Listening but no healthy path
    return ProbeResult(
        port=service.port,
        owner=service.owner,
        title=service.title,
        listening=True,
        http_ok=False,
        status_code=None,
        path_used=None,
        latency_ms=None,
        body_snippet=None,
        required=service.required,
        error=last_err or "no_healthy_path",
        role=service.role,
        classification="degraded" if service.required else "down",
    )


def probe_plane(
    ports: Iterable[int] | None = None,
    *,
    host: str = "127.0.0.1",
    timeout: float = 2.0,
) -> list[ProbeResult]:
    if ports is None:
        ordered = sorted(PORT_PLANE.keys())
    else:
        ordered = list(ports)
    results: list[ProbeResult] = []
    for port in ordered:
        service = PORT_PLANE.get(port)
        if service is None:
            results.append(
                ProbeResult(
                    port=port,
                    owner="unknown",
                    title=f"unknown:{port}",
                    listening=is_listening(port, host=host),
                    http_ok=False,
                    status_code=None,
                    path_used=None,
                    latency_ms=None,
                    body_snippet=None,
                    required=False,
                    error="not_in_plane",
                    classification="down",
                )
            )
            continue
        results.append(probe_service(service, host=host, timeout=timeout))
    return results


def plane_summary(results: Sequence[ProbeResult]) -> dict[str, Any]:
    required = [r for r in results if r.required]
    up = [r for r in results if r.classification == "up"]
    degraded = [r for r in results if r.classification == "degraded"]
    down_req = [r for r in required if r.classification in {"down", "degraded"}]
    overall = "ok"
    if down_req:
        overall = "degraded" if any(r.http_ok for r in required) else "critical"
    if any(r.required and not r.listening for r in results):
        overall = "critical" if overall != "ok" else "degraded"

    layers = []
    by_port = {r.port: r for r in results}
    for layer_id, title, ports in PIPELINE_LAYERS:
        layer_results = [by_port[p] for p in ports if p in by_port]
        layers.append(
            {
                "id": layer_id,
                "title": title,
                "ports": [
                    {
                        "port": r.port,
                        "classification": r.classification,
                        "path": r.path_used,
                    }
                    for r in layer_results
                ],
            }
        )

    return {
        "status": overall,
        "required_up": sum(1 for r in required if r.classification == "up"),
        "required_total": len(required),
        "up": len(up),
        "degraded": len(degraded),
        "down_required": [
            {"port": r.port, "owner": r.owner, "error": r.error} for r in down_req
        ],
        "pipeline_layers": layers,
        "routing_chain": [
            "clients → 7357 GodMode (profiles) OR 7352 Brain (governed)",
            "7352 Brain → 7350 Node ModelRelay → 7355 Python fallback",
            "GMR/Chimera/CogER → 7350 (NODERELAY_PORT)",
            "Browser lanes → CDP 9224 + MCP 7354 → supervisor",
            "Operator UI → 3001 Next + 7356 static arena/wiki",
        ],
        "stale_doc_warnings": [
            "Any doc claiming 7352=ModelRelay is STALE — 7352 is Brain API only.",
            "Probing 7350/health is wrong — use / or /v1/models.",
        ],
    }


def doctor_report(
    *,
    host: str = "127.0.0.1",
    timeout: float = 2.0,
    band_only: bool = False,
) -> dict[str, Any]:
    if band_only:
        ports = list(range(7350, 7361))
    else:
        ports = sorted(PORT_PLANE.keys())
    results = probe_plane(ports, host=host, timeout=timeout)
    summary = plane_summary(results)
    return {
        "command": "ports doctor",
        "host": host,
        **summary,
        "services": [r.to_dict() for r in results],
        "plane_version": "2026-07-09",
    }
