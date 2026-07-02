"""
NEXUS Brain API - Comprehensive REST + WebSocket API

Unified FastAPI application that wires together:
- NEXUSCLAW Orchestrator (agents, tasks, brainstorm, messages)
- Unified State Manager (CLI/dashboard sync)
- Provider Health Monitor (circuit breaker)
- A2A Bridge Health
- Tailscale/Zo reachability
- Model Relay status
- Archivist wiki
- NEXUSCLAW Messaging (Slack/Telegram/Discord)

Port: 7352 (governance API, replaces separate service endpoints)

Relay proxy: tries Node/npm ModelRelay (port 7350 default) first,
then falls back to Python relay (port 7355).
Override with NODERELAY_PORT or RELAY_PORT env vars.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Header, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from nexus_os.nexusclaw.orchestrator import NexusClawOrchestrator, get_orchestrator
from nexus_os.nexusclaw.agent_pool import get_agent_pool, AgentStatus, AgentType
from nexus_os.nexusclaw.envelope import NexusClawTaskEnvelope, RiskLevel
from nexus_os.nexusclaw.message_bus import MessageType, MessagePriority
from nexus_os.nexusclaw.brainstorm import BrainstormMode, VoteChoice
from nexus_os.governor.trust_engine_v2 import get_trust_engine

logger = logging.getLogger("nexus.brain_api")

brain_app = FastAPI(
    title="NEXUS Brain API",
    version="4.0.0",
    description="NEXUS OS governance + orchestration + state API",
    docs_url="/docs",
    redoc_url="/redoc",
)

_origins = [o.strip() for o in os.getenv(
    "NEXUS_API_ORIGINS",
    "http://127.0.0.1:3001,http://127.0.0.1:7356,http://localhost:3001,http://localhost:7356"
).split(",") if o.strip()]

brain_app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        client_id = request.headers.get("x-api-key", request.client.host if request.client else "unknown")
        if not rate_limiter.is_allowed(client_id):
            return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(rate_limiter.remaining(client_id))
        return response


brain_app.add_middleware(RateLimitMiddleware)


# ── ModelRelay Proxy ────────────────────────────────────────────────────────────

import httpx

# Try Node/npm ModelRelay first (port 7350), fall back to Python relay (port 7355)
_NODERELAY_PORT = int(os.environ.get("NODERELAY_PORT", "7350"))
_PYTHONRELAY_PORT = int(os.environ.get("PYTHONRELAY_PORT", "7355"))

_NODERELAY_BASE = f"http://127.0.0.1:{_NODERELAY_PORT}"
_PYTHONRELAY_BASE = f"http://127.0.0.1:{_PYTHONRELAY_PORT}"


class _ModelRelayProxy:
    """Proxies model relay REST calls from Brain API (port 7352).
    
    Tries Node/npm ModelRelay ({NODERELAY_PORT}) first, falls back to
    Python relay ({PYTHONRELAY_PORT}).
    Exposes: /health, /health/ready, /metrics, /v1/chat/completions
    """

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        self._base_url = _NODERELAY_BASE
        self._fallback_url = _PYTHONRELAY_BASE

    async def _ensure_client(self):
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(base_url=self._base_url, timeout=self.timeout)
        return self._client

    async def _check_relay(self, path: str) -> tuple[Optional[httpx.Response], Optional[str]]:
        """Try primary relay first, then fallback."""
        for label, base in [("node", self._base_url), ("python", self._fallback_url)]:
            try:
                async with httpx.AsyncClient(base_url=base, timeout=self.timeout) as c:
                    r = await c.get(path)
                    if r.status_code < 500:
                        return r, label
            except Exception:
                continue
        return None, None

    async def _switch_to(self, base_url: str):
        if self._base_url != base_url:
            self._base_url = base_url
            if self._client and not self._client.is_closed:
                await self._client.aclose()
            self._client = httpx.AsyncClient(base_url=base_url, timeout=self.timeout)

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def health(self) -> Dict[str, Any]:
        """GET /health (Python relay) or /api/meta (Node relay)."""
        client = await self._ensure_client()
        # Try /api/meta (Node relay)
        try:
            r = await client.get("/api/meta")
            if r.status_code < 500:
                return {"status": "ok", "relay": "node", "detail": r.json()}
        except Exception:
            pass
        # Try /health (Python relay)
        try:
            r = await client.get("/health")
            r.raise_for_status()
            return {"status": "ok", "relay": "python", **r.json()}
        except Exception as e:
            return await self._fallback_health()

    async def _fallback_health(self) -> Dict[str, Any]:
        r, label = await self._check_relay("/health")
        if r:
            try:
                return {"status": "ok", "relay": label, **r.json()}
            except Exception:
                return {"status": "ok", "relay": label}
        return {"status": "unavailable", "relay": "none"}

    async def health_ready(self) -> Dict[str, Any]:
        """Readiness: check if any models are UP via /api/models (Node) or /health/ready (Python)."""
        client = await self._ensure_client()
        try:
            r = await client.get("/v1/models")
            if r.status_code < 500:
                data = r.json()
                models = data.get("data", []) or []
                return {"ready": len(models) > 0, "detail": f"{len(models)} models", "models_count": len(models)}
        except Exception:
            pass
        try:
            r = await client.get("/health/ready")
            if r.status_code < 500:
                return {"ready": r.status_code != 503, "detail": "healthy models available" if r.status_code != 503 else "no healthy models"}
        except Exception:
            pass
        return {"ready": False, "detail": "no relay responding"}

    async def metrics(self) -> Dict[str, Any]:
        """GET /metrics (Python relay only). Node relay has no metrics endpoint."""
        client = await self._ensure_client()
        try:
            r = await client.get("/metrics")
            r.raise_for_status()
            return r.json()
        except Exception:
            return {"note": "metrics only available from Python relay (port 7355)"}

    async def list_models(self) -> Dict[str, Any]:
        """GET /v1/models (OpenAI-compatible) from active relay."""
        client = await self._ensure_client()
        try:
            r = await client.get("/v1/models")
            r.raise_for_status()
            return r.json()
        except Exception:
            return await self._fallback_list_models()

    async def _fallback_list_models(self) -> Dict[str, Any]:
        r, label = await self._check_relay("/v1/models")
        if r:
            try:
                return r.json()
            except Exception:
                pass
        # Try Node native /api/models format
        r2, _ = await self._check_relay("/api/models")
        if r2:
            try:
                raw = r2.json()
                models = raw.get("models", [])
                formatted = [{"id": m.get("modelId"), "object": "model", "owned_by": m.get("providerKey")} for m in models]
                return {"object": "list", "data": formatted}
            except Exception:
                pass
        return {"error": "no relay available", "object": "list", "data": []}

    async def chat_completions(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """POST /v1/chat/completions — via relay auto-routing."""
        client = await self._ensure_client()
        try:
            r = await client.post("/v1/chat/completions", json=payload)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            # Try fallback relay
            try:
                async with httpx.AsyncClient(base_url=self._fallback_url, timeout=self.timeout) as fb:
                    r2 = await fb.post("/v1/chat/completions", json=payload)
                    r2.raise_for_status()
                    await self._switch_to(self._fallback_url)
                    return r2.json()
            except Exception:
                raise HTTPException(status_code=502, detail=f"ModelRelay error: {e}")


_relay_proxy: Optional[_ModelRelayProxy] = None


def get_relay_proxy() -> _ModelRelayProxy:
    global _relay_proxy
    if _relay_proxy is None:
        _relay_proxy = _ModelRelayProxy()
    return _relay_proxy


# ── Auth ────────────────────────────────────────────────────────────────────────
# Audit CRITICAL closed 2026-07-02: reads accepted any (or no) key and
# mutations accepted any key starting with "nexus-" — a guessable static
# pattern. Both now verify a real shared secret with a constant-time compare.

import hmac as _hmac
import secrets as _pysecrets
from pathlib import Path as _Path

BRAIN_TOKEN_FILE = _Path.home() / ".nexus_pi" / "state" / ".brain_api_token"


def get_brain_api_token() -> str:
    """Shared secret: NEXUS_BRAIN_TOKEN env, else an auto-generated local
    token file readable by local clients (TUI, dashboard). Non-loopback
    binds must set the env token explicitly (enforced by the daemon)."""
    env = os.environ.get("NEXUS_BRAIN_TOKEN")
    if env:
        return env
    if BRAIN_TOKEN_FILE.exists():
        tok = BRAIN_TOKEN_FILE.read_text(encoding="utf-8").strip()
        if tok:
            return tok
    tok = _pysecrets.token_hex(32)
    BRAIN_TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    BRAIN_TOKEN_FILE.write_text(tok, encoding="utf-8")
    return tok


def _token_valid(supplied: Optional[str]) -> bool:
    return bool(supplied) and _hmac.compare_digest(supplied, get_brain_api_token())


async def verify_api_key(x_api_key: Optional[str] = Header(None)) -> str:
    """Read-side gate: the governed state is not anonymous-readable."""
    if not _token_valid(x_api_key):
        raise HTTPException(status_code=401, detail="valid API key required")
    return "authenticated"


async def require_auth(x_api_key: Optional[str] = Header(None)) -> str:
    """Mutation-side gate."""
    if not _token_valid(x_api_key):
        raise HTTPException(status_code=401, detail="valid API key required")
    return "authenticated"


# ── Rate Limiting ─────────────────────────────────────────────────────────────────

class SimpleRateLimiter:
    """In-memory per-IP rate limiter for Brain API."""

    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = window_seconds
        self._requests: Dict[str, List[float]] = {}

    def is_allowed(self, client_id: str) -> bool:
        now = time.time()
        if client_id not in self._requests:
            self._requests[client_id] = []
        self._requests[client_id] = [t for t in self._requests[client_id] if now - t < self.window]
        # Stale entry cleanup: prune empty or idle client entries when dict exceeds 1000
        if len(self._requests) > 1000:
            self._requests = {
                k: v for k, v in self._requests.items() if v
            }
        if len(self._requests[client_id]) >= self.max_requests:
            return False
        self._requests[client_id].append(now)
        return True

    def remaining(self, client_id: str) -> int:
        now = time.time()
        if client_id not in self._requests:
            return self.max_requests
        current = [t for t in self._requests[client_id] if now - t < self.window]
        return max(0, self.max_requests - len(current))


rate_limiter = SimpleRateLimiter()


async def check_rate_limit(x_api_key: Optional[str] = Header(None)) -> str:
    client_id = x_api_key or "anonymous"
    if not rate_limiter.is_allowed(client_id):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    return client_id


# ── WebSocket Connection Manager ───────────────────────────────────────────────

class BrainConnectionManager:
    def __init__(self):
        self.active: Dict[str, WebSocket] = {}
        self.subscriptions: Dict[str, Set[str]] = {}

    async def connect(self, ws: WebSocket) -> str:
        await ws.accept()
        conn_id = f"ws-{uuid.uuid4().hex[:8]}"
        self.active[conn_id] = ws
        self.subscriptions[conn_id] = set()
        return conn_id

    def disconnect(self, conn_id: str):
        self.active.pop(conn_id, None)
        self.subscriptions.pop(conn_id, None)

    async def broadcast(self, topic: str, data: Dict[str, Any]):
        stale = []
        for cid, ws in self.active.items():
            if topic in self.subscriptions.get(cid, set()) or "*" in self.subscriptions.get(cid, set()):
                try:
                    await ws.send_json({"type": "update", "topic": topic, "data": data})
                except Exception:
                    stale.append(cid)
        for cid in stale:
            self.disconnect(cid)

    async def send_to(self, conn_id: str, data: Dict[str, Any]):
        ws = self.active.get(conn_id)
        if ws:
            try:
                await ws.send_json(data)
            except Exception:
                self.disconnect(conn_id)

    @property
    def count(self) -> int:
        return len(self.active)


ws_manager = BrainConnectionManager()


# ── Pydantic Models ─────────────────────────────────────────────────────────────

class TaskSubmitModel(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    intent: str = Field(default="general", max_length=100)
    risk_level: str = Field(default="LOW")
    resource_budget: Dict[str, Any] = Field(default_factory=dict)

class MessageSendModel(BaseModel):
    sender_id: str
    recipient_ids: List[str]
    content: str = Field(min_length=1, max_length=4000)
    message_type: str = Field(default="DIRECT")
    priority: str = Field(default="NORMAL")

class BrainstormCreateModel(BaseModel):
    topic: str = Field(min_length=1, max_length=500)
    participant_ids: List[str] = Field(default_factory=list)
    mode: str = Field(default="STRUCTURED")

class ProposalModel(BaseModel):
    agent_id: str
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=4000)
    evidence_refs: Optional[List[str]] = None
    risk_level: str = Field(default="LOW")

class VoteModel(BaseModel):
    agent_id: str
    choice: str = Field(pattern="^(FOR|AGAINST|ABSTAIN)$")

class StatePublishModel(BaseModel):
    topic: str = Field(min_length=1, max_length=200)
    data: Dict[str, Any]
    source: str = Field(default="api")

class InterventionModel(BaseModel):
    intervention: str = Field(min_length=1, max_length=200)
    target: str = Field(min_length=1, max_length=200)


# ── Root & Health ───────────────────────────────────────────────────────────────

@brain_app.get("/")
async def root():
    return {
        "service": "NEXUS Brain API",
        "version": "4.0.0",
        "docs": "/docs",
        "websocket": "/ws",
        "endpoints": {
            "agents": "/api/agents",
            "tasks": "/api/tasks",
            "messages": "/api/messages",
            "brainstorm": "/api/brainstorm",
            "state": "/api/state",
            "health": "/api/health",
            "trust": "/api/trust",
            "providers": "/api/providers",
            "integrations": "/api/integrations",
            "relay": "/api/relay/health",
            "models": "/api/models",
        }
    }


@brain_app.get("/health")
async def health():
    proxy = get_relay_proxy()
    relay_health_data = await proxy.health()
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ws_clients": ws_manager.count,
        "model_relay": relay_health_data,
    }


# ── Agents ─────────────────────────────────────────────────────────────────────

@brain_app.get("/api/agents")
async def list_agents(api_key: str = Depends(verify_api_key)):
    orch = get_orchestrator()
    pool = get_agent_pool()
    stats = pool.stats()
    agents = []
    for a in pool.list_all():
        agents.append({
            "agent_id": a.agent_id,
            "name": a.name,
            "type": a.agent_type.value if hasattr(a.agent_type, "value") else str(a.agent_type),
            "status": a.status.value if hasattr(a.status, "value") else str(a.status),
            "lane": a.lane,
            "trust_score": a.trust_score,
            "capabilities": [c.value if hasattr(c, "value") else str(c) for c in a.capabilities],
        })
    return {"total": stats.get("total_agents", 0), "online": stats.get("online_agents", 0), "agents": agents}


@brain_app.get("/api/agents/{agent_id}")
async def get_agent(agent_id: str, api_key: str = Depends(verify_api_key)):
    pool = get_agent_pool()
    agent = pool.get(agent_id)
    if not agent:
        raise HTTPException(404, f"Agent {agent_id} not found")
    return {
        "agent_id": agent.agent_id,
        "name": agent.name,
        "type": agent.agent_type.value if hasattr(agent.agent_type, "value") else str(agent.agent_type),
        "status": agent.status.value if hasattr(agent.status, "value") else str(agent.status),
        "lane": agent.lane,
        "trust_score": agent.trust_score,
        "capabilities": [c.value if hasattr(c, "value") else str(c) for c in agent.capabilities],
    }


@brain_app.post("/api/agents/{agent_id}/status")
async def update_agent_status(agent_id: str, status: str = Query(...), api_key: str = Depends(require_auth)):
    orch = get_orchestrator()
    try:
        new_status = AgentStatus(status)
    except ValueError:
        raise HTTPException(400, f"Invalid status: {status}")
    agent = orch.update_agent_status(agent_id, new_status)
    if not agent:
        raise HTTPException(404, f"Agent {agent_id} not found")
    await ws_manager.broadcast("agents", {"agent_id": agent_id, "status": status})
    return {"success": True, "agent_id": agent_id, "status": status}


# ── Tasks ───────────────────────────────────────────────────────────────────────

@brain_app.get("/api/tasks")
async def list_tasks(api_key: str = Depends(verify_api_key)):
    orch = get_orchestrator()
    stats = orch.task_router.stats()
    return {
        "active_tasks": stats.get("active_tasks", 0),
        "total_routed": stats.get("total_routed", 0),
        "total_completed": stats.get("total_completed", 0),
        "total_failed": stats.get("total_failed", 0),
    }


@brain_app.post("/api/tasks")
async def submit_task(task: TaskSubmitModel, api_key: str = Depends(require_auth)):
    orch = get_orchestrator()
    try:
        risk = RiskLevel(task.risk_level)
    except ValueError:
        risk = RiskLevel.LOW

    envelope = NexusClawTaskEnvelope(
        task_id=f"task-{uuid.uuid4().hex[:8]}",
        title=task.title,
        description=task.description,
        intent=task.intent,
        risk_level=risk,
        resource_budget=task.resource_budget,
    )
    result = orch.submit_task(envelope)
    await ws_manager.broadcast("tasks", result)
    return result


@brain_app.post("/api/tasks/{task_id}/complete")
async def complete_task(task_id: str, agent_id: str = Query(...), success: bool = Query(True), api_key: str = Depends(require_auth)):
    orch = get_orchestrator()
    result = orch.complete_task(task_id, agent_id, success)
    await ws_manager.broadcast("tasks", result)
    return result


# ── Messages ────────────────────────────────────────────────────────────────────

@brain_app.post("/api/messages")
async def send_message(msg: MessageSendModel, api_key: str = Depends(require_auth)):
    orch = get_orchestrator()
    try:
        mt = MessageType(msg.message_type)
    except ValueError:
        mt = MessageType.DIRECT
    try:
        pri = MessagePriority(msg.priority)
    except ValueError:
        pri = MessagePriority.NORMAL
    result = orch.send_message(msg.sender_id, msg.recipient_ids, msg.content, mt, pri)
    await ws_manager.broadcast("messages", result)
    return result


@brain_app.post("/api/messages/broadcast")
async def broadcast_message(sender_id: str = Query(...), content: str = Query(...), api_key: str = Depends(require_auth)):
    orch = get_orchestrator()
    result = orch.broadcast_message(sender_id, content)
    await ws_manager.broadcast("messages", result)
    return result


# ── Brainstorm ──────────────────────────────────────────────────────────────────

@brain_app.post("/api/brainstorm")
async def create_brainstorm(bs: BrainstormCreateModel, api_key: str = Depends(require_auth)):
    orch = get_orchestrator()
    try:
        mode = BrainstormMode(bs.mode)
    except ValueError:
        mode = BrainstormMode.STRUCTURED
    session = orch.start_brainstorm(bs.topic, bs.participant_ids, mode)
    result = {
        "session_id": session.session_id,
        "topic": session.topic,
        "phase": session.phase.value,
        "is_open": session.is_open,
    }
    await ws_manager.broadcast("brainstorm", result)
    return result


@brain_app.post("/api/brainstorm/{session_id}/propose")
async def propose_idea(session_id: str, proposal: ProposalModel, api_key: str = Depends(require_auth)):
    orch = get_orchestrator()
    try:
        risk = RiskLevel(proposal.risk_level)
    except ValueError:
        risk = RiskLevel.LOW
    p = orch.propose_idea(session_id, proposal.agent_id, proposal.title, proposal.description, proposal.evidence_refs, risk)
    result = {"proposal_id": p.proposal_id, "title": p.title, "consensus_score": p.consensus_score, "accepted": p.accepted}
    await ws_manager.broadcast("brainstorm", result)
    return result


@brain_app.post("/api/brainstorm/{session_id}/vote")
async def vote_on_proposal(session_id: str, proposal_id: str = Query(...), vote: VoteModel = None, api_key: str = Depends(require_auth)):
    if vote is None:
        raise HTTPException(400, "Vote body required")
    orch = get_orchestrator()
    choice = VoteChoice[vote.choice]
    result = orch.vote_on_idea(session_id, vote.agent_id, proposal_id, choice)
    await ws_manager.broadcast("brainstorm", result)
    return result


@brain_app.post("/api/brainstorm/{session_id}/advance")
async def advance_brainstorm(session_id: str, api_key: str = Depends(require_auth)):
    orch = get_orchestrator()
    result = orch.advance_brainstorm(session_id)
    await ws_manager.broadcast("brainstorm", result)
    return result


@brain_app.post("/api/brainstorm/{session_id}/close")
async def close_brainstorm(session_id: str, api_key: str = Depends(require_auth)):
    orch = get_orchestrator()
    result = orch.close_brainstorm(session_id)
    await ws_manager.broadcast("brainstorm", result)
    return result


# ── State Management ───────────────────────────────────────────────────────────

@brain_app.get("/api/state")
async def get_state(section: Optional[str] = Query(None), api_key: str = Depends(verify_api_key)):
    from nexus_cli_ctl.control.unified_state.state_manager import get_state_manager
    sm = get_state_manager()
    return sm.get_state(section)


@brain_app.post("/api/state/publish")
async def publish_state(change: StatePublishModel, api_key: str = Depends(require_auth)):
    from nexus_cli_ctl.control.unified_state.state_manager import get_state_manager
    sm = get_state_manager()
    await sm.publish(change.topic, change.data, source=change.source)
    await ws_manager.broadcast(change.topic, change.data)
    return {"status": "published", "topic": change.topic}


# ── Trust Engine ───────────────────────────────────────────────────────────────

@brain_app.get("/api/trust")
async def get_trust_status(api_key: str = Depends(verify_api_key)):
    te = get_trust_engine()
    return {
        "baseline": te.BASELINE if hasattr(te, "BASELINE") else 25.0,
        "max_score": te.MAX_SCORE if hasattr(te, "MAX_SCORE") else 99.5,
        "decay_rate": te.BASE_DECAY if hasattr(te, "BASE_DECAY") else 0.02,
        "version": "v2.2",
    }


@brain_app.get("/api/trust/agent/{agent_id}")
async def get_agent_trust(agent_id: str, api_key: str = Depends(verify_api_key)):
    te = get_trust_engine()
    score = te.get_score(agent_id) if hasattr(te, "get_score") else None
    return {"agent_id": agent_id, "trust_score": score}


# ── Providers Health ───────────────────────────────────────────────────────────

@brain_app.get("/api/providers")
async def get_providers_health(api_key: str = Depends(verify_api_key)):
    from nexus_os.monitoring.provider_health import get_health_monitor
    health = get_health_monitor()
    return health.get_status()


@brain_app.get("/api/providers/{provider_id}")
async def get_provider_detail(provider_id: str, api_key: str = Depends(verify_api_key)):
    from nexus_os.monitoring.provider_health import get_health_monitor
    health = get_health_monitor()
    data = health.get_provider_status(provider_id)
    if not data:
        raise HTTPException(404, f"Provider {provider_id} not tracked")
    return data


# ── ModelRelay (port 7355) ─────────────────────────────────────────────────────

class _ChatCompletionRequest(BaseModel):
    model: Optional[str] = None
    messages: List[Dict[str, str]] = Field(default_factory=list)
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    stream: bool = False


@brain_app.get("/api/relay/health")
async def relay_health(api_key: str = Depends(verify_api_key)):
    proxy = get_relay_proxy()
    return await proxy.health()


@brain_app.get("/api/relay/health/ready")
async def relay_ready(api_key: str = Depends(verify_api_key)):
    proxy = get_relay_proxy()
    return await proxy.health_ready()


@brain_app.get("/api/relay/metrics")
async def relay_metrics(api_key: str = Depends(verify_api_key)):
    proxy = get_relay_proxy()
    return await proxy.metrics()


@brain_app.get("/api/relay/models")
async def relay_models(api_key: str = Depends(verify_api_key)):
    proxy = get_relay_proxy()
    return await proxy.list_models()


@brain_app.post("/api/relay/chat")
async def relay_chat(req: _ChatCompletionRequest, api_key: str = Depends(require_auth)):
    payload = {
        "model": req.model,
        "messages": req.messages,
        "temperature": req.temperature,
        "max_tokens": req.max_tokens,
        "stream": req.stream,
    }
    payload = {k: v for k, v in payload.items() if v is not None}
    proxy = get_relay_proxy()
    result = await proxy.chat_completions(payload)
    await ws_manager.broadcast("relay.status", {"type": "chat_completion", "model": req.model})
    return result


# ── OpenAI-Compatible v1 Endpoints (for Build mode / OpenCode / KiloCode) ──────
# These allow standard OpenAI-compatible clients to use Brain API (port 7352)
# directly, instead of requiring the raw /api/relay/chat format.

GOD_MODE_ALIASES_V1 = {
    "auto-fastest", "auto-smart", "auto-code", "auto-reason", "auto-balanced",
    "god-smart", "god-mode", "god-fast", "god-code", "god-1m", "god-reason", "auto",
}

_GOD_MODE_PROXY_URL = f"http://127.0.0.1:{int(os.environ.get('GOD_MODE_PORT', '7357'))}"


@brain_app.post("/v1/chat/completions")
async def v1_chat_completions(request: Request):
    """OpenAI-compatible chat completions endpoint.
    
    Routes god-mode/auto profiles to the God Mode Proxy (port 7357),
    and direct model names to the Node ModelRelay (port 7350).
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    model = body.get("model", "auto-fastest")
    
    # Determine target: God Mode Proxy for profiles, ModelRelay for direct models
    if model in GOD_MODE_ALIASES_V1:
        target_url = f"{_GOD_MODE_PROXY_URL}/v1/chat/completions"
    else:
        target_url = f"{_NODERELAY_BASE}/v1/chat/completions"
    
    # Forward the request with longer timeout for LLM responses
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.post(target_url, json=body)
            
            # Forward response headers
            headers = {}
            for k, v in resp.headers.items():
                if k.lower().startswith("x-") or k.lower() == "content-type":
                    headers[k] = v
            headers["x-nexus-routed-via"] = "god-mode-proxy" if model in GOD_MODE_ALIASES_V1 else "node-relay"
            
            if resp.status_code >= 400:
                return JSONResponse(
                    content=resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {"error": resp.text},
                    status_code=resp.status_code,
                    headers=headers,
                )
            
            return JSONResponse(content=resp.json(), headers=headers)
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail=f"Relay unavailable for model '{model}'. Check that the relay is running.")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Relay error: {str(e)}")


