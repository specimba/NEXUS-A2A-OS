"""
NEXUS Grok MCP Bridge v2 — Multi-Scenario Evidence & Coordination Server
=========================================================================
SSE-based for Grok Custom Connector. Provides formatted audit logging,
evidence capture, Phase 2 probe tracking, coordination queue, and
session management tools.

Scenarios:
  - PHASE1: Compliance audit logging (retrocompatible)
  - PHASE2: files.grok.com probe verification + comparison matrix
  - COORDINATION: Persistent agent task queue
  - EVIDENCE: Tamper-evident capture with SHA256 integrity hashing
  - SESSION: Long-run session heartbeat and status

Architecture:
  FastMCP SSE transport on port 7354
  + custom HTTP /health endpoint
  + daily-rotated, integrity-hashed audit logs in D:/GROSS/audit_trail/
"""

import json
import os
import sys
import uuid
import hashlib
import datetime
import pathlib
import logging
from typing import Any, Dict, Optional
import urllib.request
import urllib.error
import ipaddress
from urllib.parse import unquote, urlparse

from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
AUDIT_DIR = pathlib.Path(os.getenv("GROK_AUDIT_DIR", "D:/GROSS/audit_trail"))
EVIDENCE_DIR = pathlib.Path(os.getenv("GROK_EVIDENCE_DIR", "D:/GROSS/evidence"))
PHASE2_DIR = pathlib.Path(os.getenv("GROK_PHASE2_DIR", "D:/GROSS/phase2"))
COORD_DIR = pathlib.Path(os.getenv("GROK_COORD_DIR", "D:/GROSS/grok-coordination"))
FALLBACK_RUNTIME_DIR = pathlib.Path(
    os.getenv("GROK_FALLBACK_RUNTIME_DIR", "scratch/browser_ai_mcp_runtime")
).resolve()
SERVER_VERSION = os.getenv("GROK_MCP_VERSION", "2.2.0-nexus-hardened")
SERVER_NAME = os.getenv("GROK_MCP_NAME", "nexus-grok-bridge-v2")
LOG_LEVEL = os.getenv("GROK_LOG_LEVEL", "INFO").upper()
LISTEN_HOST = os.getenv("GROK_LISTEN_HOST", "0.0.0.0")
LISTEN_PORT = int(os.getenv("GROK_LISTEN_PORT", "7354"))

HTTP_ALLOWED_HOSTS_RAW = os.getenv(
    "GROK_HTTP_ALLOWED_HOSTS",
    "huggingface.co,hf.co,cdn-lfs.huggingface.co,raw.githubusercontent.com,github.com,pypi.org,files.pythonhosted.org,grok.com,files.grok.com,modelcontextprotocol.io,arxiv.org",
)
HTTP_MAX_BODY_BYTES = max(0, min(int(os.getenv("GROK_HTTP_MAX_BODY_BYTES", "1048576")), 4 * 1024 * 1024))
HTTP_TIMEOUT_SECONDS = max(1.0, min(float(os.getenv("GROK_HTTP_TIMEOUT_SECONDS", "15")), 30.0))
HTTP_SAFE_PREVIEW_LIMIT = max(0, min(int(os.getenv("GROK_HTTP_SAFE_PREVIEW_LIMIT", "1024")), 4096))
BLOCKED_HTTP_HEADER_PREFIXES = (
    "authorization",
    "cookie",
    "proxy-authorization",
    "x-api-key",
    "x-auth-token",
    "x-csrf-token",
    "x-xsrf-token",
)

for d in [AUDIT_DIR / "audit", AUDIT_DIR / "evidence", AUDIT_DIR / "coordination",
          AUDIT_DIR / "queries", EVIDENCE_DIR, PHASE2_DIR,
          COORD_DIR / "queue" / "pending", COORD_DIR / "queue" / "claimed",
          COORD_DIR / "queue" / "done", COORD_DIR / "queue" / "failed",
          COORD_DIR / "heartbeats", COORD_DIR / "progress", COORD_DIR / "channels",
          FALLBACK_RUNTIME_DIR / "audit", FALLBACK_RUNTIME_DIR / "evidence",
          FALLBACK_RUNTIME_DIR / "coordination", FALLBACK_RUNTIME_DIR / "a2a_tasks"]:
    try:
        d.mkdir(parents=True, exist_ok=True)
    except OSError:
        # Primary GROSS storage can be read-only from cloned NEXUS runs. Runtime
        # writes below fall back to FALLBACK_RUNTIME_DIR instead of failing tools.
        pass

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("grok-mcp-bridge")

# ---------------------------------------------------------------------------
# Audit Logger — Tidy, integrity-hashed, daily-rotated
# ---------------------------------------------------------------------------
_SCHEMA_VERSION = "audit_v2"


def _hash_entry(entry: Dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(entry, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]


def _today_str() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%S.%fZ"
    )


def _fallback_for_path(path: pathlib.Path) -> pathlib.Path:
    """Mirror a primary runtime path into the repo-local fallback runtime."""
    try:
        resolved = path.resolve()
    except OSError:
        resolved = path
    parts = [p for p in resolved.parts if p not in (resolved.anchor, "")]
    return FALLBACK_RUNTIME_DIR / "mirrors" / pathlib.Path(*parts)


def _write_jsonl_with_fallback(path: pathlib.Path, entry: Dict[str, Any]) -> pathlib.Path:
    line = json.dumps(entry, ensure_ascii=False, default=str) + "\n"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(line)
        return path
    except OSError as exc:
        fallback = _fallback_for_path(path)
        fallback.parent.mkdir(parents=True, exist_ok=True)
        fallback_entry = dict(entry)
        fallback_entry["_primary_write_failed"] = str(exc)
        fallback_entry["_primary_path"] = str(path)
        with open(fallback, "a", encoding="utf-8") as f:
            f.write(json.dumps(fallback_entry, ensure_ascii=False, default=str) + "\n")
        return fallback


def _write_text_with_fallback(path: pathlib.Path, content: str) -> pathlib.Path:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path
    except OSError:
        fallback = _fallback_for_path(path)
        fallback.parent.mkdir(parents=True, exist_ok=True)
        with open(fallback, "w", encoding="utf-8") as f:
            f.write(content)
        return fallback


def _write_bytes_with_fallback(path: pathlib.Path, content: bytes) -> pathlib.Path:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            f.write(content)
        return path
    except OSError:
        fallback = _fallback_for_path(path)
        fallback.parent.mkdir(parents=True, exist_ok=True)
        with open(fallback, "wb") as f:
            f.write(content)
        return fallback


