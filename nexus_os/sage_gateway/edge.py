"""Loopback-only, deny-by-default reverse-proxy edge for NEXUS SAGE.

This edge is the only component intended to sit behind an operator-managed
HTTPS tunnel.  It is deliberately not a general reverse proxy: the Brain
origin is fixed in code, the six SAGE operations are matched exactly, and all
other paths, methods, query shapes, and encoded paths are rejected locally.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
import ipaddress
import json
import math
import os
import re
import threading
import time
from typing import Iterable
from urllib.parse import parse_qsl, urlencode

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse, Response
import httpx

from nexus_os.bridge.port_registry import PortRegistry
from nexus_os.sage_gateway.security import (
    authenticate_sage_bearer,
    max_body_bytes,
)


DEFAULT_EDGE_HOST = "127.0.0.1"
DEFAULT_EDGE_PORT = 17_452
UPSTREAM_ORIGIN = "http://127.0.0.1:7352"
LIVENESS_PATH = "/_nexus/sage-edge/live"
READINESS_PATH = "/_nexus/sage-edge/ready"
PRIVACY_PATH = "/nexus-sage/privacy"

_FIXED_OPERATIONS = frozenset(
    {
        ("GET", "/api/sage/v1/health"),
        ("GET", "/api/sage/v1/capabilities"),
        ("GET", "/api/sage/v1/grounding"),
        ("GET", "/api/sage/v1/model-cards"),
        ("POST", "/api/sage/v1/jobs"),
    }
)
_JOB_STATUS_PATH = re.compile(r"^/api/sage/v1/jobs/sage-job-[0-9a-f]{32}$")
_SAFE_REQUEST_HEADERS = frozenset({"accept", "authorization", "content-type"})
_SAFE_RESPONSE_HEADERS = frozenset(
    {
        "cache-control",
        "content-language",
        "content-type",
        "etag",
        "expires",
        "last-modified",
        "retry-after",
        "vary",
        "x-nexus-idempotency",
    }
)
_HOP_BY_HOP_HEADERS = frozenset(
    {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailer",
        "transfer-encoding",
        "upgrade",
    }
)
_MAX_UPSTREAM_RESPONSE_BYTES = 1_048_576
_DEFAULT_MAX_IN_FLIGHT = 4
_DEFAULT_RATE_LIMIT_REQUESTS = 60
_DEFAULT_RATE_LIMIT_WINDOW_SECONDS = 60
_MAX_CONFIGURED_IN_FLIGHT = 16
_MAX_CONFIGURED_RATE_REQUESTS = 120
_MAX_CONFIGURED_RATE_WINDOW_SECONDS = 3_600
_MIN_CONFIGURED_RATE_WINDOW_SECONDS = 10

_PRIVACY_NOTICE = """NEXUS SAGE Edge Privacy Notice

This private operator preview forwards exactly six allowlisted SAGE operations
to the local NEXUS Brain governance service: health, capabilities, grounding,
model-card lookup, proposal-job submission, and proposal-job status. The edge
itself does not persist bearer credentials or request bodies; it holds them in
memory only while authenticating and forwarding a request.

When this preview is used from a private ChatGPT GPT through an operator-selected
tunnel, OpenAI and the tunnel provider may process request and response data
under their respective policies. The Brain may persist submitted proposal-job
data according to its configured retention. There is currently no user-facing
deletion API for that persisted Brain data.