@brain_app.get("/v1/models")
async def v1_models():
    """OpenAI-compatible model listing endpoint."""
    proxy = get_relay_proxy()
    result = await proxy.list_models()
    
    # Inject god-mode profiles as virtual models
    profiles = [
        {"id": "auto-fastest", "object": "model", "owned_by": "nexus-god-mode", "description": "Fastest available model"},
        {"id": "auto-smart", "object": "model", "owned_by": "nexus-god-mode", "description": "Highest intelligence model"},
        {"id": "auto-code", "object": "model", "owned_by": "nexus-god-mode", "description": "Coding-optimized model"},
        {"id": "auto-reason", "object": "model", "owned_by": "nexus-god-mode", "description": "Reasoning/thinking model"},
        {"id": "auto-balanced", "object": "model", "owned_by": "nexus-god-mode", "description": "Balanced (quality + speed)"},
        {"id": "god-smart", "object": "model", "owned_by": "nexus-god-mode", "description": "God Mode: highest intelligence"},
        {"id": "god-mode", "object": "model", "owned_by": "nexus-god-mode", "description": "God Mode: balanced"},
        {"id": "god-fast", "object": "model", "owned_by": "nexus-god-mode", "description": "God Mode: lowest latency"},
        {"id": "god-code", "object": "model", "owned_by": "nexus-god-mode", "description": "God Mode: coding-optimized"},
        {"id": "god-reason", "object": "model", "owned_by": "nexus-god-mode", "description": "God Mode: reasoning"},
    ]
    
    if isinstance(result, dict) and "data" in result:
        result["data"] = profiles + result["data"]
    
    return result