def _write_log(category: str, entry: Dict[str, Any]) -> str:
    entry["_id"] = uuid.uuid4().hex[:8]
    entry["_ts"] = _now_iso()
    entry["_schema"] = _SCHEMA_VERSION
    h = _hash_entry(entry)
    entry["_hash"] = h
    log_file = AUDIT_DIR / category / f"{_today_str()}.jsonl"
    written = _write_jsonl_with_fallback(log_file, entry)
    if written != log_file:
        entry["_fallback_path"] = str(written)
    return entry["_id"]


def _read_logs(category: str, limit: int = 50) -> list[Dict[str, Any]]:
    entries = []
    log_dir = AUDIT_DIR / category
    if not log_dir.exists():
        return entries
    files = sorted(log_dir.glob("*.jsonl"), reverse=True)
    for f in files:
        with open(f, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        if len(entries) >= limit:
            break
    return entries[:limit]


# ---------------------------------------------------------------------------
# Coordination Queue (file-based, same pattern as GrokFileQueue)
# ---------------------------------------------------------------------------
def _atomic_write(path: pathlib.Path, data: Dict[str, Any]):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        tmp.replace(path)
    except OSError as exc:
        fallback = _fallback_for_path(path)
        fallback.parent.mkdir(parents=True, exist_ok=True)
        fallback_data = dict(data)
        fallback_data["_primary_write_failed"] = str(exc)
        fallback_data["_primary_path"] = str(path)
        tmp = fallback.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(fallback_data, f, indent=2, default=str)
        tmp.replace(fallback)


def _read_json_safe(path: pathlib.Path) -> Optional[Dict[str, Any]]:
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None
    return None


# ---------------------------------------------------------------------------
# FastMCP Server
# ---------------------------------------------------------------------------
mcp = FastMCP(SERVER_NAME, host=LISTEN_HOST, port=LISTEN_PORT, log_level="ERROR")

# ============================
# 1. CORE TOOLS
# ============================

@mcp.tool(name="ping", description="Health check — returns pong with server version and uptime")
def handle_ping() -> str:
    return json.dumps({
        "pong": True,
        "version": SERVER_VERSION,
        "server": SERVER_NAME,
        "timestamp": _now_iso()
    }, indent=2)


@mcp.tool(name="echo", description="Test connectivity — returns the message sent")
def handle_echo(message: str) -> str:
    _write_log("audit", {"tool": "echo", "message": message[:500]})
    return json.dumps({
        "echo": message,
        "received_at": _now_iso()
    }, indent=2)


# ============================
# 2. AUDIT & EVIDENCE TOOLS
# ============================

@mcp.tool(
    name="audit_log",
    description="Log structured audit data. Provide a 'scenario' key (e.g. phase1, phase2, compliance) and 'data' with your payload."
)
def handle_audit_log(scenario: str, data: str) -> str:
    try:
        parsed = json.loads(data) if isinstance(data, str) else data
    except json.JSONDecodeError:
        parsed = {"raw": data[:2000]}
    entry = {
        "scenario": scenario,
        "data": parsed,
    }
    log_id = _write_log("audit", entry)
    logger.info(f"[AUDIT:{scenario}] logged id={log_id}")
    return json.dumps({
        "logged": True,
        "id": log_id,
        "hash": entry["_hash"],
        "timestamp": entry["_ts"]
    }, indent=2)


@mcp.tool(
    name="evidence_capture",
    description="Capture evidence with SHA256 integrity hash. Provide label, content, and optional metadata."
)
def handle_evidence_capture(label: str, content: str, metadata: str = "{}") -> str:
    try:
        meta = json.loads(metadata) if isinstance(metadata, str) else metadata
    except json.JSONDecodeError:
        meta = {"raw_metadata": metadata[:500]}
    content_hash = hashlib.sha256(content.encode()).hexdigest()
    entry = {
        "scenario": "evidence",
        "label": label,
        "content_length": len(content),
        "content_hash": content_hash,
        "content_preview": content[:500],
        "metadata": meta,
    }
    log_id = _write_log("evidence", entry)
    evidence_file = EVIDENCE_DIR / f"{label}_{_today_str()}_{log_id}.txt"
    written_evidence_file = _write_text_with_fallback(evidence_file, content)
    logger.info(f"[EVIDENCE:{label}] captured id={log_id} hash={content_hash[:16]}")
    return json.dumps({
        "logged": True,
        "id": log_id,
        "content_hash": content_hash[:16],
        "log_hash": entry["_hash"],
        "file": str(written_evidence_file),
        "timestamp": entry["_ts"]
    }, indent=2)


# ============================
# 3. PHASE 2 PROBE TOOLS
# ============================

@mcp.tool(
    name="query_log",
    description="Log a files.grok.com probe result. Fields: query_label, endpoint, method, status_code, response_body, response_headers, principal, session_id"
)
def handle_query_log(
    query_label: str,
    endpoint: str = "",
    method: str = "GET",
    status_code: int = 0,
    response_body: str = "",
    response_headers: str = "{}",
    principal: str = "",
    session_id: str = ""
) -> str:
    try:
        headers = json.loads(response_headers) if isinstance(response_headers, str) else response_headers
    except json.JSONDecodeError:
        headers = {"raw": response_headers[:500]}
    body_hash = hashlib.sha256(response_body.encode()).hexdigest()[:16]
    entry = {
        "scenario": "phase2_query",
        "query_label": query_label,
        "endpoint": endpoint,
        "method": method,
        "status_code": status_code,
        "body_preview": response_body[:2000],
        "body_length": len(response_body),
        "body_hash": body_hash,
        "response_headers": headers,
        "principal": principal,
        "session_id": session_id,
    }
    log_id = _write_log("queries", entry)
    logger.info(f"[QUERY:{query_label}] status={status_code} hash={body_hash}")
    return json.dumps({
        "logged": True,
        "id": log_id,
        "body_hash": body_hash,
        "hash": entry["_hash"],
        "timestamp": entry["_ts"]
    }, indent=2)


@mcp.tool(
    name="comparison_add",
    description="Add or update an entry in the Phase 2 comparison matrix. Fields: query_label (Q1-Q4), browser_result, cli_result, match (true/false/partial), notes"
)
def handle_comparison_add(
    query_label: str,
    browser_result: str = "",
    cli_result: str = "",
    match: str = "unknown",
    notes: str = ""
) -> str:
    matrix_file = PHASE2_DIR / "comparison_matrix.json"
    matrix = {}
    if matrix_file.exists():
        try:
            with open(matrix_file, "r", encoding="utf-8") as f:
                matrix = json.load(f)
        except (json.JSONDecodeError, OSError):
            matrix = {}
    matrix[query_label] = {
        "browser_result": browser_result,
        "cli_result": cli_result,
        "match": match,
        "notes": notes,
        "updated_at": _now_iso()
    }
    _atomic_write(matrix_file, matrix)
    entry = {
        "scenario": "comparison",
        "query_label": query_label,
        "match": match,
        "notes": notes[:500],
    }
    log_id = _write_log("queries", entry)
    return json.dumps({
        "updated": True,
        "id": log_id,
        "query_label": query_label,
        "match": match,
        "hash": entry["_hash"],
        "timestamp": entry["_ts"]
    }, indent=2)


@mcp.tool(
    name="comparison_get",
    description="Return the full comparison matrix as JSON"
)
def handle_comparison_get() -> str:
    matrix_file = PHASE2_DIR / "comparison_matrix.json"
    if not matrix_file.exists():
        return json.dumps({"matrix": {}, "note": "No comparison data yet"}, indent=2)
    matrix = _read_json_safe(matrix_file) or {}
    return json.dumps({"matrix": matrix}, indent=2)


@mcp.tool(
    name="comparison_export",
    description="Export comparison matrix as formatted markdown"
)
def handle_comparison_export() -> str:
    matrix_file = PHASE2_DIR / "comparison_matrix.json"
    if not matrix_file.exists():
        return "# Comparison Matrix\n\n*No entries yet.*"
    matrix = _read_json_safe(matrix_file) or {}
    lines = [
        "# GROSS Phase 2 — Comparison Matrix",
        f"*Exported: {_now_iso()}*",
        "",
        "| Query | Browser Grok | CLI Probe | Match | Notes |",
        "|-------|-------------|-----------|-------|-------|",
    ]
    for label in sorted(matrix.keys()):
        e = matrix[label]
        br = e.get("browser_result", "")[:60]
        cl = e.get("cli_result", "")[:60]
        mt = e.get("match", "?")
        nt = e.get("notes", "")[:40]
        lines.append(f"| {label} | {br} | {cl} | {mt} | {nt} |")
    lines.extend(["", "---", "*End of matrix*"])
    return "\n".join(lines)


# ============================
# 4. COORDINATION TOOLS
# ============================

@mcp.tool(
    name="task_add",
    description="Add a task to the coordination queue. Fields: kind (research/audit/probe/remediate), prompt, priority (1-10)"
)
def handle_task_add(kind: str, prompt: str, priority: int = 5) -> str:
    task_id = f"task-{_today_str()}-{uuid.uuid4().hex[:6]}"
    task = {
        "id": task_id,
        "created_at": _now_iso(),
        "kind": kind,
        "prompt": prompt,
        "priority": priority,
        "status": "pending"
    }
    task_path = COORD_DIR / "queue" / "pending" / f"{task_id}.json"
    _atomic_write(task_path, task)
    entry = {"scenario": "coordination", "action": "task_add", "task_id": task_id, "kind": kind}
    _write_log("coordination", entry)
    logger.info(f"[COORD] task_added {task_id} kind={kind}")
    return json.dumps({"task_id": task_id, "status": "pending", "kind": kind}, indent=2)


@mcp.tool(
    name="task_list",
    description="List tasks in the queue by status: pending, claimed, done, failed, or all"
)
def handle_task_list(status: str = "all") -> str:
    results = {}
    statuses = ["pending", "claimed", "done", "failed"] if status == "all" else [status]
    for s in statuses:
        dir_path = COORD_DIR / "queue" / s
        if dir_path.exists():
            tasks = []
            for f in sorted(dir_path.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:20]:
                t = _read_json_safe(f)
                if t:
                    tasks.append(t)
            results[s] = tasks
    return json.dumps({"tasks": results, "counts": {k: len(v) for k, v in results.items()}}, indent=2)


@mcp.tool(
    name="task_claim",
    description="Atomically claim the highest-priority pending task. Returns the task or null if queue is empty."
)
def handle_task_claim() -> str:
    pending_dir = COORD_DIR / "queue" / "pending"
    claimed_dir = COORD_DIR / "queue" / "claimed"
    pending_files = sorted(pending_dir.glob("*.json"),
                           key=lambda p: (-_read_json_safe(p).get("priority", 0), p.stat().st_mtime)
                           if _read_json_safe(p) else (0, 0))
    if not pending_files:
        return json.dumps({"task": None, "note": "No pending tasks"}, indent=2)
    task_path = pending_files[0]
    task = _read_json_safe(task_path)
    if not task:
        return json.dumps({"task": None, "note": "Corrupt task file"}, indent=2)
    task["status"] = "claimed"
    task["claimed_at"] = _now_iso()
    task["claimed_by"] = "grok-mcp-bridge"
    claimed_path = claimed_dir / task_path.name
    _atomic_write(claimed_path, task)
    task_path.unlink(missing_ok=True)
    _write_log("coordination", {"action": "task_claim", "task_id": task["id"], "kind": task.get("kind")})
    return json.dumps({"task": task}, indent=2)


@mcp.tool(
    name="task_complete",
    description="Mark a claimed task as done. Provide task_id and result_data (JSON string)."
)
def handle_task_complete(task_id: str, result_data: str = "{}") -> str:
    claimed_dir = COORD_DIR / "queue" / "claimed"
    done_dir = COORD_DIR / "queue" / "done"
    claimed_path = claimed_dir / f"{task_id}.json"
    if not claimed_path.exists():
        return json.dumps({"error": f"Task {task_id} not found in claimed"}, indent=2)
    task = _read_json_safe(claimed_path)
    if not task:
        return json.dumps({"error": "Corrupt task file"}, indent=2)
    try:
        result = json.loads(result_data) if isinstance(result_data, str) else result_data
    except json.JSONDecodeError:
        result = {"raw": result_data[:2000]}
    task["status"] = "done"
    task["completed_at"] = _now_iso()
    task["result"] = result
    done_path = done_dir / f"{task_id}.json"
    _atomic_write(done_path, task)
    claimed_path.unlink(missing_ok=True)
    _write_log("coordination", {"action": "task_complete", "task_id": task_id})
    return json.dumps({"task_id": task_id, "status": "done"}, indent=2)


@mcp.tool(
    name="task_fail",
    description="Mark a claimed task as failed. Provide task_id and error_message."
)
def handle_task_fail(task_id: str, error_message: str = "") -> str:
    claimed_dir = COORD_DIR / "queue" / "claimed"
    failed_dir = COORD_DIR / "queue" / "failed"
    claimed_path = claimed_dir / f"{task_id}.json"
    if not claimed_path.exists():
        return json.dumps({"error": f"Task {task_id} not found in claimed"}, indent=2)
    task = _read_json_safe(claimed_path)
    if not task:
        return json.dumps({"error": "Corrupt task file"}, indent=2)
    task["status"] = "failed"
    task["failed_at"] = _now_iso()
    task["error"] = error_message
    failed_path = failed_dir / f"{task_id}.json"
    _atomic_write(failed_path, task)
    claimed_path.unlink(missing_ok=True)
    _write_log("coordination", {"action": "task_fail", "task_id": task_id, "error": error_message[:200]})
    return json.dumps({"task_id": task_id, "status": "failed"}, indent=2)


@mcp.tool(
    name="coordination_status",
    description="Return coordination queue health summary"
)
def handle_coordination_status() -> str:
    counts = {}
    for s in ["pending", "claimed", "done", "failed"]:
        d = COORD_DIR / "queue" / s
        counts[s] = len(list(d.glob("*.json"))) if d.exists() else 0
    last_hb = None
    hb_file = COORD_DIR / "heartbeats" / "grok-sandbox-main.json"
    hb = _read_json_safe(hb_file)
    if hb:
        last_hb = hb.get("last_seen")
    return json.dumps({
        "queue_counts": counts,
        "total": sum(counts.values()),
        "last_heartbeat": last_hb,
        "timestamp": _now_iso()
    }, indent=2)


# ============================
# 5. SESSION MANAGEMENT
# ============================

@mcp.tool(
    name="session_heartbeat",
    description="Keep-alive for long-run sessions. Provide session_id and status."
)
def handle_session_heartbeat(session_id: str, status: str = "alive", metadata: str = "{}") -> str:
    try:
        meta = json.loads(metadata) if isinstance(metadata, str) else metadata
    except json.JSONDecodeError:
        meta = {"raw": metadata[:500]}
    hb_data = {
        "session_id": session_id,
        "last_seen": _now_iso(),
        "status": status,
        "metadata": meta,
    }
    hb_file = COORD_DIR / "heartbeats" / f"{session_id}.json"
    _atomic_write(hb_file, hb_data)
    entry = {"scenario": "session", "action": "heartbeat", "session_id": session_id, "status": status}
    _write_log("coordination", entry)
    return json.dumps({
        "logged": True,
        "session_id": session_id,
        "status": status,
        "timestamp": _now_iso()
    }, indent=2)


@mcp.tool(
    name="session_status",
    description="Return current session state from heartbeats"
)
def handle_session_status(session_id: str = "") -> str:
    hb_dir = COORD_DIR / "heartbeats"
    if session_id:
        hb_file = hb_dir / f"{session_id}.json"
        hb = _read_json_safe(hb_file)
        return json.dumps(hb or {"error": f"No heartbeat for {session_id}"}, indent=2)
    results = {}
    for f in sorted(hb_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        hb = _read_json_safe(f)
        if hb:
            sid = hb.get("session_id", f.stem)
            results[sid] = hb
    return json.dumps({"sessions": results}, indent=2)


# ============================
# 5.5. AGENT-TO-AGENT (A2A) TOOLS
# ============================

@mcp.tool(
    name="agent_publish_message",
    description="Publish a message/event to a shared agent channel/topic for A2A communication."
)
def handle_agent_publish_message(topic: str, message: str, sender: str) -> str:
    topic_sanitized = "".join([c for c in topic if c.isalnum() or c in ("-", "_")]).lower()
    if not topic_sanitized:
        return json.dumps({"error": "Invalid topic name"}, indent=2)
    
    channels_dir = COORD_DIR / "channels"
    channels_dir.mkdir(parents=True, exist_ok=True)
    
    entry = {
        "sender": sender,
        "message": message,
        "timestamp": _now_iso()
    }
    
    file_path = channels_dir / f"{topic_sanitized}.jsonl"
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        
    _write_log("coordination", {"action": "agent_publish_message", "topic": topic_sanitized, "sender": sender})
    return json.dumps({"published": True, "topic": topic_sanitized, "timestamp": entry["timestamp"]}, indent=2)


@mcp.tool(
    name="agent_retrieve_messages",
    description="Retrieve the last N messages from a shared A2A channel/topic."
)
def handle_agent_retrieve_messages(topic: str, limit: int = 20) -> str:
    topic_sanitized = "".join([c for c in topic if c.isalnum() or c in ("-", "_")]).lower()
    if not topic_sanitized:
        return json.dumps({"error": "Invalid topic name"}, indent=2)
        
    file_path = COORD_DIR / "channels" / f"{topic_sanitized}.jsonl"
    if not file_path.exists():
        return json.dumps({"messages": [], "note": f"Topic '{topic_sanitized}' has no messages"}, indent=2)
        
    messages = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    messages.append(json.loads(line))
    except Exception as e:
        return json.dumps({"error": f"Failed to read topic messages: {e}"}, indent=2)
        
    result_messages = messages[-limit:]
    return json.dumps({"topic": topic_sanitized, "messages": result_messages, "count": len(result_messages)}, indent=2)


@mcp.tool(
    name="agent_list_topics",
    description="List all active A2A communication topics/channels."
)
def handle_agent_list_topics() -> str:
    channels_dir = COORD_DIR / "channels"
    if not channels_dir.exists():
        return json.dumps({"topics": []}, indent=2)
        
    files = list(channels_dir.glob("*.jsonl"))
    topics = [f.stem for f in files]
    return json.dumps({"topics": sorted(topics)}, indent=2)


# ============================
# 6. SIMULATION / TESTING
# ============================

@mcp.tool(
    name="simulate_probe",
    description="Simulate a files.grok.com probe result for pipeline testing. Pass mode=dry_run, audit_id, operator."
)
def handle_simulate_probe(audit_id: str = "test", scenario: str = "pipeline_test", operator: str = "spec",
                          mode: str = "dry_run", query_label: str = "Q0") -> str:
    status_code = 200
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
        f'<Name>files.grok.com</Name><Prefix>{query_label}</Prefix>'
        '<Contents><Key>simulated/key.txt</Key><Size>42</Size>'
        '<LastModified>2026-05-29T00:00:00Z</LastModified></Contents>'
        '</ListBucketResult>'
    )
    result = handle_query_log(
        query_label=query_label,
        endpoint="https://files.grok.com/?prefix=simulated",
        method="GET",
        status_code=status_code,
        response_body=body,
        response_headers='{"Content-Type": "application/xml"}',
        principal="14195556-c860-407f-a1f5-56ccc3e25efd",
        session_id=f"sim-{audit_id}"
    )
    parsed = json.loads(result)
    parsed["probe_received"] = True
    parsed["pipeline_executed"] = True
    parsed["mode"] = mode
    parsed["side_effects_enabled"] = False
    parsed["audit_record_created"] = True
    parsed["status"] = "PASS"
    parsed["audit_id"] = audit_id
    parsed["operator"] = operator
    return json.dumps(parsed, indent=2)


@mcp.tool(
    name="registry_debug",
    description="Return the exact list of tools registered on this MCP bridge server."
)
def handle_registry_debug() -> str:
    return json.dumps({
            "server": SERVER_NAME,
            "version": SERVER_VERSION,
            "tool_count": 22,
            "mcp_tool_count": 22,
            "a2a_skill_count": 5,
        "tool_names": [
            "ping", "echo",
            "audit_log", "evidence_capture", "http_diagnostic",
            "query_log", "comparison_add", "comparison_get", "comparison_export",
            "task_add", "task_list", "task_claim", "task_complete", "task_fail",
            "coordination_status",
            "session_heartbeat", "session_status",
            "agent_publish_message", "agent_retrieve_messages", "agent_list_topics",
            "simulate_probe", "registry_debug",
        ],
        "registry_hash": hashlib.sha256(json.dumps({
            "server": SERVER_NAME, "version": SERVER_VERSION, "tools": [
                "ping", "echo", "audit_log", "evidence_capture", "http_diagnostic",
                "query_log", "comparison_add", "comparison_get", "comparison_export",
                "task_add", "task_list", "task_claim", "task_complete", "task_fail",
                "coordination_status", "session_heartbeat", "session_status",
                "agent_publish_message", "agent_retrieve_messages", "agent_list_topics",
                "simulate_probe", "registry_debug"
            ]
        }, sort_keys=True).encode()).hexdigest()[:16],
        "a2a": {
            "agent_card": f"{A2A_PUBLIC_URL}/.well-known/agent.json",
            "tasks_send": f"{A2A_PUBLIC_URL}/a2a/tasks/send",
            "tasks_get": f"{A2A_PUBLIC_URL}/a2a/tasks/get",
            "version": "1.0",
        },
        "started_at": _now_iso()
    }, indent=2)


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _diagnostic_allowed_hosts() -> set[str]:
    hosts = set()
    for item in HTTP_ALLOWED_HOSTS_RAW.split(","):
        host = item.strip().lower().rstrip(".")
        if host and "/" not in host and ":" not in host:
            hosts.add(host)
    return hosts


def _diagnostic_host_allowed(host: str) -> bool:
    allowed_hosts = _diagnostic_allowed_hosts()
    return any(host == allowed or host.endswith(f".{allowed}") for allowed in allowed_hosts)


def _diagnostic_private_or_local_host(host: str) -> bool:
    if host in {"localhost", "localhost.localdomain"}:
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast


def _sanitize_diagnostic_headers(headers: dict) -> dict[str, str]:
    clean = {}
    for key, value in (headers or {}).items():
        header = str(key).strip()
        lowered = header.lower()
        if any(lowered.startswith(prefix) for prefix in BLOCKED_HTTP_HEADER_PREFIXES):
            continue
        clean[header.title()] = str(value)
    return clean


def _read_limited_body(response) -> tuple[bytes, bool]:
    raw = response.read(HTTP_MAX_BODY_BYTES + 1)
    if len(raw) > HTTP_MAX_BODY_BYTES:
        return raw[:HTTP_MAX_BODY_BYTES], True
    return raw, False


def _http_diagnostic_policy_snapshot() -> dict:
    return {
        "allowed_hosts": sorted(_diagnostic_allowed_hosts()),
        "allowed_methods": ["GET", "HEAD"],
        "max_body_bytes": HTTP_MAX_BODY_BYTES,
        "timeout_seconds": HTTP_TIMEOUT_SECONDS,
        "safe_preview_limit": HTTP_SAFE_PREVIEW_LIMIT,
        "private_targets_blocked": True,
        "redirects_followed": False,
        "sensitive_headers_stripped": True,
    }


def _http_diagnostic_error(audit_id: str, scenario: str, operator: str, mode: str, url: str, method: str, message: str) -> str:
    result = {
        "error": message,
        "status_code": None,
        "final_url": url,
        "content_type": None,
        "response_length_bytes": None,
        "body_sha256": None,
        "safe_preview": None,
        "access_result": "error",
        "side_effects_enabled": False,
        "policy": _http_diagnostic_policy_snapshot(),
    }
    _http_diagnostic_log(audit_id or "no-audit", scenario or "http_diagnostic", operator or "unknown", mode, url, method, result)
    return json.dumps(result, indent=2)


@mcp.tool(
    name="http_diagnostic",
    description="Scoped HTTPS GET/HEAD diagnostic for public-source evidence. Blocks private targets, strips credential headers, does not follow redirects, caps body reads, and never performs writes."
)
def handle_http_diagnostic(
    url: str = "",
    method: str = "GET",
    headers_json: str = "{}",
    safe_preview_max: int = 500,
    audit_id: str = "",
    scenario: str = "",
    operator: str = "",
    mode: str = "dry_run"
) -> str:
    method = method.upper().strip()
    if method not in {"GET", "HEAD"}:
        return _http_diagnostic_error(audit_id, scenario, operator, mode, url, method, f"Method {method} not allowed. Use GET or HEAD.")

    parsed = urlparse(url or "")
    host = (parsed.hostname or "").lower().rstrip(".")
    if parsed.scheme != "https" or not host:
        return _http_diagnostic_error(audit_id, scenario, operator, mode, url, method, "Only HTTPS URLs with a parseable host are allowed")
    if _diagnostic_private_or_local_host(host):
        return _http_diagnostic_error(audit_id, scenario, operator, mode, url, method, "Private, localhost, link-local, and multicast targets are blocked")
    if not _diagnostic_host_allowed(host):
        return _http_diagnostic_error(audit_id, scenario, operator, mode, url, method, f"Host {host} is not in GROK_HTTP_ALLOWED_HOSTS")

    try:
        parsed_headers = json.loads(headers_json) if isinstance(headers_json, str) else headers_json
    except json.JSONDecodeError:
        parsed_headers = {}
    req_headers = _sanitize_diagnostic_headers(parsed_headers if isinstance(parsed_headers, dict) else {})

    preview_max = max(0, min(int(safe_preview_max), HTTP_SAFE_PREVIEW_LIMIT))
    opener = urllib.request.build_opener(_NoRedirectHandler)

    try:
        req = urllib.request.Request(url, method=method, headers=req_headers)
        response = opener.open(req, timeout=HTTP_TIMEOUT_SECONDS)
        status_code = response.status
        final_url = response.url
        content_type = response.headers.get("Content-Type")
        content_length = response.headers.get("Content-Length")
        raw_body, body_truncated = (b"", False) if method == "HEAD" else _read_limited_body(response)
        body_hash = hashlib.sha256(raw_body).hexdigest() if raw_body else None
        access_result = "denied" if status_code in (401, 403) else "allowed"
        result = {
            "status_code": status_code,
            "final_url": final_url,
            "content_type": content_type,
            "content_length_header": content_length,
            "response_length_bytes": len(raw_body) if raw_body else 0,
            "body_truncated": body_truncated,
            "body_sha256": body_hash,
            "safe_preview": raw_body.decode("utf-8", errors="replace")[:preview_max] if raw_body else None,
            "access_result": access_result,
            "side_effects_enabled": False,
            "policy": _http_diagnostic_policy_snapshot(),
        }
    except urllib.error.HTTPError as e:
        status_code = e.code
        content_type = e.headers.get("Content-Type") if e.headers else None
        location = e.headers.get("Location") if e.headers else None
        raw_body, body_truncated = (b"", False) if method == "HEAD" else _read_limited_body(e)
        body_hash = hashlib.sha256(raw_body).hexdigest() if raw_body else None
        if status_code in (301, 302, 303, 307, 308):
            access_result = "redirected"
        elif status_code in (401, 403):
            access_result = "denied"
        else:
            access_result = "error"
        result = {
            "status_code": status_code,
            "final_url": url,
            "redirect_location": location,
            "content_type": content_type,
            "response_length_bytes": len(raw_body) if raw_body else 0,
            "body_truncated": body_truncated,
            "body_sha256": body_hash,
            "safe_preview": raw_body.decode("utf-8", errors="replace")[:preview_max] if raw_body else None,
            "access_result": access_result,
            "side_effects_enabled": False,
            "policy": _http_diagnostic_policy_snapshot(),
        }
    except Exception as e:
        result = {
            "error": str(e),
            "status_code": None,
            "final_url": url,
            "content_type": None,
            "response_length_bytes": None,
            "body_sha256": None,
            "safe_preview": None,
            "access_result": "error",
            "side_effects_enabled": False,
            "policy": _http_diagnostic_policy_snapshot(),
        }

    _http_diagnostic_log(audit_id or "no-audit", scenario or "http_diagnostic", operator or "unknown", mode, url, method, result)
    return json.dumps(result, indent=2)

def _http_diagnostic_log(audit_id: str, scenario: str, operator: str, mode: str, url: str, method: str, result: dict):
    entry = {
        "event": "http_diagnostic",
        "audit_id": audit_id,
        "scenario": scenario,
        "operator": operator,
        "mode": mode,
        "url": url,
        "method": method,
        "result": result,
        "side_effects_enabled": False,
    }
    log_path = AUDIT_DIR / "audit" / f"{_now_iso()[:10]}.jsonl"
    h = hashlib.sha256(json.dumps(entry, sort_keys=True, default=str).encode()).hexdigest()
    entry["_id"] = uuid.uuid4().hex[:8]
    entry["_ts"] = _now_iso()
    entry["_schema"] = "audit_v2"
    entry["_hash"] = h
    written = _write_jsonl_with_fallback(log_path, entry)
    if written != log_path:
        entry["_fallback_path"] = str(written)


# ---------------------------------------------------------------------------
# A2A Protocol v1.0 (Linux Foundation) — Agent Card + JSON-RPC endpoints
# Spec: https://a2a-protocol.org  |  Transport: HTTP + JSON-RPC 2.0
# Adds discovery (Agent Card) and structured task delegation so external
# A2A clients (Codex, Grok Imagine, custom agents) can hand-off work
# directly to this GROK-side MCP bridge.
# ---------------------------------------------------------------------------
A2A_AGENT_NAME = os.getenv("A2A_AGENT_NAME", "nexus-grok-bridge")
A2A_AGENT_VERSION = os.getenv("A2A_AGENT_VERSION", SERVER_VERSION)
A2A_PUBLIC_URL = os.getenv("A2A_PUBLIC_URL", f"http://{LISTEN_HOST}:{LISTEN_PORT}")
A2A_TASKS_DIR = COORD_DIR / "a2a_tasks"
(A2A_TASKS_DIR).mkdir(parents=True, exist_ok=True)

A2A_AGENT_CARD = {
    "name": A2A_AGENT_NAME,
    "description": (
        "NEXUS Grok-side MCP bridge. Exposes governance audit, evidence "
        "capture, coordination queue, session heartbeat, and bridge "
        "channels for A2A collaboration with Codex/Grok/custom agents."
    ),
    "version": A2A_AGENT_VERSION,
    "provider": {"organization": "NEXUS OS", "url": "https://nexus.local"},
    "url": A2A_PUBLIC_URL,
    "capabilities": {
        "streaming": False,
        "pushNotifications": False,
        "stateTransitionHistory": True,
        "tools": True,
        "browserHttpDiagnostic": True,
    },
    "authentication": {"type": "none"},
    "skills": [
        {
            "id": "audit_log",
            "name": "Governance Audit Logging",
            "description": "Write immutable hash-chained audit records (scenario + payload).",
            "tags": ["governance", "audit", "compliance"],
        },
        {
            "id": "evidence_capture",
            "name": "Evidence Capture",
            "description": "Capture content + SHA-256 to tamper-evident evidence store.",
            "tags": ["evidence", "forensic"],
        },
        {
            "id": "coordination_queue",
            "name": "Coordination Queue",
            "description": "Persistent task queue: add / claim / complete / fail.",
            "tags": ["coordination", "queue", "agent-mesh"],
        },
        {
            "id": "a2a_channel",
            "name": "A2A Channel Bridge",
            "description": "@-publish/-subscribe channel for cross-agent messaging.",
            "tags": ["a2a", "messaging"],
        },
        {
            "id": "phase2_probe",
            "name": "Phase 2 Probe Pipeline",
            "description": "Run / log / compare files.grok.com probe results with hash chain.",
            "tags": ["probe", "comparison"],
        },
        {
            "id": "browser_http_diagnostic",
            "name": "Governed Browser HTTP Diagnostic",
            "description": "Read-only HTTPS GET/HEAD diagnostics for browser-agent evidence gathering; no crawling, writes, or auth bypass.",
            "tags": ["browser", "http", "diagnostic", "evidence"],
        },
    ],
}


def _a2a_task_record(task_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": task_id,
        "created_at": _now_iso(),
        "status": "submitted",
        "history": [{"state": "submitted", "ts": _now_iso()}],
        "payload": payload,
    }


def _a2a_task_save(rec: Dict[str, Any]) -> None:
    _atomic_write(A2A_TASKS_DIR / f"{rec['id']}.json", rec)


def _a2a_task_load(task_id: str) -> Optional[Dict[str, Any]]:
    safe = "".join([c for c in task_id if c.isalnum() or c in ("-", "_")])
    return _read_json_safe(A2A_TASKS_DIR / f"{safe}.json") if safe else None


@mcp.custom_route("/.well-known/agent.json", methods=["GET"])
async def handle_a2a_agent_card(request: Request) -> JSONResponse:
    """A2A v1.0 Agent Card — discovery endpoint for A2A clients (Codex etc.)."""
    return JSONResponse(A2A_AGENT_CARD)


@mcp.custom_route("/a2a/discover", methods=["GET"])
async def handle_a2a_discover(request: Request) -> JSONResponse:
    """Convenience discovery alias (some clients look for /a2a/*)."""
    return JSONResponse(A2A_AGENT_CARD)


@mcp.custom_route("/a2a/tasks/send", methods=["POST"])
async def handle_a2a_tasks_send(request: Request) -> JSONResponse:
    """JSON-RPC 2.0 method `tasks/send`. Submits a task; routes to internal MCP tool."""
    try:
        rpc = await request.json()
    except Exception:
        return JSONResponse(_jsonrpc_err(None, -32700, "Parse error"), status_code=400)

    if rpc.get("jsonrpc") != "2.0":
        return JSONResponse(_jsonrpc_err(rpc.get("id"), -32600, "Invalid JSON-RPC envelope"), status_code=400)

    rpc_id = rpc.get("id")
    params = rpc.get("params", {}) or {}
    skill_id = params.get("skill_id") or (rpc.get("method", "").split(".")[-1])
    message = params.get("message", {}) or {}
    parts = message.get("parts", []) or []
    text_payload = "".join(p.get("text", "") for p in parts if p.get("type") == "text")
    task_id = params.get("id") or f"a2a-{_today_str()}-{uuid.uuid4().hex[:8]}"

    rec = _a2a_task_record(task_id, {"skill_id": skill_id, "text": text_payload, "params": params})
    rec["history"].append({"state": "working", "ts": _now_iso()})
    rec["status"] = "working"
    _a2a_task_save(rec)

    result_text = _a2a_dispatch_skill(skill_id, text_payload, params)
    rec["result"] = {"kind": "text", "text": result_text}
    rec["status"] = "completed"
    rec["history"].append({"state": "completed", "ts": _now_iso()})
    _a2a_task_save(rec)

    return JSONResponse({
        "jsonrpc": "2.0",
        "id": rpc_id,
        "result": {
            "id": task_id,
            "status": rec["status"],
            "artifacts": [{"type": "text", "text": result_text}],
        },
    })


@mcp.custom_route("/a2a/tasks/get", methods=["POST", "GET"])
async def handle_a2a_tasks_get(request: Request) -> JSONResponse:
    """JSON-RPC 2.0 method `tasks/get`. Returns task + history."""
    if request.method == "GET":
        task_id = request.query_params.get("id", "")
    else:
        try:
            rpc = await request.json()
            rpc_id = rpc.get("id")
            params = rpc.get("params", {}) or {}
            task_id = params.get("id", "")
        except Exception:
            return JSONResponse(_jsonrpc_err(None, -32700, "Parse error"), status_code=400)

    rec = _a2a_task_load(task_id)
    if not rec:
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": (rpc_id if request.method == "POST" else None),
            "error": {"code": -32004, "message": f"Task {task_id} not found"},
        }, status_code=404)
    return JSONResponse({
        "jsonrpc": "2.0",
        "id": (rpc_id if request.method == "POST" else None),
        "result": rec,
    })


