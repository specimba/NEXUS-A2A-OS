"""Fail-closed authentication and payload controls for NEXUS SAGE."""

from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
import re
import hashlib
import os
from pathlib import Path
import secrets
from typing import Any, Awaitable, Callable
import unicodedata
from urllib.parse import unquote

from fastapi import Header, HTTPException, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


ASGIReceive = Callable[[], Awaitable[dict[str, Any]]]

_PERSISTED_CONTENT_PATTERNS = (
    re.compile(r"-----BEGIN(?: [A-Z0-9]+)? PRIVATE KEY-----", re.IGNORECASE),
    re.compile(
        r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"
    ),
    re.compile(r"\bbearer\s+[A-Za-z0-9._~+/=-]{16,}", re.IGNORECASE),
    re.compile(
        r"\b(?:api[-_ ]?key|access[-_ ]?token|refresh[-_ ]?token|"
        r"client[-_ ]?secret|password|passwd|authorization)\b"
        r"\s*(?:=|:)\s*(?:bearer\s+)?[^\s,;\"\'}]{6,}",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|"
        r"github_pat_[A-Za-z0-9_]{20,}|glpat-[A-Za-z0-9_-]{20,}|"
        r"hf_[A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9-]{20,}|"
        r"AIza[A-Za-z0-9_-]{20,})\b"
    ),
    re.compile(r"(?<![A-Za-z0-9])(?:[A-Za-z]:[\\/]|\\\\[^\\/\s]+[\\/][^\\/\s]+)"),
    re.compile(
        r"(?<![A-Za-z0-9])/(?:home|users|root|etc|var|tmp|data|opt|srv)(?:/|$)",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:https?|ftp)://[^\s]+", re.IGNORECASE),
    re.compile(r"```|~~~"),
    re.compile(r"(?m)^\s*#!\s*/(?:usr/bin/env\s+)?(?:ba|z|k)?sh\b", re.IGNORECASE),
    re.compile(
        r"(?im)(?:^|[\r\n;&|])\s*(?:sudo\s+)?(?:powershell(?:\.exe)?|"
        r"pwsh(?:\.exe)?|cmd(?:\.exe)?|bash|zsh|sh|python(?:3(?:\.\d+)?)?|node)"
        r"\s+(?:-|/)[A-Za-z]"
    ),
    re.compile(r"\b(?:rm\s+-rf|Invoke-Expression|Start-Process)\b", re.IGNORECASE),
    re.compile(
        r"\b(?:subprocess\.(?:run|Popen|call)|os\.(?:system|popen)|eval|exec)"
        r"\s*\(\s*(?:\[|[\"\'])",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?m)^\s*(?:from\s+[A-Za-z_][\w.]*\s+import\s+|"
        r"import\s+[A-Za-z_][\w.]*|def\s+[A-Za-z_]\w*\s*\(|"
        r"class\s+[A-Za-z_]\w*\s*[:(])"
    ),
)

_MAX_DECODED_PERSISTENCE_VIEW_CHARS = 20_000
_BASE64_TEXT_CANDIDATE = re.compile(
    r"(?<![A-Za-z0-9+/_-])([A-Za-z0-9+/_-]{24,}={0,2})"
    r"(?![A-Za-z0-9+/_=-])"
)


def _normalized_persistence_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    return "".join(
        character
        for character in normalized
        if unicodedata.category(character) != "Cf"
    )


def _persistence_text_views(value: str) -> tuple[str, ...]:
    """Build bounded semantic views used only for high-confidence DLP scans."""

    views: list[str] = []
    seen: set[str] = set()

    def add_view(candidate: str, *, decoded: bool = False) -> None:
        if decoded and len(candidate) > _MAX_DECODED_PERSISTENCE_VIEW_CHARS:
            return
        if candidate not in seen:
            seen.add(candidate)
            views.append(candidate)

    def add_normalized_percent_views(candidate: str, *, decoded: bool = False) -> None:
        normalized = _normalized_persistence_text(candidate)
        add_view(normalized, decoded=decoded)
        current = normalized
        for _ in range(2):
            if not re.search(r"%[0-9A-Fa-f]{2}", current):
                break
            expanded = _normalized_persistence_text(unquote(current))
            if expanded == current:
                break
            add_view(expanded, decoded=decoded)
            current = expanded

    add_view(value)
    add_normalized_percent_views(value)

    encoded_views = tuple(views)
    for view in encoded_views:
        for match in _BASE64_TEXT_CANDIDATE.finditer(view):
            candidate = match.group(1)
            if len(candidate) > _MAX_DECODED_PERSISTENCE_VIEW_CHARS:
                continue
            if len(candidate) % 4 == 1:
                continue
            padded = candidate + ("=" * (-len(candidate) % 4))
            try:
                decoded_bytes = base64.b64decode(
                    padded.encode("ascii"),
                    altchars=b"-_",
                    validate=True,
                )
                if len(decoded_bytes) > _MAX_DECODED_PERSISTENCE_VIEW_CHARS:
                    continue
                decoded_text = decoded_bytes.decode("utf-8")
            except (UnicodeDecodeError, ValueError, binascii.Error):
                continue
            if not decoded_text or not all(
                character.isprintable() or character in "\r\n\t"
                for character in decoded_text
            ):
                continue
            add_normalized_percent_views(decoded_text, decoded=True)

    return tuple(views)


def contains_disallowed_persisted_content(value: Any) -> bool:
    """Return True when a proposal value contains high-confidence private/code data."""

    if isinstance(value, str):
        return any(
            pattern.search(view)
            for view in _persistence_text_views(value)
            for pattern in _PERSISTED_CONTENT_PATTERNS
        )
    if isinstance(value, dict):
        return any(
            contains_disallowed_persisted_content(nested)
            for nested in value.values()
        )
    if isinstance(value, (list, tuple)):
        return any(contains_disallowed_persisted_content(nested) for nested in value)
    return False