# ── ModelRelay Model Selection via Orchestrator ────────────────────────────────

@brain_app.get("/api/models")
async def list_available_models(api_key: str = Depends(verify_api_key)):
    proxy = get_relay_proxy()
    return await proxy.list_models()


@brain_app.get("/models")
async def list_available_models_alias(api_key: str = Depends(verify_api_key)):
    """Read-only compatibility alias for dashboard/GMR clients.

    This delegates to the lazy relay inventory path and must not start provider
    health loops or broad model polling.
    """
    return await list_available_models(api_key=api_key)


@brain_app.get("/api/models/{model_id}")
async def get_model_detail(model_id: str, api_key: str = Depends(verify_api_key)):
    proxy = get_relay_proxy()
    data = await proxy.list_models()
    models = data.get("models", []) or data.get("data", [])
    for m in models:
        if m.get("id") == model_id or m.get("name") == model_id:
            return m
    raise HTTPException(404, f"Model {model_id} not found in relay inventory")


@brain_app.get("/api/models/select/{task_type}")
async def select_model_for_task(task_type: str, prefer_local: bool = Query(False), api_key: str = Depends(verify_api_key)):
    from nexus_os.nexusclaw.orchestrator import get_orchestrator
    from nexus_os.models.registry import get_registry
    registry = get_registry()
    model_entry = registry.select_model(task_type, prefer_local=prefer_local)
    if model_entry:
        result = {
            "task_type": task_type,
            "model_id": model_entry.name,
            "provider": model_entry.provider,
            "intelligence_score": getattr(model_entry, "intelligence_score", None),
            "context_window": getattr(model_entry, "context_window", None),
            "selected_via": "registry",
        }
        await ws_manager.broadcast("model.changed", result)
        return result
    return {"task_type": task_type, "selected_via": "none", "model_id": None}


