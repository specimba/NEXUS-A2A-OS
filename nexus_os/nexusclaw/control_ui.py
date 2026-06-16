"""NEXUSCLAW Control UI - Tailscale-compatible web UI server."""

from __future__ import annotations

import json
import os
import uuid
from typing import Any, Dict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field

control_app = FastAPI(
    title="NEXUSCLAW Control UI",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


def _allowed_origins() -> list[str]:
    raw = os.getenv(
        "NEXUSCLAW_CONTROL_ORIGINS",
        "http://127.0.0.1:18789,http://localhost:18789",
    )
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


control_app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["content-type", "authorization"],
)


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket) -> str:
        await websocket.accept()
        conn_id = f"conn-{uuid.uuid4().hex[:8]}"
        self.active_connections[conn_id] = websocket
        return conn_id

    def disconnect(self, conn_id: str) -> None:
        self.active_connections.pop(conn_id, None)

    async def broadcast(self, message: Dict[str, Any]) -> None:
        stale: list[str] = []
        for conn_id, conn in self.active_connections.items():
            try:
                await conn.send_text(json.dumps(message))
            except Exception:
                stale.append(conn_id)
        for conn_id in stale:
            self.disconnect(conn_id)

    async def send_personal(self, conn_id: str, message: Dict[str, Any]) -> None:
        if conn_id in self.active_connections:
            await self.active_connections[conn_id].send_text(json.dumps(message))


manager = ConnectionManager()


class MessageRequest(BaseModel):
    platform: str = Field(min_length=1, max_length=32)
    target: str = Field(min_length=1, max_length=256)
    text: str = Field(min_length=1, max_length=4000)
    dry_run: bool = True


