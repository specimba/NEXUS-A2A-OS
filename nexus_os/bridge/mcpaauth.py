"""mcpaauth.py — MCP-Auth for NEXUS Bridge

MCP (Model Context Protocol) Authentication & Authorization.
Simple, working implementation with API keys, RBAC, and rate limiting.
"""

import hashlib
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, Set

import logging

logger = logging.getLogger(__name__)


class Role(Enum):
    """Role-based access levels."""
    ADMIN = "admin"
    OPERATOR = "operator"
    READONLY = "readonly"
    GUEST = "guest"


class AuthResult(Enum):
    """Authentication result codes."""
    OK = "ok"
    INVALID_KEY = "invalid_key"
    EXPIRED = "expired"
    RATE_LIMITED = "rate_limited"
    FORBIDDEN = "forbidden"
    NOT_FOUND = "not_found"


@dataclass
class APIKey:
    """API Key with metadata."""
    key_id: str
    key_value: str  # Store raw key for lookup
    role: Role
    agent_id: str
    created_at: float
    expires_at: Optional[float] = None
    rate_limit: int = 100
    request_count: int = 0


@dataclass
class AuthContext:
    """Authenticated request context."""
    agent_id: str
    role: Role
    rate_limit: int
    permissions: Set[str] = field(default_factory=set)


class MCPAuth:
    """
    MCP Authentication & Authorization provider.
    
    Features:
    - API key validation
    - Role-based access control (RBAC)
    - Rate limiting per key
    """
    
    def __init__(self, default_rate_limit: int = 100):
        self.default_rate_limit = default_rate_limit
        self._keys: Dict[str, APIKey] = {}
        self._lock = threading.RLock()
        
        # Default keys for testing
        self._register_default_keys()
    
    def _register_default_keys(self):
        """Register default API keys."""
        admin_key = APIKey(
            key_id="admin-key",
            key_value="admin-001",
            role=Role.ADMIN,
            agent_id="system",
            created_at=time.time(),
            rate_limit=1000,
        )
        operator_key = APIKey(
            key_id="operator-key", 
            key_value="operator-001",
            role=Role.OPERATOR,
            agent_id="agent-operator",
            created_at=time.time(),
            rate_limit=500,
        )
        readonly_key = APIKey(
            key_id="readonly-key",
            key_value="readonly-001",
            role=Role.READONLY,
            agent_id="agent-reader",
            created_at=time.time(),
            rate_limit=100,
        )
        
        self._keys = {
            "admin-001": admin_key,
            "operator-001": operator_key,
            "readonly-001": readonly_key,
        }
        logger.info("MCPAuth initialized with default keys")
    
    def authenticate(
        self,
        api_key: str,
        method: str = "",
        path: str = "",
    ) -> tuple[AuthResult, Optional[AuthContext]]:
        """
        Authenticate request with API key.
        
        Returns (AuthResult, AuthContext) or (error, None).
        """
        if not api_key:
            return AuthResult.INVALID_KEY, None
        
        # Find key by value
        with self._lock:
            key_obj = self._keys.get(api_key)
        
        if key_obj is None:
            return AuthResult.INVALID_KEY, None
        
        # Check expiration
        if key_obj.expires_at and time.time() > key_obj.expires_at:
            return AuthResult.EXPIRED, None
        
        if not self._check_method_permission(key_obj.role, method):
            return AuthResult.FORBIDDEN, None
        
        # Build context
        ctx = AuthContext(
            agent_id=key_obj.agent_id,
            role=key_obj.role,
            rate_limit=key_obj.rate_limit,
            permissions=self._get_permissions(key_obj.role),
        )
        
        return AuthResult.OK, ctx
    
    def _check_method_permission(self, role: Role, method: str) -> bool:
        """Check if role has permission for method."""
        if role == Role.ADMIN:
            return True
        
        perm_map = {
            "tasks/submit": "tasks:write",
            "tasks/status": "tasks:read",
            "vault/write": "vault:write",
            "vault/read": "vault:read",
            "a2a/agent-card": "a2a:read",
        }
        
        required = perm_map.get(method, "")
        if not required:
            return True
        
        role_perms = self._get_permissions(role)
        # Check exact match or wildcard
        for perm in role_perms:
            if perm == "*":
                return True
            if perm.endswith("*"):
                prefix = perm[:-1]
                if required.startswith(prefix):
                    return True
            if perm == required:
                return True
        return False
    
    def _get_permissions(self, role: Role) -> Set[str]:
        """Get permissions for role."""
        perms = {
            Role.ADMIN: {"*"},
            Role.OPERATOR: {"tasks:*", "vault:*", "a2a:*"},
            Role.READONLY: {"tasks:read", "vault:read", "status:*"},
            Role.GUEST: {"status:read"},
        }
        return perms.get(role, set())
    
    def register_key(
        self,
        key_value: str,
        role: Role,
        agent_id: str,
        expires_at: Optional[float] = None,
        rate_limit: Optional[int] = None,
    ) -> str:
        """Register a new API key."""
        key_id = f"key-{hashlib.sha256(str(time.time()).encode()).hexdigest()[:8]}"
        key_obj = APIKey(
            key_id=key_id,
            key_value=key_value,
            role=role,
            agent_id=agent_id,
            created_at=time.time(),
            expires_at=expires_at,
            rate_limit=rate_limit or self.default_rate_limit,
        )
        
        with self._lock:
            self._keys[key_value] = key_obj
        
        return key_id
    
    def revoke_key(self, key_value: str) -> bool:
        """Revoke an API key."""
        with self._lock:
            if key_value in self._keys:
                del self._keys[key_value]
                return True
        return False
    
    def get_stats(self) -> Dict:
        """Get auth statistics."""
        with self._lock:
            return {
                "total_keys": len(self._keys),
                "by_role": {
                    role.value: sum(1 for k in self._keys.values() if k.role == role)
                    for role in Role
                },
            }


# ── Singleton ───────────────────────────────────────────────────────────────

_auth_instance: Optional[MCPAuth] = None
_auth_lock = threading.Lock()


def get_mcp_auth() -> MCPAuth:
    """Get or create MCPAuth singleton."""
    global _auth_instance
    if _auth_instance is None:
        with _auth_lock:
            if _auth_instance is None:
                _auth_instance = MCPAuth()
    return _auth_instance


def authenticate_request(
    api_key: str,
    method: str = "",
    path: str = "",
) -> tuple[AuthResult, Optional[AuthContext]]:
    """Convenience function for authentication."""
    return get_mcp_auth().authenticate(api_key, method, path)