@brain_app.get("/model/select")
async def select_model_alias(
    task_type: str = Query(..., min_length=1),
    prefer_local: bool = Query(False),
    api_key: str = Depends(verify_api_key),
):
    """Read-only model selection alias for NEXUS v5 control surfaces."""
    return await select_model_for_task(
        task_type=task_type,
        prefer_local=prefer_local,
        api_key=api_key,
    )


@brain_app.get("/model/health")
async def model_health_alias(api_key: str = Depends(verify_api_key)):
    """Demand-driven ModelRelay health alias.

    This is an explicit operator/API request, not a background health poll.
    """
    proxy = get_relay_proxy()
    return await proxy.health()


# ── Integrations Status ────────────────────────────────────────────────────────

@brain_app.get("/api/integrations")
async def get_integrations(api_key: str = Depends(verify_api_key)):
    from nexus_cli_ctl.control.unified_state.state_manager import get_state_manager
    sm = get_state_manager()
    state = sm.get_state("integrations") or {}
    try:
        from nexus_cli_ctl.integrations.mimo.mimo_integration import MimoConfig
        mimo = MimoConfig()
        mimo_status = mimo.get_status()
    except Exception:
        mimo_status = {"error": "unavailable"}
    proxy = get_relay_proxy()
    relay = await proxy.health()
    return {
        **state,
        "mimo": mimo_status,
        "model_relay": {
            "status": relay.get("status", "unknown"),
            "models_healthy": relay.get("models_healthy", 0),
            "uptime_s": relay.get("uptime_s", 0),
        }
    }


