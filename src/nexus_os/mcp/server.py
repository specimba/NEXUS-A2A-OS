"""
NEXUS OS MCP Server — ARMED v2.0
==================================
Full MCP (Model Context Protocol) governance server over stdio transport.
9 tools: propose, approve, trust, quarantine, kill_switch, heartbeat,
         set_defcon, vault_status, list_proposals
2 resources: VAP chain log, vault status

Protocol: JSON-RPC 2.0 + MCP 2024-11-05 over stdio
"""

import sys, json, hashlib, math, uuid, os, sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

from nexus_os.governor.trust_kernel import TrustDecisionKind, TrustKernel

ARMED_DB = os.environ.get("NEXUS_MCP_DB", str(Path(__file__).parent / "nexus_mcp.db"))

BLOCKED_SKILLS = ["model.delete", "secret.expose", "fine_tune.auto", "system.wipe"]
REVIEW_KEYWORDS = ["delete", "expose", "override", "escalate", "root", "wipe"]
LANE_PARAMS = {
    "general": {"qmin": 0.1, "n0": 3, "Rcrit": 0.6, "bias": 0.0},
    "research": {"qmin": 0.3, "n0": 5, "Rcrit": 0.8, "bias": 0.1},
    "audit_sec": {"qmin": 0.7, "n0": 2, "Rcrit": 0.4, "bias": -0.1},
    "code_gen": {"qmin": 0.2, "n0": 4, "Rcrit": 0.7, "bias": 0.05},
    "data_ops": {"qmin": 0.5, "n0": 3, "Rcrit": 0.5, "bias": -0.05},
    "realtime": {"qmin": 0.3, "n0": 6, "Rcrit": 0.65, "bias": 0.15},
    "autonomous": {"qmin": 0.6, "n0": 8, "Rcrit": 0.3, "bias": -0.2},
}

def get_db(db_path: Optional[str] = None):
    db_target = db_path or os.environ.get("NEXUS_MCP_DB") or ARMED_DB
    conn = sqlite3.connect(db_target, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS vap_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT, type TEXT, data TEXT, hash TEXT, prev_hash TEXT
        )""")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS proposals (
            id TEXT PRIMARY KEY, skill TEXT, params TEXT, agent_id TEXT,
            provenance TEXT, timestamp TEXT, status TEXT, verdict TEXT,
            approved_by TEXT, approved_at TEXT
        )""")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS agents (
            id TEXT PRIMARY KEY, trust_score REAL DEFAULT 0.5,
            state TEXT DEFAULT 'active', kill_switch INTEGER DEFAULT 0,
            last_heartbeat TEXT, resource_quota INTEGER DEFAULT 100,
            resource_used INTEGER DEFAULT 0
        )""")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS defcon_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT, level INTEGER, reason TEXT, set_by TEXT
        )""")
    conn.commit()
    return conn

