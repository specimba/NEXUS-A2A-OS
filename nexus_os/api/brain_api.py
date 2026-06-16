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


# ── Auth ────────────────────────────────────────────────────────────────────────

async def verify_api_key(x_api_key: Optional[str] = Header(None)) -> str:
    if not x_api_key:
        return "anonymous"
    return x_api_key


async def require_auth(x_api_key: Optional[str] = Header(None)) -> str:
    if not x_api_key or not x_api_key.startswith("nexus-"):
        raise HTTPException(status_code=401, detail="API key required (nexus-*)")
    return x_api_key


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
        }
    }


@brain_app.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ws_clients": ws_manager.count,
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


# ── Integrations Status ────────────────────────────────────────────────────────

@brain_app.get("/api/integrations")
async def get_integrations(api_key: str = Depends(verify_api_key)):
    from nexus_cli_ctl.control.unified_state.state_manager import get_state_manager
    sm = get_state_manager()
    return sm.get_state("integrations")


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