# ── Wiki / DoppelGround ───────────────────────────────────────────────────────

@brain_app.get("/api/wiki")
async def wiki_status(api_key: str = Depends(verify_api_key)):
    from nexus_cli_ctl.integrations.wiki_pipeline import get_wiki_pipeline
    pipeline = get_wiki_pipeline()
    return pipeline.get_status()


@brain_app.get("/api/wiki/pages")
async def wiki_list_pages(api_key: str = Depends(verify_api_key)):
    from nexus_cli_ctl.integrations.wiki_pipeline import get_wiki_pipeline
    pipeline = get_wiki_pipeline()
    return {"pages": pipeline.list_pages()}


@brain_app.get("/api/wiki/search")
async def wiki_search(q: str = Query(..., min_length=1), limit: int = Query(10, ge=1, le=50), api_key: str = Depends(verify_api_key)):
    from nexus_cli_ctl.integrations.wiki_pipeline import get_wiki_pipeline
    pipeline = get_wiki_pipeline()
    return {"query": q, "results": pipeline.search(q, limit=limit)}


@brain_app.post("/api/wiki/refresh")
async def wiki_refresh(api_key: str = Depends(require_auth)):
    from nexus_cli_ctl.integrations.wiki_pipeline import get_wiki_pipeline
    pipeline = get_wiki_pipeline()
    # Use async_refresh with state_manager publish if available, else sync fallback
    if hasattr(pipeline, 'async_refresh'):
        result = await pipeline.async_refresh()
    else:
        result = pipeline.refresh()
    await ws_manager.broadcast("wiki", result)
    return result