class NexusGovernanceMCP:
    def __init__(self, db_path=None):
        self.db_path = db_path or os.environ.get("NEXUS_MCP_DB") or ARMED_DB
        self.conn = get_db(self.db_path)
        self._init_defaults()
        self._defcon_level = self._load_defcon()
        self.trust_kernel = TrustKernel(db=self.conn)

    def _init_defaults(self):
        for aid in ["codex", "grok", "neo", "speci"]:
            self.conn.execute(
                "INSERT OR IGNORE INTO agents (id, trust_score, state) VALUES (?, ?, ?)",
                (aid, 0.5, "active"))
        self.conn.commit()

    def _load_defcon(self):
        row = self.conn.execute("SELECT level FROM defcon_log ORDER BY id DESC LIMIT 1").fetchone()
        return row["level"] if row else 5

    def _vap_hash(self, data: dict) -> str:
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()[:16]

    def _log_vap(self, event_type: str, data: dict):
        h = self._vap_hash(data)
        prev = self.conn.execute("SELECT hash FROM vap_log ORDER BY id DESC LIMIT 1").fetchone()
        prev_hash = prev["hash"] if prev else "0" * 16
        self.conn.execute(
            "INSERT INTO vap_log (ts, type, data, hash, prev_hash) VALUES (?, ?, ?, ?, ?)",
            (datetime.now(timezone.utc).isoformat(), event_type, json.dumps(data), h, prev_hash))
        self.conn.commit()
        return h

    def propose_skill(self, skill: str, params: dict, agent_id: str, provenance: str = "mcp") -> dict:
        pid = f"PROP-{hashlib.sha256((skill + str(datetime.now())).encode()).hexdigest()[:8]}"
        proposal = {"id": pid, "skill": skill, "params": params, "agent_id": agent_id,
                    "provenance": provenance, "timestamp": datetime.now(timezone.utc).isoformat()}
        if skill in BLOCKED_SKILLS:
            proposal.update({"status": "denied", "verdict": "HARD_BLOCK"})
        else:
            lane = params.get("lane", "orchestration") if isinstance(params, dict) else "orchestration"
            trust_decision = self.trust_kernel.evaluate(
                agent_id=agent_id,
                action="execute" if "." in skill else skill,
                lane=lane,
                context={"skill": skill, "side_effect": True},
            )
            proposal["trust"] = trust_decision.to_dict()
            if trust_decision.decision == TrustDecisionKind.DENY:
                proposal.update({"status": "denied", "verdict": "TRUST_DENY"})
            elif trust_decision.decision in {
                TrustDecisionKind.HOLD,
                TrustDecisionKind.ESCALATE,
                TrustDecisionKind.QUARANTINE,
            }:
                proposal.update({"status": "needs_review", "verdict": "TRUST_HOLD"})
            elif any(kw in skill for kw in REVIEW_KEYWORDS):
                proposal.update({"status": "needs_review", "verdict": "ARMED_REVIEW"})
                if self._defcon_level <= 2:
                    proposal["verdict"] = "HARD_BLOCK"
            else:
                proposal.update({"status": "approved", "verdict": "CLEARED"})
        self.conn.execute(
            "INSERT OR REPLACE INTO proposals (id, skill, params, agent_id, provenance, timestamp, status, verdict) VALUES (?,?,?,?,?,?,?,?)",
            (pid, skill, json.dumps(params), agent_id, provenance, proposal["timestamp"], proposal["status"], proposal["verdict"]))
        self.conn.commit()
        snapshot = self.trust_kernel.record_proposal_outcome(
            agent_id=agent_id,
            proposal_id=pid,
            status=proposal["status"],
            verdict=proposal["verdict"],
            skill=skill,
            lane=params.get("lane", "orchestration") if isinstance(params, dict) else "orchestration",
        )
        self._sync_agent_trust(agent_id, snapshot.trust)
        proposal["trust_snapshot"] = snapshot.to_dict()
        self._log_vap("propose", {"id": pid, "skill": skill, "status": proposal["status"]})
        return proposal

    def approve_proposal(self, pid: str, approver: str, decision: str) -> dict:
        p = self.conn.execute("SELECT * FROM proposals WHERE id=?", (pid,)).fetchone()
        if not p:
            return {"error": "not_found", "id": pid}
        new_status = "approved" if decision == "approve" else "denied"
        self.conn.execute("UPDATE proposals SET status=?, approved_by=?, approved_at=? WHERE id=?",
                          (new_status, approver, datetime.now(timezone.utc).isoformat(), pid))
        self.conn.commit()
        snapshot = self.trust_kernel.record_proposal_outcome(
            agent_id=p["agent_id"],
            proposal_id=pid,
            status=new_status,
            verdict="HUMAN_APPROVED" if new_status == "approved" else "HUMAN_DENIED",
            skill=p["skill"],
            lane="orchestration",
        )
        self._sync_agent_trust(p["agent_id"], snapshot.trust)
        self._log_vap("approve", {"id": pid, "decision": decision, "by": approver})
        return {
            "proposal_id": pid,
            "status": new_status,
            "approved_by": approver,
            "trust_snapshot": snapshot.to_dict(),
        }

    def get_trust(self, agent_id: str, lane: str = "general") -> dict:
        row = self.conn.execute("SELECT * FROM agents WHERE id=?", (agent_id,)).fetchone()
        if not row:
            return {"error": "agent_not_found", "agent_id": agent_id}
        snapshot = self.trust_kernel.get_snapshot(agent_id, lane)
        return {
            "agent": agent_id, "lane": snapshot.lane,
            "raw": snapshot.latest_score if snapshot.latest_score is not None else 0.0,
            "scaled": round(snapshot.trust, 3),
            "finding": snapshot.finding_state.upper(),
            "state": row["state"], "kill_switch": bool(row["kill_switch"]),
            "resource_used": row["resource_used"], "resource_quota": row["resource_quota"],
            "last_heartbeat": row["last_heartbeat"],
            "trust_snapshot": snapshot.to_dict(),
            "source": "canonical_trust_kernel",
        }

    def quarantine_agent(self, agent_id: str, reason: str) -> dict:
        self.conn.execute("UPDATE agents SET state='quarantined' WHERE id=?", (agent_id,))
        self.conn.commit()
        self._log_vap("quarantine", {"agent_id": agent_id, "reason": reason})
        if self._defcon_level > 3:
            self.set_defcon(3, f"Auto-escalated: {agent_id} quarantined", "system")
        return {"agent_id": agent_id, "action": "QUARANTINED", "reason": reason}

    def kill_switch(self, agent_id: str, reason: str) -> dict:
        self.conn.execute("UPDATE agents SET state='killed', kill_switch=1, trust_score=0 WHERE id=?",
                          (agent_id,))
        self.conn.commit()
        self._log_vap("kill_switch", {"agent_id": agent_id, "reason": reason})
        return {"agent_id": agent_id, "action": "KILL_SWITCH_ACTIVATED", "reason": reason}

    def record_task_result(
        self,
        task_id: str,
        agent_id: str,
        status: str,
        error: str = "",
        lane: str = "implementation",
    ) -> dict:
        success = status in {"completed", "success", "ok"}
        snapshot = self.trust_kernel.record_task_outcome(
            agent_id=agent_id,
            task_id=task_id,
            success=success,
            lane=lane,
            error=error or None,
            source="governance_rest",
        )
        self._sync_agent_trust(agent_id, snapshot.trust)
        return snapshot.to_dict()

    def heartbeat(self, agent_id: str) -> dict:
        row = self.conn.execute("SELECT * FROM agents WHERE id=?", (agent_id,)).fetchone()
        if not row:
            self.conn.execute("INSERT INTO agents (id, state) VALUES (?, 'active')", (agent_id,))
            self.conn.commit()
            return {"status": "ALIVE", "agent_id": agent_id}
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute("UPDATE agents SET last_heartbeat=?, resource_used=resource_used+1 WHERE id=?",
                          (now, agent_id))
        self.conn.commit()
        state = row["state"]
        if row["kill_switch"]:
            return {"status": "KILLED", "agent_id": agent_id}
        if state == "quarantined":
            return {"status": "QUARANTINED", "agent_id": agent_id}
        deny_count = self.conn.execute(
            "SELECT COUNT(*) as c FROM proposals WHERE agent_id=? AND status='denied'",
            (agent_id,)).fetchone()["c"]
        if deny_count >= 3:
            self.conn.execute("UPDATE agents SET state='circuit_broken' WHERE id=?", (agent_id,))
            self.conn.commit()
            return {"status": "CIRCUIT_BROKEN", "agent_id": agent_id, "reason": f"{deny_count} denials"}
        return {"status": "ALIVE", "agent_id": agent_id}

    def set_defcon(self, level: int, reason: str, set_by: str = "manual") -> dict:
        self._defcon_level = max(1, min(5, level))
        self.conn.execute("INSERT INTO defcon_log (ts, level, reason, set_by) VALUES (?,?,?,?)",
                          (datetime.now(timezone.utc).isoformat(), self._defcon_level, reason, set_by))
        self.conn.commit()
        labels = {1: "LOCKDOWN", 2: "HIGH ALERT", 3: "ELEVATED", 4: "GUIDED", 5: "NORMAL"}
        return {"level": self._defcon_level, "label": labels[self._defcon_level],
                "reason": reason, "set_by": set_by}

    def get_vault_status(self) -> dict:
        total = self.conn.execute("SELECT COUNT(*) as c FROM proposals").fetchone()["c"]
        statuses = {}
        for s in ["pending", "approved", "denied", "needs_review"]:
            statuses[s] = self.conn.execute("SELECT COUNT(*) as c FROM proposals WHERE status=?", (s,)).fetchone()["c"]
        agents = self.conn.execute("SELECT id, state, kill_switch FROM agents").fetchall()
        agent_breakdown = {"active": 0, "quarantined": 0, "circuit_broken": 0, "killed": 0}
        for a in agents:
            if a["kill_switch"]: agent_breakdown["killed"] += 1
            else: agent_breakdown[a["state"]] = agent_breakdown.get(a["state"], 0) + 1
        vap_count = self.conn.execute("SELECT COUNT(*) as c FROM vap_log").fetchone()["c"]
        chain_valid = self._verify_chain()
        labels = {1: "LOCKDOWN", 2: "HIGH ALERT", 3: "ELEVATED", 4: "GUIDED", 5: "NORMAL"}
        return {
            "defcon_level": self._defcon_level, "defcon_label": labels[self._defcon_level],
            "total_proposals": total, "proposal_breakdown": statuses,
            "total_agents": len(agents), "agent_breakdown": agent_breakdown,
            "vap_entries": vap_count, "chain_integrity": {"valid": chain_valid, "entries": vap_count},
            "trust_source": "canonical_trust_kernel",
        }

    def _verify_chain(self) -> bool:
        rows = self.conn.execute("SELECT hash, prev_hash FROM vap_log ORDER BY id").fetchall()
        prev = "0" * 16
        for r in rows:
            if r["prev_hash"] != prev:
                return False
            prev = r["hash"]
        return True

    def list_proposals(self, status: Optional[str] = None) -> list:
        if status:
            rows = self.conn.execute("SELECT * FROM proposals WHERE status=? ORDER BY timestamp DESC", (status,))
        else:
            rows = self.conn.execute("SELECT * FROM proposals ORDER BY timestamp DESC")
        return [dict(r) for r in rows]

    def _sync_agent_trust(self, agent_id: str, trust: float) -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO agents (id, trust_score, state) VALUES (?, ?, ?)",
            (agent_id, trust, "active"),
        )
        self.conn.execute("UPDATE agents SET trust_score=? WHERE id=?", (trust, agent_id))
        self.conn.commit()

    def close(self):
        self.conn.close()