This preview is not a public-production service. It does not expose arbitrary
program execution, raw memory export, or a general proxy.
"""


@dataclass(frozen=True)
class EdgeTarget:
    method: str
    path: str
    query: str = ""

    @property
    def relative_url(self) -> str:
        return f"{self.path}?{self.query}" if self.query else self.path


class EdgeRequestRejected(ValueError):
    """A request did not match the public SAGE edge contract."""

    def __init__(
        self,
        status_code: int,
        code: str,
        detail: str,
        *,
        retry_after: int = 0,
    ) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.code = code
        self.detail = detail
        self.retry_after = retry_after


def _bounded_ascii_int_env(
    name: str,
    *,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    """Read one bounded positive integer without permissive coercions."""

    raw = os.environ.get(name)
    if raw is None:
        return default
    if re.fullmatch(r"[1-9][0-9]*", raw) is None:
        raise ValueError(f"{name} must be an ASCII positive integer")
    value = int(raw)
    if value < minimum or value > maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


def edge_max_in_flight() -> int:
    return _bounded_ascii_int_env(
        "NEXUS_SAGE_EDGE_MAX_IN_FLIGHT",
        default=_DEFAULT_MAX_IN_FLIGHT,
        minimum=1,
        maximum=_MAX_CONFIGURED_IN_FLIGHT,
    )


def edge_rate_limit_requests() -> int:
    return _bounded_ascii_int_env(
        "NEXUS_SAGE_EDGE_RATE_LIMIT_REQUESTS",
        default=_DEFAULT_RATE_LIMIT_REQUESTS,
        minimum=1,
        maximum=_MAX_CONFIGURED_RATE_REQUESTS,
    )


def edge_rate_limit_window_seconds() -> int:
    return _bounded_ascii_int_env(
        "NEXUS_SAGE_EDGE_RATE_LIMIT_WINDOW_SECONDS",
        default=_DEFAULT_RATE_LIMIT_WINDOW_SECONDS,
        minimum=_MIN_CONFIGURED_RATE_WINDOW_SECONDS,
        maximum=_MAX_CONFIGURED_RATE_WINDOW_SECONDS,
    )


class _EdgeAbuseGuard:
    """Bounded process-global admission control for authenticated operations."""

    def __init__(
        self,
        *,
        max_in_flight: int,
        max_requests: int,
        window_seconds: int,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if not 1 <= max_in_flight <= _MAX_CONFIGURED_IN_FLIGHT:
            raise ValueError("max_in_flight is outside the safe bound")
        if not 1 <= max_requests <= _MAX_CONFIGURED_RATE_REQUESTS:
            raise ValueError("max_requests is outside the safe bound")
        if not (
            _MIN_CONFIGURED_RATE_WINDOW_SECONDS
            <= window_seconds
            <= _MAX_CONFIGURED_RATE_WINDOW_SECONDS
        ):
            raise ValueError("window_seconds is outside the safe bound")
        self._max_in_flight = max_in_flight
        self._max_requests = max_requests
        self._window_seconds = float(window_seconds)
        self._clock = clock
        self._lock = threading.Lock()
        self._active = 0
        self._admitted_at: deque[float] = deque()
        self._last_now = 0.0

    def enter(self) -> None:
        """Admit immediately or reject without waiting or reading a body."""

        now = float(self._clock())
        if not math.isfinite(now):
            raise EdgeRequestRejected(
                503,
                "sage_edge_admission_unavailable",
                "SAGE edge admission control is unavailable",
                retry_after=1,
            )
        with self._lock:
            now = max(now, self._last_now)
            self._last_now = now
            cutoff = now - self._window_seconds
            while self._admitted_at and self._admitted_at[0] <= cutoff:
                self._admitted_at.popleft()

            if self._active >= self._max_in_flight:
                raise EdgeRequestRejected(
                    503,
                    "sage_edge_concurrency_saturated",
                    "SAGE edge concurrency limit is saturated",
                    retry_after=1,
                )
            if len(self._admitted_at) >= self._max_requests:
                retry_after = max(
                    1,
                    math.ceil(self._admitted_at[0] + self._window_seconds - now),
                )
                raise EdgeRequestRejected(
                    429,
                    "sage_edge_rate_limited",
                    "SAGE edge request rate limit exceeded",
                    retry_after=retry_after,
                )

            self._active += 1
            self._admitted_at.append(now)

    def leave(self) -> None:
        with self._lock:
            if self._active <= 0:
                raise RuntimeError("SAGE edge admission release imbalance")
            self._active -= 1


_PROCESS_ABUSE_GUARD = _EdgeAbuseGuard(
    max_in_flight=edge_max_in_flight(),
    max_requests=edge_rate_limit_requests(),
    window_seconds=edge_rate_limit_window_seconds(),
)


def validate_edge_bind_host(host: str) -> str:
    """Return a normalized literal loopback address or fail closed."""

    candidate = str(host).strip()
    try:
        address = ipaddress.ip_address(candidate)
    except ValueError as exc:
        raise ValueError("SAGE edge host must be a literal loopback address") from exc
    if not address.is_loopback:
        raise ValueError("SAGE edge refuses non-loopback bind addresses")
    return str(address)


def validate_edge_port(port: int | str) -> int:
    """Reject privileged, invalid, and NEXUS-reserved ports."""

    try:
        candidate = int(port)
    except (TypeError, ValueError) as exc:
        raise ValueError("SAGE edge port must be an integer") from exc
    if candidate < 1_024 or candidate > 65_535:
        raise ValueError("SAGE edge port must be between 1024 and 65535")
    if candidate in PortRegistry.CANONICAL_PORTS:
        owner = PortRegistry.CANONICAL_PORTS[candidate]
        raise ValueError(f"SAGE edge port {candidate} is reserved for {owner}")
    return candidate


def configured_edge_host() -> str:
    return validate_edge_bind_host(
        os.environ.get("NEXUS_SAGE_EDGE_HOST", DEFAULT_EDGE_HOST)
    )


def configured_edge_port() -> int:
    return validate_edge_port(
        os.environ.get("NEXUS_SAGE_EDGE_PORT", str(DEFAULT_EDGE_PORT))
    )


def edge_body_limit() -> int:
    """Clamp the edge limit so it can never exceed the Brain SAGE limit."""

    brain_limit = max_body_bytes()
    try:
        requested = int(
            os.environ.get("NEXUS_SAGE_EDGE_MAX_BODY_BYTES", str(brain_limit))
        )
    except ValueError:
        requested = brain_limit
    return max(1, min(requested, brain_limit))


def _raw_path_matches(scope: dict, path: str) -> bool:
    raw_path = scope.get("raw_path")
    if not isinstance(raw_path, (bytes, bytearray)):
        return False
    raw_bytes = bytes(raw_path)
    # ASGI servers normally exclude the query from ``raw_path``.  HTTPX's
    # in-process transport includes it, so accept that representation only
    # when the suffix is byte-for-byte identical to ``query_string``.
    if b"?" in raw_bytes:
        raw_bytes, separator, raw_query = raw_bytes.partition(b"?")
        if not separator or raw_query != scope.get("query_string", b""):
            return False
    try:
        raw_text = raw_bytes.decode("ascii")
    except UnicodeDecodeError:
        return False
    # Valid SAGE paths are ASCII and require no percent-encoding. Comparing the
    # raw and decoded forms rejects encoded slashes, dots, and alternate spellings.
    return raw_text == path and "%" not in raw_text and "\\" not in raw_text


def _canonical_query(path: str, raw_query: bytes) -> str:
    if not raw_query:
        return ""
    if path != "/api/sage/v1/model-cards":
        raise EdgeRequestRejected(
            400, "sage_edge_query_rejected", "query parameters are not allowed"
        )
    try:
        raw_text = raw_query.decode("ascii")
        pairs = parse_qsl(raw_text, keep_blank_values=True, strict_parsing=True)
    except (UnicodeDecodeError, ValueError) as exc:
        raise EdgeRequestRejected(
            400, "sage_edge_query_rejected", "invalid query parameters"
        ) from exc
    if len(pairs) != 1 or pairs[0][0] != "limit" or not pairs[0][1].isdigit():
        raise EdgeRequestRejected(
            400, "sage_edge_query_rejected", "only one numeric limit is allowed"
        )
    limit = int(pairs[0][1])
    if limit < 1 or limit > 100:
        raise EdgeRequestRejected(
            400, "sage_edge_query_rejected", "limit must be between 1 and 100"
        )
    return urlencode({"limit": limit})


def classify_edge_target(request: Request) -> EdgeTarget:
    """Validate the exact method/path/query tuple before any upstream I/O."""

    method = request.method.upper()
    path = request.scope.get("path")
    if not isinstance(path, str) or not _raw_path_matches(request.scope, path):
        raise EdgeRequestRejected(
            404, "sage_edge_path_rejected", "path is not allowlisted"
        )

    allowed = (method, path) in _FIXED_OPERATIONS
    if method == "GET" and _JOB_STATUS_PATH.fullmatch(path):
        allowed = True
    if not allowed:
        same_path_allowed = any(
            candidate_path == path for _, candidate_path in _FIXED_OPERATIONS
        )
        same_path_allowed = same_path_allowed or bool(_JOB_STATUS_PATH.fullmatch(path))
        if same_path_allowed:
            raise EdgeRequestRejected(
                405, "sage_edge_method_rejected", "method is not allowlisted"
            )
        raise EdgeRequestRejected(
            404, "sage_edge_path_rejected", "path is not allowlisted"
        )

    query = _canonical_query(path, request.scope.get("query_string", b""))
    return EdgeTarget(method=method, path=path, query=query)


async def _read_bounded_body(request: Request, limit: int) -> bytes:
    chunks: list[bytes] = []
    seen = 0
    async for chunk in request.stream():
        seen += len(chunk)
        if seen > limit:
            raise EdgeRequestRejected(
                413, "sage_edge_payload_too_large", "request body is too large"
            )
        if chunk:
            chunks.append(chunk)
    return b"".join(chunks)


def _request_headers(request: Request) -> dict[str, str]:
    return {
        name: value
        for name, value in request.headers.items()
        if name.lower() in _SAFE_REQUEST_HEADERS
        and name.lower() not in _HOP_BY_HOP_HEADERS
    }


def _connection_tokens(headers: httpx.Headers) -> set[str]:
    values = headers.get_list("connection")
    return {
        token.strip().lower()
        for value in values
        for token in value.split(",")
        if token.strip()
    }


def _response_headers(headers: httpx.Headers) -> dict[str, str]:
    connection_scoped = _connection_tokens(headers)
    return {
        name: value
        for name, value in headers.multi_items()
        if name.lower() in _SAFE_RESPONSE_HEADERS
        and name.lower() not in _HOP_BY_HOP_HEADERS
        and name.lower() not in connection_scoped
    }


def _make_upstream_client(
    transport: httpx.AsyncBaseTransport | None = None,
) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=UPSTREAM_ORIGIN,
        timeout=httpx.Timeout(10.0, connect=3.0),
        follow_redirects=False,
        trust_env=False,
        transport=transport,
    )


async def _read_upstream_response(response: httpx.Response) -> bytes:
    chunks: list[bytes] = []
    seen = 0
    async for chunk in response.aiter_bytes():
        seen += len(chunk)
        if seen > _MAX_UPSTREAM_RESPONSE_BYTES:
            raise EdgeRequestRejected(
                502,
                "sage_edge_upstream_response_too_large",
                "upstream response exceeded the edge limit",
            )
        chunks.append(chunk)
    return b"".join(chunks)


def _error_response(error: EdgeRequestRejected) -> JSONResponse:
    headers = {
        "Cache-Control": "no-store, private",
        "Pragma": "no-cache",
    }
    if error.retry_after:
        headers["Retry-After"] = str(error.retry_after)
    return JSONResponse(
        status_code=error.status_code,
        content={"detail": error.detail, "code": error.code},
        headers=headers,
    )


def _auth_error_response(error: HTTPException) -> JSONResponse:
    headers = {"Cache-Control": "no-store, private", "Pragma": "no-cache"}
    if error.status_code == 401:
        headers["WWW-Authenticate"] = "Bearer"
    return JSONResponse(
        status_code=error.status_code,
        content={"detail": str(error.detail), "code": "sage_edge_auth_rejected"},
        headers=headers,
    )


async def _brain_sage_is_ready(
    *,
    transport: httpx.AsyncBaseTransport | None,
    authorization: str,
    expected_mode: str,
) -> bool:
    """Verify the fixed Brain SAGE health contract without exposing it."""

    try:
        async with _make_upstream_client(transport) as client:
            upstream_request = client.build_request(
                "GET",
                "/api/sage/v1/health",
                headers={"Accept": "application/json", "Authorization": authorization},
            )
            upstream = await client.send(
                upstream_request,
                stream=True,
                follow_redirects=False,
            )
            try:
                if upstream.status_code != 200:
                    return False
                body = await _read_upstream_response(upstream)
            finally:
                await upstream.aclose()
    except (EdgeRequestRejected, httpx.RequestError, httpx.TimeoutException):
        return False

    try:
        payload = json.loads(body)
    except (TypeError, UnicodeDecodeError, json.JSONDecodeError):
        return False
    return (
        isinstance(payload, dict)
        and payload.get("ok") is True
        and payload.get("service") == "nexus-sage-ingress"
        and payload.get("mode") == expected_mode
        and payload.get("execution_allowed") is False
    )


def create_sage_edge_app(
    *,
    transport: httpx.AsyncBaseTransport | None = None,
) -> FastAPI:
    """Create the fixed-origin SAGE edge app; transport exists only for tests."""
    abuse_guard = _PROCESS_ABUSE_GUARD

    app = FastAPI(
        title="NEXUS SAGE Edge",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        redirect_slashes=False,
    )

    @app.middleware("http")
    async def dispatch_sage_edge(request: Request, call_next):
        path = request.scope.get("path", "")
        if path in {LIVENESS_PATH, READINESS_PATH, PRIVACY_PATH}:
            if not _raw_path_matches(request.scope, str(path)):
                return _error_response(
                    EdgeRequestRejected(
                        404, "sage_edge_path_rejected", "path is not allowlisted"
                    )
                )
            local_response = await call_next(request)
            if local_response.status_code >= 400:
                local_response.headers["Cache-Control"] = "no-store, private"
                local_response.headers["Pragma"] = "no-cache"
            return local_response

        admitted = False
        try:
            target = classify_edge_target(request)
            authenticate_sage_bearer(request.headers.get("authorization"))
            abuse_guard.enter()
            admitted = True
            body = await _read_bounded_body(request, edge_body_limit())
            if target.method == "GET" and body:
                raise EdgeRequestRejected(
                    400, "sage_edge_body_rejected", "GET request bodies are not allowed"
                )
            if target.method == "POST":
                media_type = (
                    request.headers.get("content-type", "")
                    .split(";", 1)[0]
                    .strip()
                    .lower()
                )
                if media_type != "application/json":
                    raise EdgeRequestRejected(
                        415,
                        "sage_edge_media_type_rejected",
                        "application/json is required",
                    )

            async with _make_upstream_client(transport) as client:
                upstream_request = client.build_request(
                    target.method,
                    target.relative_url,
                    headers=_request_headers(request),
                    content=body,
                )
                for header in _HOP_BY_HOP_HEADERS:
                    if header in upstream_request.headers:
                        del upstream_request.headers[header]
                upstream = await client.send(
                    upstream_request, stream=True, follow_redirects=False
                )
                try:
                    if 300 <= upstream.status_code < 400:
                        raise EdgeRequestRejected(
                            502,
                            "sage_edge_upstream_redirect_rejected",
                            "upstream redirect was rejected",
                        )
                    content = await _read_upstream_response(upstream)
                    response_headers = _response_headers(upstream.headers)
                    response_headers["cache-control"] = "no-store, private"
                    response_headers["pragma"] = "no-cache"
                    return Response(
                        status_code=upstream.status_code,
                        content=content,
                        headers=response_headers,
                    )
                finally:
                    await upstream.aclose()
        except EdgeRequestRejected as exc:
            return _error_response(exc)
        except HTTPException as exc:
            return _auth_error_response(exc)
        except httpx.TimeoutException:
            return _error_response(
                EdgeRequestRejected(
                    504, "sage_edge_upstream_timeout", "Brain SAGE upstream timed out"
                )
            )
        except httpx.RequestError:
            return _error_response(
                EdgeRequestRejected(
                    502,
                    "sage_edge_upstream_unavailable",
                    "Brain SAGE upstream is unavailable",
                )
            )
        finally:
            if admitted:
                abuse_guard.leave()

    @app.get(LIVENESS_PATH, include_in_schema=False)
    async def liveness() -> JSONResponse:
        return JSONResponse(
            {
                "ok": True,
                "service": "nexus-sage-edge",
                "check": "liveness",
                "upstream_checked": False,
            },
            headers={"Cache-Control": "no-store"},
        )

    @app.get(READINESS_PATH, include_in_schema=False)
    async def readiness(request: Request) -> JSONResponse:
        admitted = False
        try:
            context = authenticate_sage_bearer(request.headers.get("authorization"))
            abuse_guard.enter()
            admitted = True
            body = await _read_bounded_body(request, edge_body_limit())
            if body:
                raise EdgeRequestRejected(
                    400,
                    "sage_edge_body_rejected",
                    "GET request bodies are not allowed",
                )
            if not await _brain_sage_is_ready(
                transport=transport,
                authorization=request.headers.get("authorization", ""),
                expected_mode=context.mode,
            ):
                raise EdgeRequestRejected(
                    503,
                    "sage_edge_upstream_not_ready",
                    "Brain SAGE upstream is not ready",
                )
            return JSONResponse(
                {
                    "ok": True,
                    "service": "nexus-sage-edge",
                    "check": "readiness",
                    "upstream_checked": True,
                    "mode": context.mode,
                    "execution_allowed": False,
                },
                headers={"Cache-Control": "no-store, private", "Pragma": "no-cache"},
            )
        except EdgeRequestRejected as exc:
            return _error_response(exc)
        except HTTPException as exc:
            return _auth_error_response(exc)
        finally:
            if admitted:
                abuse_guard.leave()

    @app.get(PRIVACY_PATH, include_in_schema=False)
    async def privacy() -> PlainTextResponse:
        return PlainTextResponse(
            _PRIVACY_NOTICE,
            headers={"Cache-Control": "public, max-age=3600"},
        )

    return app


app = create_sage_edge_app()


__all__: Iterable[str] = (
    "DEFAULT_EDGE_HOST",
    "DEFAULT_EDGE_PORT",
    "LIVENESS_PATH",
    "PRIVACY_PATH",
    "READINESS_PATH",
    "UPSTREAM_ORIGIN",
    "app",
    "classify_edge_target",
    "configured_edge_host",
    "configured_edge_port",
    "create_sage_edge_app",
    "edge_body_limit",
    "edge_max_in_flight",
    "edge_rate_limit_requests",
    "edge_rate_limit_window_seconds",
    "validate_edge_bind_host",
    "validate_edge_port",
)