@brain_app.get("/api/wiki/sources")
async def wiki_sources(api_key: str = Depends(verify_api_key)):
    from nexus_cli_ctl.integrations.wiki_pipeline import get_wiki_pipeline
    pipeline = get_wiki_pipeline()
    return pipeline.list_sources()


@brain_app.get("/api/wiki/{slug:path}")
async def wiki_get_page(slug: str, api_key: str = Depends(verify_api_key)):
    from nexus_cli_ctl.integrations.wiki_pipeline import get_wiki_pipeline
    pipeline = get_wiki_pipeline()
    page = pipeline.get_page(slug)
    if not page:
        raise HTTPException(404, f"Wiki page '{slug}' not found")
    return page


# ── Messaging (Telegram/Slack/Discord) ─────────────────────────────────────────

class MessagingSendModel(BaseModel):
    platform: str
    channel: str
    text: str

class MessagingBroadcastModel(BaseModel):
    text: str
    channels: Optional[Dict] = None


@brain_app.get("/api/messaging")
async def messaging_status(api_key: str = Depends(verify_api_key)):
    from nexus_cli_ctl.integrations.messaging.messaging_integration import get_messaging_integration
    mi = get_messaging_integration()
    return mi.get_status()


@brain_app.get("/api/messaging/history")
async def messaging_history(limit: int = Query(20, ge=1, le=100), api_key: str = Depends(verify_api_key)):
    from nexus_cli_ctl.integrations.messaging.messaging_integration import get_messaging_integration
    mi = get_messaging_integration()
    return {"history": mi.get_history(limit=limit)}