def _ui_shell() -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>NEXUSCLAW Control</title>
  <style>
    :root {
      --ink: #17211c;
      --muted: #647067;
      --paper: #f5f0e6;
      --panel: rgba(255, 252, 244, 0.88);
      --line: rgba(23, 33, 28, 0.16);
      --accent: #c4572b;
      --accent-2: #266f63;
      --good: #1f7a4d;
      --warn: #9b5b10;
      --shadow: 0 24px 70px rgba(23, 33, 28, 0.18);
      font-family: "Aptos", "Segoe UI", sans-serif;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      color: var(--ink);
      background:
        radial-gradient(circle at 12% 12%, rgba(196, 87, 43, 0.18), transparent 28%),
        radial-gradient(circle at 86% 8%, rgba(38, 111, 99, 0.2), transparent 28%),
        linear-gradient(135deg, #f7efe1 0%, #e8dcc8 52%, #d9e0d2 100%);
    }
    main {
      width: min(1120px, calc(100% - 32px));
      margin: 0 auto;
      padding: 42px 0;
    }
    .hero {
      display: grid;
      grid-template-columns: 1.25fr 0.75fr;
      gap: 22px;
      align-items: stretch;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 28px;
      box-shadow: var(--shadow);
      backdrop-filter: blur(14px);
      padding: 28px;
    }
    .eyebrow {
      color: var(--accent-2);
      font-size: 12px;
      font-weight: 800;
      letter-spacing: 0.18em;
      text-transform: uppercase;
    }
    h1 {
      margin: 12px 0 10px;
      font-size: clamp(40px, 7vw, 88px);
      line-height: 0.88;
      letter-spacing: -0.07em;
    }
    p { color: var(--muted); line-height: 1.6; }
    .status-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 14px;
      margin-top: 20px;
    }
    .metric {
      border: 1px solid var(--line);
      border-radius: 20px;
      padding: 16px;
      background: rgba(255,255,255,0.38);
    }
    .metric strong { display: block; font-size: 28px; }
    .metric span { color: var(--muted); font-size: 13px; }
    form {
      display: grid;
      gap: 12px;
      margin-top: 18px;
    }
    input, textarea, select, button {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 13px 14px;
      font: inherit;
      background: rgba(255,255,255,0.72);
      color: var(--ink);
    }
    textarea { min-height: 110px; resize: vertical; }
    button {
      cursor: pointer;
      border: none;
      background: linear-gradient(135deg, var(--accent), #d98744);
      color: white;
      font-weight: 800;
      box-shadow: 0 14px 34px rgba(196, 87, 43, 0.28);
    }
    .rail {
      display: grid;
      gap: 14px;
    }
    .badge {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      border-radius: 999px;
      padding: 8px 12px;
      background: rgba(38, 111, 99, 0.12);
      color: var(--accent-2);
      font-weight: 800;
      font-size: 13px;
    }
    pre {
      overflow: auto;
      border-radius: 18px;
      padding: 16px;
      background: #17211c;
      color: #f8f0df;
      min-height: 120px;
    }
    @media (max-width: 820px) {
      .hero { grid-template-columns: 1fr; }
      .status-grid { grid-template-columns: 1fr; }
      main { padding-top: 22px; }
    }
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <div class="panel">
        <div class="eyebrow">Governed control surface</div>
        <h1>NEXUSCLAW</h1>
        <p>Dry-run-first operator console for coordinated messaging and local runtime checks. No provider call is made unless dry-run is disabled by an operator.</p>
        <div class="status-grid">
          <div class="metric"><strong id="connections">0</strong><span>WebSocket clients</span></div>
          <div class="metric"><strong id="platforms">0</strong><span>Enabled platforms</span></div>
          <div class="metric"><strong id="mode">dry</strong><span>Default send mode</span></div>
        </div>
        <form id="messageForm">
          <select id="platform">
            <option value="slack">Slack</option>
            <option value="telegram">Telegram</option>
            <option value="discord">Discord</option>
          </select>
          <input id="target" placeholder="Target channel, chat id, or room" value="#ops">
          <textarea id="text" placeholder="Message text">NEXUSCLAW dry-run check.</textarea>
          <button type="submit">Preview Governed Send</button>
        </form>
      </div>
      <aside class="rail">
        <div class="panel">
          <span class="badge">localhost-first</span>
          <p>Control UI defaults to loopback and scoped CORS. Put it behind Tailscale or an approved gateway before wider exposure.</p>
        </div>
        <div class="panel">
          <span class="badge">operator output</span>
          <pre id="output">Loading status...</pre>
        </div>
      </aside>
    </section>
  </main>
  <script>
    async function refreshStatus() {
      const res = await fetch('/api/status');
      const data = await res.json();
      document.getElementById('connections').textContent = data.active_connections;
      document.getElementById('platforms').textContent = data.enabled_platforms.length;
      document.getElementById('mode').textContent = data.default_dry_run ? 'dry' : 'live';
      document.getElementById('output').textContent = JSON.stringify(data, null, 2);
    }
    document.getElementById('messageForm').addEventListener('submit', async (event) => {
      event.preventDefault();
      const payload = {
        platform: document.getElementById('platform').value,
        target: document.getElementById('target').value,
        text: document.getElementById('text').value,
        dry_run: true
      };
      const res = await fetch('/api/message', {
        method: 'POST',
        headers: {'content-type': 'application/json'},
        body: JSON.stringify(payload)
      });
      document.getElementById('output').textContent = JSON.stringify(await res.json(), null, 2);
    });
    refreshStatus();
    setInterval(refreshStatus, 10000);
  </script>
</body>
</html>"""


@control_app.get("/", response_class=HTMLResponse)
async def dashboard() -> str:
    return _ui_shell()


@control_app.get("/healthz")
async def healthz() -> Dict[str, Any]:
    return {"ok": True, "service": "nexusclaw-control-ui"}


@control_app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> Response:
    return Response(status_code=204)


@control_app.get("/api/status")
async def status() -> Dict[str, Any]:
    from nexus_os.nexusclaw.messaging import NEXUSCLAWMessagingHub

    hub = NEXUSCLAWMessagingHub()
    return {
        "service": "nexusclaw-control-ui",
        "default_dry_run": True,
        "active_connections": len(manager.active_connections),
        "enabled_platforms": hub.get_enabled_platforms(),
        "available_platforms": ["telegram", "slack", "discord"],
        "cors_origins": _allowed_origins(),
    }


@control_app.post("/api/message")
async def send_message(request: MessageRequest) -> Dict[str, Any]:
    from nexus_os.nexusclaw.messaging import NEXUSCLAWMessagingHub
    hub = NEXUSCLAWMessagingHub()
    connector = hub.get_connector(request.platform)

    if not connector:
        return {
            "success": False,
            "error": f"Platform {request.platform} not available",
            "dry_run": True,
        }

    if request.dry_run:
        return {
            "success": True,
            "dry_run": True,
            "platform": request.platform,
            "target": request.target,
            "text_preview": request.text[:100] + "..." if len(request.text) > 100 else request.text,
        }

    if request.platform == "telegram":
        result = await connector.send_message(chat_id=request.target, text=request.text)
    elif request.platform == "slack":
        result = await connector.send_message(channel=request.target, text=request.text)
    elif request.platform == "discord":
        result = await connector.send_message(channel_id=request.target, content=request.text)
    else:
        result = None

    if result:
        return result.to_dict()
    return {"success": False, "error": "Unknown platform"}


@control_app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    conn_id = await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            if message.get("type") == "subscribe":
                await manager.send_personal(
                    conn_id,
                    {"type": "subscribed", "connection_id": conn_id}
                )
    except WebSocketDisconnect:
        manager.disconnect(conn_id)


def run_control_ui(host: str = "127.0.0.1", port: int = 18789):
    import uvicorn
    uvicorn.run(control_app, host=host, port=port)