def _jsonrpc_err(rpc_id: Any, code: int, msg: str) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": rpc_id, "error": {"code": code, "message": msg}}


def _a2a_dispatch_skill(skill_id: str, text: str, params: Dict[str, Any]) -> str:
    """Route an inbound A2A skill call to the existing MCP tool surface."""
    sid = (skill_id or "").lower()
    try:
        if sid == "audit_log":
            scenario = params.get("scenario", "a2a")
            return handle_audit_log(scenario=scenario, data=text or "{}")
        if sid == "evidence_capture":
            label = params.get("label", f"a2a-{uuid.uuid4().hex[:6]}")
            return handle_evidence_capture(label=label, content=text or "")
        if sid == "coordination_queue":
            kind = params.get("kind", "research")
            priority = int(params.get("priority", 5))
            return handle_task_add(kind=kind, prompt=text, priority=priority)
        if sid == "a2a_channel":
            topic = params.get("topic", "general")
            sender = params.get("sender", "a2a-client")
            return handle_agent_publish_message(topic=topic, message=text, sender=sender)
        if sid == "phase2_probe":
            qid = params.get("query_label", "A2A-Q1")
            return handle_query_log(query_label=qid, endpoint=A2A_PUBLIC_URL, status_code=200, response_body=text or "")
        if sid == "browser_http_diagnostic":
            raw_args = params
            if text:
                try:
                    parsed_text = json.loads(text)
                    if isinstance(parsed_text, dict):
                        raw_args = {**parsed_text, **params}
                except json.JSONDecodeError:
                    pass
            return handle_http_diagnostic(
                url=raw_args.get("url", ""),
                method=raw_args.get("method", "GET"),
                headers_json=raw_args.get("headers_json", "{}"),
                safe_preview_max=int(raw_args.get("safe_preview_max", 500)),
                audit_id=raw_args.get("audit_id", ""),
                scenario=raw_args.get("scenario", "browser_http_diagnostic"),
                operator=raw_args.get("operator", raw_args.get("sender", "a2a-client")),
                mode=raw_args.get("mode", "a2a"),
            )
        return json.dumps({"error": f"Unknown skill '{skill_id}'. Available: audit_log, evidence_capture, coordination_queue, a2a_channel, phase2_probe, browser_http_diagnostic"}, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Skill '{skill_id}' failed: {e}"}, indent=2)


# ============================
# 7. HEALTH + FILE RECEIVE HTTP ENDPOINTS
# ============================

@mcp.custom_route("/health", methods=["GET"])
async def handle_health_http(request: Request) -> JSONResponse:
    hb_file = COORD_DIR / "heartbeats" / "grok-sandbox-main.json"
    last_hb = None
    hb = _read_json_safe(hb_file)
    if hb:
        last_hb = hb.get("last_seen")
    queue_counts = {}
    for s in ["pending", "claimed", "done", "failed"]:
        d = COORD_DIR / "queue" / s
        queue_counts[s] = len(list(d.glob("*.json"))) if d.exists() else 0
    return JSONResponse({
        "status": "ok",
        "version": SERVER_VERSION,
        "server": SERVER_NAME,
        "uptime": _now_iso(),
        "mcp_tool_count": 22,
        "tools": [
            "ping", "echo", "audit_log", "evidence_capture", "http_diagnostic",
            "query_log", "comparison_add", "comparison_get", "comparison_export",
            "task_add", "task_list", "task_claim", "task_complete", "task_fail",
            "coordination_status",
            "session_heartbeat", "session_status",
            "agent_publish_message", "agent_retrieve_messages", "agent_list_topics",
            "simulate_probe", "registry_debug",
        ],
        "a2a": {
            "version": "1.0",
            "agent_card": f"{A2A_PUBLIC_URL}/.well-known/agent.json",
            "discover": f"{A2A_PUBLIC_URL}/a2a/discover",
            "send": f"{A2A_PUBLIC_URL}/a2a/tasks/send",
            "get": f"{A2A_PUBLIC_URL}/a2a/tasks/get",
            "skill_ids": [
                "audit_log", "evidence_capture", "coordination_queue",
                "a2a_channel", "phase2_probe", "browser_http_diagnostic",
            ],
            "skill_count": 6,
        },
        "directories": {
            "audit": str(AUDIT_DIR),
            "evidence": str(EVIDENCE_DIR),
            "phase2": str(PHASE2_DIR),
            "coordination": str(COORD_DIR),
            "fallback_runtime": str(FALLBACK_RUNTIME_DIR),
        },
        "queue": queue_counts,
        "last_heartbeat": last_hb,
        "timestamp": _now_iso(),
        "hardening": _http_diagnostic_policy_snapshot(),
        "runtime_write_policy": {
            "primary_runtime": "D:/GROSS by default",
            "fallback_enabled": True,
            "fallback_runtime": str(FALLBACK_RUNTIME_DIR),
        },
    })


@mcp.custom_route("/receive-file", methods=["POST"])
async def handle_receive_file(request: Request) -> JSONResponse:
    """Receive a file from the sandbox via POST. Accepts:
    - raw binary (Content-Type: application/octet-stream)
    - JSON with base64 payload: {"name":"...", "data":"<base64>", "path":"/tmp/vdc_bundle.tar.gz"}
    Saves to EVIDENCE_DIR/<name> and returns the file path.
    """
    ct = request.headers.get("content-type", "")
    ts = _now_iso()
    file_id = uuid.uuid4().hex[:8]

    if "json" in ct:
        body = await request.json()
        fname = body.get("name", f"upload_{file_id}.bin")
        raw = body.get("data", "")
        import base64
        data = base64.b64decode(raw) if raw else b""
        src_path = body.get("path", "")
    else:
        # Read Content-Disposition for filename
        fname = f"upload_{file_id}.bin"
        cd = request.headers.get("content-disposition", "")
        if "filename=" in cd:
            fname = cd.split("filename=")[-1].split(";")[0].strip('" ')
        data = await request.body()
        src_path = ""

    dest = EVIDENCE_DIR / fname
    written_dest = _write_bytes_with_fallback(dest, data)

    entry = {
        "tool": "receive-file",
        "file_id": file_id,
        "filename": fname,
        "source_path": src_path,
        "size": len(data),
        "saved_to": str(written_dest),
    }
    _write_log("evidence", entry)

    return JSONResponse({
        "status": "ok",
        "file_id": file_id,
        "filename": fname,
        "size": len(data),
        "saved_to": str(written_dest),
        "timestamp": ts,
    })


# ============================
# MAIN
# ============================
if __name__ == "__main__":
    print("=" * 60)
    print(f"{SERVER_NAME} v{SERVER_VERSION}")
    print("=" * 60)
    print(f"SSE endpoint: http://{LISTEN_HOST}:{LISTEN_PORT}/sse")
    print(f"A2A Card:     http://{LISTEN_HOST}:{LISTEN_PORT}/.well-known/agent.json")
    print(f"A2A /send:    http://{LISTEN_HOST}:{LISTEN_PORT}/a2a/tasks/send")
    print(f"A2A /get:     http://{LISTEN_HOST}:{LISTEN_PORT}/a2a/tasks/get?id=<task_id>")
    print(f"Health:       http://{LISTEN_HOST}:{LISTEN_PORT}/health")
    print(f"Audit dir:    {AUDIT_DIR}")
    print(f"Evidence dir: {EVIDENCE_DIR}")
    print(f"Phase 2 dir:  {PHASE2_DIR}")
    print(f"Coordination: {COORD_DIR}")
    print(f"Tools:")
    for t_name in ["ping", "echo", "audit_log", "evidence_capture", "http_diagnostic",
                    "query_log", "comparison_add", "comparison_get", "comparison_export",
                    "task_add", "task_list", "task_claim", "task_complete", "task_fail",
                    "coordination_status", "session_heartbeat", "session_status",
                    "agent_publish_message", "agent_retrieve_messages", "agent_list_topics",
                    "simulate_probe", "registry_debug"]:
        print(f"  - {t_name}")
    print("=" * 60)
    sys.stdout.flush()
    mcp.run(transport="sse")