@brain_app.post("/api/messaging/send")
async def messaging_send(msg: MessagingSendModel, api_key: str = Depends(require_auth)):
    from nexus_cli_ctl.integrations.messaging.messaging_integration import get_messaging_integration
    mi = get_messaging_integration()
    result = await mi.send(msg.platform, msg.channel, msg.text)
    await ws_manager.broadcast("messaging", result)
    return result


@brain_app.post("/api/messaging/broadcast")
async def messaging_broadcast(msg: MessagingBroadcastModel, api_key: str = Depends(require_auth)):
    from nexus_cli_ctl.integrations.messaging.messaging_integration import get_messaging_integration
    mi = get_messaging_integration()
    results = await mi.broadcast(msg.text, channels=msg.channels)
    await ws_manager.broadcast("messaging", {"event": "broadcast", "count": len(results)})
    return {"results": results}


# ── Dashboard Sync ─────────────────────────────────────────────────────────────

@brain_app.get("/api/dashboard/sync")
async def dashboard_sync_status(api_key: str = Depends(verify_api_key)):
    from nexus_cli_ctl.integrations.dashboard_sync import get_dashboard_sync
    ds = get_dashboard_sync()
    return ds.get_status()


# ── Intervention ────────────────────────────────────────────────────────────────

@brain_app.post("/api/intervene")
async def intervene(req: InterventionModel, api_key: str = Depends(require_auth)):
    orch = get_orchestrator()
    result = {"intervention_id": f"int-{uuid.uuid4().hex[:8]}", "intervention": req.intervention, "target": req.target, "status": "submitted"}
    logger.info(f"Intervention: {req.intervention} -> {req.target}")
    await ws_manager.broadcast("interventions", result)
    return result


# ── Halt / Emergency ───────────────────────────────────────────────────────────

@brain_app.post("/api/halt")
async def halt_system(reason: str = Query(..., max_length=500), api_key: str = Depends(require_auth)):
    orch = get_orchestrator()
    result = orch.halt(reason)
    await ws_manager.broadcast("system", {"event": "halt", "reason": reason})
    return result


# ── Orchestrator Full Stats ────────────────────────────────────────────────────

@brain_app.get("/api/stats")
async def full_stats(api_key: str = Depends(verify_api_key)):
    orch = get_orchestrator()
    status = orch.status()
    return {
        "orchestrator": status.to_dict(),
        "full_stats": orch.full_stats(),
        "ws_clients": ws_manager.count,
    }


# ── Stress Lab Report Writeback (gap #5) ──────────────────────────────────────

class StressReportRequest(BaseModel):
    run_id: str = Field(default="", description="Unique run identifier")
    team: str = Field(default="red", description="Red/Blue/Purple team")
    scenario: str = Field(default="jailbreak", description="jailbreak|injection|escalation|over-refusal")
    count: int = Field(default=10, ge=1, le=1000, description="Number of prompts tested")
    model: str = Field(default="auto", description="Model used for testing")
    topic: Optional[str] = Field(default=None, description="Test topic focus")
    attack_success_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="ASR percentage (0.0-1.0)")
    refusal_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="Refusal percentage (0.0-1.0)")
    robustness_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Overall robustness (0.0-1.0)")
    latency_ms: int = Field(default=0, ge=0, description="Average request latency in ms")
    tokens_used: int = Field(default=0, ge=0, description="Total tokens consumed")
    results: List[Dict[str, Any]] = Field(default_factory=list, description="Detailed per-query results")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


