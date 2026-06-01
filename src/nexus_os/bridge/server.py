"""
bridge/server.py â€” Nexus OS A2A Bridge Server

Production-hardened FastAPI endpoint for agent-to-agent communication.
Implements JSON-RPC 2.0 over HTTP with:

  1. HMAC-SHA256 authentication via SecretStore
  2. KAIJU 4-variable authorization via NexusGovernor
  3. Task execution via TaskExecutor
  4. Structured JSON-RPC 2.0 responses
  5. Comprehensive error handling

Endpoints:
  POST /tasks/submit  â€” Submit task for execution
  POST /tasks/status  â€” Query task status
  POST /vault/read    â€” Query Vault memory
  POST /vault/write   â€” Write to Vault memory
  POST /              â€” JSON-RPC 2.0 router (dispatches to above)
"""

import json
import time
import uuid
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# â”€â”€ Exceptions â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class BridgeError(Exception):
    """Base exception for Bridge errors."""
    def __init__(self, code: int, message: str, http_status: int = 500):
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


class AuthError(BridgeError):
    def __init__(self, message: str):
        super().__init__(401, message, http_status=401)


class ForbiddenError(BridgeError):
    def __init__(self, message: str):
        super().__init__(403, message, http_status=403)


class HeldError(BridgeError):
    def __init__(self, message: str, trace_id: str):
        super().__init__(202, message, http_status=202)
        self.hold_ticket = trace_id


class ParseError(BridgeError):
    def __init__(self, message: str):
        super().__init__(32700, message, http_status=400)


def scan_payload_for_anomalies(payload: Any) -> bool:
    """Recursively walks a JSON-RPC payload and checks string values for anomalies."""
    if isinstance(payload, str):
        try:
            from scripts.stresslab_v7.remediate_vulns import run_format_validator
            return run_format_validator(payload)
        except Exception:
            return False
    elif isinstance(payload, dict):
        return any(scan_payload_for_anomalies(v) for v in payload.values())
    elif isinstance(payload, list):
        return any(scan_payload_for_anomalies(item) for item in payload)
    return False


# â”€â”€ Request Models â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@dataclass
class BridgeRequest:
    """Parsed Bridge request with validated headers and body."""
    agent_id: str
    project_id: str
    trace_id: str
    signature: str
    lineage_id: Optional[str]
    payload: Dict[str, Any]
    raw_payload: str
    method: str  # "tasks/submit", "tasks/status", "vault/read", "vault/write"
    kaiju: Dict[str, str] = field(default_factory=dict)


# â”€â”€ JSON-RPC Response Builder â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def jsonrpc_result(result: Any, trace_id: Optional[str] = None, input_tokens: int = 0, output_tokens: int = 0) -> Dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "result": result,
        "trace_id": trace_id,
        "x-nexus-input-tokens": input_tokens,
        "x-nexus-output-tokens": output_tokens,
    }

def jsonrpc_error(code: int, message: str, trace_id: Optional[str] = None, data: Any = None) -> Dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "error": {
            "code": code,
            "message": message,
            "data": data,
        },
        "trace_id": trace_id,
    }