ASGISend = Callable[[dict[str, Any]], Awaitable[None]]

DEFAULT_SAGE_KEY_FILE = Path.home() / ".nexus_pi" / "state" / ".sage_api_token"



@dataclass(frozen=True)
class SageSecurityContext:
    principal: str
    mode: str
    key_id: str


def sage_gateway_mode() -> str:
    mode = (os.environ.get("NEXUS_SAGE_GATEWAY_MODE") or "observe_only").strip().lower()
    return mode if mode in {"disabled", "observe_only", "proposal_write"} else "disabled"


def _configured_key() -> str:
    key = (os.environ.get("NEXUS_SAGE_API_KEY") or "").strip()
    if not key:
        configured_path = (os.environ.get("NEXUS_SAGE_API_KEY_FILE") or "").strip()
        key_path = Path(configured_path).expanduser() if configured_path else DEFAULT_SAGE_KEY_FILE
        try:
            if key_path.is_file():
                key = key_path.read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise HTTPException(
                status_code=503,
                detail="SAGE credential store is unavailable",
            ) from exc
    if not key.isascii() or any(char.isspace() for char in key):
        raise HTTPException(status_code=503, detail="SAGE credential has an invalid format")
    if not key:
        raise HTTPException(status_code=503, detail="SAGE credential is not provisioned")
    if len(key) < 32:
        raise HTTPException(status_code=503, detail="SAGE credential does not meet minimum strength")
    return key


def max_body_bytes() -> int:
    try:
        value = int(os.environ.get("NEXUS_SAGE_MAX_BODY_BYTES", "90000"))
    except ValueError:
        value = 90_000
    return max(1_024, min(value, 99_000))


def authenticate_sage_bearer(authorization: str | None) -> SageSecurityContext:
    """Validate the SAGE bearer without consuming or forwarding a request body."""

    mode = sage_gateway_mode()
    if mode == "disabled":
        raise HTTPException(status_code=503, detail="SAGE gateway is disabled")

    key = _configured_key()
    scheme, separator, supplied = (authorization or "").partition(" ")
    if not separator or scheme.lower() != "bearer" or not supplied.strip():
        raise HTTPException(status_code=401, detail="valid SAGE bearer token required")
    normalized_supplied = supplied.strip()
    if not normalized_supplied.isascii():
        raise HTTPException(status_code=401, detail="valid SAGE bearer token required")
    if not secrets.compare_digest(
        normalized_supplied.encode("ascii"),
        key.encode("ascii"),
    ):
        raise HTTPException(status_code=401, detail="valid SAGE bearer token required")

    key_id = hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]
    return SageSecurityContext(
        principal=f"nexus-sage:{key_id}",
        mode=mode,
        key_id=key_id,
    )


async def require_sage_auth(
    request: Request,
    authorization: str | None = Header(default=None),
) -> SageSecurityContext:
    context = authenticate_sage_bearer(authorization)

    body = await request.body()
    if len(body) > max_body_bytes():
        raise HTTPException(status_code=413, detail="SAGE request body is too large")

    return context


def require_proposal_write(context: SageSecurityContext) -> None:
    if context.mode != "proposal_write":
        raise HTTPException(
            status_code=403,
            detail="SAGE proposal writes are disabled until promotion gates pass",
        )


async def sage_request_validation_handler(
    request: Request,
    exc: RequestValidationError,
):
    """Redact caller input from SAGE 422 responses; delegate all other routes."""

    if not request.url.path.startswith("/api/sage/v1"):
        return await request_validation_exception_handler(request, exc)

    detail: list[dict[str, Any]] = []
    for error in exc.errors():
        safe_location = []
        for part in error.get("loc", ()):
            if isinstance(part, (str, int)) and not isinstance(part, bool):
                safe_location.append(part)
            else:
                safe_location.append(str(part))
        detail.append(
            {
                "loc": safe_location,
                "type": str(error.get("type") or "validation_error"),
            }
        )
    return JSONResponse(
        status_code=422,
        content={"detail": detail, "code": "sage_validation_error"},
        headers={"Cache-Control": "no-store"},
    )


class SageBodyLimitMiddleware:
    """Buffer and count SAGE body bytes before FastAPI model parsing."""

    def __init__(self, app, prefix: str = "/api/sage/v1") -> None:
        self.app = app
        self.prefix = prefix

    async def __call__(self, scope, receive: ASGIReceive, send: ASGISend) -> None:
        if scope.get("type") != "http" or not str(scope.get("path", "")).startswith(self.prefix):
            await self.app(scope, receive, send)
            return

        messages: list[dict[str, Any]] = []
        seen = 0
        limit = max_body_bytes()
        while True:
            message = await receive()
            messages.append(message)
            if message.get("type") == "http.request":
                seen += len(message.get("body", b""))
            if seen > limit:
                await self._reject(send)
                return
            if message.get("type") != "http.request" or not message.get("more_body", False):
                break

        index = 0

        async def replay_receive() -> dict[str, Any]:
            nonlocal index
            if index < len(messages):
                message = messages[index]
                index += 1
                return message
            return {"type": "http.request", "body": b"", "more_body": False}

        await self.app(scope, replay_receive, send)

    @staticmethod
    async def _reject(send: ASGISend) -> None:
            body = (
                b'{"detail":"SAGE request body is too large",'
                b'"code":"sage_payload_too_large"}'
            )
            await send(
                {
                    "type": "http.response.start",
                    "status": 413,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"content-length", str(len(body)).encode("ascii")),
                    ],
                }
            )
            await send({"type": "http.response.body", "body": body})