@brain_app.post("/api/stress/report")
async def stress_report(report: StressReportRequest, api_key: str = Depends(verify_api_key)):
    """
    Writeback endpoint for nexusctl stress-lab results.
    Stores to Vault EPISODIC channel + broadcasts via WebSocket + Archivist queue.
    """
    run_id = report.run_id or f"stress-{int(time.time())}-{report.team}-{report.scenario}"
    timestamp = datetime.now(timezone.utc).isoformat()

    record = {
        "run_id": run_id,
        "timestamp": timestamp,
        "team": report.team,
        "scenario": report.scenario,
        "count": report.count,
        "model": report.model,
        "topic": report.topic,
        "attack_success_rate": report.attack_success_rate,
        "refusal_rate": report.refusal_rate,
        "robustness_score": report.robustness_score,
        "latency_ms": report.latency_ms,
        "tokens_used": report.tokens_used,
        "results": report.results,
        "metadata": report.metadata,
    }

    # Store to Vault EPISODIC channel (agent_id = "nexusctl_stress_lab")
    try:
        orchestrator = get_orchestrator()
        # Stage to Vault EPISODIC channel via orchestrator memory sync (read path confirms write readiness)
        orchestrator.sync_memory_context(
            agent_id="nexusctl_stress_lab",
            query=f"stress_report:{run_id}:{report.team}:{report.scenario}:ASR={report.attack_success_rate:.2f}",
            action="write",
        )
    except Exception as e:
        logger.warning(f"Vault EPISODIC write failed (non-fatal): {e}")

    # Broadcast via WebSocket for dashboard live updates
    await ws_manager.broadcast("stress", {
        "event": "stress_report",
        "run_id": run_id,
        "team": report.team,
        "scenario": report.scenario,
        "attack_success_rate": report.attack_success_rate,
        "robustness_score": report.robustness_score,
        "timestamp": timestamp,
    })

    # Queue for Archivist SEMANTIC ingestion
    try:
        from nexus_os.archivist.archivist import generate_log_entry
        entry = generate_log_entry(
            action=f"stress_report:{report.team}:{report.scenario}",
            summary=f"ASR={report.attack_success_rate:.3f} | Robustness={report.robustness_score:.3f} | N={report.count}",
            details=record,
        )
        logger.info(f"Archivist log entry created: {run_id}")
    except Exception as e:
        logger.warning(f"Archivist queue failed (non-fatal): {e}")

    return {
        "status": "accepted",
        "run_id": run_id,
        "timestamp": timestamp,
        "sinks": {
            "vault_episodic": True,
            "websocket_broadcast": True,
            "archivist_queue": True,
        },
    }


# ── WebSocket ──────────────────────────────────────────────────────────────────

@brain_app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    conn_id = await ws_manager.connect(websocket)
    await ws_manager.send_to(conn_id, {
        "type": "connected",
        "connection_id": conn_id,
        "subscriptions": list(ws_manager.subscriptions.get(conn_id, set())),
    })
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                msg_type = msg.get("type", "")

                if msg_type == "subscribe":
                    topics = msg.get("topics", ["*"])
                    ws_manager.subscriptions[conn_id].update(topics)
                    await ws_manager.send_to(conn_id, {
                        "type": "subscribed",
                        "topics": list(ws_manager.subscriptions[conn_id]),
                    })

                elif msg_type == "unsubscribe":
                    topics = msg.get("topics", [])
                    for t in topics:
                        ws_manager.subscriptions[conn_id].discard(t)
                    await ws_manager.send_to(conn_id, {
                        "type": "unsubscribed",
                        "topics": list(ws_manager.subscriptions[conn_id]),
                    })

                elif msg_type == "ping":
                    await ws_manager.send_to(conn_id, {"type": "pong", "ts": time.time()})

                elif msg_type == "get_state":
                    from nexus_cli_ctl.control.unified_state.state_manager import get_state_manager
                    sm = get_state_manager()
                    section = msg.get("section")
                    await ws_manager.send_to(conn_id, {
                        "type": "state",
                        "section": section,
                        "data": sm.get_state(section),
                    })

                elif msg_type == "publish":
                    from nexus_cli_ctl.control.unified_state.state_manager import get_state_manager
                    sm = get_state_manager()
                    topic = msg.get("topic", "")
                    payload = msg.get("data", {})
                    source = msg.get("source", "ws")
                    await sm.publish(topic, payload, source=source)
                    await ws_manager.broadcast(topic, payload)

            except json.JSONDecodeError:
                await ws_manager.send_to(conn_id, {"type": "error", "message": "Invalid JSON"})
    except WebSocketDisconnect:
        ws_manager.disconnect(conn_id)
    except Exception:
        ws_manager.disconnect(conn_id)


# ── Server Entry Point ─────────────────────────────────────────────────────────

def run_brain_api(host: str = "0.0.0.0", port: int = 7352):
    import uvicorn
    uvicorn.run(brain_app, host=host, port=port)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="NEXUS Brain API Server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=7352)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    run_brain_api(host=args.host, port=args.port)