# â”€â”€ Bridge Server â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class BridgeServer:
    """
    Nexus OS A2A Bridge Server.

    Can be used standalone (via handle_request()) or mounted on FastAPI/ASGI.
    All public methods take raw HTTP inputs and return (status_code, response_dict).
    TokenGuard integration: tracks token usage and adds X-Nexus-Input-Tokens,
    X-Nexus-Output-Tokens headers to FastAPI responses.
    """

    def __init__(
        self,
        secret_store=None,
        governor=None,
        executor=None,
        token_guard=None,
    ):
        from nexus_os.bridge.secrets import SecretStore
        from nexus_os.engine.executor import MockExecutor
        from nexus_os.monitoring.token_guard import TokenGuard

        self.secret_store = secret_store or SecretStore()
        self.governor = governor
        self.executor = executor or MockExecutor()
        self.token_guard = token_guard or TokenGuard()
        self._task_results: Dict[str, Any] = {}

    # â”€â”€ Token Guard Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _parse_input_tokens(self, headers, payload) -> int:
        """Extract input token count. Header > payload > fallback(0)."""
        hval = headers.get("x-nexus-input-tokens") or headers.get("x-nexus-tokens")
        if hval:
            try:
                return int(hval)
            except (TypeError, ValueError):
                pass
        if isinstance(payload, dict) and "tokens" in payload:
            try:
                return int(payload["tokens"])
            except (TypeError, ValueError):
                pass
        return 0

    def _track_tokens(self, agent_id, project_id, operation, input_tokens, output_tokens):
        """Track tokens via TokenGuard. Non-blocking â€” never breaks requests."""
        if input_tokens <= 0 and output_tokens <= 0:
            return None
        try:
            if input_tokens > 0:
                self.token_guard.track(agent_id, input_tokens,
                                   operation=operation,
                                   context={"project_id": project_id})
            if output_tokens > 0:
                self.token_guard.track(agent_id, output_tokens,
                                       operation=f"{operation}_output",
                                       context={"project_id": project_id})
            return {
                "input": input_tokens,
                "output": output_tokens,
                "total": input_tokens + output_tokens,
                "budget_remaining": self.token_guard.remaining(agent_id),
            }
        except Exception:
            # Non-blocking â€” log but never fail a request
            import logging
            logging.getLogger(__name__).warning("TokenGuard tracking failed")
            return {"input": input_tokens, "output": output_tokens, "total": input_tokens + output_tokens}


    # â”€â”€ Authentication â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _authenticate(self, request: BridgeRequest):
        """Validate HMAC-SHA256 signature. Raises AuthError on failure."""
        from nexus_os.bridge.secrets import verify_signature, SecretNotFoundError

        if not request.signature:
            raise AuthError("Missing X-Nexus-Signature header")

        if not request.trace_id:
            raise AuthError("Missing X-Nexus-Trace-ID header")

        try:
            secret = self.secret_store.get_secret(request.agent_id)
        except SecretNotFoundError:
            raise AuthError(f"Unknown agent: {request.agent_id}")

        if not verify_signature(secret, request.trace_id, request.raw_payload, request.signature):
            raise AuthError("Invalid signature")

    # â”€â”€ Authorization â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _authorize(self, request: BridgeRequest):
        """Run KAIJU 4-variable authorization. Raises ForbiddenError or HeldError."""
        if self.governor is None:
            return  # No governor â€” skip authz (dev mode)

        from nexus_os.governor.kaiju_auth import Decision

        kaiju = request.kaiju
        result = self.governor.check_access(
            agent_id=request.agent_id,
            project_id=request.project_id,
            action=self._kaiju_action(request.method),
            scope=kaiju.get("scope", "project"),
            intent=kaiju.get("intent", ""),
            impact=kaiju.get("impact", "low"),
            clearance=kaiju.get("clearance", "contributor"),
            trace_id=request.trace_id,
            context={
                "signature_verified": True,
                "has_secret": True,
                "is_registered": True,
            },
        )

        if result.decision == Decision.DENY:
            raise ForbiddenError(result.reason)
        elif result.decision == Decision.HOLD:
            raise HeldError(result.reason, request.trace_id)

    def _kaiju_action(self, method: str) -> str:
        """Map Bridge method to KAIJU action type."""
        action_map = {
            "tasks/submit": "execute",
            "tasks/status": "read",
            "vault/read": "read",
            "vault/write": "write",
        }
        return action_map.get(method, "read")

    # â”€â”€ Request Parsing â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def parse_request(
        self,
        body: bytes,
        headers: Dict[str, str],
    ) -> BridgeRequest:
        """Parse and validate raw HTTP request into BridgeRequest."""
        # Parse JSON body
        try:
            raw = body.decode("utf-8")
            payload = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            raise ParseError(f"Malformed JSON body: {e}")

        if not isinstance(payload, dict):
            raise ParseError("Request body must be a JSON object")

        # Extract required headers
        agent_id = headers.get("x-nexus-agent-id", "")
        project_id = headers.get("x-nexus-project-id", "")
        trace_id = headers.get("x-nexus-trace-id", "")
        signature = headers.get("x-nexus-signature", "")
        lineage_id = headers.get("x-nexus-lineage-id")

        # Determine method from the path
        # (The caller passes method via the path; for the single "/" endpoint,
        #  we use the "method" field in the JSON body if present, default to tasks/submit)
        method = payload.pop("method", "tasks/submit") if isinstance(payload, dict) else "tasks/submit"

        kaiju = payload.pop("kaiju", {}) if isinstance(payload, dict) else {}

        # Smart Anomaly Pre-Filter Scan
        if scan_payload_for_anomalies(payload):
            logger.warning(f"Security Alert: Smart Anomaly Filter blocked request from agent {agent_id} targeting {method}")
            raise ForbiddenError("Security anomaly detected in request payload.")

        return BridgeRequest(
            agent_id=agent_id,
            project_id=project_id,
            trace_id=trace_id,
            signature=signature,
            lineage_id=lineage_id,
            payload=payload,
            raw_payload=raw,
            method=method,
            kaiju=kaiju if isinstance(kaiju, dict) else {},
        )

    # â”€â”€ Handler Dispatch â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    
    def get_agent_card(self, agent_id: str) -> Dict[str, Any]:
        """A2A v1.1: Expose agent capabilities for inter-agent negotiation."""
        # In production: pull from TrustScorer/AgentCard registry
        return {
            "agent_id": agent_id,
            "protocol": "A2A-v1.1",
            "capabilities": ["code_generation", "governance_audit", "swarm_orchestration"],
            "trust_band": "COMMUNITY_VERIFIED",
            "status": "active"
        }
        
    def get_agent_card(self, agent_id: str) -> Dict[str, Any]:
        """A2A v1.1 Endpoint: Expose capabilities and trust score to external swarms."""
        # In production, this queries the Vault/Governor for dynamic, verified capabilities.
        return {
            "agent_id": agent_id,
            "protocol": "A2A-v1.1",
            "capabilities": [
                "code_generation", 
                "governance_audit", 
                "swarm_orchestration"
            ],
            "negotiation_policies": {
                "fallback_behavior": "adaptive",
                "timeout_ms": 30000
            },
            "status": "active"
        }
    
    def handle_request(
        self,
        method: str,
        body: bytes,
        headers: Dict[str, str],
    ) -> tuple:
        """
        Handle a single Bridge request.

        Args:
            method: HTTP method (must be POST)
            body: Raw request body bytes
            headers: Dict of HTTP headers (case-insensitive keys)

        Returns:
            (status_code: int, response_dict: dict)
        """
        start = time.perf_counter()

        try:
            # Only POST allowed
            if method.upper() != "POST":
                return 405, jsonrpc_error(
                    -32600, "Method not allowed. Use POST.",
                    data="Only POST is supported"
                )

            # Parse request â€” method read from JSON payload['method']
            req = self.parse_request(body, headers)

            # Budget pre-check (P0: TokenGuard gate)
            if not self.token_guard.check(req.agent_id, 1000):
                return 429, jsonrpc_error(
                    429, "Token budget exceeded",
                    trace_id=req.trace_id,
                    data={"remaining": self.token_guard.remaining(req.agent_id)},
                )

            # Track tokens (before dispatch if input_tokens known)
            input_tokens = self._parse_input_tokens(headers, req.payload)

            # Authenticate
            self._authenticate(req)

            # Authorize
            self._authorize(req)

            # Dispatch
            result = self._dispatch(req)

            duration = (time.perf_counter() - start) * 1000
            if isinstance(result, dict) and "duration_ms" not in result:
                result["duration_ms"] = round(duration, 2)


            # Track token usage
            response_json = json.dumps(result) if isinstance(result, dict) else "{}"
            output_tokens = len(response_json) * 4 // 10  # rough: chars to ~token estimate
            token_info = self._track_tokens(req.agent_id, req.project_id,
                                            req.method, input_tokens, output_tokens)
            if token_info:
                result["token_usage"] = token_info

            return 200, jsonrpc_result(result, req.trace_id)

        except HeldError as e:
            return e.http_status, jsonrpc_result(
                {
                    "task_id": None,
                    "status": "held",
                    "hold_reason": e.message,
                    "hold_ticket": e.hold_ticket,
                },
                e.hold_ticket,
            )
        except AuthError as e:
            return e.http_status, jsonrpc_error(e.code, e.message)
        except ForbiddenError as e:
            return e.http_status, jsonrpc_error(e.code, e.message)
        except ParseError as e:
            return e.http_status, jsonrpc_error(e.code, e.message)
        except Exception as e:
            logger.exception("Bridge internal error")
            return 500, jsonrpc_error(
                -32603, f"Internal error: {e}"
            )

    def handle_submit(self, body: bytes, headers: Dict[str, str]) -> tuple:
        """Handle POST /tasks/submit."""
        start = time.perf_counter()
        try:
            req = self.parse_request(body, headers)
            req.method = "tasks/submit"

            # Budget pre-check (P0: TokenGuard gate)
            if not self.token_guard.check(req.agent_id, 1000):
                return 429, jsonrpc_error(
                    429, "Token budget exceeded",
                    trace_id=req.trace_id,
                    data={"remaining": self.token_guard.remaining(req.agent_id)},
                )

            self._authenticate(req)
            self._authorize(req)

            task_id = f"task-{uuid.uuid4().hex[:12]}"
            description = req.payload.get("description", "")
            context = req.payload.get("context", {})
            context["agent_id"] = req.agent_id

            exec_result = self.executor.execute(task_id, description, context)

            self._task_results[task_id] = {
                "task_id": task_id,
                "status": "completed" if exec_result.success else "failed",
                "output": exec_result.output,
                "error": exec_result.error,
            }

            duration = (time.perf_counter() - start) * 1000
            return 200, jsonrpc_result({
                "task_id": task_id,
                "status": "completed" if exec_result.success else "failed",
                "output": exec_result.output,
                "error": exec_result.error,
                "duration_ms": round(duration, 2),
            }, req.trace_id)

        except HeldError as e:
            return e.http_status, jsonrpc_result(
                {"task_id": None, "status": "held", "hold_reason": e.message, "hold_ticket": e.hold_ticket},
                e.hold_ticket,
            )
        except AuthError as e:
            return e.http_status, jsonrpc_error(e.code, e.message)
        except ForbiddenError as e:
            return e.http_status, jsonrpc_error(e.code, e.message)
        except ParseError as e:
            return e.http_status, jsonrpc_error(e.code, e.message)
        except Exception as e:
            logger.exception("Bridge submit error")
            return 500, jsonrpc_error(-32603, f"Internal error: {e}")

    def handle_status(self, body: bytes, headers: Dict[str, str]) -> tuple:
        """Handle POST /tasks/status."""
        try:
            req = self.parse_request(body, headers)
            req.method = "tasks/status"
            self._authenticate(req)
            self._authorize(req)

            task_id = req.payload.get("task_id", "")
            result = self._task_results.get(task_id)

            if result is None:
                return 404, jsonrpc_error(-32602, f"Task not found: {task_id}")

            return 200, jsonrpc_result(result, req.trace_id)
        except (AuthError, ForbiddenError, ParseError, HeldError) as e:
            return e.http_status, jsonrpc_error(e.code, e.message, data=e.hold_ticket if isinstance(e, HeldError) else None)
        except Exception as e:
            return 500, jsonrpc_error(-32603, f"Internal error: {e}")

    def handle_vault_read(self, body: bytes, headers: Dict[str, str]) -> tuple:
        """Handle POST /vault/read."""
        try:
            req = self.parse_request(body, headers)
            req.method = "vault/read"
            self._authenticate(req)
            self._authorize(req)
            return 200, jsonrpc_result(
                {"records": [], "query": req.payload.get("query", ""), "count": 0},
                req.trace_id,
            )
        except (AuthError, ForbiddenError, ParseError, HeldError) as e:
            return e.http_status, jsonrpc_error(e.code, e.message)
        except Exception as e:
            return 500, jsonrpc_error(-32603, f"Internal error: {e}")

    def handle_vault_write(self, body: bytes, headers: Dict[str, str]) -> tuple:
        """Handle POST /vault/write."""
        try:
            req = self.parse_request(body, headers)
            req.method = "vault/write"
            self._authenticate(req)
            self._authorize(req)
            return 200, jsonrpc_result(
                {"record_id": f"rec-{uuid.uuid4().hex[:8]}", "status": "written"},
                req.trace_id,
            )
        except (AuthError, ForbiddenError, ParseError, HeldError) as e:
            return e.http_status, jsonrpc_error(e.code, e.message)
        except Exception as e:
            return 500, jsonrpc_error(-32603, f"Internal error: {e}")

    def _dispatch(self, req: BridgeRequest) -> Dict[str, Any]:
        """Dispatch parsed request to appropriate handler."""
        handlers = {
            "tasks/submit": self._exec_submit,
            "tasks/status": self._exec_status,
            "vault/read": self._exec_vault_read,
            "vault/write": self._exec_vault_write,
            "a2a/agent-card": self._exec_agent_card,  # A2A v1.1
        }
        handler = handlers.get(req.method)
        if handler is None:
            raise ParseError(f"Unknown method: {req.method}")
        return handler(req)

    def _exec_agent_card(self, req: BridgeRequest) -> Dict[str, Any]:
        """A2A v1.1: Return agent capabilities for inter-agent negotiation."""
        from nexus_os.governor.trust_scoring import AgentCard
        # Create a default card with common capabilities
        card = AgentCard(agent_id=req.agent_id or "default")
        card.capabilities = [
            "code_generation",
            "swarm_orchestration",
            "governance_audit",
            "memory_query",
            "skill_discovery",
        ]
        return card.get_agent_card()

    def _exec_submit(self, req: BridgeRequest) -> Dict[str, Any]:
        task_id = f"task-{uuid.uuid4().hex[:12]}"
        description = req.payload.get("description", "")
        context = req.payload.get("context", {})
        context["agent_id"] = req.agent_id

        exec_result = self.executor.execute(task_id, description, context)

        self._task_results[task_id] = {
            "task_id": task_id,
            "status": "completed" if exec_result.success else "failed",
            "output": exec_result.output,
            "error": exec_result.error,
        }

        return {
            "task_id": task_id,
            "status": "completed" if exec_result.success else "failed",
            "output": exec_result.output,
            "error": exec_result.error,
        }

    def _exec_status(self, req: BridgeRequest) -> Dict[str, Any]:
        task_id = req.payload.get("task_id", "")
        result = self._task_results.get(task_id)
        if result is None:
            raise ParseError(f"Task not found: {task_id}")
        return result

    def _exec_vault_read(self, req: BridgeRequest) -> Dict[str, Any]:
        return {"records": [], "query": req.payload.get("query", ""), "count": 0}

    def _exec_vault_write(self, req: BridgeRequest) -> Dict[str, Any]:
        return {"record_id": f"rec-{uuid.uuid4().hex[:8]}", "status": "written"}


