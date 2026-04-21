"""
NEXUS OS Bridge — HMAC authentication, JSON-RPC, API key management

The Bridge pillar handles all authentication, message signing, and
API key lifecycle. It is the entry point for all external requests.
"""

import hmac
import hashlib
import uuid
import json
import logging
from typing import Any

logger = logging.getLogger("nexus_os.bridge")

# ── Message Signing ──────────────────────────────────────────────

def sign(secret: str, trace: str, payload: str) -> str:
    """Create HMAC-SHA256 signature for a trace+payload pair."""
    msg = f"{trace}:{payload}".encode()
    return hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()


def verify(secret: str, trace: str, payload: str, sig: str) -> bool:
    """Verify an HMAC-SHA256 signature matches."""
    expected = sign(secret, trace, payload)
    return hmac.compare_digest(expected, sig)


class BridgeServer:
    """JSON-RPC server with HMAC message authentication."""

    def __init__(self, secret: str | None = None):
        self.secret = secret or uuid.uuid4().hex
        self._handlers: dict[str, Any] = {}

    def register(self, method: str, handler):
        """Register a JSON-RPC method handler."""
        self._handlers[method] = handler
        logger.info("Bridge: registered handler for method '%s'", method)

    def handle(self, request: dict) -> dict:
        """Route a JSON-RPC request to the appropriate handler."""
        method = request.get("method", "")
        params = request.get("params", {})
        req_id = request.get("id")

        handler = self._handlers.get(method)
        if not handler:
            logger.warning("Bridge: no handler for method '%s'", method)
            return {"jsonrpc": "2.0", "error": {"code": -32601, "message": f"Method not found: {method}"}, "id": req_id}

        try:
            result = handler(params)
            logger.debug("Bridge: method '%s' returned successfully", method)
            return {"jsonrpc": "2.0", "result": result, "id": req_id}
        except Exception as exc:
            logger.error("Bridge: method '%s' raised %s: %s", method, type(exc).__name__, exc)
            return {"jsonrpc": "2.0", "error": {"code": -32603, "message": str(exc)}, "id": req_id}