class MCPServer:
    """Stdio-transport MCP server — compat with Claude Desktop, Cursor, Windsurf."""

    def __init__(self, engine: Optional[NexusGovernanceMCP] = None):
        self.engine = engine or NexusGovernanceMCP()
        self.tools = self._build_tools()
        self.resources = self._build_resources()

    def _build_tools(self) -> list:
        return [
            {"name": "nexus_propose_skill", "description": "Submit a skill proposal for governance review. Returns proposal with status and verdict.",
             "inputSchema": {"type": "object", "properties": {
                 "skill": {"type": "string", "description": "Skill name e.g. vault.store, model.delete"},
                 "params": {"type": "object", "description": "Skill parameters"},
                 "agent_id": {"type": "string"}, "provenance": {"type": "string"}},
                 "required": ["skill", "agent_id"]}},
            {"name": "nexus_approve_proposal", "description": "Approve or deny a pending proposal.",
             "inputSchema": {"type": "object", "properties": {
                 "proposal_id": {"type": "string"}, "approver": {"type": "string"},
                 "decision": {"type": "string", "enum": ["approve", "deny"]}},
                 "required": ["proposal_id", "approver", "decision"]}},
            {"name": "nexus_get_trust", "description": "Get trust score for an agent in a specific lane.",
             "inputSchema": {"type": "object", "properties": {
                 "agent_id": {"type": "string"},
                 "lane": {"type": "string", "enum": list(LANE_PARAMS.keys())}},
                 "required": ["agent_id"]}},
            {"name": "nexus_quarantine_agent", "description": "ARMED: Quarantine a rogue agent. Auto-escalates DEFCON.",
             "inputSchema": {"type": "object", "properties": {
                 "agent_id": {"type": "string"}, "reason": {"type": "string"}},
                 "required": ["agent_id", "reason"]}},
            {"name": "nexus_kill_switch", "description": "ARMED: Activate kill switch. Immediate quarantine + skill revocation.",
             "inputSchema": {"type": "object", "properties": {
                 "agent_id": {"type": "string"}, "reason": {"type": "string"}},
                 "required": ["agent_id", "reason"]}},
            {"name": "nexus_heartbeat", "description": "Agent heartbeat. Returns ALIVE/KILLED/QUARANTINED/CIRCUIT_BROKEN.",
             "inputSchema": {"type": "object", "properties": {"agent_id": {"type": "string"}},
                 "required": ["agent_id"]}},
            {"name": "nexus_set_defcon", "description": "Set DEFCON level. 1=LOCKDOWN, 5=NORMAL.",
             "inputSchema": {"type": "object", "properties": {
                 "level": {"type": "integer", "minimum": 1, "maximum": 5},
                 "reason": {"type": "string"}, "set_by": {"type": "string"}},
                 "required": ["level", "reason"]}},
            {"name": "nexus_get_vault_status", "description": "Full vault status: DEFCON, proposals, agents, chain integrity.",
             "inputSchema": {"type": "object", "properties": {}}},
            {"name": "nexus_list_proposals", "description": "List proposals, optionally filtered by status.",
             "inputSchema": {"type": "object", "properties": {"status": {"type": "string"}}}},
        ]

    def _build_resources(self) -> list:
        return [
            {"uri": "nexus://governance/log", "name": "VAP Chain of Custody",
             "description": "Tamper-evident audit log with hash chaining", "mimeType": "application/jsonl"},
            {"uri": "nexus://governance/vault", "name": "Nexus Vault Status",
             "description": "Real-time vault state with DEFCON", "mimeType": "application/json"},
        ]

    def _send(self, data: dict):
        sys.stdout.write(f"data: {json.dumps(data)}\n\n")
        sys.stdout.flush()

    def _read_line(self) -> Optional[str]:
        line = sys.stdin.readline()
        return line[6:].strip() if line and line.startswith("data: ") else None

    def run(self):
        self._send({"jsonrpc": "2.0", "id": 0, "result": {
            "protocolVersion": "2024-11-05",
            "serverInfo": {"name": "nexus-governance-mcp", "version": "2.0.0-ARMED"},
            "capabilities": {"tools": {}, "resources": {}, "prompts": {}}}})
        while True:
            msg = self._read_line()
            if not msg:
                break
            try:
                req = json.loads(msg)
                method = req.get("method")
                params = req.get("params", {})
                req_id = req.get("id")
                if method == "initialize":
                    self._send({"jsonrpc": "2.0", "id": req_id, "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {"listChanged": False}, "resources": {"listChanged": False}, "prompts": {"listChanged": False}},
                        "serverInfo": {"name": "nexus-governance-mcp", "version": "2.0.0-ARMED"}}})
                elif method == "tools/list":
                    self._send({"jsonrpc": "2.0", "id": req_id, "result": {"tools": self.tools}})
                elif method == "resources/list":
                    self._send({"jsonrpc": "2.0", "id": req_id, "result": {"resources": self.resources}})
                elif method == "tools/call":
                    name = params.get("name")
                    args = params.get("arguments", {})
                    engine = self.engine
                    try:
                        if name == "nexus_propose_skill":
                            result = engine.propose_skill(args["skill"], args.get("params", {}), args["agent_id"], args.get("provenance", "mcp"))
                        elif name == "nexus_approve_proposal":
                            result = engine.approve_proposal(args["proposal_id"], args["approver"], args["decision"])
                        elif name == "nexus_get_trust":
                            result = engine.get_trust(args["agent_id"], args.get("lane", "general"))
                        elif name == "nexus_quarantine_agent":
                            result = engine.quarantine_agent(args["agent_id"], args["reason"])
                        elif name == "nexus_kill_switch":
                            result = engine.kill_switch(args["agent_id"], args["reason"])
                        elif name == "nexus_heartbeat":
                            result = engine.heartbeat(args["agent_id"])
                        elif name == "nexus_set_defcon":
                            result = engine.set_defcon(args["level"], args["reason"], args.get("set_by", "manual"))
                        elif name == "nexus_get_vault_status":
                            result = engine.get_vault_status()
                        elif name == "nexus_list_proposals":
                            result = {"proposals": engine.list_proposals(args.get("status"))}
                        else:
                            result = {"error": f"Unknown tool: {name}"}
                    except Exception as e:
                        result = {"error": str(e)}
                    self._send({"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": json.dumps(result)}]}})
                elif method == "resources/read":
                    uri = params.get("uri")
                    if uri == "nexus://governance/log":
                        rows = self.engine.conn.execute("SELECT ts,type,data,hash,prev_hash FROM vap_log ORDER BY id").fetchall()
                        content = "\n".join(json.dumps(dict(r)) for r in rows)
                        self._send({"jsonrpc": "2.0", "id": req_id, "result": {"contents": [{"uri": uri, "mimeType": "application/jsonl", "text": content}]}})
                    elif uri == "nexus://governance/vault":
                        vs = self.engine.get_vault_status()
                        self._send({"jsonrpc": "2.0", "id": req_id, "result": {"contents": [{"uri": uri, "mimeType": "application/json", "text": json.dumps(vs)}]}})
                    else:
                        self._send({"jsonrpc": "2.0", "id": req_id, "error": {"code": -32602, "message": "Not found"}})
            except json.JSONDecodeError:
                continue
            except Exception as e:
                self._send({"jsonrpc": "2.0", "id": req_id, "error": {"code": -32603, "message": str(e)}})

if __name__ == "__main__":
    server = MCPServer()
    server.run()