# â”€â”€ FastAPI Integration â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def create_app(bridge: Optional[BridgeServer] = None) -> "FastAPI":
    """
    Create a FastAPI application wrapping the BridgeServer.

    Usage:
        from nexus_os.bridge.server import create_app
        app = create_app()
        # uvicorn.run(app, host="0.0.0.0", port=8000)
    """
    try:
        from fastapi import FastAPI, Request, Response
        from fastapi.responses import JSONResponse
    except ImportError:
        raise ImportError(
            "FastAPI is required for the Bridge server. "
            "Install it with: pip install fastapi uvicorn"
        )

    app = FastAPI(title="Nexus OS A2A Bridge", version="1.0.0")
    server = bridge or BridgeServer()

    # --- 7352 Governance & Proposal REST Endpoints (Pillar 2) ---
    from nexus_os.db.manager import DatabaseManager, DBConfig
    import sqlite3
    import uuid

    # Resolve DB manager
    db_config = DBConfig(
        db_path="db/custom.db",
        passphrase="governance-dev",
        encrypted=False,
        allow_unencrypted=True
    )
    db_manager = DatabaseManager(db_config)
    
    # Ensure tables are created if not present
    try:
        conn = db_manager.get_connection()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS GovernanceTask (
                id TEXT PRIMARY KEY,
                agentId TEXT NOT NULL,
                taskId TEXT UNIQUE NOT NULL,
                type TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                progress REAL DEFAULT 0,
                message TEXT,
                output TEXT,
                tokensUsed INTEGER DEFAULT 0,
                durationMs INTEGER DEFAULT 0,
                riskLevel TEXT DEFAULT 'low',
                createdAt DATETIME DEFAULT CURRENT_TIMESTAMP,
                updatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
                completedAt DATETIME
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS GovernanceProposal (
                id TEXT PRIMARY KEY,
                agentId TEXT NOT NULL,
                type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                riskLevel TEXT DEFAULT 'low',
                status TEXT DEFAULT 'pending',
                approver TEXT,
                notes TEXT,
                createdAt DATETIME DEFAULT CURRENT_TIMESTAMP,
                updatedAt DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    except Exception as e:
        logger.warning(f"Failed to bootstrap Governance tables: {e}")

    @app.post("/skills/propose")
    async def propose_skill(request: Request):
        try:
            body = await request.json()
        except Exception:
            return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})

        agent_id = body.get("agentId", "unknown")
        prop_type = body.get("type", "skill")
        title = body.get("title", "Untitled Proposal")
        description = body.get("description", "")
        risk_level = body.get("riskLevel", "low")

        prop_id = f"prop-{uuid.uuid4().hex[:12]}"
        
        try:
            conn = db_manager.get_connection()
            conn.execute("""
                INSERT INTO GovernanceProposal (id, agentId, type, title, description, riskLevel, status, createdAt, updatedAt)
                VALUES (?, ?, ?, ?, ?, ?, 'pending', datetime('now'), datetime('now'))
            """, (prop_id, agent_id, prop_type, title, description, risk_level))
            conn.commit()
            
            return {
                "id": prop_id,
                "agentId": agent_id,
                "type": prop_type,
                "title": title,
                "description": description,
                "riskLevel": risk_level,
                "status": "pending",
                "createdAt": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "updatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ")
            }
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": f"Database error: {e}"})

    @app.get("/skills/status/{proposal_id}")
    async def get_proposal_status(proposal_id: str):
        try:
            conn = db_manager.get_connection()
            cursor = conn.execute("""
                SELECT id, agentId, type, title, description, riskLevel, status, approver, notes, createdAt, updatedAt
                FROM GovernanceProposal WHERE id = ?
            """, (proposal_id,))
            row = conn.fetchone(cursor)
            if not row:
                return JSONResponse(status_code=404, content={"error": f"Proposal not found: {proposal_id}"})
            
            return {
                "id": row[0],
                "agentId": row[1],
                "type": row[2],
                "title": row[3],
                "description": row[4],
                "riskLevel": row[5],
                "status": row[6],
                "approver": row[7],
                "notes": row[8],
                "createdAt": row[9],
                "updatedAt": row[10]
            }
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": f"Database error: {e}"})

    @app.get("/dashboard/stats")
    async def get_dashboard_stats():
        try:
            conn = db_manager.get_connection()
            
            # Tasks stats
            cursor = conn.execute("SELECT status, COUNT(*) FROM GovernanceTask GROUP BY status")
            task_rows = conn.fetchall(cursor)
            tasks = {"active": 0, "completed": 0, "failed": 0, "held": 0, "total": 0}
            for row in task_rows:
                status = row[0]
                count = row[1]
                if status in tasks:
                    tasks[status] = count
                tasks["total"] += count
                
            # Proposals stats
            cursor = conn.execute("SELECT status, COUNT(*) FROM GovernanceProposal GROUP BY status")
            prop_rows = conn.fetchall(cursor)
            proposals = {"pending": 0, "approved": 0, "rejected": 0, "held": 0, "total": 0}
            for row in prop_rows:
                status = row[0]
                count = row[1]
                if status in proposals:
                    proposals[status] = count
                proposals["total"] += count

            # Recent active agents
            agents = []
            try:
                cursor = conn.execute("""
                    SELECT agentId, status, updatedAt 
                    FROM GovernanceTask 
                    ORDER BY updatedAt DESC 
                    LIMIT 10
                """)
                agent_rows = conn.fetchall(cursor)
                agent_map = {}
                for row in agent_rows:
                    a_id = row[0]
                    status = row[1]
                    updated_at = row[2]
                    if a_id not in agent_map:
                        agent_map[a_id] = {
                            "agentId": a_id,
                            "status": "online" if status == "active" else "offline",
                            "lastHeartbeat": updated_at
                        }
                agents = list(agent_map.values())
            except Exception as e:
                logger.warning(f"Failed to fetch agents stats: {e}")

            # Constitution info
            constitution_version = 'v3.2'
            constitution_rules = 12
            try:
                cursor = conn.execute("SELECT value FROM SystemConfig WHERE key = 'constitution_version'")
                row = conn.fetchone(cursor)
                if row:
                    constitution_version = row[0]
                cursor = conn.execute("SELECT value FROM SystemConfig WHERE key = 'constitution_rules'")
                row = conn.fetchone(cursor)
                if row:
                    constitution_rules = int(row[0])
            except Exception as e:
                logger.warning(f"Failed to fetch constitution stats: {e}")

            return {
                "tasks": tasks,
                "proposals": proposals,
                "agents": agents,
                "constitution": {
                    "version": constitution_version,
                    "rules": constitution_rules
                }
            }
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": f"Database error: {e}"})

    @app.get("/governance/proposals")
    async def get_all_proposals():
        try:
            conn = db_manager.get_connection()
            cursor = conn.execute("""
                SELECT id, agentId, type, title, description, riskLevel, status, approver, notes, createdAt, updatedAt
                FROM GovernanceProposal ORDER BY createdAt DESC
            """)
            rows = conn.fetchall(cursor)
            
            results = []
            for row in rows:
                results.append({
                    "id": row[0],
                    "agentId": row[1],
                    "type": row[2],
                    "title": row[3],
                    "description": row[4],
                    "riskLevel": row[5],
                    "status": row[6],
                    "approver": row[7],
                    "notes": row[8],
                    "createdAt": row[9],
                    "updatedAt": row[10]
                })
            return results
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": f"Database error: {e}"})

    @app.post("/governance/approve")
    async def approve_proposal(request: Request):
        try:
            body = await request.json()
        except Exception:
            return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})

        proposal_id = body.get("proposalId")
        approver = body.get("approver", "operator")
        notes = body.get("notes", "")
        status = body.get("status", "approved")

        if not proposal_id:
            return JSONResponse(status_code=400, content={"error": "Missing proposalId"})

        try:
            conn = db_manager.get_connection()
            
            # Check if proposal exists
            cursor = conn.execute("SELECT agentId, type, title FROM GovernanceProposal WHERE id = ?", (proposal_id,))
            row = conn.fetchone(cursor)
            if not row:
                return JSONResponse(status_code=404, content={"error": f"Proposal not found: {proposal_id}"})
            
            agent_id, prop_type, title = row
            
            # Update proposal
            conn.execute("""
                UPDATE GovernanceProposal
                SET status = ?, approver = ?, notes = ?, updatedAt = datetime('now')
                WHERE id = ?
            """, (status, approver, notes, proposal_id))
            
            # Create Audit Log inside VaultEntry table
            try:
                conn.execute("""
                    INSERT OR IGNORE INTO Agent (id, name, type, status, domain, trustScore, createdAt, updatedAt)
                    VALUES (?, ?, 'worker', 'idle', 'code', 0.5, datetime('now'), datetime('now'))
                """, (agent_id, agent_id))
            except Exception:
                pass
                
            entry_id = f"entry-{uuid.uuid4().hex[:8]}"
            value_json = json.dumps({
                "proposalId": proposal_id,
                "title": title,
                "type": prop_type,
                "status": status,
                "approver": approver,
                "notes": notes
            })
            try:
                conn.execute("""
                    INSERT INTO VaultEntry (id, agentId, track, category, key, value, score, createdAt)
                    VALUES (?, ?, 'GOV', 'proposal_approval', ?, ?, 1.0, datetime('now'))
                """, (entry_id, agent_id, proposal_id, value_json))
            except Exception as e:
                logger.warning(f"Could not write proposal to VaultEntry: {e}")
                
            conn.commit()

            # Retrieve complete updated proposal to return it
            cursor = conn.execute("""
                SELECT id, agentId, type, title, description, riskLevel, status, approver, notes, createdAt, updatedAt
                FROM GovernanceProposal WHERE id = ?
            """, (proposal_id,))
            row = conn.fetchone(cursor)
            proposal_obj = {
                "id": row[0],
                "agentId": row[1],
                "type": row[2],
                "title": row[3],
                "description": row[4],
                "riskLevel": row[5],
                "status": row[6],
                "approver": row[7],
                "notes": row[8],
                "createdAt": row[9],
                "updatedAt": row[10]
            }
            return {
                "status": "success",
                "proposalId": proposal_id,
                "decision": status,
                "proposal": proposal_obj
            }
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": f"Database error: {e}"})

    @app.post("/tasks/heartbeat")
    async def task_heartbeat(request: Request):
        try:
            body = await request.json()
        except Exception:
            return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})

        agent_id = body.get("agentId")
        task_id = body.get("taskId")
        task_type = body.get("type", "execution")
        progress = float(body.get("progress", 0))
        message = body.get("message", "")
        risk_level = body.get("riskLevel", "low")

        if not task_id or not agent_id:
            return JSONResponse(status_code=400, content={"error": "Missing agentId or taskId"})

        try:
            conn = db_manager.get_connection()
            
            # Check if task already exists
            cursor = conn.execute("SELECT id FROM GovernanceTask WHERE taskId = ?", (task_id,))
            row = conn.fetchone(cursor)
            
            if row:
                conn.execute("""
                    UPDATE GovernanceTask
                    SET progress = ?, message = ?, riskLevel = ?, updatedAt = datetime('now')
                    WHERE taskId = ?
                """, (progress, message, risk_level, task_id))
            else:
                db_id = f"gtask-{uuid.uuid4().hex[:12]}"
                conn.execute("""
                    INSERT INTO GovernanceTask (id, agentId, taskId, type, status, progress, message, riskLevel, createdAt, updatedAt)
                    VALUES (?, ?, ?, ?, 'active', ?, ?, ?, datetime('now'), datetime('now'))
                """, (db_id, agent_id, task_id, task_type, progress, message, risk_level))
            
            conn.commit()

            # Retrieve complete task object to return it
            cursor = conn.execute("""
                SELECT id, agentId, taskId, type, status, progress, message, output, tokensUsed, durationMs, riskLevel, createdAt, updatedAt, completedAt
                FROM GovernanceTask WHERE taskId = ?
            """, (task_id,))
            row = conn.fetchone(cursor)
            task_obj = {
                "id": row[0],
                "agentId": row[1],
                "taskId": row[2],
                "type": row[3],
                "status": row[4],
                "progress": row[5],
                "message": row[6],
                "output": row[7],
                "tokensUsed": row[8],
                "durationMs": row[9],
                "riskLevel": row[10],
                "createdAt": row[11],
                "updatedAt": row[12],
                "completedAt": row[13]
            }
            return {
                "status": "success",
                "taskId": task_id,
                "progress": progress,
                "task": task_obj
            }
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": f"Database error: {e}"})

    @app.post("/tasks/result")
    async def task_result(request: Request):
        try:
            body = await request.json()
        except Exception:
            return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})

        task_id = body.get("taskId")
        status = body.get("status", "completed")
        output = body.get("output", "")
        tokens_used = int(body.get("tokensUsed", 0))
        duration_ms = int(body.get("durationMs", 0))

        if not task_id:
            return JSONResponse(status_code=400, content={"error": "Missing taskId"})

        try:
            conn = db_manager.get_connection()
            
            # Check if task exists
            cursor = conn.execute("SELECT id FROM GovernanceTask WHERE taskId = ?", (task_id,))
            row = conn.fetchone(cursor)
            
            if not row:
                # If not registered via heartbeat, auto-create it first
                db_id = f"gtask-{uuid.uuid4().hex[:12]}"
                conn.execute("""
                    INSERT INTO GovernanceTask (id, agentId, taskId, type, status, progress, message, riskLevel, createdAt, updatedAt)
                    VALUES (?, 'unknown', ?, 'execution', ?, 100.0, 'completed via task/result', 'low', datetime('now'), datetime('now'))
                """, (db_id, task_id, status))
                
            conn.execute("""
                UPDATE GovernanceTask
                SET status = ?, output = ?, tokensUsed = ?, durationMs = ?, progress = 100.0, completedAt = datetime('now'), updatedAt = datetime('now')
                WHERE taskId = ?
            """, (status, output, tokens_used, duration_ms, task_id))
            
            conn.commit()

            # Retrieve complete task object to return it
            cursor = conn.execute("""
                SELECT id, agentId, taskId, type, status, progress, message, output, tokensUsed, durationMs, riskLevel, createdAt, updatedAt, completedAt
                FROM GovernanceTask WHERE taskId = ?
            """, (task_id,))
            row = conn.fetchone(cursor)
            task_obj = {
                "id": row[0],
                "agentId": row[1],
                "taskId": row[2],
                "type": row[3],
                "status": row[4],
                "progress": row[5],
                "message": row[6],
                "output": row[7],
                "tokensUsed": row[8],
                "durationMs": row[9],
                "riskLevel": row[10],
                "createdAt": row[11],
                "updatedAt": row[12],
                "completedAt": row[13]
            }
            return {
                "status": "success",
                "taskId": task_id,
                "state": status,
                "task": task_obj
            }
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": f"Database error: {e}"})

    @app.post("/tasks/submit")
    async def submit_task(request: Request):
        body = await request.body()
        req_headers = {k.lower(): v for k, v in request.headers.items()}
        agent_id = req_headers.get("x-nexus-agent-id", "unknown")
        input_tokens = len(body) // 4  # Rough estimate
        status_code, response = server.handle_submit(body, req_headers)
        output_tokens = len(str(response).encode()) // 4  # Rough estimate
        server.token_guard.track(agent_id, input_tokens + output_tokens,
                                  operation="task_delegation",
                                  input_tokens=input_tokens,
                                  output_tokens=output_tokens)
        return JSONResponse(content=response, status_code=status_code,
                           headers={"X-Nexus-Input-Tokens": str(input_tokens),
                                   "X-Nexus-Output-Tokens": str(output_tokens),
                                   "X-Token-Remaining": str(server.token_guard.remaining(agent_id))})

    @app.post("/tasks/status")
    async def query_status(request: Request):
        body = await request.body()
        req_headers = {k.lower(): v for k, v in request.headers.items()}
        agent_id = req_headers.get("x-nexus-agent-id", "unknown")
        input_tokens = len(body) // 4
        status_code, response = server.handle_status(body, req_headers)
        output_tokens = len(str(response).encode()) // 4
        server.token_guard.track(agent_id, input_tokens + output_tokens,
                                  operation="memory_query",
                                  input_tokens=input_tokens,
                                  output_tokens=output_tokens)
        return JSONResponse(content=response, status_code=status_code,
                           headers={"X-Nexus-Input-Tokens": str(input_tokens),
                                   "X-Nexus-Output-Tokens": str(output_tokens),
                                   "X-Token-Remaining": str(server.token_guard.remaining(agent_id))})

    @app.post("/vault/read")
    async def vault_read(request: Request):
        body = await request.body()
        req_headers = {k.lower(): v for k, v in request.headers.items()}
        agent_id = req_headers.get("x-nexus-agent-id", "unknown")
        input_tokens = len(body) // 4
        status_code, response = server.handle_vault_read(body, req_headers)
        output_tokens = len(str(response).encode()) // 4
        server.token_guard.track(agent_id, input_tokens + output_tokens,
                                  operation="memory_query",
                                  input_tokens=input_tokens,
                                  output_tokens=output_tokens)
        return JSONResponse(content=response, status_code=status_code,
                           headers={"X-Nexus-Input-Tokens": str(input_tokens),
                                   "X-Nexus-Output-Tokens": str(output_tokens),
                                   "X-Token-Remaining": str(server.token_guard.remaining(agent_id))})

    @app.post("/vault/write")
    async def vault_write(request: Request):
        body = await request.body()
        req_headers = {k.lower(): v for k, v in request.headers.items()}
        agent_id = req_headers.get("x-nexus-agent-id", "unknown")
        input_tokens = len(body) // 4
        status_code, response = server.handle_vault_write(body, req_headers)
        output_tokens = len(str(response).encode()) // 4
        server.token_guard.track(agent_id, input_tokens + output_tokens,
                                  operation="memory_query",
                                  input_tokens=input_tokens,
                                  output_tokens=output_tokens)
        return JSONResponse(content=response, status_code=status_code,
                           headers={"X-Nexus-Input-Tokens": str(input_tokens),
                                   "X-Nexus-Output-Tokens": str(output_tokens),
                                   "X-Token-Remaining": str(server.token_guard.remaining(agent_id))})

    @app.post("/")
    async def jsonrpc_router(request: Request):
        body = await request.body()
        req_headers = {k.lower(): v for k, v in request.headers.items()}
        agent_id = req_headers.get("x-nexus-agent-id", "unknown")
        input_tokens = len(body) // 4
        status_code, response = server.handle_request("POST", body, req_headers)
        # handle_request() already tracks tokens via _track_tokens()
        output_tokens = len(str(response).encode()) // 4
        return JSONResponse(content=response, status_code=status_code,
                           headers={"X-Nexus-Input-Tokens": str(input_tokens),
                                   "X-Nexus-Output-Tokens": str(output_tokens),
                                   "X-Token-Remaining": str(server.token_guard.remaining(agent_id))})

    @app.get("/health")
    async def health():
        return {"status": "ok", "service": "nexus-bridge", "version": "1.0.0"}

    return app

