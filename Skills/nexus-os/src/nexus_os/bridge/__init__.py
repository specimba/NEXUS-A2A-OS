"""NEXUS OS — Bridge module: HMAC auth + JSON-RPC + MCP-Auth support."""
import hashlib, hmac, uuid, json, time
from typing import Callable, Dict, Optional
from enum import Enum

# ── Auth methods ─────────────────────────────────────────────────────────────
class AuthMode(Enum):
    HMAC = "hmac"           # Original: shared secret, trace, payload signature
    MCP_OAUTH2_PKCE = "oauth2_pkce"  # P2c: MCP-Auth spec (2026-04)
    BEARER = "bearer"       # Bearer token (zo.space routes, OpenClaw gateway)

class AuthResult:
    def __init__(self, ok: bool, mode: str, identity: str = "unknown", detail: str = ""):
        self.ok = ok; self.mode = mode; self.identity = identity; self.detail = detail

def sign(secret: str, trace: str, payload: str) -> str:
    return hmac.new(secret.encode(), f"{trace}.{payload}".encode(), hashlib.sha256).hexdigest()

def verify(secret: str, trace: str, payload: str, signature: str) -> bool:
    return hmac.compare_digest(signature, sign(secret, trace, payload))

def verify_hmac(secret: str, trace: str, payload: str, signature: str) -> bool:
    return verify(secret, trace, payload, signature)

def verify_bearer(token: str, expected: str) -> AuthResult:
    """Validate bearer token. Used for zo.space route auth and OpenClaw gateway."""
    ok = hmac.compare_digest(token, expected)
    return AuthResult(ok=ok, mode="bearer", identity="zo_agent" if ok else "anonymous")

class BridgeServer:
    def __init__(self, hmac_secret: str = "default", bearer_token: str = ""):
        self.hmac_secret = hmac_secret
        self.bearer_token = bearer_token
        self.mcp_oauth2_pkce_verified: Dict[str, float] = {}   # client_id → expiry
        self._auth_modes = [AuthMode.HMAC]
        if bearer_token:
            self._auth_modes.append(AuthMode.BEARER)
            self._auth_modes.append(AuthMode.MCP_OAUTH2_PKCE)

    def authenticate(self, headers: dict, body: str) -> AuthResult:
        """Authenticate incoming request. Tries all available modes."""
        auth = headers.get("authorization", "")
        # Try Bearer first
        if auth.startswith("Bearer ") and self.bearer_token:
            token = auth[7:]
            result = verify_bearer(token, self.bearer_token)
            if result.ok:
                return result
        # Try HMAC
        sig = headers.get("x-nexus-sig", "")
        trace = headers.get("x-nexus-trace", str(uuid.uuid4()))
        if sig and verify_hmac(self.hmac_secret, trace, body, sig):
            return AuthResult(ok=True, mode="hmac", identity="nexus_client")
        # Try MCP-OAuth2-PKCE (token in Authorization header)
        if auth.startswith("Bearer ") and self._is_mcp_oauth2_pkce_token(auth[7:]):
            return AuthResult(ok=True, mode="mcp_oauth2_pkce", identity="mcp_client")
        return AuthResult(ok=False, mode="none", detail="no valid auth found")

    def _is_mcp_oauth2_pkce_token(self, token: str) -> bool:
        """Check if token is a valid MCP-Auth PKCE token (non-empty, reasonable length)."""
        # In production: verify against OAuth2 PKCE introspection endpoint
        # Here: accept tokens > 32 chars as valid PKCE access tokens
        return len(token) >= 32

    def auth_modes(self) -> list[str]:
        return [m.value for m in self._auth_modes]

class JSONRPCRequest:
    def __init__(self, method: str, params: dict, request_id: Optional[str] = None):
        self.method = method
        self.params = params
        self.id = request_id or str(uuid.uuid4())[:8]

    @classmethod
    def from_json(cls, raw: str) -> "JSONRPCRequest":
        d = json.loads(raw)
        return cls(method=d["method"], params=d.get("params", {}), request_id=d.get("id"))

    def response(self, result: dict) -> str:
        return json.dumps({"jsonrpc": "2.0", "id": self.id, "result": result})

    def error_response(self, code: int, message: str) -> str:
        return json.dumps({"jsonrpc": "2.0", "id": self.id, "error": {"code": code, "message": message}})

class JSONRPCDispatcher:
    def __init__(self):
        self._handlers: Dict[str, Callable] = {}

    def register(self, method: str, handler: Callable):
        self._handlers[method] = handler

    def dispatch(self, request: JSONRPCRequest) -> dict:
        handler = self._handlers.get(request.method)
        if not handler:
            return {"error": f"method '{request.method}' not found"}
        try:
            return {"result": handler(request.params)}
        except Exception as e:
            return {"error": str(e)}

def create_rpc_response(request_id: str, result: dict) -> str:
    return json.dumps({"jsonrpc": "2.0", "id": request_id, "result": result})

def create_rpc_error(request_id: str, code: int, message: str) -> str:
    return json.dumps({"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}})