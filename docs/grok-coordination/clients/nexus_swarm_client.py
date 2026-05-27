#!/usr/bin/env python3
"""
NexusSwarmClient — drop-in replacement for the stub `SwarmClawClient` referenced
in Grok's `persistent_grok_agent.py`.

This client talks to the Zo-hosted Grok-Swarm coordinator (HTTPS, bearer-token
auth). It gives an ephemeral Grok sandbox a durable, external memory + task
queue + heartbeat layer so the agent can run across resets.

Hard guarantees:
- No model calls from this client (provider-agnostic).
- No reads/writes outside the HTTP boundary.
- Bearer token read from env (NEXUS_SWARM_TOKEN); never logged.
- Stdlib only — no pip dependencies.

Endpoints (all served by zo.space):
    GET  /api/grok-swarm?action=status
    POST /api/grok-swarm?action=next      body: {sandbox_id}
    POST /api/grok-swarm?action=add       body: {prompt, kind, priority, ...}
    POST /api/grok-swarm?action=report    body: {task_id, cycle, status, result}
    POST /api/grok-swarm?action=heartbeat body: {sandbox_id, status, note}

Usage in persistent_grok_agent.py:

    from nexus_swarm_client import NexusSwarmClient
    swarm = NexusSwarmClient()       # reads token + base URL from env
    swarm.heartbeat(status="alive")
    task = swarm.claim_next()        # returns dict or None
    if task:
        # ... do the work ...
        swarm.report_progress(task["id"], cycle=1, partial_result="...")
        swarm.report_done(task["id"], final_result="...")
"""

from __future__ import annotations

import json
import os
import socket
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional


class NexusSwarmError(RuntimeError):
    """Raised when the coordinator returns a non-2xx response."""


class NexusSwarmClient:
    """Thin HTTPS client for the Zo-hosted Grok-Swarm coordinator."""

    DEFAULT_BASE = "https://specimba.zo.space/api/grok-swarm"

    def __init__(
        self,
        base_url: Optional[str] = None,
        token: Optional[str] = None,
        sandbox_id: Optional[str] = None,
        timeout_seconds: float = 15.0,
    ):
        self.base_url = (base_url or os.environ.get("NEXUS_SWARM_URL") or self.DEFAULT_BASE).rstrip("/")
        self.token = token or os.environ.get("NEXUS_SWARM_TOKEN") or ""
        if not self.token:
            raise NexusSwarmError(
                "NEXUS_SWARM_TOKEN not set. Operator must set this secret in Zo "
                "Settings -> Advanced and share the token with the Grok sandbox env."
            )
        self.sandbox_id = sandbox_id or os.environ.get("NEXUS_SWARM_SANDBOX_ID") or f"grok-{socket.gethostname()[:32]}"
        self.timeout = timeout_seconds

    # ---------------- HTTP plumbing ----------------

    def _request(self, action: str, method: str = "GET", body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}?action={action}"
        data = None
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
            "X-Sandbox-Id": self.sandbox_id,
        }
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url=url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            try:
                detail = e.read().decode("utf-8", errors="replace")
            except Exception:
                detail = "<no body>"
            raise NexusSwarmError(f"HTTP {e.code} on {action}: {detail[:512]}")
        except urllib.error.URLError as e:
            raise NexusSwarmError(f"Network error on {action}: {e.reason}")

    # ---------------- Public surface ----------------

    def status(self) -> Dict[str, Any]:
        """Queue depths + last heartbeat across all sandboxes."""
        return self._request("status", method="GET")

    def heartbeat(self, status: str = "alive", note: str = "") -> Dict[str, Any]:
        """Ping the coordinator. Stale heartbeats (>10 min) are visible in status."""
        return self._request("heartbeat", method="POST", body={
            "sandbox_id": self.sandbox_id, "status": status, "note": note,
        })

    def claim_next(self) -> Optional[Dict[str, Any]]:
        """
        Atomically claim the next pending task. Returns the task dict or None
        if the queue is empty. The claim leases the task for 60 minutes; if you
        don't report progress within the lease, the task auto-requeues.
        """
        res = self._request("next", method="POST", body={"sandbox_id": self.sandbox_id})
        return res.get("task")

    def add_task(
        self,
        prompt: str,
        kind: str = "research",
        priority: int = 5,
        context_files: Optional[list] = None,
        max_cycles: int = 4,
        deadline_iso: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Add a new task to the pending queue. Normally done by the operator, not Grok."""
        return self._request("add", method="POST", body={
            "id": task_id, "prompt": prompt, "kind": kind, "priority": int(priority),
            "context_files": context_files or [], "max_cycles": int(max_cycles),
            "deadline_iso": deadline_iso,
        })

    def report_progress(self, task_id: str, cycle: int, partial_result: Any = None, notes: str = "") -> Dict[str, Any]:
        """Mid-run checkpoint. Extends the lease and prevents auto-requeue."""
        return self._request("report", method="POST", body={
            "task_id": task_id, "cycle": int(cycle), "status": "progress",
            "partial_result": partial_result, "notes": notes, "sandbox_id": self.sandbox_id,
        })

    def report_done(self, task_id: str, final_result: Any, cycles_used: int = 0) -> Dict[str, Any]:
        """Mark task complete; moves it from claimed/ to done/."""
        return self._request("report", method="POST", body={
            "task_id": task_id, "cycle": int(cycles_used), "status": "done",
            "final_result": final_result, "sandbox_id": self.sandbox_id,
        })

    def report_failed(self, task_id: str, reason: str, cycle: int = 0) -> Dict[str, Any]:
        """Mark task failed; moves it from claimed/ to failed/."""
        return self._request("report", method="POST", body={
            "task_id": task_id, "cycle": int(cycle), "status": "failed",
            "error": reason, "sandbox_id": self.sandbox_id,
        })


# ---------------- Minimal self-test (no network) ----------------

def _selftest() -> None:
    """Runs without hitting the coordinator; verifies surface + error messages."""
    os.environ.pop("NEXUS_SWARM_TOKEN", None)
    try:
        NexusSwarmClient()
    except NexusSwarmError as e:
        assert "NEXUS_SWARM_TOKEN not set" in str(e)
        print("  [OK] missing-token surfaces NexusSwarmError")

    os.environ["NEXUS_SWARM_TOKEN"] = "sandbox-test-token-not-real"
    c = NexusSwarmClient(base_url="https://example.invalid/api/grok-swarm")
    assert c.sandbox_id.startswith("grok-") or c.sandbox_id == os.environ.get("NEXUS_SWARM_SANDBOX_ID", "")
    print("  [OK] client constructs with token + derives sandbox_id")
    print("  [OK] all 7 public methods present:",
          all(hasattr(c, m) for m in [
              "status","heartbeat","claim_next","add_task",
              "report_progress","report_done","report_failed"]))


if __name__ == "__main__":
    print("NexusSwarmClient selftest")
    _selftest()
    print("OK")
