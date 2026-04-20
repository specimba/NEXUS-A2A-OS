# NEXUS OS — Heartbeat Protocol

Heartbeats keep NEXUS OS sub-agents alive, tracked, and governed between sessions.

## Heartbeat File Schema
```
/home/.z/workspaces/con_<id>/heartbeat.json
```

Fields:
- `agent_id`: unique agent identifier
- `parent_id`: orchestrator instance that spawned this agent
- `domain`: current Domain (CODE, REASON, RESEARCH, FAST, SEC)
- `task`: current task description
- `status`: IDLE | ACTIVE | WAIT | DONE | ERR
- `tokens_used`: running token count
- `tokens_budget`: per-session budget
- `checkpoint`: last completed checkpoint
- `heartbeat_at`: ISO timestamp of last beat
- `spawned_at`: ISO timestamp of spawn time
- `spawn_via`: GMR model used for spawn (endpoint name)

## Heartbeat Interval Rules

| Status | Interval | Action |
|--------|----------|--------|
| IDLE | 60s | Check in, resume if task queued |
| ACTIVE | 30s | Log token delta, check budget |
| WAIT | 120s | Poll parent for signal |
| DONE | — | Write final Vault record, stop |
| ERR | — | Log to Monitor, escalate to Governor |

## Token Budget Enforcement (per heartbeat)
```python
def on_heartbeat(agent_id):
    usage = get_usage()
    if usage["remaining"] < 5000:
        Governor().check("abort", agent_id)
        Vault().store(agent_id, Track.FAIL, "budget", "token_exhaustion", ...)
    elif usage["remaining"] < 15000:
        Governor().check("throttle", agent_id)
```

## Spawn Heartbeat on Sub-Agent
```python
import json, time
from pathlib import Path
from datetime import datetime

def spawn_heartbeat(agent_id, domain, task, spawn_via, parent_id):
    hb = {
        "agent_id": agent_id,
        "parent_id": parent_id,
        "domain": domain,
        "task": task,
        "status": "ACTIVE",
        "tokens_used": 0,
        "tokens_budget": 100000,
        "checkpoint": 0,
        "heartbeat_at": datetime.now().isoformat(),
        "spawned_at": datetime.now().isoformat(),
        "spawn_via": spawn_via,
    }
    path = Path(f"/home/.z/workspaces/con_<id>/heartbeat.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(hb, indent=2))
    return hb
```

## Monitor Integration
- `TokenTracker` writes to heartbeat on every API call
- `TokenGuard` blocks new tool calls when `tokens_remaining < budget * 0.1`
- Governor evaluates on every WAIT→ACTIVE transition

## Health Check (from orchestrator)
```bash
for hb in /home/.z/workspaces/*/heartbeat.json; do
  age=$(($(date +%s) - $(date -d $(jq -r .heartbeat_at $hb) +%s)))
  status=$(jq -r .status $hb)
  if [ $age -gt 300 ] && [ "$status" == "ACTIVE" ]; then
    echo "STALE: $(jq -r .agent_id $hb)"
  fi
done
```

## Graceful Shutdown
```python
def shutdown(agent_id):
    usage = get_usage()
    Vault().store(agent_id, Track.EVENT, "shutdown", "final_tokens", usage)
    hb_write(agent_id, "status", "DONE")
    end_tracking()
```
